import aiohttp
import asyncio
import logging
from config import SEEN_API_URL
from database import db

logger = logging.getLogger(__name__)

# Fallback default catalog if API key is not yet set or during initial setup
DEFAULT_SMM_SERVICES = [
    # Telegram
    {
        "service": 101,
        "name": "✈️ Telegram Obunachi (O'zbek kanallar / Aralash)",
        "category": "✈️ Telegram Obunachilar",
        "type": "Default",
        "rate": 18000.0,  # 18,000 UZS per 1000
        "min": 50,
        "max": 50000,
        "desc": "Tezkor yetkazish. Chiqib ketish ehtimoli past. Kafolat: 30 kun."
    },
    {
        "service": 102,
        "name": "✈️ Telegram Obunachi (Toza O'zbek auditoriya)",
        "category": "✈️ Telegram Obunachilar",
        "type": "Default",
        "rate": 32000.0,
        "min": 100,
        "max": 20000,
        "desc": "100% haqiqiy O'zbek foydalanuvchilar. Faol auditoriya."
    },
    {
        "service": 103,
        "name": "👁️ Telegram Post Ko'rish (Tezkor / So'nggi post)",
        "category": "✈️ Telegram Ko'rishlar & Reaksiya",
        "type": "Default",
        "rate": 1500.0,
        "min": 100,
        "max": 100000,
        "desc": "1-5 daqiqada boshlanadi. Har qanday kanal uchun mos."
    },
    {
        "service": 104,
        "name": "👍 Telegram Reaksiyalar (Pozitiv ❤️🔥👍)",
        "category": "✈️ Telegram Ko'rishlar & Reaksiya",
        "type": "Default",
        "rate": 3000.0,
        "min": 50,
        "max": 10000,
        "desc": "Aralash ijobiy reaksiyalar. Tezkor start."
    },
    # Instagram
    {
        "service": 201,
        "name": "📸 Instagram Obunachi (Sifatli / Chiqmas)",
        "category": "📸 Instagram Obunachilar",
        "type": "Default",
        "rate": 22000.0,
        "min": 100,
        "max": 50000,
        "desc": "Tezkor start. Profillari to'liq profilli obunachilar. Kafolat 30 kun."
    },
    {
        "service": 202,
        "name": "📸 Instagram Obunachi (O'zbek / Faol)",
        "category": "📸 Instagram Obunachilar",
        "type": "Default",
        "rate": 45000.0,
        "min": 100,
        "max": 20000,
        "desc": "O'zbekiston auditoriyasi. Profil rivojlantirish uchun a'lo."
    },
    {
        "service": 203,
        "name": "❤️ Instagram Layk (Tezkor / Rasm & Video)",
        "category": "📸 Instagram Layk & Ko'rish",
        "type": "Default",
        "rate": 4000.0,
        "min": 50,
        "max": 20000,
        "desc": "Post joylangandan so'ng darhol kiritish mumkin. Soni cheklanmagan."
    },
    {
        "service": 204,
        "name": "🎬 Instagram Reels & Video Ko'rish (Tezkor)",
        "category": "📸 Instagram Layk & Ko'rish",
        "type": "Default",
        "rate": 2000.0,
        "min": 100,
        "max": 500000,
        "desc": "Tavsiyalar (Rekomendatsiya)ga chiqish ehtimolini oshiradi."
    },
    # TikTok
    {
        "service": 301,
        "name": "🎵 TikTok Obunachi (Dunyo / Tezkor)",
        "category": "🎵 TikTok Xizmatlari",
        "type": "Default",
        "rate": 35000.0,
        "min": 100,
        "max": 30000,
        "desc": "Stream ochish (1000 obunachi) va profilni ko'tarish uchun."
    },
    {
        "service": 302,
        "name": "🎵 TikTok Video Layklar",
        "category": "🎵 TikTok Xizmatlari",
        "type": "Default",
        "rate": 8000.0,
        "min": 100,
        "max": 50000,
        "desc": "Tezkor yuklanadi. Video reytingini ko'taradi."
    },
    {
        "service": 303,
        "name": "👁️ TikTok Video Ko'rishlar (Ultra Tez)",
        "category": "🎵 TikTok Xizmatlari",
        "type": "Default",
        "rate": 1000.0,
        "min": 1000,
        "max": 1000000,
        "desc": "Rekomendatsiyaga tezroq tushish uchun ideal."
    },
    # YouTube
    {
        "service": 401,
        "name": "🎬 YouTube Obunachi (Monetizatsiya uchun)",
        "category": "🎬 YouTube Xizmatlari",
        "type": "Default",
        "rate": 95000.0,
        "min": 50,
        "max": 10000,
        "desc": "Sekin va xavfsiz qo'shiladi. Chiqib ketmaydi. 30 kun kafolat."
    },
    {
        "service": 402,
        "name": "👁️ YouTube Video Ko'rish (Real foydalanuvchilar)",
        "category": "🎬 YouTube Xizmatlari",
        "type": "Default",
        "rate": 28000.0,
        "min": 500,
        "max": 100000,
        "desc": "Ushlab turish vaqti (Retention) yuqori ko'rishlar."
    },
    {
        "service": 403,
        "name": "👍 YouTube Video Layklar",
        "category": "🎬 YouTube Xizmatlari",
        "type": "Default",
        "rate": 15000.0,
        "min": 50,
        "max": 20000,
        "desc": "Yuqori sifatli YouTube layklari."
    }
]

# Fallback virtual numbers services & countries
DEFAULT_NUMBER_SERVICES = [
    {"code": "tg", "name": "✈️ Telegram", "price": 9500},
    {"code": "wa", "name": "💬 WhatsApp", "price": 12000},
    {"code": "ig", "name": "📸 Instagram", "price": 6000},
    {"code": "tk", "name": "🎵 TikTok", "price": 7000},
    {"code": "go", "name": "🔍 Google / Gmail", "price": 8500},
    {"code": "vk", "name": "🟦 VKontakte", "price": 7500},
    {"code": "fb", "name": "🔷 Facebook", "price": 6500},
    {"code": "vi", "name": "🟣 Viber", "price": 8000}
]

DEFAULT_NUMBER_COUNTRIES = [
    {"country": 1, "name": "🇷🇺 Rossiya (+7)", "price": 8500},
    {"country": 2, "name": "🇰🇿 Qozog'iston (+7)", "price": 9000},
    {"country": 3, "name": "🇰🇬 Qirg'iziston (+996)", "price": 9500},
    {"country": 4, "name": "🇺🇸 AQSh (+1)", "price": 12000},
    {"country": 5, "name": "🇬🇧 Buyuk Britaniya (+44)", "price": 14000},
    {"country": 6, "name": "🇮🇩 Indoneziya (+62)", "price": 6500},
    {"country": 7, "name": "🇻🇳 Vyetnam (+84)", "price": 6000},
    {"country": 8, "name": "🇵🇭 Filippin (+63)", "price": 6500}
]


class SeenSMSClient:
    def __init__(self, api_url=SEEN_API_URL):
        self.api_url = api_url

    async def _get_key(self):
        return await db.get_setting("seen_api_key", "")

    async def _post(self, data: dict):
        key = await self._get_key()
        if not key:
            return {"error": "API key kiritilmagan. Admin /admin orqali kalit kiritishi lozim."}

        post_data = {"key": key, **data}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, data=post_data, timeout=15) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        text = await resp.text()
                        logger.error(f"SeenSMS API error status {resp.status}: {text}")
                        return {"error": f"API Xatosi ({resp.status}): {text}"}
        except Exception as e:
            logger.error(f"SeenSMS connection error: {e}")
            return {"error": f"Tarmoq xatosi: {str(e)}"}

    async def get_balance(self):
        """Returns {balance: float, currency: str} or fallback."""
        key = await self._get_key()
        if not key:
            return {"balance": 0.0, "currency": "UZS", "connected": False}
        res = await self._post({"action": "balance"})
        if isinstance(res, dict) and "balance" in res:
            return {"balance": float(res["balance"]), "currency": res.get("currency", "UZS"), "connected": True}
        return {"balance": 0.0, "currency": "UZS", "connected": False, "error": res.get("error")}

    async def fetch_services(self):
        """Fetches services from live API or falls back to standard catalog."""
        key = await self._get_key()
        if key:
            res = await self._post({"action": "services"})
            if isinstance(res, list) and len(res) > 0:
                await db.sync_services(res)
                return res
        # If no key or API failed, sync default catalog to DB
        await db.sync_services(DEFAULT_SMM_SERVICES)
        return DEFAULT_SMM_SERVICES

    async def add_order(self, service_id: int, link: str, quantity: int):
        """Creates an SMM order via SeenSMS API."""
        key = await self._get_key()
        if not key:
            # Simulation mode when API key is pending
            import random
            sim_id = random.randint(100000, 999999)
            return {"order": sim_id, "simulated": True}

        res = await self._post({
            "action": "add",
            "service": service_id,
            "link": link,
            "quantity": quantity
        })
        return res

    async def get_order_status(self, order_id: int):
        """Checks SMM order status."""
        key = await self._get_key()
        if not key:
            return {"status": "Processing", "remains": 0, "start_count": 100}
        return await self._post({"action": "status", "order": order_id})

    # Virtual Numbers Methods
    async def get_numbers_services(self):
        key = await self._get_key()
        if key:
            res = await self._post({"action": "numbers_services"})
            if isinstance(res, list) and len(res) > 0:
                return res
        return DEFAULT_NUMBER_SERVICES

    async def get_numbers_countries(self, service_code: str):
        key = await self._get_key()
        if key:
            res = await self._post({"action": "numbers_countries", "service": service_code})
            if isinstance(res, list) and len(res) > 0:
                return res
        return DEFAULT_NUMBER_COUNTRIES

    async def buy_number(self, country: int, service_code: str):
        key = await self._get_key()
        if not key:
            # Demo/simulated number
            import random
            sim_order_id = random.randint(200000, 899999)
            sim_phone = f"+99890{random.randint(1000000, 9999999)}"
            return {"id": sim_order_id, "phone": sim_phone, "simulated": True}

        return await self._post({
            "action": "numbers_get",
            "country": country,
            "service": service_code
        })

    async def get_number_status(self, number_order_id: int):
        key = await self._get_key()
        if not key:
            # Simulated code after delay
            import random
            return {"status": "RECEIVED", "code": str(random.randint(10000, 99999))}
        return await self._post({"action": "numbers_status", "id": number_order_id})

    async def cancel_number(self, number_order_id: int):
        key = await self._get_key()
        if not key:
            return {"status": "CANCELLED"}
        return await self._post({"action": "numbers_cancel", "id": number_order_id})


seen_client = SeenSMSClient()
