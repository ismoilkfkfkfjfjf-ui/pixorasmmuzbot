from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from config import ADMINS, WEBAPP_URL, is_admin, is_owner

def get_start_inline_keyboard(user_id: int, webapp_url: str = None) -> InlineKeyboardMarkup:
    """Xabar tagidagi asosiy Inline menyu tugmalari."""
    target_url = webapp_url or WEBAPP_URL
    buttons = [
        [
            InlineKeyboardButton(text="🎁 Bepul Xizmatlar", callback_data="free_act:tg_sub"),
            InlineKeyboardButton(text="⚡ SMM Xizmatlari", callback_data="btn_smm")
        ],
        [
            InlineKeyboardButton(text="📲 Virtual Raqamlar", callback_data="btn_numbers"),
            InlineKeyboardButton(text="💳 Balans to'ldirish", callback_data="btn_balance")
        ],
        [
            InlineKeyboardButton(text="👤 Shaxsiy Kabinet", callback_data="btn_profile"),
            InlineKeyboardButton(text="📦 Buyurtmalarim", callback_data="btn_orders")
        ],
        [
            InlineKeyboardButton(text="🎟 Promokod", callback_data="btn_promocode"),
            InlineKeyboardButton(text="🛍️ Xizmatlar Do'koni", callback_data="open_shop")
        ],
        [
            InlineKeyboardButton(text="📥 Bio & Profil Rasm", callback_data="btn_downloader"),
            InlineKeyboardButton(text="💬 Qo'llab-quvvatlash", callback_data="btn_support")
        ],
        [
            InlineKeyboardButton(text="📱 Mini App (Do'kon)", web_app=WebAppInfo(url=target_url))
        ]
    ]

    if is_admin(user_id):
        buttons.append([InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="btn_admin")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    """Pastki Reply klaviatura tugmalari."""
    buttons = [
        [
            KeyboardButton(text="🎁 Bepul Xizmatlar"),
            KeyboardButton(text="⚡ SMM Xizmatlari")
        ],
        [
            KeyboardButton(text="📲 Virtual Raqamlar"),
            KeyboardButton(text="💳 Balans to'ldirish")
        ],
        [
            KeyboardButton(text="👤 Shaxsiy Kabinet"),
            KeyboardButton(text="📦 Buyurtmalarim")
        ],
        [
            KeyboardButton(text="🎟 Promokod"),
            KeyboardButton(text="🛍️ Xizmatlar Do'koni")
        ],
        [
            KeyboardButton(text="📥 Bio & Profil Rasm"),
            KeyboardButton(text="💬 Qo'llab-quvvatlash")
        ]
    ]

    if is_admin(user_id):
        buttons.append([KeyboardButton(text="⚙️ Admin Panel")])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_free_services_inline() -> InlineKeyboardMarkup:
    """Bepul xizmatlar tugmalari (SeenSMS rasmidagidek)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✈️ Bepul Telegram Obunachi", callback_data="free_act:tg_sub")],
        [InlineKeyboardButton(text="✈️ Bepul Telegram Ko'rish", callback_data="free_act:tg_view")],
        [InlineKeyboardButton(text="✈️ Bepul Telegram Reaksiya", callback_data="free_act:tg_react")],
        [InlineKeyboardButton(text="📸 Bepul Instagram Ko'rish", callback_data="free_act:ig_view")],
        [InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="btn_home")]
    ])


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


def get_support_inline(support_username: str = "ismoiluzb022") -> InlineKeyboardMarkup:
    clean_username = str(support_username).lstrip("@").strip()
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👨‍💻 Administrator", url=f"https://t.me/{clean_username}"),
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


def get_subcategories_inline(category: str) -> InlineKeyboardMarkup:
    """Ijtimoiy tarmoq ichidagi aniq bo'limlar (obunachi, layk, ko'rish)."""
    buttons = []
    if category == "Telegram":
        buttons = [
            [
                InlineKeyboardButton(text="👥 Obunachilar (Kafolatli & Jonli)", callback_data="subcat:Telegram:obunachi"),
            ],
            [
                InlineKeyboardButton(text="👁 Post Ko'rishlar (Tezkor)", callback_data="subcat:Telegram:korish"),
                InlineKeyboardButton(text="👍 Reaksiyalar (Pozitiv)", callback_data="subcat:Telegram:reaksiya")
            ],
            [
                InlineKeyboardButton(text="💎 Premium Obunachilar", callback_data="subcat:Telegram:premium"),
                InlineKeyboardButton(text="📋 Barcha Telegram xizmatlari", callback_data="subcat:Telegram:all")
            ]
        ]
    elif category == "Instagram":
        buttons = [
            [
                InlineKeyboardButton(text="👥 Obunachilar (Kafolatli)", callback_data="subcat:Instagram:obunachi"),
            ],
            [
                InlineKeyboardButton(text="❤️ Layklar (Tezkor)", callback_data="subcat:Instagram:layk"),
                InlineKeyboardButton(text="🎬 Video & Reels Ko'rish", callback_data="subcat:Instagram:video")
            ],
            [
                InlineKeyboardButton(text="📋 Barcha Instagram xizmatlari", callback_data="subcat:Instagram:all")
            ]
        ]
    elif category == "TikTok":
        buttons = [
            [
                InlineKeyboardButton(text="👥 Obunachilar (Followers)", callback_data="subcat:TikTok:obunachi"),
            ],
            [
                InlineKeyboardButton(text="🎬 Video Ko'rishlar (Views)", callback_data="subcat:TikTok:korish"),
                InlineKeyboardButton(text="❤️ Layklar & Kommentlar", callback_data="subcat:TikTok:other")
            ],
            [
                InlineKeyboardButton(text="📋 Barcha TikTok xizmatlari", callback_data="subcat:TikTok:all")
            ]
        ]
    elif category == "YouTube":
        buttons = [
            [
                InlineKeyboardButton(text="🎬 Video Ko'rishlar & Jonli efir", callback_data="subcat:YouTube:korish"),
            ],
            [
                InlineKeyboardButton(text="👍 Video Layklar", callback_data="subcat:YouTube:like"),
                InlineKeyboardButton(text="👥 Obunachilar", callback_data="subcat:YouTube:obunachi")
            ],
            [
                InlineKeyboardButton(text="📋 Barcha YouTube xizmatlari", callback_data="subcat:YouTube:all")
            ]
        ]
    else:
        buttons = [
            [InlineKeyboardButton(text="📋 Barcha xizmatlar", callback_data=f"subcat:{category}:all")]
        ]

    buttons.append([
        InlineKeyboardButton(text="⬅️ Boshqa tarmoqlar", callback_data="back_categories"),
        InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="btn_home")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_services_inline(services: list, margin_percent: float, category_key: str, page: int = 0, per_page: int = 6) -> InlineKeyboardMarkup:
    total = len(services)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))

    start = page * per_page
    end = start + per_page
    page_items = services[start:end]

    keyboard = []
    for s in page_items:
        s_id = s.get("service_id") or s.get("service") or s.get("id")
        rate = round(float(s.get("rate", 0)) * (1 + margin_percent / 100))
        name = s.get("name", "Xizmat")
        if len(name) > 38:
            name = name[:36] + ".."
        btn_text = f"{name} — {rate:,} so'm".replace(",", " ")
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"srv:{s_id}")])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"srv_page:{category_key}:{page - 1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"srv_page:{category_key}:{page + 1}"))

    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([
        InlineKeyboardButton(text="⬅️ Kategoriyalar", callback_data="back_categories"),
        InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="btn_home")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_admin_inline(free_enabled: bool = True) -> InlineKeyboardMarkup:
    free_status_text = "Yoqilgan ✅" if free_enabled else "O'chirilgan ❌"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
            InlineKeyboardButton(text="💰 SeenSMS Balansi", callback_data="admin_seen_balance")
        ],
        [
            InlineKeyboardButton(text=f"🎁 Bepul xizmatlar: {free_status_text}", callback_data="admin_toggle_free")
        ],
        [
            InlineKeyboardButton(text="👑 Adminlar Boshqaruvi & Faollik", callback_data="admin_manage_admins")
        ],
        [
            InlineKeyboardButton(text="🎟 Promokodlar", callback_data="admin_promos"),
            InlineKeyboardButton(text="👥 Foydalanuvchilar (Rasmi bilan)", callback_data="admin_user_idx:0")
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
            InlineKeyboardButton(text="💬 Qo'llab-quvvatlash sozlash", callback_data="admin_set_support"),
            InlineKeyboardButton(text="🌐 Web App URL sozlash", callback_data="admin_set_url")
        ],
        [
            InlineKeyboardButton(text="🔄 Xizmatlarni Yangilash", callback_data="admin_sync_services"),
            InlineKeyboardButton(text="✉️ Xabar Tarqatish", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="btn_home")
        ]
    ])


def get_admin_management_inline(admins: list, viewer_id: int) -> InlineKeyboardMarkup:
    buttons = []
    if is_owner(viewer_id):
        buttons.append([
            InlineKeyboardButton(text="➕ Yangi Admin qo'shish", callback_data="admin_add_new_admin")
        ])
        for a in admins:
            if a.get("role") != "owner" and a.get("user_id") != viewer_id:
                name = a.get("first_name") or f"Admin {a.get('user_id')}"
                if len(name) > 18:
                    name = name[:16] + ".."
                buttons.append([
                    InlineKeyboardButton(
                        text=f"🗑 O'chirish: {name} ({a['user_id']})",
                        callback_data=f"admin_del:{a['user_id']}"
                    )
                ])

    buttons.append([
        InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="btn_admin")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_promos_inline(promos: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="➕ Yangi Promokod yaratish", callback_data="admin_add_promo")]
    ]
    for p in promos[:15]:
        p_id = p["id"]
        code = p["code"]
        rew = int(p["reward_amount"])
        uses = p["current_uses"]
        limit = f"{p['max_uses']} ta" if p["max_uses"] > 0 else "Cheksiz"
        btn_text = f"🗑 O'chirish: {code} (+{rew:,} | {uses}/{limit})".replace(",", " ")
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"del_promo:{p_id}")])

    buttons.append([InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="btn_admin")] )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_user_view_inline(current_idx: int, total_users: int, user_id: int) -> InlineKeyboardMarkup:
    buttons = []
    nav_row = []
    if current_idx > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_user_idx:{current_idx - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📌 {current_idx + 1} / {total_users}", callback_data="noop"))
    if current_idx < total_users - 1:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_user_idx:{current_idx + 1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(text="💳 Balansni o'zgartirish", callback_data=f"admin_edit_bal:{user_id}"),
        InlineKeyboardButton(text="🔍 Qidirish", callback_data="admin_search_user")
    ])
    buttons.append([
        InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="btn_admin")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
