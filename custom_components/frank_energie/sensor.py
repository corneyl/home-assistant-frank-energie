"""Frank Energie current electricity and gas price information service."""
from __future__ import annotations, annotations, annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import CONF_COORDINATOR, DOMAIN, SENSOR_TYPES
from .sensor_base import FrankEnergieSensorBase

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Frank Energie sensor entries."""
    frank_coordinator = hass.data[DOMAIN][config_entry.entry_id][CONF_COORDINATOR]

    # Add an entity for each sensor type
    async_add_entities(
        [
            FrankEnergieSensor(frank_coordinator, description)
            for description in SENSOR_TYPES
        ],
        True
    )


class FrankEnergieSensor(FrankEnergieSensorBase, SensorEntity):

    async def async_update(self) -> None:
        """Get the latest data and updates the states."""
        sensor_data = self.coordinator.processed_data()
        self._attr_native_value = self.entity_description.value_fn(sensor_data)
        self._attr_extra_state_attributes = self.entity_description.attr_fn(sensor_data) \
            if self.entity_description.attr_fn else None
        self.schedule_update()
