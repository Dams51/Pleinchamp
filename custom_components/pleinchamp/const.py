"""Constants in Pleinchamp component."""

from homeassistant.const import Platform

# #####################################################
# Domain and platforms
# #####################################################
DOMAIN = "pleinchamp"

PLEINCHAMP_PLATFORMS = (
    Platform.SENSOR,
    Platform.WEATHER,
)
DEVICE_TYPE_WEATHER = "weather"

# #####################################################
# Configuration settings
# #####################################################
CONF_FORECAST_INTERVAL = "forecast_interval"
CONF_LOCATION_NAME = "location_name"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"

# #####################################################
# Default values
# #####################################################
DEFAULT_ATTRIBUTION = "Data provided by Pleinchamp"
DEFAULT_FORECAST_INTERVAL = 5
FORECAST_INTERVAL_MIN = 1
FORECAST_INTERVAL_MAX = 240
DEFAULT_LOCATION_NAME = "Backyard"

DEFAULT_CACHE_TIMEOUT = 1770
DEFAULT_TIMEOUT = 10
BASE_URL_PLEINCHAMP = "https://api.prod.pleinchamp.com/"
ENDPOINT_URL_PLEINCHAMP_CURRENT = "forecasts-summary"
ENDPOINT_URL_PLEINCHAMP_DAILY = "forecasts-15d"
ENDPOINT_URL_PLEINCHAMP_HOURLY = "forecasts-hourly" # Need &date=2025-06-12
