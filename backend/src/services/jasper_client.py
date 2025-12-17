import httpx
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from backend.src.config import settings
import logging

logger = logging.getLogger(__name__)

class JasperClient:
    def __init__(self):
        self.base_url = settings.jasper_config["base_url"]
        self.api_key = settings.jasper_config["api_key"]
        self.domain_id = settings.jasper_config["domain_id"]

        if not self.api_key or not self.domain_id:
            logger.error("Jasper Vision API key or Domain ID is not set!")
            raise ValueError("Missing API key or Domain ID")

        self.headers = {
            "X-Api-Key": self.api_key,
            "x-domainid": self.domain_id,
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def get_historical_data(
            self,
            data_point_id: str,
            start_time: datetime,
            end_time: datetime,
            step: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical data from Jasper API
        Endpoint: /api/public/datapoints/{id}/history/retrieve
        """
        url = f"{self.base_url}/{data_point_id}/history/retrieve"

        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        payload = {
            "start": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }

        if step:
            payload["step"] = step

        try:
            response = await self.client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "historyValues" in data:
                history_values = data["historyValues"]
                logger.debug(f"Retrieved {len(history_values)} records for {data_point_id}")
                return history_values
            elif isinstance(data, list):
                logger.debug(f"Retrieved {len(data)} records for {data_point_id}")
                return data
            else:
                logger.warning(f"Unexpected response format for {data_point_id}: {type(data)}")
                return []

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for {data_point_id}: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.error(f"Error fetching history for {data_point_id}: {e}")
            return []

    async def get_station_power_data(
            self,
            station_code: str,
            start_time: datetime,
            end_time: datetime
    ) -> Dict[str, List[Dict]]:
        """
        Fetch power data for a specific station
        Returns dict with power_type -> list of history items
        """
        station_data_points = settings.data_points.get(station_code, {})

        if not station_data_points:
            logger.warning(f"No data points configured for station {station_code}")
            return {}

        results = {}
        step = "PT15M"

        for power_type, data_point_id in station_data_points.items():
            if data_point_id and data_point_id.strip():
                history = await self.get_historical_data(data_point_id, start_time, end_time, step)

                if history:
                    results[power_type] = history
                    logger.debug(f"Retrieved {len(history)} records for {station_code}.{power_type}")

        return results