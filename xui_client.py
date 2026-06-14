import aiohttp
import uuid
import json
import time
from config import XUI_URL, XUI_USERNAME, XUI_PASSWORD

XUI_INBOUND_ID = 1

class XUIClient:
    def __init__(self):
        self.base_url = XUI_URL
        self.cookies = None

    async def login(self):
        async with aiohttp.ClientSession() as s:
            resp = await s.post(
                f"{self.base_url}/login",
                data={"username": XUI_USERNAME, "password": XUI_PASSWORD},
                ssl=False
            )
            self.cookies = resp.cookies
            return (await resp.json()).get("success")

    async def create_client(self, days: int, traffic_gb: float = 0) -> dict:
        client_id = str(uuid.uuid4())
        expire_ms = int(time.time() * 1000) + days * 86400 * 1000
        total_bytes = int(traffic_gb * 1024 ** 3) if traffic_gb > 0 else 0

        client = {
            "id": client_id,
            "alterId": 0,
            "email": client_id[:8],
            "limitIp": 3,
            "totalGB": total_bytes,
            "expiryTime": expire_ms,
            "enable": True,
            "tgId": "",
            "subId": client_id[:16]
        }

        async with aiohttp.ClientSession(cookies=self.cookies) as s:
            resp = await s.post(
                f"{self.base_url}/panel/api/inbounds/addClient",
                json={"id": XUI_INBOUND_ID, "settings": json.dumps({"clients": [client]})},
                ssl=False
            )
            data = await resp.json()
            if data.get("success"):
                return {"client_id": client_id, "sub_id": client_id[:16]}
            return {}

    async def get_client_url(self, client_id: str) -> str:
        async with aiohttp.ClientSession(cookies=self.cookies) as s:
            resp = await s.get(
                f"{self.base_url}/panel/api/inbounds/list",
                ssl=False
            )
            data = await resp.json()
            for inbound in data.get("obj", []):
                if inbound["id"] == XUI_INBOUND_ID:
                    sub_url = f"{self.base_url}/sub/{client_id[:16]}"
                    return sub_url
        return ""

    async def disable_client(self, client_id: str):
        async with aiohttp.ClientSession(cookies=self.cookies) as s:
            await s.post(
                f"{self.base_url}/panel/api/inbounds/{XUI_INBOUND_ID}/updateClient/{client_id}",
                json={"id": XUI_INBOUND_ID, "settings": json.dumps({"clients": [{"id": client_id, "enable": False}]})},
                ssl=False
            )

    async def enable_client(self, client_id: str):
        async with aiohttp.ClientSession(cookies=self.cookies) as s:
            await s.post(
                f"{self.base_url}/panel/api/inbounds/{XUI_INBOUND_ID}/updateClient/{client_id}",
                json={"id": XUI_INBOUND_ID, "settings": json.dumps({"clients": [{"id": client_id, "enable": True}]})},
                ssl=False
            )

xui = XUIClient()
