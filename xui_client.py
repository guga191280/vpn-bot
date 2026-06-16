import aiohttp
import uuid
import time
import logging

XUI_BASE_URL = "https://russ.official-happ.ru:12822/lpTK27EkL3HLJGkZgp"
XUI_TOKEN = "Rz0rxMg2O02xSJjs5yLtuWeawLvzvPc8srB7QOT4ui5SYm6b"
XUI_SUB_URL = "https://russ.official-happ.ru:2096/sub"

class XUIClient:
    def __init__(self):
        self.base_url = XUI_BASE_URL
        self.token = XUI_TOKEN
        self.sub_url = XUI_SUB_URL
        self._session = None

    async def get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.token}"}
            )
        return self._session

    async def login(self):
        return True

    async def get_inbound_ids(self) -> list:
        session = await self.get_session()
        try:
            resp = await session.get(f"{self.base_url}/panel/api/inbounds/list", ssl=False)
            data = await resp.json()
            return [i["id"] for i in data.get("obj", []) if i.get("enable", True)]
        except Exception as e:
            logging.error(f"get_inbound_ids error: {e}")
            return [11]

    async def create_client(self, days: int, traffic_gb: float = 0) -> dict:
        email = f"vpn{uuid.uuid4().hex[:8]}"
        expire_ms = int(time.time() * 1000) + days * 86400 * 1000
        total_bytes = int(traffic_gb * 1024 ** 3) if traffic_gb > 0 else 0

        inbound_ids = await self.get_inbound_ids()
        session = await self.get_session()

        success_count = 0
        for inbound_id in inbound_ids:
            payload = {
                "client": {
                    "email": email,
                    "totalGB": total_bytes,
                    "expiryTime": expire_ms,
                    "tgId": 0,
                    "limitIp": 3,
                    "enable": True
                },
                "inboundIds": [inbound_id]
            }
            try:
                resp = await session.post(
                    f"{self.base_url}/panel/api/clients/add",
                    json=payload,
                    ssl=False
                )
                data = await resp.json()
                if data.get("success"):
                    success_count += 1
            except Exception as e:
                logging.error(f"create_client inbound {inbound_id} error: {e}")

        # получаем subId
        try:
            resp2 = await session.get(
                f"{self.base_url}/panel/api/clients/get/{email}",
                ssl=False
            )
            data2 = await resp2.json()
            sub_id = data2.get("obj", {}).get("client", {}).get("subId", email)
            logging.info(f"Created client {email} in {success_count}/{len(inbound_ids)} inbounds")
            return {"client_id": email, "sub_id": sub_id}
        except Exception as e:
            logging.error(f"get subId error: {e}")
        return {"client_id": email, "sub_id": email}

    async def get_client_url(self, client_id: str) -> str:
        session = await self.get_session()
        try:
            resp = await session.get(
                f"{self.base_url}/panel/api/clients/get/{client_id}",
                ssl=False
            )
            data = await resp.json()
            sub_id = data.get("obj", {}).get("client", {}).get("subId", client_id)
            return f"{self.sub_url}/{sub_id}"
        except:
            pass
        return f"{self.sub_url}/{client_id}"

    async def disable_client(self, client_id: str):
        inbound_ids = await self.get_inbound_ids()
        session = await self.get_session()
        for inbound_id in inbound_ids:
            try:
                await session.post(
                    f"{self.base_url}/panel/api/clients/update/{client_id}",
                    json={"enable": False},
                    ssl=False
                )
            except:
                pass

    async def enable_client(self, client_id: str):
        inbound_ids = await self.get_inbound_ids()
        session = await self.get_session()
        for inbound_id in inbound_ids:
            try:
                await session.post(
                    f"{self.base_url}/panel/api/clients/update/{client_id}",
                    json={"enable": True},
                    ssl=False
                )
            except:
                pass

xui = XUIClient()
