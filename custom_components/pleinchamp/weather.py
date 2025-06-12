"""Support for the Pleinchamp weather service."""

from datetime import datetime
import logging

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
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
    1: "sunny",                  # ClearSkies (jour)
    101: "clear-night",          # ClearSkies (nuit)

    2: "partlycloudy",           # PartlyCloudy (jour)
    102: "partlycloudy",         # PartlyCloudy (nuit)

    3: "partlycloudy",           # MainlyCloudy (jour)
    103: "partlycloudy",         # MainlyCloudy (nuit)

    4: "cloudy",                 # Overcast (jour)
    104: "cloudy",               # Overcast (nuit)

    5: "rainy",                  # Rain (jour)
    105: "rainy",                # Rain (nuit)

    6: "snowy-rainy",            # RainAndSnow (jour)
    106: "snowy-rainy",          # RainAndSnow (nuit)

    7: "snowy",                  # Snow (jour)
    107: "snowy",                # Snow (nuit)

    8: "rainy",                  # RainShower (jour)
    108: "rainy",                # RainShower (nuit)

    9: "snowy",                  # SnowShower (jour)
    109: "snowy",                # SnowShower (nuit)

    10: "snowy-rainy",           # RainAndSnowShower (jour)
    110: "snowy-rainy",          # RainAndSnowShower (nuit)

    11: "fog",                   # Mist (jour)
    111: "fog",                  # Mist (nuit)

    12: "fog",                   # Mist (jour)
    112: "fog",                  # Mist (nuit)

    13: "rainy",                 # FreezingRain (jour)
    113: "rainy",                # FreezingRain (nuit)

    14: "lightning",             # Thunderstorms (jour)
    114: "lightning",            # Thunderstorms (nuit)

    15: "rainy",                 # LightDrizzle (jour)
    115: "rainy",                # LightDrizzle (nuit)

    16: "exceptional",           # Sandstorm (jour)
    116: "exceptional",          # Sandstorm (nuit)
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

    forecast_type = hass.data[DOMAIN][entry.entry_id]["forecast_type"]
    if not forecast_type:
        return False

    weather_entity = PleinchampWeather(
        coordinator,
        entry.data,
        DEVICE_TYPE_WEATHER,
        forecast_coordinator,
        unit_system,
        forecast_type,
        entry,
    )

    async_add_entities([weather_entity], True)
    return True


class PleinchampWeather(PleinchampEntity, WeatherEntity):
    """Representation of a weather entity."""

    _attr_has_entity_name = True
    _attr_name = "Weather"
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR

    def __init__(
        self,
        coordinator,
        entries,
        device_type,
        forecast_coordinator,
        unit_system,
        forecast_type,
        entry,
    ) -> None:
        """Initialize the Pleinchamp weather entity."""
        super().__init__(coordinator, entries, device_type, forecast_coordinator, entry.entry_id)
        self._weather = None
        self._unit_system = unit_system
        self._forecast_type = forecast_type

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
    def forecast(self):
        """Return the forecast data."""
        forecasts = []

        # TODO : Il en manque (https://api.prod.pleinchamp.com/forecasts-15d?latitude=47.53&longitude=1.41)
        #  ex : maxWindGustAt2m

        # forecast_coordinator.data doit être un dict comme {"1": {...}, "2": {...}}
        for day_str, day_data in sorted(self.forecast_coordinator.data.items(), key=lambda x: int(x[0])):
            forecast = {
                "datetime": dt_util.parse_datetime(day_data["date"]),
                "condition": CONDITION_MAP.get(day_data.get("weatherCode"), None),
                "humidity": day_data.get("relativeHumidity"),
                "temperature": day_data.get("maxAirTemperature"),
                "templow": day_data.get("minAirTemperature"),
                "precipitation": day_data.get("precipitationAmount"),
                "precipitation_probability": day_data.get("precipitationProbability"),
                "wind_speed": day_data.get("windSpeedAt2m"),
                "wind_bearing": day_data.get("windDirection", {}).get("degree") if isinstance(day_data.get("windDirection"), dict) else None,
            }
            forecasts.append(forecast)

        return forecasts

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units."""
        return self.forecast

    async def async_update(self) -> None:
        """Get the latest weather data."""
        self._weather = self.forecast_coordinator.data
        await self.async_update_listeners(("daily",))
