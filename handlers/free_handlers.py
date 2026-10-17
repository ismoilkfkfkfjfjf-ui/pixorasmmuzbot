import asyncio
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import WEBAPP_URL
from database import db
from seen_api import seen_client
from handlers.keyboards import get_free_services_inline, get_start_inline_keyboard, get_cancel_inline
from handlers.states import FreeOrderStates
from handlers.user_handlers import edit_or_reply
from notifications import MAINTENANCE_FREE_MSG, is_balance_or_provider_error, notify_admin_low_balance

router = Router()

FREE_SERVICES_CONFIG = {
    "tg_sub": {
        "name": "✈️ Bepul Telegram Obunachi",
        "service_id": 11015,
        "quantity": 20,
        "desc": "Kanal yoki guruh havolasini yuboring (Masalan: https://t.me/kanal_nomi yoki @kanal_nomi)",
        "prompt": "Kanal yoki guruh havolasini yuboring:"
    },
    "tg_view": {
        "name": "✈️ Bepul Telegram Ko'rish",
        "service_id": 134,
        "quantity": 100,
        "desc": "Post havolasini yuboring (Masalan: https://t.me/kanal_nomi/123)",
        "prompt": "Post havolasini yuboring:"
    },
    "tg_react": {
        "name": "✈️ Bepul Telegram Reaksiya",
        "service_id": 436,
        "quantity": 30,
        "desc": "Post havolasini yuboring (Ijobiy 👍❤️🔥 reaksiyalar qo'shiladi)",
        "prompt": "Post havolasini yuboring:"
    },
    "ig_view": {
        "name": "📸 Bepul Instagram Ko'rish",
        "service_id": 127,
        "quantity": 100,
        "desc": "Instagram video yoki Reels havolasini yuboring (Masalan: https://www.instagram.com/p/C... yoki /reel/...)",
        "prompt": "Instagram post yoki Reels havolasini yuboring:"
    }
}

@router.message(F.text == "🎁 Bepul Xizmatlar")
@router.message(Command("free"))
@router.callback_query(F.data == "btn_free")
async def free_services_menu(event: types.Message | types.CallbackQuery, state: FSMContext):
    await state.clear()
    is_enabled = await db.get_setting("free_services_enabled", "1")
    if is_enabled == "0":
        text = (
            "🎁 <b>SeenSMS Bepul xizmatlar bo'limi:</b>\n\n"
            "⚠️ Hozirda bepul xizmatlar bo'limi vaqtincha to'xtatilgan yoki profilaktika qilinmoqda.\n\n"
            "Iltimos, birozdan so'ng qayta urinib ko'ring yoki asosiy menyudagi arzon SMM xizmatlaridan foydalaning!"
        )
        saved_url = await db.get_setting("webapp_url", WEBAPP_URL)
        await edit_or_reply(event, text, get_start_inline_keyboard(event.from_user.id, saved_url))
        if isinstance(event, types.CallbackQuery):
            await event.answer()
        return

    text = (
        "🎁 <b>SeenSMS Bepul xizmatlar bo'limi:</b>\n\n"
        "Har bir foydalanuvchi har 24 soatda o'z kanali yoki sahifasini "
        "<b>mutlaqo bepul</b> rivojlantirish imkoniyatiga ega!\n\n"
        "Kerakli bepul xizmatni tanlang:"
    )
    inline_kb = get_free_services_inline()
    await edit_or_reply(event, text, inline_kb)
    if isinstance(event, types.CallbackQuery):
        await event.answer()

@router.callback_query(F.data.startswith("free_act:"))
async def free_service_chosen(callback: types.CallbackQuery, state: FSMContext):
    is_enabled = await db.get_setting("free_services_enabled", "1")
    if is_enabled == "0":
        await callback.answer("⚠️ Bepul xizmatlar bo'limi vaqtincha to'xtatilgan!", show_alert=True)
        return

    service_type = callback.data.split(":")[1]
    cfg = FREE_SERVICES_CONFIG.get(service_type)
    if not cfg:
        await callback.answer("Noma'lum xizmat!", show_alert=True)
        return

    user_id = callback.from_user.id
    can_use, hours_left = await db.can_use_free_service(user_id, service_type)

    if not can_use:
        await callback.answer(
            f"⏳ Siz ushbu bepul xizmatdan yaqinda foydalangansiz!\n"
            f"Keyingi bepul xizmat {hours_left} soatdan keyin ochiladi.",
            show_alert=True
        )
        return

    await state.update_data(free_service_type=service_type, cfg=cfg)
    await state.set_state(FreeOrderStates.waiting_for_link)

    text = (
        f"<b>{cfg['name']}</b> ({cfg['quantity']} ta)\n\n"
        f"📝 <b>Ko'rsatma:</b> {cfg['desc']}\n\n"
        f"🔗 <b>{cfg['prompt']}</b>"
    )
    await edit_or_reply(callback, text, get_cancel_inline())
    await callback.answer()

@router.message(FreeOrderStates.waiting_for_link)
async def free_order_link_received(message: types.Message, state: FSMContext):
    link = message.text.strip()
    if not link.startswith("http") and not link.startswith("@") and "t.me" not in link and "instagram.com" not in link:
        await message.answer(
            "Iltimos, to'g'ri havola yuboring (masalan: https://t.me/kanal yoki https://instagram.com/reel/...):",
            reply_markup=get_cancel_inline()
        )
        return

    data = await state.get_data()
    service_type = data["free_service_type"]
    cfg = data["cfg"]
    user_id = message.from_user.id

    wait_msg = await message.answer("⏳ Bepul buyurtma SeenSMS orqali yuborilmoqda...")

    try:
        # Call SeenSMS API
        api_res = await seen_client.add(
            service=cfg["service_id"],
            link=link,
            quantity=cfg["quantity"]
        )
        api_order_id = api_res.get("order") if isinstance(api_res, dict) else None
        if not api_order_id:
            raise Exception("Buyurtma qabul qilinmadi")
    except Exception as e:
        await wait_msg.delete()
        saved_url = await db.get_setting("webapp_url", WEBAPP_URL)
        err_str = str(e)
        if is_balance_or_provider_error(err_str):
            await message.answer(
                MAINTENANCE_FREE_MSG,
                parse_mode="HTML",
                reply_markup=get_start_inline_keyboard(user_id, saved_url)
            )
            asyncio.create_task(notify_admin_low_balance(user_id, f"Bepul: {cfg['name']}", bot=message.bot))
        else:
            await message.answer(
                f"⚠️ <b>Buyurtma yuborishda xatolik yuz berdi:</b>\n<code>{err_str}</code>\n\n"
                f"Iltimos, havola to'g'riligini tekshirib qayta urinib ko'ring.",
                parse_mode="HTML",
                reply_markup=get_start_inline_keyboard(user_id, saved_url)
            )
        await state.clear()
        return

    await wait_msg.delete()

    # Record free service cooldown
    await db.record_free_service(user_id, service_type, link)

    # Record in orders table with price 0
    order_id = await db.add_order(
        user_id=user_id,
        service_id=cfg["service_id"],
        service_name=cfg["name"],
        category="🎁 Bepul Xizmatlar",
        link=link,
        quantity=cfg["quantity"],
        price=0.0,
        api_order_id=api_order_id
    )

    await state.clear()

    saved_url = await db.get_setting("webapp_url", WEBAPP_URL)
    celebration_text = (
        f"🎉 <b>Tabriklaymiz! Bepul buyurtmangiz ishga tushirildi!</b>\n\n"
        f"📌 Xizmat: <b>{cfg['name']}</b>\n"
        f"📊 Miqdor: <b>{cfg['quantity']} ta</b>\n"
        f"🔗 Havola: <code>{link}</code>\n"
        f"💰 Narxi: <b>0 so'm (BEPUL)</b>\n"
        f"🆔 Buyurtma raqami: <code>#{order_id}</code> (SeenSMS #{api_order_id})\n\n"
        f"<i>💡 Ushbu bepul xizmatdan keyingi safar 24 soatdan so'ng yana foydalanishingiz mumkin!</i>"
    )

    await message.answer(celebration_text, parse_mode="HTML", reply_markup=get_start_inline_keyboard(user_id, saved_url))
