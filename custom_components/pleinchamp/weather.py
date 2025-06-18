"""Support for the Pleinchamp weather service."""

from datetime import datetime
import logging

from homeassistant.components.weather import (
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_HUMIDITY,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_NATIVE_DEW_POINT,
    ATTR_FORECAST_NATIVE_PRECIPITATION,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_NATIVE_WIND_SPEED,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_WEATHER_WIND_GUST_SPEED,
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_EXCEPTIONAL,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
    ATTR_CONDITION_WINDY_VARIANT,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfSpeed
from homeassistant.util import dt as dt_util
from homeassistant.core import HomeAssistant
from homeassistant.util.unit_system import METRIC_SYSTEM

from .const import (
    CONF_LOCATION_NAME,
    DEFAULT_LOCATION_NAME,
    DEVICE_TYPE_WEATHER,
    DOMAIN,
)
from .entity import PleinchampEntity

_LOGGER = logging.getLogger(__name__)

CONDITION_MAP = {
    1: ATTR_CONDITION_SUNNY,                  # ClearSkies (jour)
    101: ATTR_CONDITION_CLEAR_NIGHT,          # ClearSkies (nuit)

    2: ATTR_CONDITION_PARTLYCLOUDY,           # PartlyCloudy (jour)
    102: ATTR_CONDITION_PARTLYCLOUDY,         # PartlyCloudy (nuit)

    3: ATTR_CONDITION_PARTLYCLOUDY,           # MainlyCloudy (jour)
    103: ATTR_CONDITION_PARTLYCLOUDY,         # MainlyCloudy (nuit)

    4: ATTR_CONDITION_CLOUDY,                 # Overcast (jour)
    104: ATTR_CONDITION_CLOUDY,               # Overcast (nuit)

    5: ATTR_CONDITION_RAINY,                  # Rain (jour)
    105: ATTR_CONDITION_RAINY,                # Rain (nuit)

    6: ATTR_CONDITION_SNOWY_RAINY,            # RainAndSnow (jour)
    106: ATTR_CONDITION_SNOWY_RAINY,          # RainAndSnow (nuit)

    7: ATTR_CONDITION_SNOWY,                  # Snow (jour)
    107: ATTR_CONDITION_SNOWY,                # Snow (nuit)

    8: ATTR_CONDITION_RAINY,                  # RainShower (jour)
    108: ATTR_CONDITION_RAINY,                # RainShower (nuit)

    9: ATTR_CONDITION_SNOWY,                  # SnowShower (jour)
    109: ATTR_CONDITION_SNOWY,                # SnowShower (nuit)

    10: ATTR_CONDITION_SNOWY_RAINY,           # RainAndSnowShower (jour)
    110: ATTR_CONDITION_SNOWY_RAINY,          # RainAndSnowShower (nuit)

    11: ATTR_CONDITION_FOG,                   # Mist (jour)
    111: ATTR_CONDITION_FOG,                  # Mist (nuit)

    12: ATTR_CONDITION_FOG,                   # Mist (jour)
    112: ATTR_CONDITION_FOG,                  # Mist (nuit)

    13: ATTR_CONDITION_RAINY,                 # FreezingRain (jour)
    113: ATTR_CONDITION_RAINY,                # FreezingRain (nuit)

    14: ATTR_CONDITION_LIGHTNING,             # Thunderstorms (jour)
    114: ATTR_CONDITION_LIGHTNING,            # Thunderstorms (nuit)

    15: ATTR_CONDITION_RAINY,                 # LightDrizzle (jour)
    115: ATTR_CONDITION_RAINY,                # LightDrizzle (nuit)

    16: ATTR_CONDITION_EXCEPTIONAL,           # Sandstorm (jour)
    116: ATTR_CONDITION_EXCEPTIONAL,          # Sandstorm (nuit)
}



async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up the Pleinchamp weather platform."""
    _LOGGER.info("Set up Pleinchamp weather platform")

    unit_system = "metric" if hass.config.units is METRIC_SYSTEM else "imperial"

    forecast_coordinator = hass.data[DOMAIN][entry.entry_id]["forecast"]
    if not forecast_coordinator.data:
        return False

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    if not coordinator.data:
        return False

    weather_entity = PleinchampWeather(
        coordinator,
        entry.data,
        DEVICE_TYPE_WEATHER,
        forecast_coordinator,
        unit_system,
        entry,
    )

    async_add_entities([weather_entity], True)
    return True


class PleinchampWeather(PleinchampEntity, WeatherEntity):
    """Representation of a weather entity."""

    _attr_has_entity_name = True
    _attr_name = "Weather"
    _attr_supported_features = (WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY)
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR

    def __init__(
        self,
        coordinator,
        entries,
        device_type,
        forecast_coordinator,
        unit_system,
        entry,
    ) -> None:
        """Initialize the Pleinchamp weather entity."""
        super().__init__(coordinator, entries, device_type, forecast_coordinator, entry.entry_id)
        self._weather = None
        self._unit_system = unit_system

        self._location_name = entries.get(CONF_LOCATION_NAME, DEFAULT_LOCATION_NAME)
        self._attr_unique_id = f"{entry.entry_id}_{DOMAIN.lower()}"
        self._attr_name  = f"{DOMAIN.capitalize()} {self._location_name}"

    @property
    def native_temperature(self):
        return self._current.get("airTemperature")

    @property
    def humidity(self):
        return self._current.get("relativeHumidity")

    @property
    def native_wind_speed(self):
        return self._current.get("windSpeedAt2m")

    @property
    def wind_bearing(self):
        wind_dir = self._current.get("windDirection")
        if isinstance(wind_dir, dict):
            return wind_dir.get("degree")
        return wind_dir

    @property
    def condition(self):
        code = self._current.get("weatherCode")
        return CONDITION_MAP.get(code, code)

    @property
    def daily_forecast(self):
        """Return the forecast data."""
        forecasts = []

        daily_data = self.forecast_coordinator.data.get("daily", {})
        # daily_data doit être un dict comme {"1": {...}, "2": {...}}
        for day_str, day_data in sorted(daily_data.items(), key=lambda x: int(x[0])):
            forecast = {
                ATTR_FORECAST_TIME: dt_util.parse_datetime(day_data["date"]),
                ATTR_FORECAST_CONDITION: CONDITION_MAP.get(day_data.get("weatherCode"), None),
                ATTR_FORECAST_HUMIDITY: day_data.get("relativeHumidity"),
                ATTR_FORECAST_NATIVE_TEMP: day_data.get("maxAirTemperature"),
                ATTR_FORECAST_NATIVE_TEMP_LOW: day_data.get("minAirTemperature"),
                ATTR_FORECAST_NATIVE_PRECIPITATION: day_data.get("precipitationAmount"),
                ATTR_FORECAST_PRECIPITATION_PROBABILITY: day_data.get("precipitationProbability"),
                ATTR_FORECAST_NATIVE_WIND_SPEED: day_data.get("windSpeedAt2m"),
                ATTR_FORECAST_WIND_BEARING: day_data.get("windDirection", {}).get("degree") if isinstance(day_data.get("windDirection"), dict) else None,
                ATTR_WEATHER_WIND_GUST_SPEED: day_data.get("maxWindGustAt2m"),
            }
            forecasts.append(forecast)

        return forecasts

    @property
    def hourly_forecast(self):
        """Return the forecast data."""
        forecasts = []

        hourly_data = self.forecast_coordinator.data.get("hourly", {})
        # hourly_data doit être un dict comme {"1": {...}, "2": {...}}
        for hour_str, hour_data in sorted(hourly_data.items(), key=lambda x: datetime.strptime(x[0], "%Y-%m-%d-%H")):
            forecast = {
                ATTR_FORECAST_TIME: dt_util.parse_datetime(hour_data["datetime"]),
                ATTR_FORECAST_CONDITION: CONDITION_MAP.get(hour_data.get("weatherCode"), None),
                ATTR_FORECAST_HUMIDITY: hour_data.get("relativeHumidity"),
                ATTR_FORECAST_NATIVE_TEMP: hour_data.get("airTemperature"),
                ATTR_FORECAST_NATIVE_DEW_POINT: hour_data.get("dewPointTemperature"),
                ATTR_FORECAST_NATIVE_PRECIPITATION: hour_data.get("precipitationAmount"),
                ATTR_FORECAST_PRECIPITATION_PROBABILITY: hour_data.get("precipitationProbability"),
                ATTR_FORECAST_NATIVE_WIND_SPEED: hour_data.get("windSpeedAt2m"),
                ATTR_FORECAST_WIND_BEARING: hour_data.get("windDirection", {}).get("degree") if isinstance(hour_data.get("windDirection"), dict) else None,
                ATTR_WEATHER_WIND_GUST_SPEED: hour_data.get("maxWindGustAt2m"),
            }
            forecasts.append(forecast)

        return forecasts

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units."""
        return self.daily_forecast

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast in native units."""
        return self.hourly_forecast

    async def async_update(self) -> None:
        """Get the latest weather data."""
        self._weather = self.forecast_coordinator.data
        await self.async_update_listeners(("daily","hourly"))
