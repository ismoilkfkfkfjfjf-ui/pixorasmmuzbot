from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import ADMINS, WEBAPP_URL
from database import db
from seen_api import seen_client
from handlers.keyboards import get_admin_inline, get_cancel_inline
from handlers.states import AdminStates
from handlers.user_handlers import edit_or_reply

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

@router.message(F.text == "⚙️ Admin Panel")
@router.message(Command("admin"))
@router.callback_query(F.data == "btn_admin")
async def admin_panel_handler(event: types.Message | types.CallbackQuery, state: FSMContext = None):
    if state:
        await state.clear()
    user_id = event.from_user.id
    if not is_admin(user_id):
        if isinstance(event, types.CallbackQuery):
            await event.answer("Kechirasiz, siz admin emassiz.", show_alert=True)
        else:
            await event.answer("Kechirasiz, siz admin emassiz.")
        return

    current_url = await db.get_setting("webapp_url", WEBAPP_URL)
    text = (
        "⚙️ <b>Pixora SMM — Boshqaruv Paneli:</b>\n\n"
        f"🌐 <b>Web App URL:</b> <code>{current_url}</code>\n\n"
        "Kerakli bo'limni tanlang:"
    )
    inline_kb = get_admin_inline()
    await edit_or_reply(event, text, inline_kb)
    if isinstance(event, types.CallbackQuery):
        await event.answer()

@router.message(Command("seturl"))
async def set_webapp_url_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        current = await db.get_setting("webapp_url", WEBAPP_URL)
        await message.answer(
            f"🌐 <b>Hozirgi Web App URL:</b>\n<code>{current}</code>\n\n"
            f"O'zgartirish: <code>/seturl https://sizning-sayt.onrender.com</code>",
            parse_mode="HTML"
        )
        return
    new_url = args[1].strip()
    if not new_url.startswith("https://"):
        await message.answer("⚠️ Havola faqat <b>https://</b> bilan boshlanishi kerak!", parse_mode="HTML")
        return
    await db.set_setting("webapp_url", new_url)
    await message.answer(
        f"✅ <b>Web App URL yangilandi:</b>\n<code>{new_url}</code>\n\n"
        f"Barcha Mini App tugmalari shu yangi havolaga o'tdi!",
        parse_mode="HTML",
        reply_markup=get_admin_inline()
    )

@router.callback_query(F.data == "admin_set_url")
async def admin_set_url_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    current = await db.get_setting("webapp_url", WEBAPP_URL)
    await state.set_state(AdminStates.waiting_for_url)
    text = (
        f"🌐 <b>Web App havolasini o'rnatish:</b>\n\n"
        f"Hozirgi havola: <code>{current}</code>\n\n"
        f"Yangi Render havolasini yuboring (masalan: <code>https://pixorasmmuzbot.onrender.com</code>) "
        f"yoki <code>/seturl https://...</code> buyrug'idan foydalaning:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_cancel_inline())
    await callback.answer()

@router.message(AdminStates.waiting_for_url)
async def admin_save_url_state(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    new_url = message.text.strip()
    if not new_url.startswith("https://"):
        await message.answer("⚠️ Havola faqat <b>https://</b> bilan boshlanishi kerak!", reply_markup=get_cancel_inline())
        return
    await db.set_setting("webapp_url", new_url)
    await state.clear()
    await message.answer(
        f"✅ <b>Web App havolasi muvaffaqiyatli saqlandi!</b>\n\n"
        f"🌐 URL: <code>{new_url}</code>",
        parse_mode="HTML",
        reply_markup=get_admin_inline()
    )

@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    stats = await db.get_stats()
    text = (
        "📊 <b>Bot Statistikasi:</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total_users']:,} ta</b>\n"
        f"💳 Foydalanuvchilar balansi: <b>{int(stats['total_user_balance']):,} so'm</b>\n"
        f"📉 Jami sarflangan mablag': <b>{int(stats['total_user_spent']):,} so'm</b>\n\n"
        f"🛒 Jami SMM buyurtmalar: <b>{stats['total_orders']:,} ta</b>\n"
        f"💰 SMM aylanmasi: <b>{int(stats['total_orders_sum']):,} so'm</b>\n"
        f"📱 Virtual raqamlar: <b>{stats['total_numbers']:,} ta</b>\n\n"
        f"📥 Tasdiqlangan to'lovlar: <b>{int(stats['approved_deposits']):,} so'm</b>\n"
        f"⏳ Kutilayotgan to'lov arizalari: <b>{stats['pending_deposits']} ta</b>"
    ).replace(",", " ")

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_inline())
    await callback.answer()

@router.callback_query(F.data == "admin_seen_balance")
async def admin_seen_balance_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    try:
        b = await seen_client.balance()
        bal_val = b.get("balance", 0)
        curr_val = b.get("currency", "UZS")
        text = (
            f"💰 <b>SeenSMS API Balansi:</b>\n\n"
            f"💵 Balans: <b>{bal_val:,} {curr_val}</b>\n"
            f"🟢 Holati: Ulangan va faol!"
        ).replace(",", " ")
    except Exception as e:
        text = (
            "⚠️ <b>SeenSMS API Balansini olishda xatolik:</b>\n\n"
            f"Xatolik: <code>{str(e)}</code>\n\n"
            "Pastdagi <b>🔑 Seen API Kalit</b> tugmasi orqali API kalitni tekshiring."
        )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_inline())
    await callback.answer()

@router.callback_query(F.data == "admin_set_api_key")
async def admin_set_api_key_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    curr_key = await db.get_setting("seen_api_key", "")
    await state.set_state(AdminStates.waiting_for_api_key)
    await callback.message.answer(
        f"🔑 <b>SeenSMS API kalitini sozlash:</b>\n\n"
        f"Hozirgi kalit: <code>{curr_key or 'Kiritilmagan'}</code>\n\n"
        f"Yangi API kalitni yuboring:",
        parse_mode="HTML",
        reply_markup=get_cancel_inline()
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_api_key)
async def admin_save_api_key(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    new_key = message.text.strip()
    await db.set_setting("seen_api_key", new_key)
    await state.clear()

    # Test key
    try:
        bal = await seen_client.balance()
        bal_val = bal.get("balance", 0)
        curr_val = bal.get("currency", "UZS")
        await message.answer(
            f"✅ API kalit saqlandi va ulandi!\n"
            f"Hisob balansi: {bal_val:,} {curr_val}".replace(",", " "),
            reply_markup=get_admin_inline()
        )
    except Exception as e:
        await message.answer(
            f"⚠️ API kalit saqlandi, ammo ulanishda xatolik: {str(e)}",
            reply_markup=get_admin_inline()
        )

@router.callback_query(F.data == "admin_set_margin")
async def admin_set_margin_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    margin = await db.get_setting("margin_percent", "20.0")
    await state.set_state(AdminStates.waiting_for_margin)
    await callback.message.answer(
        f"📈 <b>Xizmatlar ustama foizi:</b>\n\n"
        f"Hozirgi foiz: <b>{margin}%</b>\n\n"
        f"Yangi foiz miqdorini kiriting (masalan: <code>25</code>):",
        parse_mode="HTML",
        reply_markup=get_cancel_inline()
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_margin)
async def admin_save_margin(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        new_margin = float(message.text.replace("%", "").strip())
        await db.set_setting("margin_percent", str(new_margin))
        await state.clear()
        await message.answer(
            f"✅ Ustama foizi <b>{new_margin}%</b> qilib belgilandi!",
            parse_mode="HTML",
            reply_markup=get_admin_inline()
        )
    except ValueError:
        await message.answer("Iltimos, to'g'ri son kiriting (masalan: 20):")

@router.callback_query(F.data == "admin_set_card")
async def admin_set_card_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    card = await db.get_setting("card_number", "8600 0000 0000 0000")
    holder = await db.get_setting("card_holder", "Pixora SMM")

    await state.set_state(AdminStates.waiting_for_card)
    await callback.message.answer(
        f"💳 <b>Karta sozlamalari:</b>\n\n"
        f"Hozirgi karta: <code>{card}</code> ({holder})\n\n"
        f"Yangi karta va egasini quyidagi formatda yuboring:\n"
        f"<code>8600 1234 5678 9012 - Ism Familiya</code>",
        parse_mode="HTML",
        reply_markup=get_cancel_inline()
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_card)
async def admin_save_card(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    text = message.text.strip()
    if "-" in text:
        parts = text.split("-")
        card_num = parts[0].strip()
        holder = parts[1].strip()
    else:
        card_num = text
        holder = "Pixora SMM"

    await db.set_setting("card_number", card_num)
    await db.set_setting("card_holder", holder)
    await state.clear()

    await message.answer(
        f"✅ Karta ma'lumotlari yangilandi:\n"
        f"💳 <code>{card_num}</code>\n"
        f"👤 {holder}",
        parse_mode="HTML",
        reply_markup=get_admin_inline()
    )

@router.callback_query(F.data == "admin_user_balance")
async def admin_balance_user_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminStates.waiting_for_user_id)
    await callback.message.answer(
        "➕/➖ <b>Foydalanuvchi balansini boshqarish:</b>\n\n"
        "Foydalanuvchining Telegram ID raqamini kiriting:",
        parse_mode="HTML",
        reply_markup=get_cancel_inline()
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_user_id)
async def admin_balance_user_id_recv(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        target_id = int(message.text.strip())
        target_user = await db.get_user(target_id)
        if not target_user:
            await message.answer("❌ Bunday ID ga ega foydalanuvchi topilmadi. Qaytadan kiriting:", reply_markup=get_cancel_inline())
            return

        await state.update_data(target_id=target_id)
        await state.set_state(AdminStates.waiting_for_balance_amount)

        await message.answer(
            f"Foydalanuvchi: <b>{target_user.get('first_name', '')}</b>\n"
            f"Joriy balansi: <b>{int(target_user.get('balance', 0)):,} so'm</b>\n\n"
            f"Qo'shish yoki ayirish miqdorini kiriting (masalan: <code>15000</code> yoki <code>-5000</code>):".replace(",", " "),
            parse_mode="HTML",
            reply_markup=get_cancel_inline()
        )
    except ValueError:
        await message.answer("Iltimos, faqat raqamli ID kiriting:", reply_markup=get_cancel_inline())

@router.message(AdminStates.waiting_for_balance_amount)
async def admin_balance_amount_recv(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        amount = float(message.text.replace(" ", "").strip())
        data = await state.get_data()
        target_id = data["target_id"]

        await db.update_balance(target_id, amount)
        user = await db.get_user(target_id)

        # Notify user
        try:
            sign = "+" if amount > 0 else ""
            await message.bot.send_message(
                target_id,
                f"💳 <b>Balans o'zgarishi:</b>\n\n"
                f"Hisobingizga <b>{sign}{int(amount):,} so'm</b> kiritildi!\n"
                f"Joriy balansingiz: <b>{int(user['balance']):,} so'm</b>".replace(",", " "),
                parse_mode="HTML"
            )
        except Exception:
            pass

        await state.clear()
        await message.answer(
            f"✅ Balans muvaffaqiyatli o'zgartirildi!\n"
            f"Yangi balans: <b>{int(user['balance']):,} so'm</b>".replace(",", " "),
            parse_mode="HTML",
            reply_markup=get_admin_inline()
        )
    except ValueError:
        await message.answer("Iltimos, to'g'ri son kiriting:", reply_markup=get_cancel_inline())

@router.callback_query(F.data == "admin_sync_services")
async def admin_sync_services_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    wait_msg = await callback.message.answer("🔄 Xizmatlar yangilanmoqda...")
    srvs = await seen_client.fetch_services()
    await wait_msg.delete()

    await callback.message.answer(
        f"✅ Xizmatlar bazasi muvaffaqiyatli yangilandi!\n"
        f"Jami xizmatlar: <b>{len(srvs)} ta</b>",
        parse_mode="HTML",
        reply_markup=get_admin_inline()
    )
    await callback.answer()

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminStates.waiting_for_broadcast_msg)
    await callback.message.answer(
        "✉️ <b>Barcha foydalanuvchilarga xabar tarqatish:</b>\n\n"
        "Yubormoqchi bo'lgan xabaringizni yozing (rasm, video yoki matn bo'lishi mumkin):",
        parse_mode="HTML",
        reply_markup=get_cancel_inline()
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast_msg)
async def admin_broadcast_exec(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    users = await db.get_all_users()
    sent_count = 0
    fail_count = 0

    status_msg = await message.answer(f"⏳ Xabar tarqatilmoqda (0/{len(users)})...")

    for u in users:
        try:
            await message.copy_to(chat_id=u["user_id"])
            sent_count += 1
        except Exception:
            fail_count += 1

    await status_msg.edit_text(
        f"🎉 <b>Xabar tarqatish yakunlandi!</b>\n\n"
        f"✅ Yuborildi: <b>{sent_count} ta</b>\n"
        f"❌ Yetib bormadi (bloklagan): <b>{fail_count} ta</b>",
        parse_mode="HTML"
    )
    await state.clear()

# Deposit Approval / Rejection Handlers
@router.callback_query(F.data.startswith("dep_ok:"))
async def deposit_approve_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    dep_id = int(callback.data.split(":")[1])
    dep = await db.get_deposit(dep_id)

    if not dep or dep["status"] != "pending":
        await callback.answer("Bu ariza allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    amount = dep["amount"]
    user_id = dep["user_id"]

    await db.update_deposit_status(dep_id, "approved")
    await db.update_balance(user_id, amount)

    user = await db.get_user(user_id)
    new_bal = user["balance"] if user else amount

    # Notify user
    try:
        await callback.bot.send_message(
            user_id,
            f"🎉 <b>To'lovingiz tasdiqlandi!</b>\n\n"
            f"💰 Hisobingizga <b>+{int(amount):,} so'm</b> qo'shildi!\n"
            f"💳 Joriy balansingiz: <b>{int(new_bal):,} so'm</b>\n\n"
            f"Xaridingiz uchun rahmat!".replace(",", " "),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.message.edit_caption(
        caption=(callback.message.caption or "") + f"\n\n✅ <b>TASDIQLANDI! (+{int(amount):,} so'm qo'shildi)</b>".replace(",", " "),
        parse_mode="HTML",
        reply_markup=None
    )
    await callback.answer("To'lov tasdiqlandi!")

@router.callback_query(F.data.startswith("dep_no:"))
async def deposit_reject_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    dep_id = int(callback.data.split(":")[1])
    dep = await db.get_deposit(dep_id)

    if not dep or dep["status"] != "pending":
        await callback.answer("Bu ariza allaqachon ko'rib chiqilgan!", show_alert=True)
        return

    user_id = dep["user_id"]
    await db.update_deposit_status(dep_id, "rejected")

    # Notify user
    try:
        await callback.bot.send_message(
            user_id,
            f"❌ <b>To'lov arizangiz rad etildi!</b>\n\n"
            f"Chek tasdiqlanmadi yoki mablag' hisobga tushmagan.\n"
            f"Savollar bo'lsa adminga murojaat qiling.",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.message.edit_caption(
        caption=(callback.message.caption or "") + "\n\n❌ <b>RAD ETILDI!</b>",
        parse_mode="HTML",
        reply_markup=None
    )
    await callback.answer("To'lov rad etildi!")
