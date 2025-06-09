"""Support for the Pleinchamp sensors."""

import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfPrecipitationDepth,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import CONF_LOCATION_NAME, DEFAULT_LOCATION_NAME, DOMAIN
from .entity import PleinchampEntity

_LOGGER = logging.getLogger(__name__)

SENSOR_NAME = 0
SENSOR_UNIT = 1
SENSOR_ICON = 2
SENSOR_DEVICE_CLASS = 3
SENSOR_STATE_CLASS = 4

SENSOR_TYPES = {
    "forecast_length": [
        "Forecast Length",
        UnitOfTime.DAYS,
        "mdi:calendar-range",
        None,
        None,
    ],
    "date": [
        "Date",
        None,
        "mdi:calendar",
        SensorDeviceClass.DATE,
        None,
    ],
    "weatherCode": [
        "Weather Code",
        None,
        "mdi:weather-partly-cloudy",
        None,
        None,
    ],
    "minAirTemperatureNearGround": [
        "Min Temp Near Ground",
        UnitOfTemperature.CELSIUS,
        "mdi:thermometer",
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
    ],
    "minAirTemperature": [
        "Min Air Temp",
        UnitOfTemperature.CELSIUS,
        "mdi:thermometer",
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
    ],
    "maxAirTemperature": [
        "Max Air Temp",
        UnitOfTemperature.CELSIUS,
        "mdi:thermometer-high",
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
    ],
    "precipitationAmount": [
        "Precipitation",
        UnitOfPrecipitationDepth.MILLIMETERS,
        "mdi:weather-rainy",
        SensorDeviceClass.PRECIPITATION,
        SensorStateClass.MEASUREMENT,
    ],
    "precipitationProbability": [
        "Precipitation Probability",
        PERCENTAGE,
        "mdi:weather-partly-rainy",
        SensorDeviceClass.PRECIPITATION_INTENSITY,
        SensorStateClass.MEASUREMENT,
    ],
    "relativeHumidity": [
        "Humidity",
        PERCENTAGE,
        "mdi:water-percent",
        SensorDeviceClass.HUMIDITY,
        SensorStateClass.MEASUREMENT,
    ],
    "windDirection": [
        "Wind Direction",
        DEGREE,
        "mdi:compass",
        None,
        None,
    ],
    "windSpeedAt2m": [
        "Wind Speed",
        UnitOfSpeed.KILOMETERS_PER_HOUR,
        "mdi:weather-windy",
        SensorDeviceClass.WIND_SPEED,
        SensorStateClass.MEASUREMENT,
    ],
    "maxWindGustAt2m": [
        "Max Wind Gust",
        UnitOfSpeed.KILOMETERS_PER_HOUR,
        "mdi:weather-windy-variant",
        SensorDeviceClass.WIND_SPEED,
        SensorStateClass.MEASUREMENT,
    ],
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up the Pleinchamp sensor platform."""

    _LOGGER.info("Set up Pleinchamp sensor platform")

    forecast_coordinator = hass.data[DOMAIN][entry.entry_id]["forecast"]
    if not forecast_coordinator.data:
        return False

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    if not coordinator.data:
        return False

    pleinchamp = hass.data[DOMAIN][entry.entry_id]["client"]
    if not pleinchamp:
        return False

    sensors = []

    forecast_data = forecast_coordinator.data

    # Capteur global : forecast_length
    sensors.append(
        PleinchampSensor(
            coordinator,
            entry.data,
            "forecast_length",
            forecast_coordinator,
            entry
        )
    )

    # Capteurs par jour indexé
    for day_index_str, day_data in sorted(forecast_data.items(), key=lambda x: int(x[0])):
        day_index = int(day_index_str)

        for sensor_key in SENSOR_TYPES:
            if sensor_key == "forecast_length":
                continue
            if sensor_key in day_data:
                sensors.append(
                    PleinchampSensor(
                        coordinator,
                        entry.data,
                        sensor_key,
                        forecast_coordinator,
                        entry,
                        day_index
                    )
                )

    async_add_entities(sensors, True)
    return True


class PleinchampSensor(PleinchampEntity, SensorEntity):
    """Representation of a Pleinchamp sensor."""

    def __init__(self, coordinator, entries, sensor, forecast_coordinator, entry, day_index=None):
        """Initialize the sensor."""
        super().__init__(coordinator, entries, sensor, forecast_coordinator, entry.entry_id)

        self._sensor = sensor
        self._day_index = day_index
        self._device_class = SENSOR_TYPES[sensor][SENSOR_DEVICE_CLASS]
        self._state_class = SENSOR_TYPES[sensor][SENSOR_STATE_CLASS]
        self._icon = SENSOR_TYPES[sensor][SENSOR_ICON]
        self._unit = SENSOR_TYPES[sensor][SENSOR_UNIT]

        self._location_name = entries.get(CONF_LOCATION_NAME, DEFAULT_LOCATION_NAME)

        if self._day_index:
            self._sensor_name = f"{SENSOR_TYPES[sensor][SENSOR_NAME]} Jour {self._day_index}"
        else:
            self._sensor_name = SENSOR_TYPES[sensor][SENSOR_NAME]

        uid_base = self._sensor_name.lower().replace(" ", "_")
        self._attr_unique_id = f"{entry.entry_id}_{DOMAIN}_{uid_base}"

        self._attr_name = f"{DOMAIN.capitalize()} {self._location_name} {self._sensor_name}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self._sensor == "forecast_length":
            return len(self.forecast_coordinator.data)

        value = (
            self.forecast_coordinator.data.get(self._day_index, {}).get(self._sensor)
            if self._day_index else
            self.coordinator.data.get(self._sensor)
        )

        if self._sensor == "windDirection" and isinstance(value, dict):
            # On retourne uniquement le degré
            return value.get("degree")

        device_class = SENSOR_TYPES[self._sensor][SENSOR_DEVICE_CLASS]

        if device_class == SensorDeviceClass.TIMESTAMP:
            return dt_util.parse_datetime(str(value))
        elif device_class == SensorDeviceClass.DATE:
            dt = dt_util.parse_datetime(str(value))
            if dt:
                return dt.date()
            return None

        return value

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        if self._device_class == SensorDeviceClass.TIMESTAMP:
            return None
        return self._unit

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return self._icon

    @property
    def device_class(self):
        """Return the device class."""
        return self._device_class

    @property
    def state_class(self):
        """Return the state class."""
        return self._state_class
