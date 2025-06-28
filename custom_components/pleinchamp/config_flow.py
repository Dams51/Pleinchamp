"""Config Flow to configure Pleinchamp Integration."""

import logging

import voluptuous as vol
from voluptuous.schema_builder import Schema

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_ELEVATION, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_LOCATION_NAME,
    CONF_FORECAST_INTERVAL,
    DEFAULT_FORECAST_INTERVAL,
    FORECAST_INTERVAL_MAX,
    FORECAST_INTERVAL_MIN,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _get_current_values(hass: HomeAssistant, data: ConfigType):
    """Return current values."""

    if CONF_LOCATION_NAME not in data:
        data[CONF_LOCATION_NAME] = hass.config.location_name
    if CONF_LATITUDE not in data:
        data[CONF_LATITUDE] = hass.config.latitude
    if CONF_LONGITUDE not in data:
        data[CONF_LONGITUDE] = hass.config.longitude
    if CONF_ELEVATION not in data:
        data[CONF_ELEVATION] = hass.config.elevation
    if CONF_FORECAST_INTERVAL not in data:
        data[CONF_FORECAST_INTERVAL] = DEFAULT_FORECAST_INTERVAL

    return data


def _get_config_data(hass: HomeAssistant, data: ConfigType, user_input: ConfigType) -> ConfigType:
    """Return config data."""

    data = _get_current_values(hass, data)
    return {
        CONF_LOCATION_NAME: user_input.get(
            CONF_LOCATION_NAME,
            data[CONF_LOCATION_NAME],
        ),
        CONF_LATITUDE: user_input.get(
            CONF_LATITUDE,
            data[CONF_LATITUDE],
        ),
        CONF_LONGITUDE: user_input.get(
            CONF_LONGITUDE,
            data[CONF_LONGITUDE],
        ),
        CONF_ELEVATION: user_input.get(
            CONF_ELEVATION,
            data[CONF_ELEVATION],
        ),
        CONF_FORECAST_INTERVAL: data.get(
            CONF_FORECAST_INTERVAL, 
            data[CONF_FORECAST_INTERVAL]
        ),
    }


def get_location_schema(hass: HomeAssistant, data: ConfigType) -> Schema:
    """Return the location schema."""

    return vol.Schema(
        {
            vol.Required(CONF_LOCATION_NAME, default=hass.config.location_name): vol.All(vol.Coerce(str)),
            vol.Required(CONF_LATITUDE, default=hass.config.latitude): vol.All(
                vol.Coerce(float), vol.Range(min=-89, max=89)
            ),
            vol.Required(CONF_LONGITUDE, default=hass.config.longitude): vol.All(
                vol.Coerce(float), vol.Range(min=-180, max=180)
            ),
            vol.Required(CONF_ELEVATION, default=hass.config.elevation): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=4000)
            ),
            vol.Required(CONF_FORECAST_INTERVAL, default=DEFAULT_FORECAST_INTERVAL): vol.All(
                vol.Coerce(int),
                vol.Range(min=FORECAST_INTERVAL_MIN, max=FORECAST_INTERVAL_MAX),
            ),
        }
    )


def _update_location_input(hass: HomeAssistant, data: ConfigType, location_input: ConfigType) -> None:
    """Update location data."""

    if location_input is not None:
        data[CONF_LOCATION_NAME] = location_input.get(CONF_LOCATION_NAME, hass.config.location_name)
        data[CONF_LATITUDE] = location_input.get(CONF_LATITUDE, hass.config.latitude)
        data[CONF_LONGITUDE] = location_input.get(CONF_LONGITUDE,hass.config.longitude)
        data[CONF_ELEVATION] = location_input.get(CONF_ELEVATION, hass.config.elevation)
        data[CONF_FORECAST_INTERVAL] = location_input.get(CONF_FORECAST_INTERVAL, DEFAULT_FORECAST_INTERVAL)


class PleinchampConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Pleinchamp config flow."""

    VERSION = 1
    MINOR_VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        """Init the ConfigFlow."""

        self.data: ConfigType = {}

    async def async_step_user(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""

        return await self.async_step_location(user_input=user_input)

    async def async_step_location(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""

        if user_input is not None:
            self.data = _get_config_data(self.hass, self.data, user_input=user_input)
            try:
                unique_id = f"{self.data[CONF_LOCATION_NAME]!s}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
            except AbortFlow as af:
                _LOGGER.error("Exception: %s", str(af))
                msg = f"Location {self.data[CONF_LOCATION_NAME]!s} is {af.reason.replace('_', ' ')}"
                return self.async_abort(reason=msg)
            else:
                return self.async_create_entry(title=self.data[CONF_LOCATION_NAME], data=self.data)

        _update_location_input(self.hass, data=self.data, location_input=user_input)

        return self.async_show_form(
            step_id="location",
            data_schema=get_location_schema(hass=self.hass, data=self.data),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""

        return PleinchampOptionsFlowHandler(config_entry)


class PleinchampOptionsFlowHandler(OptionsFlow):
    """Handle options."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize options flow."""

        self.entry = entry
        self.data: ConfigType = dict(self.entry.data.items())

    async def async_step_init(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Manage the options."""

        # return await self.async_step_location(user_input=user_input)
        return await self.async_step_calculation(calculation_input=user_input)

    async def async_step_location(self, user_input: ConfigType | None = None) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""

        if user_input is not None:
            self.data = _get_config_data(self.hass, self.data, user_input=user_input)

            self.hass.config_entries.async_update_entry(
                entry=self.entry,
                unique_id=f"{self.data[CONF_LOCATION_NAME]!s}",
                data=self.data,
            )

            return self.async_create_entry(title="", data={})

        # test
        _update_location_input(self.hass, data=self.data, location_input=user_input)

        return self.async_show_form(
            step_id="location",
            data_schema=get_location_schema(hass=self.hass, data=self.data),
        )
    