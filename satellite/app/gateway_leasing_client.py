import httpx
import logging

logger = logging.getLogger(__name__)

class GatewayLeasingClient:
    def __init__(self, gateway_url: str):
        self.gateway_url = gateway_url.rstrip("/")

    async def lease_node(self, device_id: str) -> bool:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.gateway_url}/leasing/lease",
                    json={"device_id": device_id},
                    timeout=10.0
                )
                if response.status_code == 200:
                    return True
                logger.warning(f"Failed to lease {device_id}: {response.text}")
                return False
            except Exception as e:
                logger.error(f"Error leasing {device_id}: {e}")
                return False

    async def release_node(self, device_id: str) -> bool:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.gateway_url}/leasing/release",
                    json={"device_id": device_id},
                    timeout=10.0
                )
                if response.status_code == 200:
                    return True
                logger.warning(f"Failed to release {device_id}: {response.text}")
                return False
            except Exception as e:
                logger.error(f"Error releasing {device_id}: {e}")
                return False
