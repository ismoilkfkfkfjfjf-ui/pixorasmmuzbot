from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from config import ADMINS, WEBAPP_URL

def get_start_inline_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Xabar tagidagi asosiy Inline menyu tugmalari."""
    buttons = [
        [
            InlineKeyboardButton(text="⚡ SMM Xizmatlari", callback_data="btn_smm"),
            InlineKeyboardButton(text="📲 Virtual Raqamlar", callback_data="btn_numbers")
        ],
        [
            InlineKeyboardButton(text="💳 Balans to'ldirish", callback_data="btn_balance"),
            InlineKeyboardButton(text="👤 Shaxsiy Kabinet", callback_data="btn_profile")
        ],
        [
            InlineKeyboardButton(text="📥 Bio & Profil Rasm", callback_data="btn_downloader"),
            InlineKeyboardButton(text="📦 Buyurtmalarim", callback_data="btn_orders")
        ],
        [
            InlineKeyboardButton(text="🛍️ Xizmatlar Do'koni", callback_data="open_shop"),
            InlineKeyboardButton(text="💬 Qo'llab-quvvatlash", callback_data="btn_support")
        ]
    ]

    if user_id in ADMINS:
        buttons.append([InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="btn_admin")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    """Pastki Reply klaviatura tugmalari."""
    buttons = [
        [
            KeyboardButton(text="⚡ SMM Xizmatlari"),
            KeyboardButton(text="📲 Virtual Raqamlar")
        ],
        [
            KeyboardButton(text="💳 Balans to'ldirish"),
            KeyboardButton(text="👤 Shaxsiy Kabinet")
        ],
        [
            KeyboardButton(text="📥 Bio & Profil Rasm"),
            KeyboardButton(text="📦 Buyurtmalarim")
        ],
        [
            KeyboardButton(text="🛍️ Xizmatlar Do'koni"),
            KeyboardButton(text="💬 Qo'llab-quvvatlash")
        ]
    ]

    if user_id in ADMINS:
        buttons.append([KeyboardButton(text="⚙️ Admin Panel")])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )


def get_cancel_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="btn_home")]
    ])


def get_profile_inline(bot_username: str, user_id: int) -> InlineKeyboardMarkup:
    share_text = f"https://t.me/share/url?url=https://t.me/{bot_username}?start=ref_{user_id}&text=Eng+arzon+va+sifatli+SMM+hamda+Virtual+raqamlar+boti!"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 Balans to'ldirish", callback_data="btn_balance"),
            InlineKeyboardButton(text="👥 Do'stlarga ulashish", url=share_text)
        ],
        [
            InlineKeyboardButton(text="📦 Buyurtmalarim", callback_data="btn_orders"),
            InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="btn_home")
        ]
    ])


def get_balance_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 To'lov qildim (Chek yuborish)", callback_data="btn_send_receipt")],
        [InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="btn_home")]
    ])


def get_orders_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡ SMM Buyurtma", callback_data="btn_smm"),
            InlineKeyboardButton(text="📲 Raqam Olish", callback_data="btn_numbers")
        ],
        [InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="btn_home")]
    ])


def get_support_inline(support_username: str = "PixoraSupport") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👨‍💻 Administrator", url=f"https://t.me/{support_username}"),
            InlineKeyboardButton(text="📢 Rasmiy Kanal", url="https://t.me/pixorasmm")
        ],
        [InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="btn_home")]
    ])


def get_categories_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✈️ Telegram", callback_data="cat:Telegram"),
            InlineKeyboardButton(text="📸 Instagram", callback_data="cat:Instagram")
        ],
        [
            InlineKeyboardButton(text="🎵 TikTok", callback_data="cat:TikTok"),
            InlineKeyboardButton(text="🎬 YouTube", callback_data="cat:YouTube")
        ],
        [
            InlineKeyboardButton(text="📋 Barcha xizmatlar ro'yxati", callback_data="open_shop")
        ],
        [
            InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="btn_home")
        ]
    ])


def get_services_inline(services: list, margin_percent: float, category: str) -> InlineKeyboardMarkup:
    keyboard = []
    for s in services[:8]:
        s_id = s.get("service_id") or s.get("service") or s.get("id")
        rate = round(float(s.get("rate", 0)) * (1 + margin_percent / 100))
        btn_text = f"{s.get('name', 'Xizmat')} — {rate:,} so'm".replace(",", " ")
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"srv:{s_id}")])

    keyboard.append([
        InlineKeyboardButton(text="⬅️ Kategoriyalar", callback_data="back_categories"),
        InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="btn_home")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
            InlineKeyboardButton(text="💰 SeenSMS Balansi", callback_data="admin_seen_balance")
        ],
        [
            InlineKeyboardButton(text="🔑 Seen API Kalit", callback_data="admin_set_api_key"),
            InlineKeyboardButton(text="📈 Ustama Foiz (%)", callback_data="admin_set_margin")
        ],
        [
            InlineKeyboardButton(text="💳 Karta sozlamasi", callback_data="admin_set_card"),
            InlineKeyboardButton(text="➕/➖ Foydalanuvchi Balansi", callback_data="admin_user_balance")
        ],
        [
            InlineKeyboardButton(text="✉️ Xabar Tarqatish", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="🔄 Xizmatlarni Yangilash", callback_data="admin_sync_services")
        ],
        [
            InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="btn_home")
        ]
    ])
