from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import ADMINS, WEBAPP_URL, DEFAULT_SUPPORT_USERNAME
from database import db
from seen_api import seen_client
from handlers.keyboards import (
    get_admin_inline,
    get_cancel_inline,
    get_admin_promos_inline,
    get_user_view_inline
)
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
    free_enabled = (await db.get_setting("free_services_enabled", "1")) == "1"
    text = (
        "⚙️ <b>Pixora SMM — Boshqaruv Paneli:</b>\n\n"
        f"🌐 <b>Web App URL:</b> <code>{current_url}</code>\n"
        f"🎁 <b>Bepul xizmatlar:</b> {'Faol (Yoqilgan) ✅' if free_enabled else 'To‘xtatilgan (O‘chirilgan) ❌'}\n\n"
        "Kerakli bo'limni tanlang:"
    )
    inline_kb = get_admin_inline(free_enabled=free_enabled)
    await edit_or_reply(event, text, inline_kb)
    if isinstance(event, types.CallbackQuery):
        await event.answer()

@router.callback_query(F.data == "admin_toggle_free")
async def admin_toggle_free_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    curr = await db.get_setting("free_services_enabled", "1")
    new_val = "0" if curr == "1" else "1"
    await db.set_setting("free_services_enabled", new_val)
    free_enabled = new_val == "1"
    status_str = "yoqildi ✅" if free_enabled else "to'xtatildi ❌ (SeenSMS balansi tejaladi)"
    await callback.answer(f"Bepul xizmatlar {status_str}!", show_alert=True)

    current_url = await db.get_setting("webapp_url", WEBAPP_URL)
    text = (
        "⚙️ <b>Pixora SMM — Boshqaruv Paneli:</b>\n\n"
        f"🌐 <b>Web App URL:</b> <code>{current_url}</code>\n"
        f"🎁 <b>Bepul xizmatlar:</b> {'Faol (Yoqilgan) ✅' if free_enabled else 'To‘xtatilgan (O‘chirilgan) ❌'}\n\n"
        "Kerakli bo'limni tanlang:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_inline(free_enabled=free_enabled))

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

@router.message(Command("setsupport"))
async def set_support_username_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        current = await db.get_setting("support_username", DEFAULT_SUPPORT_USERNAME)
        await message.answer(
            f"💬 <b>Hozirgi qo'llab-quvvatlash egasi:</b> @{current.lstrip('@')}\n\n"
            f"O'zgartirish: <code>/setsupport ismoiluzb022</code>",
            parse_mode="HTML"
        )
        return
    new_support = args[1].strip().lstrip("@")
    if not new_support:
        await message.answer("⚠️ Iltimos, to'g'ri username kiriting!", parse_mode="HTML")
        return
    await db.set_setting("support_username", new_support)
    await message.answer(
        f"✅ <b>Qo'llab-quvvatlash / Admin egasi yangilandi:</b>\n"
        f"👨‍💻 Aloqa: @{new_support}\n"
        f"🔗 Havola: https://t.me/{new_support}",
        parse_mode="HTML",
        reply_markup=get_admin_inline()
    )

@router.callback_query(F.data == "admin_set_support")
async def admin_set_support_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    current = await db.get_setting("support_username", DEFAULT_SUPPORT_USERNAME)
    await state.set_state(AdminStates.waiting_for_support_username)
    text = (
        f"💬 <b>Qo'llab-quvvatlash kontaktini sozlash:</b>\n\n"
        f"Hozirgi kontakt: <code>@{current.lstrip('@')}</code>\n\n"
        f"Yangi username'ni yuboring (masalan: <code>@ismoiluzb022</code>) "
        f"yoki <code>/setsupport ismoiluzb022</code> buyrug'idan foydalaning:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_cancel_inline())
    await callback.answer()

@router.message(AdminStates.waiting_for_support_username)
async def admin_save_support_state(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    new_support = message.text.strip().lstrip("@")
    if not new_support:
        await message.answer("⚠️ Iltimos, to'g'ri username kiriting!", reply_markup=get_cancel_inline())
        return
    await db.set_setting("support_username", new_support)
    await state.clear()
    await message.answer(
        f"✅ <b>Qo'llab-quvvatlash egasi muvaffaqiyatli saqlandi!</b>\n\n"
        f"👨‍💻 Aloqa: @{new_support}\n"
        f"🔗 Havola: https://t.me/{new_support}",
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
        status_note = ""
        if bal_val <= 0:
            status_note = (
                "\n\n⚠️ <b>DIQQAT: Hisobingizda mablag' yo'q (0 UZS)!</b>\n"
                "Foydalanuvchilar buyurtma bermoqchi bo'lganda, ularga "
                "<i>'🛠 Texnik ta'mirlash ishlari ketmoqda'</i> deb ko'rsatiladi va buyurtma bajarilmaydi.\n\n"
                "👉 Bot to'laqonli xizmat ko'rsatishi uchun <a href='https://seensms.uz'>seensms.uz</a> "
                "saytiga kirib, hisobingizni to'ldiring."
            )
        else:
            status_note = "\n🟢 Holati: Ulangan va buyurtmalarni qabul qilishga tayyor!"

        text = (
            f"💰 <b>SeenSMS API Balansi:</b>\n\n"
            f"💵 Balans: <b>{bal_val:,} {curr_val}</b>"
            f"{status_note}"
        ).replace(",", " ")
    except Exception as e:
        text = (
            "⚠️ <b>SeenSMS API Balansini olishda xatolik:</b>\n\n"
            f"Xatolik: <code>{str(e)}</code>\n\n"
            "Pastdagi <b>🔑 Seen API Kalit</b> tugmasi orqali API kalitni tekshiring."
        )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_inline(), disable_web_page_preview=True)
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


# ==========================================
# PROMO CODE MANAGEMENT (ADMIN)
# ==========================================
@router.message(Command("promos"))
@router.callback_query(F.data == "admin_promos")
async def admin_promos_list_handler(event: types.Message | types.CallbackQuery, state: FSMContext = None):
    if state:
        await state.clear()
    user_id = event.from_user.id
    if not is_admin(user_id):
        return

    promos = await db.get_all_promo_codes()
    text = "🎟 <b>Promokodlar Boshqaruv Paneli:</b>\n\n"
    if not promos:
        text += "<i>Hozirda hech qanday promokod mavjud emas.</i>\n\n"
    else:
        for p in promos:
            limit_str = f"{p['max_uses']} ta" if p['max_uses'] > 0 else "Cheksiz"
            text += (
                f"📌 <b>{p['code']}</b>\n"
                f"   ├ 💰 Mukofot: <b>+{int(p['reward_amount']):,} so'm</b>\n"
                f"   ├ 👥 Ishlatildi: <b>{p['current_uses']} / {limit_str}</b>\n"
                f"   └ 📅 Yaratilgan: <code>{p['created_at']}</code>\n\n"
            ).replace(",", " ")

    text += (
        "💡 <i>Yangi promokod yaratish uchun quyidagi tugmani bosing yoki tezkor buyruq yuboring:</i>\n"
        "<code>/newpromo NOMI SUMMA [LIMIT]</code>\n"
        "<i>Masalan: <code>/newpromo BONUS 5000 100</code></i>"
    )

    inline_kb = get_admin_promos_inline(promos)
    await edit_or_reply(event, text, inline_kb)
    if isinstance(event, types.CallbackQuery):
        await event.answer()


@router.message(Command("newpromo"))
async def admin_newpromo_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(
            "⚠️ <b>Noto'g'ri format!</b>\n\n"
            "Format: <code>/newpromo NOMI SUMMA [LIMIT]</code>\n\n"
            "Masalan:\n"
            "• <code>/newpromo BONUS5K 5000</code> (cheksiz odam uchun)\n"
            "• <code>/newpromo YANGIYIL 10000 50</code> (faqat 50 kishi uchun)",
            parse_mode="HTML"
        )
        return

    code = parts[1].strip().upper()
    try:
        reward = float(parts[2].replace(" ", "").replace(",", ""))
        limit = int(parts[3]) if len(parts) > 3 else 0
    except ValueError:
        await message.answer("⚠️ Summa va limit faqat son bo'lishi kerak!", parse_mode="HTML")
        return

    try:
        await db.create_promo_code(code, reward, limit)
        limit_desc = f"{limit} ta" if limit > 0 else "Cheksiz"
        await message.answer(
            f"✅ <b>Promokod muvaffaqiyatli yaratildi!</b>\n\n"
            f"🎟 Kod: <code>{code}</code>\n"
            f"💰 Bonus summasi: <b>+{int(reward):,} so'm</b>\n"
            f"👥 Foydalanish limiti: <b>{limit_desc}</b>".replace(",", " "),
            parse_mode="HTML",
            reply_markup=get_admin_inline()
        )
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}", parse_mode="HTML")


@router.callback_query(F.data == "admin_add_promo")
async def admin_add_promo_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminStates.waiting_for_promo_code)
    text = (
        "🎟 <b>Yangi promokod yaratish (1/3):</b>\n\n"
        "Promokod nomini yozing (masalan: <code>BONUS5000</code> yoki <code>YANGIYIL</code>):"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_cancel_inline())
    await callback.answer()


@router.message(AdminStates.waiting_for_promo_code)
async def admin_promo_code_received(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    code = message.text.strip().upper()
    await state.update_data(promo_code=code)
    await state.set_state(AdminStates.waiting_for_promo_reward)
    await message.answer(
        f"Kod: <b>{code}</b>\n\n"
        f"💰 <b>Ushbu promokod foydalanuvchiga qancha bonus bersin? (so'mda):</b>\n"
        f"<i>Masalan: <code>5000</code> yoki <code>10000</code></i>",
        parse_mode="HTML",
        reply_markup=get_cancel_inline()
    )


@router.message(AdminStates.waiting_for_promo_reward)
async def admin_promo_reward_received(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        reward = float(message.text.replace(" ", "").replace(",", "").strip())
        await state.update_data(promo_reward=reward)
        await state.set_state(AdminStates.waiting_for_promo_limit)
        await message.answer(
            f"💰 Bonus summasi: <b>{int(reward):,} so'm</b>\n\n"
            f"👥 <b>Ushbu promokodni necha kishi ishlata olsin?</b>\n"
            f"<i>Cheksiz bo'lishi uchun <code>0</code> deb yozing yoki cheklangan son kiriting (masalan: <code>50</code>):</i>".replace(",", " "),
            parse_mode="HTML",
            reply_markup=get_cancel_inline()
        )
    except ValueError:
        await message.answer("Iltimos, to'g'ri son kiriting (masalan: 5000):", reply_markup=get_cancel_inline())


@router.message(AdminStates.waiting_for_promo_limit)
async def admin_promo_limit_received(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        limit = int(message.text.strip())
        data = await state.get_data()
        code = data["promo_code"]
        reward = data["promo_reward"]

        await db.create_promo_code(code, reward, limit)
        await state.clear()

        limit_desc = f"{limit} ta" if limit > 0 else "Cheksiz"
        await message.answer(
            f"✅ <b>Promokod muvaffaqiyatli saqlandi!</b>\n\n"
            f"🎟 Kod: <code>{code}</code>\n"
            f"💰 Bonus: <b>+{int(reward):,} so'm</b>\n"
            f"👥 Limit: <b>{limit_desc}</b>".replace(",", " "),
            parse_mode="HTML",
            reply_markup=get_admin_inline()
        )
    except ValueError:
        await message.answer("Iltimos, butun son kiriting (masalan: 0 yoki 100):", reply_markup=get_cancel_inline())
    except Exception as e:
        await state.clear()
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}", reply_markup=get_admin_inline())


@router.callback_query(F.data.startswith("del_promo:"))
async def admin_delete_promo_callback(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    promo_id = int(callback.data.split(":")[1])
    await db.delete_promo_code(promo_id)
    await callback.answer("Promokod o'chirildi!", show_alert=True)

    # Refresh promo list
    promos = await db.get_all_promo_codes()
    inline_kb = get_admin_promos_inline(promos)
    text = "🎟 <b>Promokodlar Boshqaruv Paneli:</b>\n\n"
    if not promos:
        text += "<i>Hozirda hech qanday promokod mavjud emas.</i>\n\n"
    else:
        for p in promos:
            limit_str = f"{p['max_uses']} ta" if p['max_uses'] > 0 else "Cheksiz"
            text += (
                f"📌 <b>{p['code']}</b>\n"
                f"   ├ 💰 Mukofot: <b>+{int(p['reward_amount']):,} so'm</b>\n"
                f"   ├ 👥 Ishlatildi: <b>{p['current_uses']} / {limit_str}</b>\n"
                f"   └ 📅 Yaratilgan: <code>{p['created_at']}</code>\n\n"
            ).replace(",", " ")

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=inline_kb)


# ==========================================
# USERS LIST WITH AVATAR & USERNAME (ADMIN)
# ==========================================
@router.callback_query(F.data.startswith("admin_user_idx:"))
async def admin_view_user_with_photo(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    idx = int(callback.data.split(":")[1])
    users = await db.get_all_users()

    if not users:
        await callback.answer("Hozircha botda foydalanuvchilar yo'q.", show_alert=True)
        return

    idx = max(0, min(idx, len(users) - 1))
    u = users[idx]
    target_id = u["user_id"]

    uname = f"@{u['username']}" if u.get("username") else "<i>Username kiritilmagan</i>"
    ref_earned = int(u.get("referral_earned") or 0)
    spent = int(u.get("spent_total") or 0)
    bal = int(u.get("balance") or 0)

    caption = (
        f"👤 <b>Foydalanuvchi Profili ({idx + 1} / {len(users)}):</b>\n\n"
        f"👑 <b>Ismi:</b> {u.get('first_name') or 'Nomaʼlum'}\n"
        f"🔗 <b>Username:</b> {uname}\n"
        f"🆔 <b>Telegram ID:</b> <code>{target_id}</code>\n"
        f"💳 <b>Balansi:</b> <b>{bal:,} so'm</b>\n"
        f"💸 <b>Jami sarflagan:</b> <b>{spent:,} so'm</b>\n"
        f"👥 <b>Taklif qilgan do'stlari:</b> {u.get('referrals_count', 0)} ta\n"
        f"🎁 <b>Referal bonusi:</b> {ref_earned:,} so'm\n"
        f"📅 <b>Qo'shilgan sana:</b> <code>{u.get('created_at', '')}</code>"
    ).replace(",", " ")

    inline_kb = get_user_view_inline(idx, len(users), target_id)

    # Fetch user's profile photo via Telegram API
    photo_file_id = None
    try:
        photos = await callback.bot.get_user_profile_photos(target_id, limit=1)
        if photos.total_count > 0:
            photo_file_id = photos.photos[0][-1].file_id
    except Exception:
        pass

    try:
        # If current message has photo
        if callback.message.photo:
            if photo_file_id:
                media = types.InputMediaPhoto(media=photo_file_id, caption=caption, parse_mode="HTML")
                await callback.message.edit_media(media=media, reply_markup=inline_kb)
            else:
                await callback.message.delete()
                await callback.message.answer(caption, parse_mode="HTML", reply_markup=inline_kb)
        else:
            if photo_file_id:
                await callback.message.delete()
                await callback.message.answer_photo(photo=photo_file_id, caption=caption, parse_mode="HTML", reply_markup=inline_kb)
            else:
                await callback.message.edit_text(caption, parse_mode="HTML", reply_markup=inline_kb)
    except Exception:
        if photo_file_id:
            await callback.message.answer_photo(photo=photo_file_id, caption=caption, parse_mode="HTML", reply_markup=inline_kb)
        else:
            await callback.message.answer(caption, parse_mode="HTML", reply_markup=inline_kb)

    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_bal:"))
async def admin_quick_edit_balance(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    target_id = int(callback.data.split(":")[1])
    target_user = await db.get_user(target_id)
    if not target_user:
        await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    await state.update_data(target_id=target_id)
    await state.set_state(AdminStates.waiting_for_balance_amount)
    text = (
        f"💳 <b>Balansni o'zgartirish:</b>\n\n"
        f"Foydalanuvchi: <b>{target_user.get('first_name', '')}</b> (<code>{target_id}</code>)\n"
        f"Hozirgi balansi: <b>{int(target_user.get('balance', 0)):,} so'm</b>\n\n"
        f"Qo'shish yoki ayirish miqdorini yuboring (masalan: <code>10000</code> yoki <code>-5000</code>):".replace(",", " ")
    )
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, parse_mode="HTML", reply_markup=get_cancel_inline())
    else:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_cancel_inline())
    await callback.answer()


@router.callback_query(F.data == "admin_search_user")
async def admin_search_user_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminStates.waiting_for_user_search)
    text = (
        "🔍 <b>Foydalanuvchini qidirish:</b>\n\n"
        "Foydalanuvchining <b>username</b>, <b>ismi</b> yoki <b>Telegram ID</b> raqamini yuboring:"
    )
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, parse_mode="HTML", reply_markup=get_cancel_inline())
    else:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_cancel_inline())
    await callback.answer()


@router.message(AdminStates.waiting_for_user_search)
async def admin_search_user_exec(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    query = message.text.strip()
    results = await db.search_users(query)
    await state.clear()

    if not results:
        await message.answer(
            f"❌ '<b>{query}</b>' bo'yicha hech qanday foydalanuvchi topilmadi.",
            parse_mode="HTML",
            reply_markup=get_admin_inline()
        )
        return

    u = results[0]
    target_id = u["user_id"]
    uname = f"@{u['username']}" if u.get("username") else "<i>Username yo'q</i>"
    spent = int(u.get("spent_total") or 0)
    bal = int(u.get("balance") or 0)

    caption = (
        f"🔍 <b>Qidiruv natijasi ({len(results)} ta topildi):</b>\n\n"
        f"👑 <b>Ismi:</b> {u.get('first_name') or 'Nomaʼlum'}\n"
        f"🔗 <b>Username:</b> {uname}\n"
        f"🆔 <b>Telegram ID:</b> <code>{target_id}</code>\n"
        f"💳 <b>Balansi:</b> <b>{bal:,} so'm</b>\n"
        f"💸 <b>Jami sarflagan:</b> <b>{spent:,} so'm</b>\n"
        f"👥 <b>Taklif qilgan do'stlari:</b> {u.get('referrals_count', 0)} ta\n"
        f"📅 <b>Ro'yxatdan o'tgan:</b> <code>{u.get('created_at', '')}</code>"
    ).replace(",", " ")

    photo_file_id = None
    try:
        photos = await message.bot.get_user_profile_photos(target_id, limit=1)
        if photos.total_count > 0:
            photo_file_id = photos.photos[0][-1].file_id
    except Exception:
        pass

    inline_kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Balansni o'zgartirish", callback_data=f"admin_edit_bal:{target_id}")],
        [InlineKeyboardButton(text="👥 Barcha foydalanuvchilar", callback_data="admin_user_idx:0")],
        [InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="btn_admin")]
    ])

    if photo_file_id:
        await message.answer_photo(photo=photo_file_id, caption=caption, parse_mode="HTML", reply_markup=inline_kb)
    else:
        await message.answer(caption, parse_mode="HTML", reply_markup=inline_kb)
