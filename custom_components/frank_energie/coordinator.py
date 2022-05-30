from __future__ import annotations

import asyncio
from datetime import date, timedelta
from enum import Enum
import logging
import math
from typing import List, Tuple

import aiohttp

from homeassistant.components.frank_energie.const import DATA_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt


class FrankEnergieCoordinator(DataUpdateCoordinator):
    """Get the latest data and update the states."""

    class PriceType(Enum):
        Electricity = 'electricity'
        Gas = 'gas'

    def __init__(self, hass: HomeAssistant, websession) -> None:
        """Initialize the data object."""
        self.hass = hass
        self.websession = websession

        logger = logging.getLogger(__name__)
        super().__init__(
            hass,
            logger,
            name="Frank Energie coordinator",
            update_interval=timedelta(minutes=15),
        )

    async def _async_update_data(self) -> dict:
        """Get the latest data from Frank Energie"""
        self.logger.debug("Fetching Frank Energie data")

        # We request data for today up until the day after tomorrow.
        # This is to ensure we always request all available data.
        today = date.today()
        tomorrow = today + timedelta(days=2)
        query_data = {
            "query": """
                query MarketPrices($startDate: Date!, $endDate: Date!) {
                     marketPricesElectricity(startDate: $startDate, endDate: $endDate) { 
                        from till marketPrice marketPriceTax sourcingMarkupPrice energyTaxPrice 
                     } 
                     marketPricesGas(startDate: $startDate, endDate: $endDate) { 
                        from till marketPrice marketPriceTax sourcingMarkupPrice energyTaxPrice 
                     } 
                }
            """,
            "variables": {"startDate": str(today), "endDate": str(tomorrow)},
            "operationName": "MarketPrices"
        }
        try:
            resp = await self.websession.post(DATA_URL, json=query_data)

            data = await resp.json()
            return {
                self.PriceType.Electricity: self.preprocess_price_data(data['data']['marketPricesElectricity']),
                self.PriceType.Gas: self.preprocess_price_data(data['data']['marketPricesGas']),
            }

        except (asyncio.TimeoutError, aiohttp.ClientError, KeyError) as error:
            raise UpdateFailed(f"Fetching energy data failed: {error}") from error

    @staticmethod
    def preprocess_price_data(price_data):
        for hour in price_data:
            hour['from'] = dt.parse_datetime(hour['from'])
            hour['till'] = dt.parse_datetime(hour['till'])
            hour['total'] = hour['marketPrice'] + hour['marketPriceTax'] \
                            + hour['sourcingMarkupPrice'] + hour['energyTaxPrice']

        return price_data

    def processed_data(self):
        return {
            'elec': self.get_current_hourprices(self.PriceType.Electricity),
            'gas': self.get_current_hourprices(self.PriceType.Gas),
            'today_elec': self.get_hourprices(self.PriceType.Electricity),
            'today_gas': self.get_hourprices(self.PriceType.Gas),
            'low_priced_period': self.next_low_priced_period()
        }

    def get_current_hourprices(self, price_type: PriceType) -> Tuple:
        for hour in self.data[price_type]:
            if hour['from'] < dt.utcnow() < hour['till']:
                return hour['marketPrice'], hour['marketPriceTax'], hour['sourcingMarkupPrice'], hour['energyTaxPrice']

    def get_hourprices(self, price_type: PriceType) -> List:
        return [hour['total'] for hour in self.data[price_type]]

    def prices_next_24h(self, price_type: PriceType):
        # Get prices for next 24h (including the current hour)
        datetime_in_24h = dt.now() + timedelta(hours=24)
        prices_data = self.data[price_type]
        return list(filter(lambda p: dt.now() < p['till'] and p['from'] < datetime_in_24h, prices_data))

    def next_low_priced_period(self):
        percentile = 10

        # Determine the threshold for a low price
        prices_next_24h = self.prices_next_24h(self.PriceType.Electricity)
        price_threshold = self.prices_percentile(prices_next_24h, percentile)['total']

        # Loop through the prices to select the first consecutive period below the threshold
        low_prices_period = []
        for price in prices_next_24h:
            # Keep track of all low-priced hours but break the loop as soon as it's over
            if price['total'] <= price_threshold:
                low_prices_period.append(price)
            if price['total'] > price_threshold and low_prices_period:
                break

        # Determine the from/till and avg price during the cheap period
        return {
            'from': low_prices_period[0]['from'],
            'till': low_prices_period[-1]['till'],
            'avgPrice': sum(i['total'] for i in low_prices_period) / len(low_prices_period)
        }

    @staticmethod
    def prices_percentile(data, percentile):
        n = len(data)
        p = n * percentile / 100
        return sorted(data, key=lambda x: x['total'])[int(math.floor(p))]
