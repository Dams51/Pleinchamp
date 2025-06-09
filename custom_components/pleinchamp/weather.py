"""Support for the Pleinchamp weather service."""

from datetime import datetime
import logging

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
    WeatherCondition,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_CELSIUS, SPEED_KILOMETERS_PER_HOUR
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
    -9999: WeatherCondition.PARTLYCLOUDY,
    -8: WeatherCondition.PARTLYCLOUDY,
    -7: WeatherCondition.SNOWY,
    -6: WeatherCondition.POURING,
    -5: WeatherCondition.SNOWY_RAINY,
    -4: WeatherCondition.FOG,
    -3: WeatherCondition.SNOWY,
    -2: WeatherCondition.RAINY,
    -1: WeatherCondition.RAINY,
    0: WeatherCondition.SUNNY,
    1: WeatherCondition.SUNNY,
    2: WeatherCondition.PARTLYCLOUDY,
    3: WeatherCondition.PARTLYCLOUDY,
    4: WeatherCondition.PARTLYCLOUDY,
    5: WeatherCondition.CLOUDY,
    6: WeatherCondition.CLOUDY,
    7: WeatherCondition.CLOUDY,
    8: WeatherCondition.CLOUDY,
    9: WeatherCondition.CLOUDY,
    10: WeatherCondition.FOG,
    11: WeatherCondition.FOG,
    12: WeatherCondition.FOG,
    13: WeatherCondition.LIGHTNING,
    14: WeatherCondition.RAINY,
    15: WeatherCondition.RAINY,
    16: WeatherCondition.RAINY,
    17: WeatherCondition.LIGHTNING,
    18: WeatherCondition.WINDY,
    20: WeatherCondition.RAINY,
    21: WeatherCondition.RAINY,
    22: WeatherCondition.SNOWY,
    23: WeatherCondition.SNOWY_RAINY,
    24: WeatherCondition.SNOWY_RAINY,
    25: WeatherCondition.RAINY,
    26: WeatherCondition.SNOWY,
    27: WeatherCondition.SNOWY_RAINY,
    29: WeatherCondition.LIGHTNING_RAINY,
    31: WeatherCondition.WINDY,
    36: WeatherCondition.SNOWY,
    37: WeatherCondition.SNOWY,
    38: WeatherCondition.SNOWY,
    39: WeatherCondition.SNOWY,
    40: WeatherCondition.FOG,
    41: WeatherCondition.FOG,
    42: WeatherCondition.FOG,
    43: WeatherCondition.FOG,
    44: WeatherCondition.FOG,
    45: WeatherCondition.FOG,
    46: WeatherCondition.FOG,
    47: WeatherCondition.FOG,
    48: WeatherCondition.FOG,
    49: WeatherCondition.FOG,
    50: WeatherCondition.RAINY,
    51: WeatherCondition.RAINY,
    52: WeatherCondition.RAINY,
    53: WeatherCondition.RAINY,
    54: WeatherCondition.RAINY,
    55: WeatherCondition.RAINY,
    56: WeatherCondition.SNOWY_RAINY,
    57: WeatherCondition.SNOWY_RAINY,
    58: WeatherCondition.RAINY,
    59: WeatherCondition.RAINY,
    60: WeatherCondition.RAINY,
    61: WeatherCondition.RAINY,
    62: WeatherCondition.RAINY,
    63: WeatherCondition.RAINY,
    64: WeatherCondition.RAINY,
    65: WeatherCondition.RAINY,
    66: WeatherCondition.SNOWY_RAINY,
    67: WeatherCondition.SNOWY_RAINY,
    68: WeatherCondition.SNOWY_RAINY,
    69: WeatherCondition.SNOWY_RAINY,
    70: WeatherCondition.SNOWY,
    71: WeatherCondition.SNOWY,
    72: WeatherCondition.SNOWY,
    73: WeatherCondition.SNOWY,
    74: WeatherCondition.SNOWY,
    75: WeatherCondition.SNOWY,
    76: WeatherCondition.SNOWY,
    77: WeatherCondition.SNOWY,
    78: WeatherCondition.SNOWY,
    79: WeatherCondition.SNOWY,
    80: WeatherCondition.RAINY,
    81: WeatherCondition.RAINY,
    82: WeatherCondition.RAINY,
    83: WeatherCondition.SNOWY_RAINY,
    84: WeatherCondition.SNOWY_RAINY,
    85: WeatherCondition.SNOWY,
    86: WeatherCondition.SNOWY,
    87: WeatherCondition.HAIL,
    88: WeatherCondition.HAIL,
    89: WeatherCondition.HAIL,
    90: WeatherCondition.HAIL,
    91: WeatherCondition.LIGHTNING,
    92: WeatherCondition.LIGHTNING,
    93: WeatherCondition.LIGHTNING_RAINY,
    94: WeatherCondition.LIGHTNING_RAINY,
    95: WeatherCondition.LIGHTNING_RAINY,
    96: WeatherCondition.EXCEPTIONAL,
    97: WeatherCondition.LIGHTNING_RAINY,
    98: WeatherCondition.LIGHTNING_RAINY,
    99: WeatherCondition.EXCEPTIONAL,
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
    _attr_temperature_unit = TEMP_CELSIUS
    _attr_wind_speed_unit = SPEED_KILOMETERS_PER_HOUR

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
    def temperature(self):
        return self._current.get("maxAirTemperature")

    @property
    def humidity(self):
        return self._current.get("relativeHumidity")

    @property
    def wind_speed(self):
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
        return CONDITION_MAP.get(code, WeatherCondition.UNKNOWN)

    @property
    def forecast(self):
        """Return the forecast data."""
        forecasts = []

        # forecast_coordinator.data doit être un dict comme {"1": {...}, "2": {...}}
        for day_str, day_data in sorted(self.forecast_coordinator.data.items(), key=lambda x: int(x[0])):
            forecast = {
                "datetime": dt_util.parse_datetime(day_data["date"]),
                "condition": CONDITION_MAP.get(day_data.get("weatherCode"), WeatherCondition.UNKNOWN),
                "temperature": day_data.get("maxAirTemperature"),
                "templow": day_data.get("minAirTemperature"),
                "precipitation": day_data.get("precipitationAmount"),
                "wind_speed": day_data.get("windSpeedAt2m"),
                "wind_bearing": day_data.get("windDirection", {}).get("degree") if isinstance(day_data.get("windDirection"), dict) else None,
            }
            forecasts.append(forecast)

        return forecasts

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units."""
        return self._forecast()

    async def async_update(self) -> None:
        """Get the latest weather data."""
        self._weather = self.forecast_coordinator.data
        await self.async_update_listeners(("daily",))
