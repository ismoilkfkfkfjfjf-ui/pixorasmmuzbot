from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from config import ASSETS_DIR, ADMINS, WEBAPP_URL
from database import db
from handlers.keyboards import (
    get_main_keyboard,
    get_start_inline_keyboard,
    get_cancel_keyboard,
    get_cancel_inline,
    get_profile_inline,
    get_balance_inline,
    get_orders_inline,
    get_support_inline,
    get_categories_inline
)
from handlers.states import DepositStates, DownloaderStates
from downloader import profile_downloader

router = Router()

def get_start_text(first_name: str) -> str:
    return (
        f"👋 Assalomu alaykum, <b>{first_name}</b>!\n\n"
        f"🚀 <b>Pixora SMM</b> — Eng tezkor va sifatli SMM xizmatlari hamda Virtual Raqamlar platformasiga xush kelibsiz!\n\n"
        f"🔹 <b>Instagram, Telegram, TikTok, YouTube</b> uchun obunachilar, layklar, ko'rishlar\n"
        f"🔹 <b>Virtual raqamlar</b> — SMS kod qabul qilish (Telegram, WhatsApp, va b.)\n"
        f"🔹 <b>Bio & Profil rasm yuklovchi</b> — HD sifatda\n"
        f"🔹 <b>24/7 Avtomatlashtirilgan tizim</b>\n\n"
        f"👇 <b>Quyidagi tugmalardan birini tanlang:</b>"
    )

async def edit_or_reply(event: types.Message | types.CallbackQuery, text: str, reply_markup=None):
    """Xabarni joyida (in-place) yangilaydi — ortiqcha yangi matnli xabarlar beravermaydi."""
    if isinstance(event, types.CallbackQuery):
        msg = event.message
        try:
            if msg.photo:
                if len(text) <= 1024:
                    await msg.edit_caption(caption=text, parse_mode="HTML", reply_markup=reply_markup)
                    return
                else:
                    await msg.delete()
                    await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
                    return
            else:
                await msg.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
                return
        except Exception:
            try:
                await msg.delete()
            except Exception:
                pass
            await msg.answer(text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=reply_markup)

@router.message(F.text.in_({"❌ Bekor qilish", "🏠 Asosiy Menyu", "/menu"}))
@router.callback_query(F.data == "btn_home")
async def home_handler(event: types.Message | types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = event.from_user.id
    first_name = event.from_user.first_name or "Foydalanuvchi"
    text = get_start_text(first_name)
    saved_url = await db.get_setting("webapp_url", WEBAPP_URL)
    inline_kb = get_start_inline_keyboard(user_id, saved_url)

    await edit_or_reply(event, text, inline_kb)
    if isinstance(event, types.CallbackQuery):
        await event.answer()

@router.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or "Foydalanuvchi"

    # Check referral
    referrer_id = None
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            potential_ref = int(args[1].replace("ref_", ""))
            if potential_ref != user_id:
                referrer_id = potential_ref
        except ValueError:
            pass

    user = await db.get_or_create_user(user_id, username, first_name, referrer_id)

    if referrer_id:
        ref_bonus = float(await db.get_setting("ref_bonus", "500"))
        await db.update_balance(referrer_id, ref_bonus)
        try:
            await message.bot.send_message(
                referrer_id,
                f"🎉 Sizning taklif havolangiz orqali yangi foydalanuvchi (@{username or first_name}) qo'shildi!\n"
                f"💰 Hisobingizga +{int(ref_bonus):,} so'm bonus berildi!".replace(",", " ")
            )
        except Exception:
            pass

    caption = get_start_text(first_name)
    banner_path = ASSETS_DIR / "pixora_banner.jpg"
    logo_path = ASSETS_DIR / "pixora_logo.jpg"
    photo_to_send = banner_path if banner_path.exists() else (logo_path if logo_path.exists() else None)

    saved_url = await db.get_setting("webapp_url", WEBAPP_URL)
    inline_kb = get_start_inline_keyboard(user_id, saved_url)

    # Faqat bitta toza xabar — ortiqcha matnli reply klaviatura jo'natilmaydi!
    if photo_to_send:
        await message.answer_photo(
            photo=types.FSInputFile(str(photo_to_send)),
            caption=caption,
            parse_mode="HTML",
            reply_markup=inline_kb
        )
    else:
        await message.answer(
            caption,
            parse_mode="HTML",
            reply_markup=inline_kb
        )


# Profile Handler
@router.message(F.text == "👤 Shaxsiy Kabinet")
@router.message(Command("profile"))
@router.callback_query(F.data == "btn_profile")
async def profile_handler(event: types.Message | types.CallbackQuery):
    user_id = event.from_user.id
    user = await db.get_user(user_id)
    if not user:
        user = await db.get_or_create_user(user_id, event.from_user.username, event.from_user.first_name)

    balance = int(user.get("balance", 0))
    spent = int(user.get("spent_total", 0))
    ref_count = user.get("referrals_count", 0)
    ref_earned = int(user.get("referral_earned", 0))

    bot_info = await event.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"

    text = (
        f"👤 <b>Shaxsiy Kabinet:</b>\n\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"👤 <b>Ism:</b> {user.get('first_name', '')}\n"
        f"💳 <b>Balans:</b> <b>{balance:,} so'm</b>\n"
        f"📉 <b>Jami sarflangan:</b> {spent:,} so'm\n\n"
        f"👥 <b>Referal tizimi:</b>\n"
        f"├ Taklif qilingan do'stlar: <b>{ref_count} ta</b>\n"
        f"├ Referal daromadi: <b>{ref_earned:,} so'm</b>\n"
        f"└ Havolangiz:\n<code>{ref_link}</code>\n\n"
        f"<i>Do'stlaringizni taklif qilib, har bir do'stingiz uchun 500 so'm bonus oling!</i>"
    ).replace(",", " ")

    inline_kb = get_profile_inline(bot_info.username, user_id)
    await edit_or_reply(event, text, inline_kb)
    if isinstance(event, types.CallbackQuery):
        await event.answer()


# Balance Handler
@router.message(F.text == "💳 Balans to'ldirish")
@router.message(Command("balance"))
@router.callback_query(F.data == "btn_balance")
async def balance_handler(event: types.Message | types.CallbackQuery, state: FSMContext):
    user_id = event.from_user.id
    user = await db.get_user(user_id)
    balance = int(user.get("balance", 0)) if user else 0

    card_number = await db.get_setting("card_number", "8600 0000 0000 0000")
    card_holder = await db.get_setting("card_holder", "Pixora SMM")
    min_deposit = int(await db.get_setting("min_deposit", "5000"))

    text = (
        f"💳 <b>Balansni to'ldirish:</b>\n\n"
        f"Sizning joriy balansingiz: <b>{balance:,} so'm</b>\n\n"
        f"To'lov uchun karta:\n"
        f"💳 <code>{card_number}</code>\n"
        f"👤 Qabul qiluvchi: <b>{card_holder}</b>\n"
        f"💰 Minimal to'lov: <b>{min_deposit:,} so'm</b>\n\n"
        f"To'lov qilganingizdan so'ng, pastdagi <b>📥 To'lov qildim (Chek yuborish)</b> tugmasini bosing:"
    ).replace(",", " ")

    inline_kb = get_balance_inline()
    await edit_or_reply(event, text, inline_kb)
    if isinstance(event, types.CallbackQuery):
        await event.answer()


@router.callback_query(F.data == "btn_send_receipt")
async def start_deposit_flow(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(DepositStates.waiting_for_amount)
    await callback.message.answer(
        "Qancha mablag' o'tkazdingiz? (Summani faqat raqamlarda kiriting, masalan: <code>10000</code>):",
        parse_mode="HTML",
        reply_markup=get_cancel_inline()
    )
    await callback.answer()


@router.message(DepositStates.waiting_for_amount)
async def deposit_amount_handler(message: types.Message, state: FSMContext):
    amount_str = message.text.replace(" ", "").strip()
    try:
        amount = float(amount_str)
        min_dep = float(await db.get_setting("min_deposit", "5000"))
        if amount < min_dep:
            await message.answer(f"Minimal to'lov miqdori: {int(min_dep):,} so'm. Iltimos qaytadan kiriting:".replace(",", " "))
            return
        await state.update_data(amount=amount)
        await state.set_state(DepositStates.waiting_for_receipt)
        await message.answer(
            f"✅ Qabul qilindi: <b>{int(amount):,} so'm</b>.\n\n"
            f"Endi to'lov chekini (rasm yoki skrinshot) yuboring:".replace(",", " "),
            parse_mode="HTML",
            reply_markup=get_cancel_inline()
        )
    except ValueError:
        await message.answer("Iltimos, to'g'ri raqam kiriting (masalan: 10000):")


@router.message(DepositStates.waiting_for_receipt, F.photo)
async def deposit_receipt_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("amount", 0)
    photo_id = message.photo[-1].file_id

    user_id = message.from_user.id
    dep_id = await db.create_deposit(user_id, amount, photo_id)

    await state.clear()
    saved_url = await db.get_setting("webapp_url", WEBAPP_URL)
    await message.answer(
        f"✅ To'lov chekingiz qabul qilindi (Ariza #{dep_id})!\n"
        f"Administrator tekshirib chiqqach, mablag' balansingizga qo'shiladi.",
        reply_markup=get_start_inline_keyboard(user_id, saved_url)
    )

    # Notify admins
    inline_kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"dep_ok:{dep_id}"),
            types.InlineKeyboardButton(text="❌ Rad etish", callback_data=f"dep_no:{dep_id}")
        ]
    ])

    admin_text = (
        f"📥 <b>Yangi to'lov arizasi #{dep_id}!</b>\n\n"
        f"👤 Foydalanuvchi: <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a> (<code>{user_id}</code>)\n"
        f"💰 Summa: <b>{int(amount):,} so'm</b>\n"
        f"To'lovni tasdiqlaysizmi?".replace(",", " ")
    )

    for admin_id in ADMINS:
        try:
            await message.bot.send_photo(
                admin_id,
                photo=photo_id,
                caption=admin_text,
                parse_mode="HTML",
                reply_markup=inline_kb
            )
        except Exception:
            pass


# Bio & Avatar Downloader Handler
@router.message(F.text == "📥 Bio & Profil Rasm")
@router.message(Command("downloader"))
@router.callback_query(F.data == "btn_downloader")
async def downloader_prompt_handler(event: types.Message | types.CallbackQuery, state: FSMContext):
    await state.set_state(DownloaderStates.waiting_for_username)
    text = (
        "📥 <b>Profil Rasm & Bio Yuklovchi:</b>\n\n"
        "Instagram yoki Telegram profil linkini yoki usernameni yuboring:\n"
        "<i>Masalan: <code>@username</code> yoki <code>https://t.me/kanal</code> yoki <code>https://instagram.com/profil</code></i>"
    )

    if isinstance(event, types.CallbackQuery):
        await event.message.answer(text, parse_mode="HTML", reply_markup=get_cancel_keyboard())
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=get_cancel_keyboard())


@router.message(DownloaderStates.waiting_for_username)
async def downloader_process_handler(message: types.Message, state: FSMContext):
    user_input = message.text.strip()
    platform, username = profile_downloader.clean_username(user_input)

    wait_msg = await message.answer("🔍 Profil ma'lumotlari yuklanmoqda, iltimos kuting...")

    try:
        if platform == "telegram" or platform == "auto":
            data = await profile_downloader.get_telegram_profile(username)
        else:
            data = await profile_downloader.get_instagram_profile(username)

        if "error" in data:
            if platform == "auto":
                data = await profile_downloader.get_instagram_profile(username)

        await wait_msg.delete()

        if "error" in data:
            await message.answer(f"❌ Xatolik: {data['error']}", reply_markup=get_main_keyboard(message.from_user.id))
            await state.clear()
            return

        caption = (
            f"✅ <b>{data.get('platform', '')} Profil ma'lumotlari:</b>\n\n"
            f"👤 <b>Nomi:</b> {data.get('title', '')}\n"
            f"🔗 <b>Username:</b> {data.get('username', '')}\n"
            f"📝 <b>Bio:</b>\n{data.get('bio', '')}\n"
        )
        if data.get("extra"):
            caption += f"📊 <b>A'zolar/Statistika:</b> {data['extra']}\n"

        avatar = data.get("avatar_url")
        back_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="btn_home")]
        ])

        if avatar:
            await message.answer_photo(
                photo=avatar,
                caption=caption,
                parse_mode="HTML",
                reply_markup=back_kb
            )
        else:
            await message.answer(
                caption,
                parse_mode="HTML",
                reply_markup=back_kb
            )
    except Exception as e:
        await wait_msg.delete()
        saved_url = await db.get_setting("webapp_url", WEBAPP_URL)
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}", reply_markup=get_start_inline_keyboard(message.from_user.id, saved_url))

    await state.clear()


# Orders Handler
@router.message(F.text == "📦 Buyurtmalarim")
@router.message(Command("orders"))
@router.callback_query(F.data == "btn_orders")
async def user_orders_handler(event: types.Message | types.CallbackQuery):
    user_id = event.from_user.id
    orders = await db.get_user_orders(user_id, limit=5)
    numbers = await db.get_user_numbers(user_id, limit=3)

    if not orders and not numbers:
        text = "Sizda hali hech qanday buyurtma mavjud emas."
    else:
        text = "📦 <b>Sizning so'nggi buyurtmalaringiz:</b>\n\n"
        if orders:
            text += "<b>⚡ SMM Buyurtmalar:</b>\n"
            for o in orders:
                status_emoji = "⏳" if o["status"] == "pending" else "✅"
                text += (
                    f"{status_emoji} <b>#{o['id']}</b> — {o['service_name']}\n"
                    f"   ├ Soni: {o['quantity']:,} ta | Narxi: {int(o['price']):,} so'm\n"
                    f"   └ Holati: <code>{o['status']}</code>\n"
                ).replace(",", " ")

        if numbers:
            text += "\n<b>📲 Virtual Raqamlar:</b>\n"
            for n in numbers:
                sms = f"<code>{n['sms_code']}</code>" if n["sms_code"] else "<i>Kod kutilmoqda...</i>"
                text += (
                    f"📱 <b>{n['phone']}</b> ({n['service_title']})\n"
                    f"   └ SMS Kod: {sms}\n"
                )

    inline_kb = get_orders_inline()
    await edit_or_reply(event, text, inline_kb)
    if isinstance(event, types.CallbackQuery):
        await event.answer()


# Support Handler
@router.message(F.text == "💬 Qo'llab-quvvatlash")
@router.message(Command("help"))
@router.callback_query(F.data == "btn_support")
async def support_handler(event: types.Message | types.CallbackQuery):
    support_username = await db.get_setting("support_username", "ismoiluzb022")
    clean_username = str(support_username).lstrip("@").strip()
    text = (
        f"💬 <b>Qo'llab-quvvatlash xizmati:</b>\n\n"
        f"Savollar, takliflar yoki to'lov bo'yicha muammolar yuzaga kelsa, adminga murojaat qiling:\n\n"
        f"👨‍💻 Aloqa: @{clean_username}\n"
        f"📢 Yangiliklar kanali: https://t.me/pixorasmm"
    )
    inline_kb = get_support_inline(clean_username)
    await edit_or_reply(event, text, inline_kb)
    if isinstance(event, types.CallbackQuery):
        await event.answer()
