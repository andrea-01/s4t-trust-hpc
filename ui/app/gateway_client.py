import httpx
import logging
from typing import Dict, Any, List
from app.config import settings

logger = logging.getLogger(__name__)

class GatewayUnavailableError(Exception):
    pass

class GatewayClient:
    def __init__(self):
        self.base_url = settings.gateway_url
        self.timeout = 5.0
        self.auth = (settings.ui_admin_username, settings.ui_admin_password)
        
    async def get_recent_events(self) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/events/recent")
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Error fetching recent events from gateway: {e}")
            raise GatewayUnavailableError("Gateway non disponibile")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} fetching events: {e}")
            raise GatewayUnavailableError(f"Errore dal gateway: {e.response.status_code}")

    async def get_status(self, request_id: int) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/status/{request_id}")
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Error fetching status from gateway: {e}")
            raise GatewayUnavailableError("Gateway non disponibile")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"error": "Not found"}
            raise GatewayUnavailableError(f"Errore dal gateway: {e.response.status_code}")

    async def request_onboarding(self, device_id: str, owner_address: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/onboarding-request",
                    json={"device_id": device_id, "owner_address": owner_address}
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Error requesting onboarding: {e}")
            raise GatewayUnavailableError("Gateway non disponibile")
        except httpx.HTTPStatusError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = str(e)
            if e.response.status_code in (400, 422):
                raise ValueError(detail)
            raise GatewayUnavailableError(f"Errore dal gateway: {detail}")

    async def get_trusted_stacks(self) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/trust/stacks", auth=self.auth)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Error fetching trusted stacks from gateway: {e}")
            raise GatewayUnavailableError("Gateway non disponibile")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} fetching trusted stacks: {e}")
            raise GatewayUnavailableError(f"Errore dal gateway: {e.response.status_code}")

    async def add_trusted_stack(self, stack_id: str, description: str, device_id_prefixes: List[str]) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/trust/stacks",
                    json={
                        "stackId": stack_id,
                        "description": description,
                        "deviceIdPrefixes": device_id_prefixes,
                    },
                    auth=self.auth,
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Error adding trusted stack: {e}")
            raise GatewayUnavailableError("Gateway non disponibile")
        except httpx.HTTPStatusError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = str(e)
            if e.response.status_code in (400, 422):
                raise ValueError(detail)
            raise GatewayUnavailableError(f"Errore dal gateway: {detail}")

    async def delete_trusted_stack(self, stack_id: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(f"{self.base_url}/trust/stacks/{stack_id}", auth=self.auth)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.error(f"Error deleting trusted stack: {e}")
            raise GatewayUnavailableError("Gateway non disponibile")
        except httpx.HTTPStatusError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = str(e)
            if e.response.status_code in (400, 404):
                raise ValueError(detail)
            raise GatewayUnavailableError(f"Errore dal gateway: {detail}")

gateway_client = GatewayClient()

