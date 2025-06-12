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
    -9999: "partlycloudy",
    -8: "partlycloudy",
    -7: "snowy",
    -6: "pouring",
    -5: "snowy-rainy",
    -4: "fog",
    -3: "snowy",
    -2: "rainy",
    -1: "rainy",
    0: "sunny",
    1: "sunny",
    2: "partlycloudy",
    3: "partlycloudy",
    4: "partlycloudy",
    5: "cloudy",
    6: "cloudy",
    7: "cloudy",
    8: "cloudy",
    9: "cloudy",
    10: "fog",
    11: "fog",
    12: "fog",
    13: "lightning",
    14: "rainy",
    15: "rainy",
    16: "rainy",
    17: "lightning",
    18: "windy",
    20: "rainy",
    21: "rainy",
    22: "snowy",
    23: "snowy-rainy",
    24: "snowy-rainy",
    25: "rainy",
    26: "snowy",
    27: "snowy-rainy",
    29: "lightning-rainy",
    31: "windy",
    36: "snowy",
    37: "snowy",
    38: "snowy",
    39: "snowy",
    40: "fog",
    41: "fog",
    42: "fog",
    43: "fog",
    44: "fog",
    45: "fog",
    46: "fog",
    47: "fog",
    48: "fog",
    49: "fog",
    50: "rainy",
    51: "rainy",
    52: "rainy",
    53: "rainy",
    54: "rainy",
    55: "rainy",
    56: "snowy-rainy",
    57: "snowy-rainy",
    58: "rainy",
    59: "rainy",
    60: "rainy",
    61: "rainy",
    62: "rainy",
    63: "rainy",
    64: "rainy",
    65: "rainy",
    66: "snowy-rainy",
    67: "snowy-rainy",
    68: "snowy-rainy",
    69: "snowy-rainy",
    70: "snowy",
    71: "snowy",
    72: "snowy",
    73: "snowy",
    74: "snowy",
    75: "snowy",
    76: "snowy",
    77: "snowy",
    78: "snowy",
    79: "snowy",
    80: "rainy",
    81: "rainy",
    82: "rainy",
    83: "snowy-rainy",
    84: "snowy-rainy",
    85: "snowy",
    86: "snowy",
    87: "hail",
    88: "hail",
    89: "hail",
    90: "hail",
    91: "lightning",
    92: "lightning",
    93: "lightning-rainy",
    94: "lightning-rainy",
    95: "lightning-rainy",
    96: "exceptional",
    97: "lightning-rainy",
    98: "lightning-rainy",
    99: "exceptional",
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
