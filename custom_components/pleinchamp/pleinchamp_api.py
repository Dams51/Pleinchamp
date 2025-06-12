import json
import logging
from datetime import datetime, UTC
from zoneinfo import ZoneInfo
from typing import Any
from collections import defaultdict

import asyncio
from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientError

from .const import BASE_URL_PLEINCHAMP, ENDPOINT_URL_PLEINCHAMP_CURRENT, ENDPOINT_URL_PLEINCHAMP_DAILY, DEFAULT_TIMEOUT, DEFAULT_CACHE_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class Pleinchamp:
    def __init__(self, session: ClientSession, options: dict):
        self._session = session
        self._options = options
        self._last_daily_forecast_fetch: datetime | None = None
        self._cached_daily_forecast_data: dict | None = None
        self._last_current_forecast_fetch: datetime | None = None
        self._cached_current_forecast_data: dict | None = None

    async def initialize(self) -> None:
        """Optional setup logic if needed."""
        pass

    def _build_url(self, Endpoint) -> str:
        _LOGGER.debug(f"_build_url - Endpoint : {Endpoint}")
        lat = self._options.get("latitude")
        lon = self._options.get("longitude")
        return f"{BASE_URL_PLEINCHAMP}{Endpoint}?latitude={lat:.6f}&longitude={lon:.6f}"


    # --------------------------------------
    #             Daily forecast
    # --------------------------------------

    async def fetch_daily_forecast_datas(self) -> dict:
        """Return current weather data."""
        if self._cached_daily_forecast_data and self._last_daily_forecast_fetch:
            if (datetime.now(UTC) - self._last_daily_forecast_fetch).total_seconds() < DEFAULT_CACHE_TIMEOUT:
                _LOGGER.debug("Using cached data")
                return self._cached_daily_forecast_data

        url = self._build_url(ENDPOINT_URL_PLEINCHAMP_DAILY)
        try:
            _LOGGER.debug(f"Fetching data from: {url}")
            async with self._session.get(url, timeout=ClientTimeout(total=DEFAULT_TIMEOUT)) as response:
                response.raise_for_status()
                data = await response.json(content_type=None)
                _LOGGER.debug(f"fetch_daily_forecast_datas - Raw forecast datas : \n{json.dumps(data, indent=2, ensure_ascii=False)}")
                data = self.reorganiser_par_date(data)

                self._last_daily_forecast_fetch = datetime.now(UTC)
                self._cached_daily_forecast_data = data
                _LOGGER.debug(f"fetch_daily_forecast_datas - Ordered forecast datas : \n{json.dumps(data, indent=2, ensure_ascii=False)}")
                return data
        except (asyncio.TimeoutError, ClientError, json.JSONDecodeError) as err:
            _LOGGER.error(f"Error fetching Pleinchamp daily forecast data: {err}")
            return {}

    async def get_daily_forecast_datas(self) -> list[dict]:
        """Extract forecast entries from API."""
        data = await self.fetch_daily_forecast_datas()
        return data

    def reorganiser_par_date(self, data):
        result = defaultdict(dict)
        tz = ZoneInfo("Europe/Paris")
        today = datetime.now(tz).date()

        for metric, entries in data.items():
            if metric == "nbMetrics":
                continue  # on ignore ce champ

            for entry in entries:
                date_str = entry["date"]
                value = entry["value"]

                # Conversion date/heure en datetime Paris
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00")).astimezone(tz)
                date_courte = dt.date()

                # Calcul de l'index jour (1 = aujourd'hui)
                index_jour = (date_courte - today).days + 1

                if index_jour > 0:
                    result[index_jour]["date"] = date_courte.isoformat()
                    result[index_jour][metric] = value

        return dict(result)

    
    # --------------------------------------
    #             Current forecast
    # --------------------------------------
    async def fetch_current_forecast_datas(self) -> dict:
        """Return current weather data."""
        if self._cached_current_forecast_data and self._last_current_forecast_fetch:
            if (datetime.now(UTC) - self._last_current_forecast_fetch).total_seconds() < DEFAULT_CACHE_TIMEOUT:
                _LOGGER.debug("Using cached data")
                return self._cached_current_forecast_data

        url = self._build_url(ENDPOINT_URL_PLEINCHAMP_CURRENT)
        try:
            _LOGGER.debug(f"Fetching data from: {url}")
            async with self._session.get(url, timeout=ClientTimeout(total=DEFAULT_TIMEOUT)) as response:
                response.raise_for_status()
                data = await response.json(content_type=None)
                _LOGGER.debug(f"fetch_current_forecast_datas - Raw forecast datas : \n{json.dumps(data, indent=2, ensure_ascii=False)}")
                data = self.reorganiser(data)

                self._last_current_forecast_fetch = datetime.now(UTC)
                self._cached_current_forecast_data = data
                _LOGGER.debug(f"fetch_current_forecast_datas - Ordered forecast datas : \n{json.dumps(data, indent=2, ensure_ascii=False)}")
                return data
        except (asyncio.TimeoutError, ClientError, json.JSONDecodeError) as err:
            _LOGGER.error(f"Error fetching Pleinchamp current forecast data: {err}")
            return {}

    async def get_current_forecast_data(self) -> list[dict]:
        """Extract forecast entries from API."""
        data = await self.fetch_current_forecast_datas()
        return data

    def reorganiser(self, data):
        result = defaultdict(dict)
        tz = ZoneInfo("Europe/Paris")

        for metric, entry in data.items():
            if metric == "nbMetrics":
                continue  # on ignore ce champ

            if metric == "airTemperature":
                # on récupère la date avec heure plus précise dans airTemperature et weatherCode que dans les autres valeurs
                date_str = entry["date"]
                # Conversion date/heure en datetime Paris
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00")).astimezone(tz)
                # date_courte = dt.date()
                # result["date"] = date_courte.isoformat()
                result["datetime"] = dt.isoformat()

            result[metric] = entry["value"]

        return dict(result)
