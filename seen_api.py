import aiohttp
import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from config import SEEN_API_URL, DEFAULT_SEEN_API_KEY
from database import db

logger = logging.getLogger(__name__)

class SeenSMSError(Exception):
    """Custom exception raised when SeenSMS API returns an error."""
    def __init__(self, message: str, raw_response: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.raw_response = raw_response or {}

class SeenSMSClient:
    """
    Clean, reusable async client for the official SeenSMS API (https://seensms.uz/api/v1).
    Supports all actions: SMM, Virtual Numbers, Ready Accounts, Telegram Stars & Premium.
    Features:
    - One method per API action
    - Proper error handling on the 'error' field
    - Gzip compression enabled via 'Accept-Encoding: gzip'
    - Configurable timeouts
    - Dynamic key retrieval from database settings with fallback
    """

    def __init__(self, api_url: str = SEEN_API_URL, default_key: str = DEFAULT_SEEN_API_KEY, timeout: int = 15):
        self.api_url = api_url
        self.default_key = default_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def _get_key(self) -> str:
        key = await db.get_setting("seen_api_key", self.default_key)
        return key or self.default_key

    async def _request(self, action: str, **params) -> Union[Dict[str, Any], List[Any]]:
        """Core request method sending action and key with gzip enabled."""
        key = await self._get_key()
        if not key:
            raise SeenSMSError("API kalit kiritilmagan. Admin panel orqali SeenSMS API kalitini kiriting.")

        data = {"key": key, "action": action, **params}
        # Filter None values
        data = {k: str(v) for k, v in data.items() if v is not None}

        headers = {
            "Accept-Encoding": "gzip",
            "User-Agent": "PixoraSMM-Client/2.0"
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(self.api_url, data=data, headers=headers) as resp:
                    if resp.status == 200:
                        res = await resp.json()
                        if isinstance(res, dict) and "error" in res:
                            logger.warning(f"SeenSMS API error for action '{action}': {res['error']}")
                            raise SeenSMSError(res["error"], raw_response=res)
                        return res
                    else:
                        text = await resp.text()
                        logger.error(f"SeenSMS HTTP {resp.status} on action '{action}': {text}")
                        raise SeenSMSError(f"HTTP Xatosi ({resp.status}): {text}")
        except asyncio.TimeoutError:
            logger.error(f"SeenSMS request timeout on action '{action}'")
            raise SeenSMSError("SeenSMS serveriga ulanish vaqti tugadi (Timeout).")
        except aiohttp.ClientError as e:
            logger.error(f"SeenSMS connection error on action '{action}': {e}")
            raise SeenSMSError(f"Tarmoq xatosi: {str(e)}")

    # ==========================================
    # 1. SMM SERVICES
    # ==========================================

    async def services(self) -> List[Dict[str, Any]]:
        """Get list of available SMM services: [{service, name, type, category, rate, min, max, refill, cancel}]."""
        res = await self._request("services")
        return res if isinstance(res, list) else []

    async def add(self, service: int, link: str, quantity: int) -> Dict[str, Any]:
        """Place a new SMM order -> {order}."""
        return await self._request("add", service=service, link=link, quantity=quantity)

    async def status(self, order: int) -> Dict[str, Any]:
        """Check order status -> {charge, start_count, status, remains, currency}."""
        return await self._request("status", order=order)

    async def refill(self, order: int) -> Dict[str, Any]:
        """Request refill for an order -> {refill}."""
        return await self._request("refill", order=order)

    async def cancel(self, order: int) -> Dict[str, Any]:
        """Cancel an SMM order -> {order, cancel}."""
        return await self._request("cancel", order=order)

    async def balance(self) -> Dict[str, Any]:
        """Check account balance -> {balance, currency}."""
        return await self._request("balance")

    # ==========================================
    # 2. VIRTUAL NUMBERS (SMS RECEIPT)
    # ==========================================

    async def numbers_services(self) -> List[Dict[str, Any]]:
        """List available services for SMS activation -> [{service, name}]."""
        res = await self._request("numbers_services")
        return res if isinstance(res, list) else []

    async def numbers_countries(self, service: str) -> List[Dict[str, Any]]:
        """List available countries & prices for a service -> [{country, name, price, count}]."""
        res = await self._request("numbers_countries", service=service)
        return res if isinstance(res, list) else []

    async def numbers_get(self, country: Union[int, str], service: str) -> Dict[str, Any]:
        """Request a virtual number -> {id, number, cost}."""
        return await self._request("numbers_get", country=country, service=service)

    async def numbers_status(self, id: int) -> Dict[str, Any]:
        """Check status / SMS code for a rented number -> {id, status, code} (status: WAITING | OK | EXPIRED)."""
        return await self._request("numbers_status", id=id)

    async def numbers_cancel(self, id: int) -> Dict[str, Any]:
        """Cancel virtual number request -> {id, cancel, refunded}."""
        return await self._request("numbers_cancel", id=id)

    # ==========================================
    # 3. READY TELEGRAM ACCOUNTS
    # ==========================================

    async def accounts_countries(self) -> List[Dict[str, Any]]:
        """List countries with ready Telegram accounts -> [{country, price}]."""
        res = await self._request("accounts_countries")
        return res if isinstance(res, list) else []

    async def accounts_get(self, country: Union[int, str]) -> Dict[str, Any]:
        """Purchase ready Telegram account -> {id, number, cost}."""
        return await self._request("accounts_get", country=country)

    async def accounts_code(self, id: int) -> Dict[str, Any]:
        """Retrieve login code for account -> {id, status, code, password} (status: WAITING | OK)."""
        return await self._request("accounts_code", id=id)

    # ==========================================
    # 4. TELEGRAM STARS & PREMIUM
    # ==========================================

    async def user_info(self, username: str, type: str = "stars") -> Dict[str, Any]:
        """Get Telegram user info for gifting Stars/Premium -> {found, name, recipient, avatar}."""
        return await self._request("user_info", username=username, type=type)

    async def stars_prices(self) -> List[Dict[str, Any]]:
        """Get Telegram Stars packages and prices -> [{quantity, price}]."""
        res = await self._request("stars_prices")
        return res if isinstance(res, list) else []

    async def stars_buy(self, username: str, quantity: int) -> Dict[str, Any]:
        """Buy Telegram Stars for user -> {id, status, amount}."""
        return await self._request("stars_buy", username=username, quantity=quantity)

    async def premium_prices(self) -> List[Dict[str, Any]]:
        """Get Telegram Premium packages and prices -> [{months, price}]."""
        res = await self._request("premium_prices")
        return res if isinstance(res, list) else []

    async def premium_buy(self, username: str, months: int) -> Dict[str, Any]:
        """Buy Telegram Premium subscription for user -> {id, status, amount}."""
        return await self._request("premium_buy", username=username, months=months)

    async def stars_status(self, id: int) -> Dict[str, Any]:
        """Check status of Stars or Premium order -> {id, type, username, amount, status, error}."""
        return await self._request("stars_status", id=id)

    # Backward compatibility helper for sync
    async def fetch_services(self) -> List[Dict[str, Any]]:
        try:
            srvs = await self.services()
            if srvs:
                await db.sync_services(srvs)
                return srvs
        except Exception as e:
            logger.warning(f"Could not fetch live services: {e}")
        return await db.get_services()

DEFAULT_NUMBER_SERVICES = [
    {"service": "tg", "name": "✈️ Telegram"},
    {"service": "wa", "name": "💬 WhatsApp"},
    {"service": "ig", "name": "📸 Instagram"},
    {"service": "tk", "name": "🎵 TikTok"},
    {"service": "go", "name": "🔍 Google / Gmail"},
    {"service": "fb", "name": "🔷 Facebook"}
]

DEFAULT_NUMBER_COUNTRIES = [
    {"country": "31", "name": "Janubiy Afrika", "price": 1313, "count": 300000},
    {"country": "6", "name": "Indoneziya", "price": 1488, "count": 79000},
    {"country": "1", "name": "Rossiya (+7)", "price": 8500, "count": 50000},
    {"country": "2", "name": "Qozog'iston (+7)", "price": 9000, "count": 25000},
    {"country": "12", "name": "AQSh (+1)", "price": 12000, "count": 15000}
]

seen_client = SeenSMSClient()
