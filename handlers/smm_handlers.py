from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from config import WEBAPP_URL
from database import db
from seen_api import seen_client
from handlers.keyboards import get_categories_inline, get_services_inline, get_start_inline_keyboard, get_cancel_inline
from handlers.states import OrderStates
from handlers.user_handlers import edit_or_reply

router = Router()

@router.message(F.text == "⚡ SMM Xizmatlari")
@router.callback_query(F.data == "btn_smm")
async def smm_menu_handler(event: types.Message | types.CallbackQuery):
    text = (
        "⚡ <b>SMM Xizmatlari bo'limi:</b>\n\n"
        "Ijtimoiy tarmoqni tanlang:"
    )
    inline_kb = get_categories_inline()
    await edit_or_reply(event, text, inline_kb)
    if isinstance(event, types.CallbackQuery):
        await event.answer()

@router.callback_query(F.data == "back_categories")
async def back_to_categories(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⚡ <b>SMM Xizmatlari bo'limi:</b>\n\n"
        "Ijtimoiy tarmoqni tanlang:",
        parse_mode="HTML",
        reply_markup=get_categories_inline()
    )
    await callback.answer()

@router.message(F.text == "🛍️ Xizmatlar Do'koni")
@router.callback_query(F.data.in_({"open_webapp", "open_shop"}))
async def open_all_services_in_bot(event: types.Message | types.CallbackQuery):
    services = await db.get_services()
    if not services:
        services = await seen_client.fetch_services()

    margin = float(await db.get_setting("margin_percent", "20.0"))
    text = (
        "🛍️ <b>Pixora SMM — Barcha xizmatlar do'koni:</b>\n\n"
        "Xarid qilmoqchi bo'lgan xizmatingizni tanlang:"
    )
    inline_kb = get_services_inline(services[:10], margin, "Barchasi")
    await edit_or_reply(event, text, inline_kb)
    if isinstance(event, types.CallbackQuery):
        await event.answer()

@router.callback_query(F.data.startswith("cat:"))
async def category_selected_handler(callback: types.CallbackQuery):
    category = callback.data.split(":")[1]
    services = await db.get_services()
    if not services:
        services = await seen_client.fetch_services()

    # Filter matching category
    matched = [s for s in services if category.lower() in s.get("category", "").lower() or category.lower() in s.get("name", "").lower()]
    if not matched:
        matched = services[:6]

    margin = float(await db.get_setting("margin_percent", "20.0"))

    await callback.message.edit_text(
        f"<b>{category} xizmatlari:</b>\n\n"
        f"Quyidagi xizmatlardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=get_services_inline(matched, margin, category)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("srv:"))
async def service_selected_handler(callback: types.CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split(":")[1])
    service = await db.get_service(service_id)
    if not service:
        await callback.answer("Xizmat topilmadi!", show_alert=True)
        return

    margin = float(await db.get_setting("margin_percent", "20.0"))
    rate = round(float(service["rate"]) * (1 + margin / 100))

    await state.update_data(
        service_id=service_id,
        service_name=service["name"],
        category=service["category"],
        rate=rate,
        min_q=service["min"],
        max_q=service["max"]
    )
    await state.set_state(OrderStates.waiting_for_link)

    text = (
        f"📌 <b>{service['name']}</b>\n\n"
        f"📝 <b>Tavsif:</b> {service.get('description') or 'Tezkor yetkazib berish.'}\n"
        f"💰 <b>Narxi (1000 ta):</b> {rate:,} so'm\n"
        f"📊 <b>Cheklov:</b> Min {service['min']:,} | Max {service['max']:,}\n\n"
        f"Iltimos, havolani (link) yuboring:\n"
        f"<i>(Kanal, guruh, post yoki profil havolasi)</i>"
    ).replace(",", " ")

    await callback.message.answer(text, parse_mode="HTML", reply_markup=get_cancel_keyboard())
    await callback.answer()

@router.message(OrderStates.waiting_for_link)
async def order_link_handler(message: types.Message, state: FSMContext):
    link = message.text.strip()
    if not link.startswith("http") and not link.startswith("@") and not "t.me" in link:
        await message.answer("Iltimos, to'g'ri havola yuboring (masalan: https://t.me/... yoki @username):")
        return

    await state.update_data(link=link)
    data = await state.get_data()

    await state.set_state(OrderStates.waiting_for_quantity)
    await message.answer(
        f"Havola qabul qilindi: <code>{link}</code>\n\n"
        f"Endi buyurtma miqdorini kiriting:\n"
        f"<i>(Minimal: {data['min_q']:,} ta, Maksimal: {data['max_q']:,} ta)</i>".replace(",", " "),
        parse_mode="HTML",
        reply_markup=get_cancel_inline()
    )

@router.message(OrderStates.waiting_for_quantity)
async def order_quantity_handler(message: types.Message, state: FSMContext):
    try:
        qty = int(message.text.replace(" ", "").strip())
        data = await state.get_data()

        if qty < data["min_q"] or qty > data["max_q"]:
            await message.answer(
                f"Miqdor {data['min_q']:,} va {data['max_q']:,} oralig'ida bo'lishi kerak!".replace(",", " "),
                reply_markup=get_cancel_inline()
            )
            return

        total_price = round((qty / 1000) * data["rate"])
        await state.update_data(quantity=qty, total_price=total_price)

        user = await db.get_user(message.from_user.id)
        balance = user.get("balance", 0) if user else 0

        confirm_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="✅ Buyurtmani tasdiqlash", callback_data="confirm_smm_order"),
                types.InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_smm_order")
            ]
        ])

        text = (
            f"🛒 <b>Buyurtmani tasdiqlang:</b>\n\n"
            f"📌 Xizmat: <b>{data['service_name']}</b>\n"
            f"🔗 Havola: <code>{data['link']}</code>\n"
            f"📊 Miqdor: <b>{qty:,} dona</b>\n"
            f"💰 Umumiy narx: <b>{total_price:,} so'm</b>\n"
            f"💳 Sizning balansingiz: <b>{int(balance):,} so'm</b>\n\n"
            f"Buyurtmani tasdiqlaysizmi?"
        ).replace(",", " ")

        await state.set_state(OrderStates.confirm_order)
        await message.answer(text, parse_mode="HTML", reply_markup=confirm_kb)
    except ValueError:
        await message.answer("Iltimos, faqat raqam kiriting (masalan: 1000):")

@router.callback_query(OrderStates.confirm_order, F.data == "confirm_smm_order")
async def execute_smm_order(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    total_price = data["total_price"]

    user = await db.get_user(user_id)
    if not user or user["balance"] < total_price:
        await callback.answer("Mablag' yetarli emas! Iltimos, hisobingizni to'ldiring.", show_alert=True)
        return

    # Call SeenSMS API
    try:
        api_res = await seen_client.add(data["service_id"], data["link"], data["quantity"])
        api_order_id = api_res.get("order") if isinstance(api_res, dict) else None
    except Exception as e:
        await callback.answer(f"API xatosi: {str(e)}", show_alert=True)
        return

    # Deduct balance
    await db.update_balance(user_id, -total_price)

    # Save order in DB
    order_id = await db.add_order(
        user_id=user_id,
        service_id=data["service_id"],
        service_name=data["service_name"],
        category=data["category"],
        link=data["link"],
        quantity=data["quantity"],
        price=total_price,
        api_order_id=api_order_id
    )

    await state.clear()
    saved_url = await db.get_setting("webapp_url", WEBAPP_URL)
    await callback.message.edit_text(
        f"🎉 <b>Buyurtmangiz muvaffaqiyatli qabul qilindi!</b>\n\n"
        f"🆔 Buyurtma raqami: <code>#{order_id}</code>\n"
        f"📌 Xizmat: {data['service_name']}\n"
        f"📊 Miqdor: {data['quantity']:,} ta\n"
        f"💰 Yechildi: {total_price:,} so'm\n"
        f"⏳ Holati: Ishga tushirildi (Avtomatik)\n\n"
        f"Rahmat, xizmatimizdan foydalanganingiz uchun!".replace(",", " "),
        parse_mode="HTML",
        reply_markup=get_start_inline_keyboard(user_id, saved_url)
    )
    await callback.answer()

@router.callback_query(OrderStates.confirm_order, F.data == "cancel_smm_order")
async def cancel_smm_order_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    saved_url = await db.get_setting("webapp_url", WEBAPP_URL)
    await callback.message.edit_text(
        "Buyurtma bekor qilindi.",
        reply_markup=get_start_inline_keyboard(callback.from_user.id, saved_url)
    )
    await callback.answer()
