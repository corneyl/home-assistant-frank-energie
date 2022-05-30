from __future__ import annotations, annotations

from datetime import timedelta
import logging
from typing import Union

from homeassistant.core import HassJob
from homeassistant.helpers import event
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import utcnow
from .const import ATTRIBUTION, FrankEnergieBinaryEntityDescription, \
    FrankEnergieEntityDescription, ICON
from .coordinator import FrankEnergieCoordinator

_LOGGER = logging.getLogger(__name__)


class FrankEnergieSensorBase(CoordinatorEntity):
    """Representation of a Frank Energie sensor."""

    _attr_attribution = ATTRIBUTION
    _attr_icon = ICON

    def __init__(self, coordinator: FrankEnergieCoordinator,
                 description: Union[FrankEnergieEntityDescription, FrankEnergieBinaryEntityDescription]) -> None:
        """Initialize the sensor."""
        self.entity_description: Union[FrankEnergieEntityDescription, FrankEnergieBinaryEntityDescription] = description
        self._attr_unique_id = f"frank_energie.{description.key}"

        self._update_job = HassJob(self.async_schedule_update_ha_state)
        self._unsub_update = None

        super().__init__(coordinator)

    def schedule_update(self):
        # Cancel the currently scheduled event if there is any
        if self._unsub_update:
            self._unsub_update()
            self._unsub_update = None

        # Schedule the next update at exactly the next whole hour sharp
        self._unsub_update = event.async_track_point_in_utc_time(
            self.hass,
            self._update_job,
            utcnow().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1),
        )
