import aiohttp
import uuid
import time
import asyncio
import logging

XUI_BASE_URL = "https://russ.official-happ.ru:12822/lpTK27EkL3HLJGkZgp"
XUI_TOKEN = "Rz0rxMg2O02xSJjs5yLtuWeawLvzvPc8srB7QOT4ui5SYm6b"
XUI_SUB_URL = "https://russ.official-happ.ru:2096/sub"

class XUIClient:
    def __init__(self):
        self.base_url = XUI_BASE_URL
        self.token = XUI_TOKEN
        self.sub_url = XUI_SUB_URL

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    async def login(self):
        return True

    async def get_inbound_ids(self) -> list:
        try:
            async with aiohttp.ClientSession(headers=self._headers()) as s:
                resp = await s.get(f"{self.base_url}/panel/api/inbounds/list", ssl=False)
                data = await resp.json()
                return [i["id"] for i in data.get("obj", []) if i.get("enable", True)]
        except Exception as e:
            logging.error(f"get_inbound_ids: {e}")
            return [11]

    async def create_client(self, days: int, traffic_gb: float = 0, user_id: int = 0) -> dict:
        email = f"tg{user_id}_{uuid.uuid4().hex[:6]}"
        expire_ms = int(time.time() * 1000) + days * 86400 * 1000
        total_bytes = int(traffic_gb * 1024 ** 3) if traffic_gb > 0 else 0

        inbound_ids = await self.get_inbound_ids()

        async with aiohttp.ClientSession(headers=self._headers()) as s:
            try:
                resp = await s.post(
                    f"{self.base_url}/panel/api/clients/add",
                    json={"client": {"email": email, "totalGB": total_bytes, "expiryTime": expire_ms, "tgId": user_id, "limitIp": 3, "enable": True}, "inboundIds": [inbound_ids[0]]},
                    ssl=False
                )
                await resp.json()
            except Exception as e:
                logging.error(f"create: {e}")
                return {"client_id": email, "sub_id": email}

            await asyncio.sleep(2)

            if len(inbound_ids) > 1:
                try:
                    resp2 = await s.post(
                        f"{self.base_url}/panel/api/clients/{email}/attach",
                        json={"inboundIds": inbound_ids[1:]},
                        ssl=False
                    )
                    await resp2.json()
                except Exception as e:
                    logging.error(f"attach: {e}")

            await asyncio.sleep(1)

            try:
                resp3 = await s.get(f"{self.base_url}/panel/api/clients/get/{email}", ssl=False)
                data3 = await resp3.json()
                sub_id = data3.get("obj", {}).get("client", {}).get("subId", email)
                return {"client_id": email, "sub_id": sub_id}
            except Exception as e:
                logging.error(f"get subId: {e}")

        return {"client_id": email, "sub_id": email}

    async def get_client_url(self, client_id: str) -> str:
        try:
            async with aiohttp.ClientSession(headers=self._headers()) as s:
                resp = await s.get(f"{self.base_url}/panel/api/clients/get/{client_id}", ssl=False)
                data = await resp.json()
                sub_id = data.get("obj", {}).get("client", {}).get("subId", client_id)
                return f"{self.sub_url}/{sub_id}"
        except:
            pass
        return f"{self.sub_url}/{client_id}"

    async def disable_client(self, client_id: str):
        try:
            async with aiohttp.ClientSession(headers=self._headers()) as s:
                await s.post(f"{self.base_url}/panel/api/clients/update/{client_id}", json={"enable": False}, ssl=False)
        except:
            pass

    async def enable_client(self, client_id: str):
        try:
            async with aiohttp.ClientSession(headers=self._headers()) as s:
                await s.post(f"{self.base_url}/panel/api/clients/update/{client_id}", json={"enable": True}, ssl=False)
        except:
            pass

xui = XUIClient()
