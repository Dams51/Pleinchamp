"""Pleinchamp Integration for Home Assistant."""

import asyncio
import json, JSONDecodeError
from datetime import UTC, datetime, timedelta, timezone
from typing import TypedDict, Dict, List
import logging
import ForecastData, ForecastDataModel

from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_registry import async_migrate_entries
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    PLEINCHAMP_PLATFORMS,
    CONF_CONDITION_CALM_WEIGHT,
    CONF_CONDITION_CLOUDCOVER_HIGH_WEAKENING,
    CONF_CONDITION_CLOUDCOVER_LOW_WEAKENING,
    CONF_CONDITION_CLOUDCOVER_MEDIUM_WEAKENING,
    CONF_CONDITION_CLOUDCOVER_WEIGHT,
    CONF_CONDITION_FOG_WEIGHT,
    CONF_CONDITION_SEEING_WEIGHT,
    CONF_CONDITION_TRANSPARENCY_WEIGHT,
    CONF_EXPERIMENTAL_FEATURES,
    CONF_FORECAST_INTERVAL,
    CONF_FORECAST_TYPE,
    CONF_LATITUDE,
    CONF_LOCATION_NAME,
    CONF_LONGITUDE,
    CONF_TIMEZONE_INFO,
    DEFAULT_CONDITION_CALM_WEIGHT,
    DEFAULT_CONDITION_CLOUDCOVER_HIGH_WEAKENING,
    DEFAULT_CONDITION_CLOUDCOVER_LOW_WEAKENING,
    DEFAULT_CONDITION_CLOUDCOVER_MEDIUM_WEAKENING,
    DEFAULT_CONDITION_CLOUDCOVER_WEIGHT,
    DEFAULT_CONDITION_FOG_WEIGHT,
    DEFAULT_CONDITION_SEEING_WEIGHT,
    DEFAULT_CONDITION_TRANSPARENCY_WEIGHT,
    DEFAULT_EXPERIMENTAL_FEATURES,
    DEFAULT_FORECAST_INTERVAL,
    DEFAULT_LOCATION_NAME,
    DEFAULT_TIMEZONE_INFO,
    DEFAULT_FORECAST_TYPE,
    DEFAULT_CACHE_TIMEOUT,
    DEFAULT_TIMEOUT,
    BASE_URL_PLEINCHAMP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up configured Pleinchamp."""

    # We allow setup only through config flow type of config
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pleinchamp platforms as config entry."""

    _LOGGER.debug("Starting up")

    if (
        not entry.options
        or not entry.options.get(CONF_LATITUDE)
        or not entry.options.get(CONF_LONGITUDE)
        or entry.options.get(CONF_CONDITION_CLOUDCOVER_WEIGHT, None) is None
        or entry.options.get(CONF_CONDITION_FOG_WEIGHT, None) is None
        or entry.options.get(CONF_CONDITION_SEEING_WEIGHT, None) is None
        or entry.options.get(CONF_CONDITION_TRANSPARENCY_WEIGHT, None) is None
        or entry.options.get(CONF_EXPERIMENTAL_FEATURES, None) is None
    ):
        # Apparently 7Timer has problems with a longitude of 0 degrees so we're catching this
        hass.config_entries.async_update_entry(
            entry,
            options={
                CONF_FORECAST_INTERVAL: entry.data.get(CONF_FORECAST_INTERVAL, DEFAULT_FORECAST_INTERVAL),
                CONF_FORECAST_TYPE: entry.data.get(CONF_FORECAST_TYPE, DEFAULT_FORECAST_TYPE),
                CONF_LOCATION_NAME: entry.data.get(CONF_LOCATION_NAME, DEFAULT_LOCATION_NAME),
                CONF_LATITUDE: entry.data[CONF_LATITUDE],
                CONF_LONGITUDE: entry.data[CONF_LONGITUDE] if entry.data[CONF_LONGITUDE] != 0 else 0.000001,
                CONF_TIMEZONE_INFO: entry.data.get(CONF_TIMEZONE_INFO, DEFAULT_TIMEZONE_INFO),
                CONF_CONDITION_CLOUDCOVER_WEIGHT: entry.data.get(
                    CONF_CONDITION_CLOUDCOVER_WEIGHT,
                    DEFAULT_CONDITION_CLOUDCOVER_WEIGHT,
                ),
                CONF_CONDITION_CLOUDCOVER_HIGH_WEAKENING: entry.data.get(
                    CONF_CONDITION_CLOUDCOVER_HIGH_WEAKENING,
                    DEFAULT_CONDITION_CLOUDCOVER_HIGH_WEAKENING,
                ),
                CONF_CONDITION_CLOUDCOVER_MEDIUM_WEAKENING: entry.data.get(
                    CONF_CONDITION_CLOUDCOVER_MEDIUM_WEAKENING,
                    DEFAULT_CONDITION_CLOUDCOVER_MEDIUM_WEAKENING,
                ),
                CONF_CONDITION_CLOUDCOVER_LOW_WEAKENING: entry.data.get(
                    CONF_CONDITION_CLOUDCOVER_LOW_WEAKENING,
                    DEFAULT_CONDITION_CLOUDCOVER_LOW_WEAKENING,
                ),
                CONF_CONDITION_FOG_WEIGHT: entry.data.get(
                    CONF_CONDITION_FOG_WEIGHT,
                    DEFAULT_CONDITION_FOG_WEIGHT,
                ),
                CONF_CONDITION_SEEING_WEIGHT: entry.data.get(
                    CONF_CONDITION_SEEING_WEIGHT, DEFAULT_CONDITION_SEEING_WEIGHT
                ),
                CONF_CONDITION_TRANSPARENCY_WEIGHT: entry.data.get(
                    CONF_CONDITION_TRANSPARENCY_WEIGHT,
                    DEFAULT_CONDITION_TRANSPARENCY_WEIGHT,
                ),
                CONF_CONDITION_CALM_WEIGHT: entry.data.get(
                    CONF_CONDITION_CALM_WEIGHT,
                    DEFAULT_CONDITION_CALM_WEIGHT,
                ),
                CONF_EXPERIMENTAL_FEATURES: entry.data.get(
                    CONF_EXPERIMENTAL_FEATURES,
                    DEFAULT_EXPERIMENTAL_FEATURES,
                ),
            },
        )

    session = async_get_clientsession(hass)

    _LOGGER.debug("Options latitude %s", str(entry.options.get(CONF_LATITUDE)))
    _LOGGER.debug("Options longitude %s", str(entry.options.get(CONF_LONGITUDE)))
    _LOGGER.debug("Options timezone %s", str(entry.options.get(CONF_TIMEZONE_INFO)))
    _LOGGER.debug("Update interval %s", str(entry.options.get(CONF_FORECAST_INTERVAL)))
    _LOGGER.debug(
        "Options cloudcover_weight %s",
        str(entry.options.get(CONF_CONDITION_CLOUDCOVER_WEIGHT)),
    )
    _LOGGER.debug(
        "Options cloudcover_high_weakening %s",
        str(entry.options.get(CONF_CONDITION_CLOUDCOVER_HIGH_WEAKENING)),
    )
    _LOGGER.debug(
        "Options cloudcover_medium_weakening %s",
        str(entry.options.get(CONF_CONDITION_CLOUDCOVER_MEDIUM_WEAKENING)),
    )
    _LOGGER.debug(
        "Options cloudcover_low_weakening %s",
        str(entry.options.get(CONF_CONDITION_CLOUDCOVER_LOW_WEAKENING)),
    )
    _LOGGER.debug(
        "Options fog_weight %s",
        str(entry.options.get(CONF_CONDITION_FOG_WEIGHT)),
    )
    _LOGGER.debug("Options seeing_weight %s", str(entry.options.get(CONF_CONDITION_SEEING_WEIGHT)))
    _LOGGER.debug(
        "Options transparency_weight %s",
        str(entry.options.get(CONF_CONDITION_TRANSPARENCY_WEIGHT)),
    )
    _LOGGER.debug(
        "Options calm_weight %s",
        str(entry.options.get(CONF_CONDITION_CALM_WEIGHT)),
    )
    _LOGGER.debug("Experimental features %s", str(entry.options.get(CONF_EXPERIMENTAL_FEATURES)))

    astroweather = AstroWeather(
        session,
        latitude=entry.options.get(CONF_LATITUDE),
        longitude=entry.options.get(CONF_LONGITUDE),
        timezone_info=entry.options.get(CONF_TIMEZONE_INFO),
        cloudcover_weight=entry.options.get(CONF_CONDITION_CLOUDCOVER_WEIGHT),
        cloudcover_high_weakening=entry.options.get(CONF_CONDITION_CLOUDCOVER_HIGH_WEAKENING) / 100,
        cloudcover_medium_weakening=entry.options.get(CONF_CONDITION_CLOUDCOVER_MEDIUM_WEAKENING) / 100,
        cloudcover_low_weakening=entry.options.get(CONF_CONDITION_CLOUDCOVER_LOW_WEAKENING) / 100,
        fog_weight=entry.options.get(CONF_CONDITION_FOG_WEIGHT),
        seeing_weight=entry.options.get(CONF_CONDITION_SEEING_WEIGHT),
        transparency_weight=entry.options.get(CONF_CONDITION_TRANSPARENCY_WEIGHT),
        calm_weight=entry.options.get(CONF_CONDITION_CALM_WEIGHT),
        experimental_features=entry.options.get(CONF_EXPERIMENTAL_FEATURES),
    )
    _LOGGER.debug("Connected to Pleinchamp platform")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = astroweather

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=astroweather.get_location_data,
        update_interval=timedelta(minutes=entry.options.get(CONF_FORECAST_INTERVAL, DEFAULT_FORECAST_INTERVAL)),
    )
    await coordinator.async_config_entry_first_refresh()
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady
    _LOGGER.debug(
        "Data update coordinator created (update interval: %d)",
        entry.options.get(CONF_FORECAST_INTERVAL),
    )

    fcst_type = entry.options.get(CONF_FORECAST_TYPE, DEFAULT_FORECAST_TYPE)

    fcst_coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=get_forecast_data(fcst_type),
        update_interval=timedelta(minutes=entry.options.get(CONF_FORECAST_INTERVAL, DEFAULT_FORECAST_INTERVAL)),
    )
    await fcst_coordinator.async_config_entry_first_refresh()
    if not fcst_coordinator.last_update_success:
        raise ConfigEntryNotReady
    _LOGGER.debug(
        "Forecast update coordinator created (update interval: %d)",
        entry.options.get(CONF_FORECAST_INTERVAL),
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "fcst_coordinator": fcst_coordinator,
        "aw": astroweather,
        "fcst_type": fcst_type,
    }

    _LOGGER.debug("Forecast updated")

    # Set up all platforms for this device/entry.
    await hass.config_entries.async_forward_entry_setups(entry, PLEINCHAMP_PLATFORMS)

    if not entry.update_listeners:
        entry.add_update_listener(async_update_options)

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
    """Update options."""

    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry."""

    unload_ok = all(
        await asyncio.gather(
            *[hass.config_entries.async_forward_entry_unload(entry, component) for component in PLEINCHAMP_PLATFORMS]
        )
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def get_forecast_data(self, fcst_type) -> List[ForecastData]:
    """Returns Weather Forecast."""

    return await self._get_forecast_data(fcst_type, 5)

async def _get_forecast_data(self, forecast_type, hours_to_show) -> List[ForecastData]:
    """Return Forecast data for the Station."""

    # https://github.com/mawinkler/pyastroweatherio/blob/main/pyastroweatherio/client.py#L538

    cnv = ConversionFunctions()
    items = []

    await _retrieve_data_pleinchamp()
    now = datetime.now(UTC).replace(tzinfo=None)

    # Create items
    cnt = 0

    forecast_time = now.replace(minute=0, second=0, microsecond=0).replace(microsecond=0, tzinfo=timezone.utc)
    if self._test_datetime is not None:
        forecast_time = self._test_datetime.replace(minute=0, second=0, microsecond=0).replace(
            microsecond=0, tzinfo=timezone.utc
        )
    _LOGGER.debug("Forecast time: %s", str(forecast_time))

    # 7Timer: Search for start index
    seventimer_init = await cnv.anchor_timestamp(self._weather_data_seventimer_init)

    # Anchor timestamp
    init_ts = await cnv.anchor_timestamp(self._weather_data_seventimer_init)

    utc_to_local_diff = self._astro_routines.utc_to_local_diff()
    _LOGGER.debug("UTC to local diff: %s", str(utc_to_local_diff))

    if len(self._weather_data_metno) == 0:
        _LOGGER.error("Met.no data not available")
        return []

    last_forecast_time = forecast_time
    for metno_index, datapoint in enumerate(self._weather_data_metno):
        datapoint_time = datetime.strptime(datapoint.get("time"), "%Y-%m-%dT%H:%M:%SZ").replace(
            microsecond=0, tzinfo=timezone.utc
        )
        if forecast_time > datapoint_time:
            continue

        if datapoint_time - last_forecast_time > timedelta(hours=1):
            break

        last_forecast_time = datapoint_time
        details_metno = datapoint.get("data", {}).get("instant", {}).get("details")

        if not self._test_data(
            details_metno,
            [
                "air_pressure_at_sea_level",
                "air_temperature",
                "cloud_area_fraction",
                "cloud_area_fraction_high",
                "cloud_area_fraction_low",
                "cloud_area_fraction_medium",
                "dew_point_temperature",
                "fog_area_fraction",
                "relative_humidity",
                "ultraviolet_index_clear_sky",
                "wind_from_direction",
                "wind_speed",
            ],
        ):
            _LOGGER.error("Missing Met.no data")
            break

        details_seventimer = self._get_data_seventimer_timer(
            seventimer_init,
            datetime.strptime(datapoint.get("time"), "%Y-%m-%dT%H:%M:%SZ"),
        )
        details_metno_next_1_hours = self._weather_data_metno[metno_index].get("data", {}).get("next_1_hours")
        details_metno_next_6_hours = self._weather_data_metno[metno_index].get("data", {}).get("next_6_hours")

        # Break condition
        if details_metno_next_1_hours is None:
            # No more hourly data
            _LOGGER.debug(
                "No more hourly data at %s",
                self._weather_data_metno[metno_index].get("time", {}),
            )
            break
        if details_metno_next_6_hours is None:
            # No more 6-hourly data
            _LOGGER.debug(
                "No more 6-hourly data at %s",
                self._weather_data_metno[metno_index].get("time", {}),
            )
            break

        atmosphere_data = await self._get_atmosphere(details_seventimer, details_metno)

        td = TimeDataModel(
            {
                # seventimer_init is "init" of 7timer astro data
                "seventimer_init": init_ts,
                # seventimer_timepoint is "timepoint" of 7timer astro data and defines the data for init + timepoint
                "seventimer_timepoint": details_seventimer["timepoint"],
                # Forecast_time is the actual datetime for the forecast data onwards in UTC
                # Corresponds to "time" in met data
                "forecast_time": datetime.strptime(datapoint.get("time"), "%Y-%m-%dT%H:%M:%SZ").replace(
                    microsecond=0, tzinfo=timezone.utc
                ),  # timestamp
            }
        )

        try:
            time_data = TimeData(data=td)
        except TypeError as ve:
            _LOGGER.error(f"Failed to parse location data model data: {time_data}")
            _LOGGER.error(ve)

        item = ForecastDataModel(
            {
                # Time data
                "time_data": time_data,
                "hour": datetime.strptime(
                    datapoint.get("time"), "%Y-%m-%dT%H:%M:%SZ"
                ).hour,  # forecast_time.hour % 24,
                "condition_data": await self._get_condition(
                    details_metno,
                    details_metno_next_1_hours,
                    details_metno_next_6_hours,
                    atmosphere_data.seeing,
                    atmosphere_data.transparency,
                    atmosphere_data.lifted_index,
                ),
            }
        )

        try:
            items.append(ForecastData(data=item))
        except TypeError as ve:
            _LOGGER.error(f"Failed to parse forecast data: {item}")
            _LOGGER.error(ve)

        cnt += 1
        if cnt >= hours_to_show:
            break

    self._forecast_data = items

    _LOGGER.debug("Forceast Length: %s", str(len(items)))

    return items

_NOT_AVAILABLE = -9999

async def _retrieve_data_pleinchamp(self) -> None:
    """Retrieves current data from Pleinchamp."""

    if ((datetime.now() - self._weather_data_pleinchamp_timestamp).total_seconds()) > DEFAULT_CACHE_TIMEOUT:
        self._weather_data_pleinchamp_timestamp = datetime.now()
        _LOGGER.debug("Updating data from Pleinchamp")

        json_data_pleinchamp = await _async_request_pleinchamp()

        if json_data_pleinchamp != {}:
            self._weather_data_pleinchamp = json_data_pleinchamp
            self._weather_data_pleinchamp_init = json_data_pleinchamp.get("init")
        else:
            # Fake weather data if service is broken
            self._weather_data_pleinchamp = []
            for index in range(0, 20):
                self._weather_data_pleinchamp.append(
                    {
                        "timepoint": index * 3,
                        "seeing": _NOT_AVAILABLE,
                        "transparency": _NOT_AVAILABLE,
                        "lifted_index": _NOT_AVAILABLE,
                    }
                )
            self._weather_data_pleinchamp_init = datetime.now(UTC).replace(tzinfo=None).strftime("%Y%m%d%H")
    else:
        _LOGGER.debug("Using cached data for Pleinchamp")

async def _async_request_pleinchamp(self) -> Dict:
    """Make a request against the Pleinchamp API."""

    use_running_session = self._session and not self._session.closed

    if use_running_session:
        session = self._session
    else:
        session = ClientSession(timeout=ClientTimeout(total=DEFAULT_TIMEOUT))

    # BASE_URL_PLEINCHAMP = "https://api.prod.pleinchamp.com/forecasts-15d?latitude=XXXXXXXXXXXXX&longitude=YYYYYYYYYYYYY
    url = (
        str(f"{BASE_URL_PLEINCHAMP}")
        + "forecasts-15d?latitude="
        + str("%.1f" % round(self._location_data.latitude, 2))
        + "&longitude="
        + str("%.1f" % round(self._location_data.longitude, 2))
    )
    try:
        _LOGGER.debug(f"Query url: {url}")
        async with session.request("GET", url, ssl=False) as resp:
            resp.raise_for_status()
            plain = str(await resp.text()).replace("\n", " ")
            data = json.loads(plain)

            return data
    except JSONDecodeError as jsonerr:
        _LOGGER.error(f"JSON decode error, expecting value: {jsonerr}")
        return {}
    except asyncio.TimeoutError as tex:
        _LOGGER.error(f"Request to endpoint timed out: {tex}")
        return {}
    except ClientError as err:
        _LOGGER.error(f"Error requesting data: {err}")
        return {}

    finally:
        if not use_running_session:
            await session.close()

class ForecastDataModel(TypedDict):
    """Model for forecast data"""

    time_data: TimeData
    hour: int
    condition_data: ConditionData

class ForecastData:
    """A representation of day Based Forecast Pleinchamp Data."""

    def __init__(self, *, data: ForecastDataModel):
        self.time_data = data["time_data"]
        self.hour = data["hour"]
        self.condition_data = data["condition_data"]

    # #########################################################################
    # Time data
    # #########################################################################
    @property
    def seventimer_init(self) -> datetime:
        return self.time_data.seventimer_init

    @property
    def seventimer_timepoint(self) -> int:
        return self.time_data.seventimer_timepoint

    @property
    def forecast_time(self) -> datetime:
        return self.time_data.forecast_time

    # #########################################################################
    # Forecast data
    # #########################################################################
    @property
    def deep_sky_view(self) -> bool:
        """Return True if Deep Sky should be possible."""

        if self.condition_percentage <= DEEP_SKY_THRESHOLD:
            return True
        return False

    @property
    def condition_percentage(self) -> int:
        return self.condition_data.condition_percentage

    @property
    def cloudcover_percentage(self) -> int:
        return self.condition_data.cloudcover_percentage

    @property
    def cloudless_percentage(self) -> int:
        return self.condition_data.cloudless_percentage

    @property
    def cloud_area_fraction_percentage(self) -> int:
        return self.condition_data.cloud_area_fraction_percentage

    @property
    def cloud_area_fraction_high_percentage(self) -> int:
        return self.condition_data.cloud_area_fraction_high_percentage

    @property
    def cloud_area_fraction_medium_percentage(self) -> int:
        return self.condition_data.cloud_area_fraction_medium_percentage

    @property
    def cloud_area_fraction_low_percentage(self) -> int:
        return self.condition_data.cloud_area_fraction_low_percentage

    @property
    def fog_area_fraction_percentage(self) -> int:
        return self.condition_data.fog_area_fraction_percentage

    @property
    def fog2m_area_fraction_percentage(self) -> int:
        return self.condition_data.fog2m_area_fraction_percentage

    @property
    def seeing(self) -> float:
        return self.condition_data.seeing

    @property
    def seeing_percentage(self) -> int:
        return self.condition_data.seeing_percentage

    @property
    def transparency(self) -> float:
        return self.condition_data.transparency

    @property
    def transparency_percentage(self) -> int:
        return self.condition_data.transparency_percentage

    @property
    def lifted_index(self) -> float:
        return self.condition_data.lifted_index

    @property
    def calm_percentage(self) -> int:
        return self.condition_data.calm_percentage

    @property
    def wind10m_direction(self) -> str:
        return self.condition_data.wind10m_direction

    @property
    def wind10m_speed(self) -> float:
        return self.condition_data.wind10m_speed

    @property
    def temp2m(self) -> float:
        return self.condition_data.temp2m

    @property
    def rh2m(self) -> float:
        return self.condition_data.rh2m

    @property
    def dewpoint2m(self) -> float:
        return self.condition_data.dewpoint2m

    @property
    def weather(self) -> str:
        return self.condition_data.weather

    @property
    def weather6(self) -> str:
        return self.condition_data.weather6

    @property
    def precipitation_amount(self) -> float:
        return self.condition_data.precipitation_amount

    @property
    def precipitation_amount6(self) -> float:
        return self.condition_data.precipitation_amount6
