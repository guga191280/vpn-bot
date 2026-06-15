import aiohttp
import uuid
import time
import logging
from database import AsyncSessionLocal
from models import Server, Subscription
from sqlalchemy import select, func

async def get_best_server():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Server).where(Server.is_active == True))
        servers = result.scalars().all()
        if not servers:
            return None
        # выбираем сервер с наименьшим кол-вом активных клиентов
        best = None
        min_count = float('inf')
        for s in servers:
            count = await db.execute(
                select(func.count(Subscription.id)).where(
                    Subscription.is_active == True,
                    Subscription.vpn_key.contains(s.sub_url)
                )
            )
            c = count.scalar() or 0
            if c < min_count:
                min_count = c
                best = s
        return best

async def create_client_on_server(server, days: int, traffic_gb: float = 0) -> dict:
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
        "inboundIds": [server.inbound_id]
    }

    async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {server.token}"}) as session:
        try:
            resp = await session.post(
                f"{server.url}/panel/api/clients/add",
                json=payload,
                ssl=False
            )
            data = await resp.json()
            if data.get("success"):
                resp2 = await session.get(
                    f"{server.url}/panel/api/clients/get/{email}",
                    ssl=False
                )
                data2 = await resp2.json()
                sub_id = data2.get("obj", {}).get("client", {}).get("subId", email)
                return {
                    "client_id": email,
                    "sub_id": sub_id,
                    "vpn_key": f"{server.sub_url}/{sub_id}"
                }
        except Exception as e:
            logging.error(f"XUI error: {e}")
    return {"client_id": email, "sub_id": email, "vpn_key": ""}

async def disable_client_on_server(server, client_id: str):
    async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {server.token}"}) as session:
        try:
            await session.post(
                f"{server.url}/panel/api/clients/update/{client_id}",
                json={"enable": False},
                ssl=False
            )
        except:
            pass

async def enable_client_on_server(server, client_id: str):
    async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {server.token}"}) as session:
        try:
            await session.post(
                f"{server.url}/panel/api/clients/update/{client_id}",
                json={"enable": True},
                ssl=False
            )
        except:
            pass
