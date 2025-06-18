"""Base Entity definition for Pleinchamp Integration."""

from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.helpers.entity import Entity

from .const import (
    CONF_LOCATION_NAME,
    DEFAULT_ATTRIBUTION,
)

class PleinchampEntity(Entity):
    """Base class for Pleinchamp Entities."""

    def __init__(self, coordinator, entries, entity, forecast_coordinator, entry_id):
        """Initialize the Pleinchamp Entity."""
        super().__init__()
        self.coordinator = coordinator
        self.forecast_coordinator = forecast_coordinator
        self.entries = entries
        self._entity = entity
        self._entry_id = entry_id
        self._location_key = self.entries.get(CONF_LOCATION_NAME)

    @property
    def _current(self):
        """Return current data dictionary."""
        if self.coordinator is None or self.coordinator.data is None:
            return {}
        # On suppose que les données actuelles sont un dict simple
        return self.coordinator.data

    @property
    def _forecast(self, mode: str):
        """Return forecast data dict (jours indexés)."""
        if self.forecast_coordinator is None or self.forecast_coordinator.data is None:
            return {}
        # On suppose que forecast_coordinator.data est un dict indexé par jour ("1", "2", ...)
        return self.forecast_coordinator.data.get(mode, {})

    @property
    def available(self):
        """Return if entity is available."""
        # On vérifie que les deux coordinators ont des données valides
        return (
            self.coordinator is not None
            and self.coordinator.last_update_success
            and self.forecast_coordinator is not None
            and self.forecast_coordinator.last_update_success
        )

    @property
    def extra_state_attributes(self):
        """Return common attributes."""
        return {
            ATTR_ATTRIBUTION: DEFAULT_ATTRIBUTION,
            CONF_LOCATION_NAME: self._location_key,
        }

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        if self.coordinator is not None:
            self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
        if self.forecast_coordinator is not None:
            self.async_on_remove(self.forecast_coordinator.async_add_listener(self.async_write_ha_state))
