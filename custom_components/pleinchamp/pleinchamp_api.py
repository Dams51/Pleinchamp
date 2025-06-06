import json
import logging
from datetime import datetime, UTC
from typing import Any

from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientError

from .const import BASE_URL_PLEINCHAMP, DEFAULT_TIMEOUT, DEFAULT_CACHE_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class Pleinchamp:
    def __init__(self, session: ClientSession, options: dict):
        self._session = session
        self._options = options
        self._last_fetch: datetime | None = None
        self._cached_data: dict | None = None

    async def initialize(self) -> None:
        """Optional setup logic if needed."""
        pass

    async def get_location_data(self) -> dict:
        """Return current weather data."""
        if self._cached_data and self._last_fetch:
            if (datetime.now(UTC) - self._last_fetch).total_seconds() < DEFAULT_CACHE_TIMEOUT:
                _LOGGER.debug("Using cached data")
                return self._cached_data

        url = self._build_url()
        try:
            _LOGGER.debug(f"Fetching data from: {url}")
            async with self._session.get(url, timeout=ClientTimeout(total=DEFAULT_TIMEOUT)) as response:
                response.raise_for_status()
                data = await response.json(content_type=None)

                self._last_fetch = datetime.now(UTC)
                self._cached_data = data
                return data
        except (asyncio.TimeoutError, ClientError, json.JSONDecodeError) as err:
            _LOGGER.error(f"Error fetching Pleinchamp data: {err}")
            return {}

    async def get_forecast_data(self) -> list[dict]:
        """Extract forecast entries from API."""
        data = await self.get_location_data()
        return data.get("forecast", [])

    def _build_url(self) -> str:
        lat = self._options.get("latitude")
        lon = self._options.get("longitude")
        return f"{BASE_URL_PLEINCHAMP}forecasts-15d?latitude={lat:.2f}&longitude={lon:.2f}"
