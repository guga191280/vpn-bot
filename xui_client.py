import aiohttp
import uuid
import json
import time
from config import XUI_URL, XUI_USERNAME, XUI_PASSWORD

XUI_INBOUND_ID = 1
XUI_TOKEN = "Rz0rxMg2O02xSJjs5yLtuWeawLvzvPc8srB7QOT4ui5SYm6b"

class XUIClient:
    def __init__(self):
        self.base_url = XUI_URL
        self._session = None

    async def get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Xui-Token": XUI_TOKEN}
            )
        return self._session

    async def login(self):
        return True

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

        session = await self.get_session()
        try:
            resp = await session.post(
                f"{self.base_url}/panel/api/inbounds/addClient",
                json={"id": XUI_INBOUND_ID, "settings": json.dumps({"clients": [client]})},
                ssl=False
            )
            data = await resp.json()
            if data.get("success"):
                return {"client_id": client_id, "sub_id": client_id[:16]}
        except Exception as e:
            pass
        return {"client_id": client_id, "sub_id": client_id[:16]}

    async def get_client_url(self, client_id: str) -> str:
        return f"{self.base_url}/sub/{client_id[:16]}"

    async def disable_client(self, client_id: str):
        session = await self.get_session()
        try:
            await session.post(
                f"{self.base_url}/panel/api/inbounds/{XUI_INBOUND_ID}/updateClient/{client_id}",
                json={"id": XUI_INBOUND_ID, "settings": json.dumps({"clients": [{"id": client_id, "enable": False}]})},
                ssl=False
            )
        except:
            pass

    async def enable_client(self, client_id: str):
        session = await self.get_session()
        try:
            await session.post(
                f"{self.base_url}/panel/api/inbounds/{XUI_INBOUND_ID}/updateClient/{client_id}",
                json={"id": XUI_INBOUND_ID, "settings": json.dumps({"clients": [{"id": client_id, "enable": True}]})},
                ssl=False
            )
        except:
            pass

xui = XUIClient()
