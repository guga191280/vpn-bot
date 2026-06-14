import aiohttp
import uuid
from config import YOOMONEY_ACCESS_TOKEN, YOOMONEY_WALLET

async def create_payment_label(user_id: int, plan: str) -> str:
    return f"vpn_{user_id}_{plan}_{uuid.uuid4().hex[:8]}"

def get_payment_url(amount: float, label: str, comment: str) -> str:
    return (
        f"https://yoomoney.ru/quickpay/confirm.xml"
        f"?receiver={YOOMONEY_WALLET}"
        f"&quickpay-form=button"
        f"&targets={comment}"
        f"&paymentType=AC"
        f"&sum={amount}"
        f"&label={label}"
    )

async def check_payment(label: str) -> bool:
    async with aiohttp.ClientSession() as s:
        resp = await s.post(
            "https://yoomoney.ru/api/operation-history",
            headers={"Authorization": f"Bearer {YOOMONEY_ACCESS_TOKEN}"},
            data={"label": label}
        )
        data = await resp.json()
        for op in data.get("operations", []):
            if op.get("label") == label and op.get("status") == "success":
                return True
    return False
