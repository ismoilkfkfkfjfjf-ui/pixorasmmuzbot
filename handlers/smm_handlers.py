import asyncio
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from config import WEBAPP_URL
from database import db
from seen_api import seen_client
from handlers.keyboards import (
    get_categories_inline,
    get_subcategories_inline,
    get_services_inline,
    get_start_inline_keyboard,
    get_cancel_inline,
    get_cancel_keyboard
)
from handlers.states import OrderStates
from handlers.user_handlers import edit_or_reply
from notifications import MAINTENANCE_SMM_MSG, is_balance_or_provider_error, notify_admin_low_balance

router = Router()

def filter_services_by_subcat(services: list, cat: str, subcat: str) -> list:
    c_lower = cat.lower()
    sub_lower = subcat.lower()

    # Base filter by platform first
    if c_lower != "all":
        platform_services = [s for s in services if c_lower in s.get("category", "").lower() or c_lower in s.get("name", "").lower()]
    else:
        platform_services = services

    if sub_lower == "all":
        return platform_services

    if c_lower == "telegram":
        if sub_lower == "obunachi":
            res = [s for s in platform_services if "obunachi" in s.get("category", "").lower() or "obunachi" in s.get("name", "").lower()]
            return res or platform_services
        elif sub_lower in ("korish", "ko'rish"):
            res = [s for s in platform_services if "ko'rish" in s.get("category", "").lower() or "post" in s.get("category", "").lower() or "ko'rish" in s.get("name", "").lower()]
            return res or platform_services
        elif sub_lower == "reaksiya":
            res = [s for s in platform_services if "reaksiya" in s.get("category", "").lower() or "reaksiya" in s.get("name", "").lower()]
            return res or platform_services
        elif sub_lower == "premium":
            res = [s for s in platform_services if "premium" in s.get("category", "").lower() or "premium" in s.get("name", "").lower()]
            return res or platform_services

    elif c_lower == "instagram":
        if sub_lower == "obunachi":
            res = [s for s in platform_services if "obunachi" in s.get("category", "").lower() or "obunachi" in s.get("name", "").lower()]
            return res or platform_services
        elif sub_lower in ("layk", "like"):
            res = [s for s in platform_services if "like" in s.get("category", "").lower() or "layk" in s.get("category", "").lower() or "like" in s.get("name", "").lower()]
            return res or platform_services
        elif sub_lower in ("video", "korish", "ko'rish"):
            res = [s for s in platform_services if "ko'rish" in s.get("category", "").lower() or "video" in s.get("category", "").lower() or "story" in s.get("category", "").lower()]
            return res or platform_services

    elif c_lower == "tiktok":
        if sub_lower == "obunachi":
            res = [s for s in platform_services if "obunachi" in s.get("category", "").lower() or "obunachi" in s.get("name", "").lower()]
            return res or platform_services
        elif sub_lower in ("korish", "ko'rish"):
            res = [s for s in platform_services if "ko'rish" in s.get("category", "").lower() or "ko'rish" in s.get("name", "").lower()]
            return res or platform_services
        elif sub_lower in ("other", "layk", "like"):
            res = [s for s in platform_services if not ("obunachi" in s.get("category", "").lower() or "ko'rish" in s.get("category", "").lower())]
            return res or platform_services

    elif c_lower == "youtube":
        if sub_lower in ("korish", "ko'rish"):
            res = [s for s in platform_services if "ko'rish" in s.get("category", "").lower() or "efir" in s.get("category", "").lower() or "ko'rish" in s.get("name", "").lower()]
            return res or platform_services
        elif sub_lower in ("like", "layk"):
            res = [s for s in platform_services if "like" in s.get("category", "").lower() or "layk" in s.get("category", "").lower() or "like" in s.get("name", "").lower()]
            return res or platform_services
        elif sub_lower == "obunachi":
            res = [s for s in platform_services if "obunachi" in s.get("category", "").lower() or "obunachi" in s.get("name", "").lower()]
            return res or platform_services

    matched = [s for s in platform_services if sub_lower in s.get("category", "").lower() or sub_lower in s.get("name", "").lower()]
    return matched or platform_services


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
        f"Jami mavjud xizmatlar: <b>{len(services)} ta</b>\n"
        "Xarid qilmoqchi bo'lgan xizmatingizni tanlang:"
    )
    inline_kb = get_services_inline(services, margin, "all:all", page=0, per_page=6)
    await edit_or_reply(event, text, inline_kb)
    if isinstance(event, types.CallbackQuery):
        await event.answer()


@router.callback_query(F.data.startswith("cat:"))
async def category_selected_handler(callback: types.CallbackQuery):
    category = callback.data.split(":")[1]
    text = (
        f"<b>{category} xizmatlari:</b>\n\n"
        f"Kerakli yo'nalishni tanlang:"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_subcategories_inline(category)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("subcat:"))
async def subcategory_selected_handler(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    category = parts[1]
    subcat = parts[2]

    services = await db.get_services()
    if not services:
        services = await seen_client.fetch_services()

    matched = filter_services_by_subcat(services, category, subcat)
    if not matched:
        matched = [s for s in services if category.lower() in s.get("category", "").lower() or category.lower() in s.get("name", "").lower()]

    margin = float(await db.get_setting("margin_percent", "20.0"))
    cat_key = f"{category}:{subcat}"

    await callback.message.edit_text(
        f"<b>{category} xizmatlari</b> ({len(matched)} ta mavjud):\n\n"
        f"Quyidagi xizmatlardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=get_services_inline(matched, margin, cat_key, page=0, per_page=6)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("srv_page:"))
async def service_page_handler(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    category = parts[1]
    subcat = parts[2]
    page = int(parts[3])

    services = await db.get_services()
    if not services:
        services = await seen_client.fetch_services()

    if category == "all" and subcat == "all":
        matched = services
    else:
        matched = filter_services_by_subcat(services, category, subcat)
        if not matched:
            matched = [s for s in services if category.lower() in s.get("category", "").lower() or category.lower() in s.get("name", "").lower()]

    margin = float(await db.get_setting("margin_percent", "20.0"))
    cat_key = f"{category}:{subcat}"

    title = "Barcha xizmatlar" if category == "all" else f"{category} xizmatlari"
    await callback.message.edit_text(
        f"<b>{title}</b> ({len(matched)} ta mavjud):\n\n"
        f"Quyidagi xizmatlardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=get_services_inline(matched, margin, cat_key, page=page, per_page=6)
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
    if not link.startswith("http") and not link.startswith("@") and "t.me" not in link and "instagram.com" not in link and "tiktok.com" not in link and "youtube.com" not in link and "youtu.be" not in link:
        await message.answer("Iltimos, to'g'ri havola yuboring (masalan: https://t.me/... yoki @username):", reply_markup=get_cancel_keyboard())
        return

    await state.update_data(link=link)
    data = await state.get_data()

    await state.set_state(OrderStates.waiting_for_quantity)
    await message.answer(
        f"Havola qabul qilindi: <code>{link}</code>\n\n"
        f"Endi buyurtma miqdorini kiriting:\n"
        f"<i>(Minimal: {data['min_q']:,} ta, Maksimal: {data['max_q']:,} ta)</i>".replace(",", " "),
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(OrderStates.waiting_for_quantity)
async def order_quantity_handler(message: types.Message, state: FSMContext):
    try:
        qty = int(message.text.replace(" ", "").strip())
        data = await state.get_data()

        if qty < data["min_q"] or qty > data["max_q"]:
            await message.answer(
                f"Miqdor {data['min_q']:,} va {data['max_q']:,} oralig'ida bo'lishi kerak!".replace(",", " "),
                reply_markup=get_cancel_keyboard()
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

    wait_msg = await callback.message.answer("⏳ Buyurtma SeenSMS API orqali yuborilmoqda...")

    # Call SeenSMS API
    try:
        api_res = await seen_client.add(data["service_id"], data["link"], data["quantity"])
        api_order_id = api_res.get("order") if isinstance(api_res, dict) else None
        if not api_order_id:
            raise Exception("Provayder buyurtmani qabul qilmadi")
    except Exception as e:
        await wait_msg.delete()
        err_str = str(e)
        if is_balance_or_provider_error(err_str):
            await state.clear()
            saved_url = await db.get_setting("webapp_url", WEBAPP_URL)
            await callback.message.edit_text(
                MAINTENANCE_SMM_MSG,
                parse_mode="HTML",
                reply_markup=get_start_inline_keyboard(user_id, saved_url)
            )
            asyncio.create_task(notify_admin_low_balance(user_id, data["service_name"], bot=callback.bot))
            await callback.answer()
            return

        # Show clear error to user
        await callback.message.edit_text(
            f"⚠️ <b>Buyurtma yuborishda xatolik yuz berdi:</b>\n\n"
            f"<b>Provayder javobi:</b> <code>{err_str}</code>\n\n"
            f"<i>Iltimos, havolangiz to'g'riligini tekshirib qayta urinib ko'ring.</i>",
            parse_mode="HTML",
            reply_markup=get_cancel_inline()
        )
        await state.clear()
        await callback.answer(f"Xatolik: {err_str}", show_alert=True)
        return

    await wait_msg.delete()

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
        f"🆔 Buyurtma raqami: <code>#{order_id}</code> (SeenSMS #{api_order_id})\n"
        f"📌 Xizmat: <b>{data['service_name']}</b>\n"
        f"📊 Miqdor: <b>{data['quantity']:,} ta</b>\n"
        f"💰 Yechildi: <b>{total_price:,} so'm</b>\n"
        f"⏳ Holati: <b>Ishga tushirildi (Avtomatik)</b>\n\n"
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
