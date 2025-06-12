import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta, timezone
from typing import Dict, List, TypedDict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_FORECAST_INTERVAL,
    CONF_FORECAST_TYPE,
    CONF_LOCATION_NAME,
    CONF_TIMEZONE_INFO,
    DEFAULT_FORECAST_INTERVAL,
    DEFAULT_FORECAST_TYPE,
    DEFAULT_LOCATION_NAME,
    DEFAULT_TIMEZONE_INFO,
    DOMAIN,
    PLEINCHAMP_PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    from .pleinchamp_api import Pleinchamp  # Hypothetical class wrapping all logic

    if not entry.options:
        options = entry.data.copy()
        for conf_key, default in [
            (CONF_FORECAST_INTERVAL, DEFAULT_FORECAST_INTERVAL),
            (CONF_FORECAST_TYPE, DEFAULT_FORECAST_TYPE),
            (CONF_LOCATION_NAME, DEFAULT_LOCATION_NAME),
            (CONF_TIMEZONE_INFO, DEFAULT_TIMEZONE_INFO),
        ]:
            options.setdefault(conf_key, default)
        hass.config_entries.async_update_entry(entry, options=options)

    session = async_get_clientsession(hass)

    pleinchamp = Pleinchamp(session, entry.options)

    await pleinchamp.initialize()

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_data",
        update_method=pleinchamp.get_current_forecast_data,
        update_interval=timedelta(minutes=entry.options.get(CONF_FORECAST_INTERVAL, DEFAULT_FORECAST_INTERVAL)),
    )
    await coordinator.async_config_entry_first_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    forecast_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_forecast",
        update_method=pleinchamp.get_daily_forecast_datas,
        update_interval=timedelta(minutes=entry.options.get(CONF_FORECAST_INTERVAL, DEFAULT_FORECAST_INTERVAL)),
    )
    await forecast_coordinator.async_config_entry_first_refresh()
    if not forecast_coordinator.last_update_success:
        raise ConfigEntryNotReady

    forecast_type = entry.options.get(CONF_FORECAST_TYPE, DEFAULT_FORECAST_TYPE)
    
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "forecast": forecast_coordinator,
        "client": pleinchamp,
        "forecast_type": forecast_type,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLEINCHAMP_PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = all(
        await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(entry, platform) for platform in PLEINCHAMP_PLATFORMS]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
