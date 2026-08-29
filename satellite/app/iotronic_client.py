import httpx
import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class IotronicClient:
    def __init__(
        self,
        auth_url: str,
        username: str,
        password: str,
        project_name: str,
        user_domain_name: str = "Default",
        project_domain_name: str = "Default",
        iotronic_url: str = "http://iotronic-conductor:8812",
        timeout: float = 30.0
    ):
        self.auth_url = auth_url.rstrip("/")
        self.username = username
        self.password = password
        self.project_name = project_name
        self.user_domain_name = user_domain_name
        self.project_domain_name = project_domain_name
        self.iotronic_url = iotronic_url.rstrip("/")
        self.timeout = timeout
        self._token: Optional[str] = None
        self._lock = asyncio.Lock()

    async def get_token(self, force_refresh: bool = False) -> str:
        async with self._lock:
            if self._token and not force_refresh:
                return self._token

            auth_payload = {
                "auth": {
                    "identity": {
                        "methods": ["password"],
                        "password": {
                            "user": {
                                "name": self.username,
                                "domain": {"name": self.user_domain_name},
                                "password": self.password
                            }
                        }
                    },
                    "scope": {
                        "project": {
                            "name": self.project_name,
                            "domain": {"name": self.project_domain_name}
                        }
                    }
                }
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.auth_url}/auth/tokens", json=auth_payload)
                if resp.status_code != 201:
                    raise Exception(f"Failed to authenticate with Keystone (status {resp.status_code}): {resp.text}")
                token = resp.headers.get("X-Subject-Token")
                if not token:
                    raise Exception("Keystone response missing X-Subject-Token header")
                self._token = token
                return token

    async def call_plugin(
        self,
        board_name: str,
        plugin_name: str,
        parameters: Dict[str, Any]
    ) -> str:
        token = await self.get_token()

        url = f"{self.iotronic_url}/v1/boards/{board_name}/plugins/{plugin_name}"
        body = {
            "action": "PluginCall",
            "parameters": parameters
        }

        async def _send_request(t: str) -> httpx.Response:
            headers = {
                "X-Auth-Token": t,
                "X-OpenStack-Iotronic-API-Version": "1.0",
                "Content-Type": "application/json"
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                return await client.post(url, headers=headers, json=body)

        try:
            resp = await _send_request(token)
        except httpx.TimeoutException:
            raise Exception(f"Timeout calling plugin '{plugin_name}' on board '{board_name}'. Board might be offline or busy.")
        except httpx.RequestError as exc:
            raise Exception(f"Connection error to IoTronic conductor: {exc}")

        # Token expired -> retry once
        if resp.status_code == 401:
            token = await self.get_token(force_refresh=True)
            try:
                resp = await _send_request(token)
            except httpx.TimeoutException:
                raise Exception(f"Timeout calling plugin '{plugin_name}' on board '{board_name}' after token refresh.")
            except httpx.RequestError as exc:
                raise Exception(f"Connection error to IoTronic conductor after token refresh: {exc}")

        if resp.status_code != 200:
            raise Exception(f"IoTronic plugin call failed (status {resp.status_code}): {resp.text}")

        try:
            data = resp.json()
            if isinstance(data, str):
                return data
            return str(data)
        except Exception:
            return resp.text
