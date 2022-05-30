"""Frank Energie current electricity and gas price binary sensors."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import BINARY_SENSOR_TYPES, CONF_COORDINATOR, DOMAIN
from .sensor_base import FrankEnergieSensorBase


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Frank Energie binary_sensor entries."""
    frank_coordinator = hass.data[DOMAIN][config_entry.entry_id][CONF_COORDINATOR]

    # Add an entity for each sensor type
    async_add_entities(
        [
            FrankEnergieBinarySensor(frank_coordinator, description)
            for description in BINARY_SENSOR_TYPES
        ],
        True
    )


class FrankEnergieBinarySensor(FrankEnergieSensorBase, BinarySensorEntity):

    async def async_update(self) -> None:
        """Get the latest data and updates the states."""
        sensor_data = self.coordinator.processed_data()
        self._attr_is_on = self.entity_description.value_fn(sensor_data)
        self._attr_extra_state_attributes = self.entity_description.attr_fn(sensor_data) \
            if self.entity_description.attr_fn else None
        self.schedule_update()
