import aiohttp
import logging
from config import ADMINS, BOT_TOKEN

logger = logging.getLogger(__name__)

MAINTENANCE_SMM_MSG = (
    "🛠 <b>Ushbu xizmatda texnik ta'mirlash ishlari olib borilmoqda!</b>\n\n"
    "Serverlarimizda yangilash va profilaktika ishlari ketayotganligi sababli "
    "buyurtma vaqtincha to'xtatildi. Balansingizdan hech qanday mablag' yechilmadi.\n\n"
    "Iltimos, birozdan so'ng qayta urinib ko'ring yoki boshqa xizmatni tanlang."
)

MAINTENANCE_FREE_MSG = (
    "🛠 <b>Bepul xizmatda texnik ta'mirlash ishlari olib borilmoqda!</b>\n\n"
    "Hozirda bepul xizmat serverlarida profilaktika ishlari ketmoqda. "
    "Iltimos, birozdan so'ng qayta urinib ko'ring."
)

MAINTENANCE_NUMBER_MSG = (
    "🛠 <b>Virtual raqamlar bo'limida ta'mirlash ishlari olib borilmoqda!</b>\n\n"
    "Serverda texnik ta'mirlash ishlari sababli raqam berish vaqtincha to'xtatildi. "
    "Balansingizdan hech qanday mablag' yechilmadi.\n\n"
    "Iltimos, birozdan so'ng qayta urinib ko'ring."
)

WEB_MAINTENANCE_MSG = "🛠 Ushbu xizmatda texnik ta'mirlash ishlari olib borilmoqda. Balansingizdan pul yechilmadi. Iltimos, birozdan so'ng qayta urinib ko'ring."
WEB_FREE_MAINTENANCE_MSG = "🛠 Hozirda ushbu bepul xizmatda profilaktika va ta'mirlash ishlari olib borilmoqda. Iltimos, birozdan so'ng qayta urinib ko'ring."

def is_balance_or_provider_error(err: Exception | str) -> bool:
    """Checks if error is due to low SeenSMS balance or provider maintenance."""
    s = str(err).lower()
    keywords = [
        "insufficient balance",
        "not enough balance",
        "mablag' yetarli emas",
        "balance",
        "provayderda balans",
        "no balance"
    ]
    return any(k in s for k in keywords)

async def notify_admins(text: str, bot=None):
    """Sends high priority notification to all bot admins."""
    if bot:
        for admin_id in ADMINS:
            try:
                await bot.send_message(admin_id, text, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Could not notify admin {admin_id} via bot: {e}")
        return

    # Fallback to direct HTTP request if bot is not available
    try:
        async with aiohttp.ClientSession() as session:
            for admin_id in ADMINS:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {
                    "chat_id": admin_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True
                }
                async with session.post(url, json=payload, timeout=5) as resp:
                    if resp.status != 200:
                        logger.warning(f"Failed to notify admin {admin_id}: HTTP {resp.status}")
    except Exception as e:
        logger.error(f"Error notifying admins: {e}")

async def notify_admin_low_balance(user_id: int, service_name: str, bot=None):
    """Alerts admin that user attempted an order but SeenSMS balance is 0."""
    text = (
        "🚨 <b>SHOSHILINCH (ADMIN OGOHLANTIRISHI):</b>\n\n"
        f"👤 Foydalanuvchi ID: <code>{user_id}</code>\n"
        f"📌 Xizmat: <b>{service_name}</b>\n\n"
        "⚠️ <b>SeenSMS provayderida mablag'ingiz tugagan (0 UZS)!</b>\n"
        "Foydalanuvchiga: <i>'🛠 Texnik ta'mirlash ishlari ketmoqda'</i> deb ko'rsatildi va uning balansi yechilmadi.\n\n"
        "👉 Xizmatlar to'xtab qolmasligi uchun zudlik bilan "
        "<a href='https://seensms.uz'>seensms.uz</a> hisobingizni to'ldiring!"
    )
    await notify_admins(text, bot=bot)
