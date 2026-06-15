import aiohttp
import uuid
import time
from config import XUI_URL

XUI_INBOUND_ID = 4
XUI_TOKEN = "Rz0rxMg2O02xSJjs5yLtuWeawLvzvPc8srB7QOT4ui5SYm6b"

class XUIClient:
    def __init__(self):
        self.base_url = XUI_URL
        self._session = None

    async def get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {XUI_TOKEN}"}
            )
        return self._session

    async def login(self):
        return True

    async def create_client(self, days: int, traffic_gb: float = 0) -> dict:
        email = f"vpn{uuid.uuid4().hex[:8]}"
        expire_ms = int(time.time() * 1000) + days * 86400 * 1000
        total_bytes = int(traffic_gb * 1024 ** 3) if traffic_gb > 0 else 0

        payload = {
            "client": {
                "email": email,
                "totalGB": total_bytes,
                "expiryTime": expire_ms,
                "tgId": 0,
                "limitIp": 3,
                "enable": True
            },
            "inboundIds": [XUI_INBOUND_ID]
        }

        session = await self.get_session()
        try:
            resp = await session.post(
                f"{self.base_url}/panel/api/clients/add",
                json=payload,
                ssl=False
            )
            data = await resp.json()
            if data.get("success"):
                return {"client_id": email, "sub_id": email}
        except Exception as e:
            pass
        return {"client_id": email, "sub_id": email}

    async def get_client_url(self, client_id: str) -> str:
        session = await self.get_session()
        try:
            resp = await session.get(
                f"{self.base_url}/panel/api/clients/subLinks/{client_id}",
                ssl=False
            )
            data = await resp.json()
            if data.get("success") and data.get("obj"):
                return data["obj"]
        except:
            pass
        return f"{self.base_url}/sub/{client_id}"

    async def disable_client(self, client_id: str):
        session = await self.get_session()
        try:
            await session.post(
                f"{self.base_url}/panel/api/clients/update/{client_id}",
                json={"enable": False},
                ssl=False
            )
        except:
            pass

    async def enable_client(self, client_id: str):
        session = await self.get_session()
        try:
            await session.post(
                f"{self.base_url}/panel/api/clients/update/{client_id}",
                json={"enable": True},
                ssl=False
            )
        except:
            pass

xui = XUIClient()
