import asyncio
from aiogram import Router, F, types
from database import db
from seen_api import seen_client, DEFAULT_NUMBER_SERVICES, DEFAULT_NUMBER_COUNTRIES
from handlers.user_handlers import edit_or_reply
from notifications import MAINTENANCE_NUMBER_MSG, is_balance_or_provider_error, notify_admin_low_balance

router = Router()

@router.message(F.text == "📲 Virtual Raqamlar")
@router.callback_query(F.data == "btn_numbers")
async def numbers_menu_handler(event: types.Message | types.CallbackQuery):
    keyboard = []
    for s in DEFAULT_NUMBER_SERVICES:
        code = s.get("service") or s.get("code")
        name = s.get("name")
        keyboard.append([types.InlineKeyboardButton(text=name, callback_data=f"num_srv:{code}")])

    keyboard.append([types.InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="btn_home")])

    text = (
        "📲 <b>Virtual Raqamlar (SMS aktivatsiya):</b>\n\n"
        "Qaysi platforma uchun raqam kerak? Tanlang:"
    )
    inline_kb = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    await edit_or_reply(event, text, inline_kb)
    if isinstance(event, types.CallbackQuery):
        await event.answer()

@router.callback_query(F.data.startswith("num_srv:"))
async def number_service_chosen(callback: types.CallbackQuery):
    service_code = callback.data.split(":")[1]
    wait_msg = await callback.message.answer("⏳ Davlatlar va narxlar yuklanmoqda...")

    try:
        countries = await seen_client.numbers_countries(service_code)
    except Exception as e:
        countries = DEFAULT_NUMBER_COUNTRIES

    await wait_msg.delete()

    margin = float(await db.get_setting("margin_percent", "20.0"))

    # Filter countries with available stock > 0
    available_countries = [c for c in countries if int(c.get("count", 0)) > 0]
    if not available_countries:
        available_countries = countries[:8]

    # Sort by available count descending and price
    available_countries.sort(key=lambda x: (-int(x.get("count", 0)), float(x.get("price", 99999))))

    keyboard = []
    for c in available_countries[:8]:
        cid = str(c.get("country") or c.get("id"))
        name = c.get("name", "Davlat")
        base_price = float(c.get("price", 8500))
        final_price = round(base_price * (1 + margin / 100))
        count = int(c.get("count", 0))
        count_str = f" ({count:,} ta)" if count > 0 else ""
        btn_text = f"{name}{count_str} — {final_price:,} so'm".replace(",", " ")
        keyboard.append([types.InlineKeyboardButton(text=btn_text, callback_data=f"num_buy:{service_code}:{cid}:{final_price}")])

    keyboard.append([
        types.InlineKeyboardButton(text="⬅️ Boshqa servislar", callback_data="back_num_services"),
        types.InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="btn_home")
    ])

    service_name = service_code.upper()
    for s in DEFAULT_NUMBER_SERVICES:
        if s.get("service") == service_code:
            service_name = s.get("name")
            break

    await callback.message.edit_text(
        f"<b>{service_name} uchun davlatni tanlang:</b>\n\n"
        f"Quyida eng ko'p zaxiraga ega va arzon davlatlar ko'rsatilgan:",
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data == "back_num_services")
async def back_num_services(callback: types.CallbackQuery):
    keyboard = []
    for s in DEFAULT_NUMBER_SERVICES:
        code = s.get("service") or s.get("code")
        name = s.get("name")
        keyboard.append([types.InlineKeyboardButton(text=name, callback_data=f"num_srv:{code}")])

    keyboard.append([types.InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="btn_home")])

    await callback.message.edit_text(
        "📲 <b>Virtual Raqamlar:</b>\nPlatformani tanlang:",
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("num_buy:"))
async def number_buy_execute(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    service_code = parts[1]
    country_id = parts[2]
    price = float(parts[3])

    user_id = callback.from_user.id
    user = await db.get_user(user_id)

    if not user or user["balance"] < price:
        await callback.answer("Mablag' yetarli emas! Iltimos, balansingizni to'ldiring.", show_alert=True)
        return

    wait_msg = await callback.message.answer("⏳ Raqam olinmoqda, iltimos kuting...")

    # Purchase from API
    try:
        res = await seen_client.numbers_get(country_id, service_code)
    except Exception as e:
        await wait_msg.delete()
        err_str = str(e)
        if is_balance_or_provider_error(err_str):
            await callback.message.answer(MAINTENANCE_NUMBER_MSG, parse_mode="HTML")
            asyncio.create_task(notify_admin_low_balance(user_id, f"Virtual Raqam ({service_code.upper()})", bot=callback.bot))
        else:
            await callback.message.answer(f"⚠️ Raqam olishda xatolik: {err_str}\nIltimos, boshqa davlatni tanlab ko'ring.")
        await callback.answer()
        return

    await wait_msg.delete()

    phone = res.get("number") or res.get("phone")
    order_id = res.get("id")

    if not phone or not order_id:
        err = str(res.get("error", "Raqam mavjud emas yoki xatolik yuz berdi"))
        if is_balance_or_provider_error(err):
            await callback.message.answer(MAINTENANCE_NUMBER_MSG, parse_mode="HTML")
            asyncio.create_task(notify_admin_low_balance(user_id, f"Virtual Raqam ({service_code.upper()})", bot=callback.bot))
        else:
            await callback.message.answer("⚠️ Hozirda ushbu davlat uchun raqam mavjud emas. Iltimos, boshqa davlatni tanlab ko'ring.")
        await callback.answer()
        return

    # Deduct balance
    await db.update_balance(user_id, -price)

    # Add to DB
    num_id = await db.add_number(
        user_id=user_id,
        order_id=order_id,
        service_code=service_code,
        service_title=service_code.upper(),
        country_code=country_id,
        country_title=f"Davlat #{country_id}",
        phone=phone,
        price=price,
        expires_at="20 daqiqa"
    )

    cancel_kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="❌ Bekor qilish (Pul qaytadi)", callback_data=f"num_cancel:{num_id}:{order_id}:{price}")]
    ])

    sent_msg = await callback.message.answer(
        f"🎉 <b>Raqam muvaffaqiyatli berildi!</b>\n\n"
        f"📱 Raqam: <code>{phone}</code>\n"
        f"🏷 Servis: <b>{service_code.upper()}</b>\n"
        f"💰 Narxi: {int(price):,} so'm\n\n"
        f"⏳ <b>SMS Kodi kutilmoqda...</b>\n"
        f"<i>Kod kelganda bot sizga darhol xabar beradi!</i>".replace(",", " "),
        parse_mode="HTML",
        reply_markup=cancel_kb
    )
    await callback.answer()

    # Launch background polling task
    asyncio.create_task(poll_sms_for_number(callback.bot, user_id, num_id, order_id, phone, sent_msg.message_id))

async def poll_sms_for_number(bot, user_id: int, num_id: int, order_id: int, phone: str, message_id: int):
    """Polls SeenSMS API every 4 seconds for up to 15 minutes."""
    for _ in range(180): # 180 * 4s = 12 mins
        await asyncio.sleep(4)
        num = await db.get_number(num_id)
        if not num or num.get("status") in ("CANCELLED", "RECEIVED"):
            break

        try:
            status_res = await seen_client.numbers_status(order_id)
        except Exception:
            continue

        if isinstance(status_res, dict):
            status = status_res.get("status")
            code = status_res.get("code")
            if (status in ("OK", "RECEIVED") or code) and code:
                await db.update_number_sms(num_id, code, "RECEIVED")
                try:
                    await bot.send_message(
                        user_id,
                        f"🔔 <b>SMS KODI KELDI!</b>\n\n"
                        f"📱 Raqam: <code>{phone}</code>\n"
                        f"🔑 Kod: <b><code>{code}</code></b>\n\n"
                        f"<i>Kodni nusxalash uchun ustiga bosing!</i>",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
                break

@router.callback_query(F.data.startswith("num_cancel:"))
async def number_cancel_handler(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    num_id = int(parts[1])
    order_id = int(parts[2])
    price = float(parts[3])
    user_id = callback.from_user.id

    num = await db.get_number(num_id)
    if not num or num["status"] == "RECEIVED":
        await callback.answer("Bu raqam allaqachon kod qabul qilgan, bekor qilib bo'lmaydi!", show_alert=True)
        return

    try:
        await seen_client.numbers_cancel(order_id)
    except Exception:
        pass
    await db.update_number_status(num_id, "CANCELLED")
    # Refund balance
    await db.update_balance(user_id, price)

    await callback.message.edit_text(
        f"❌ Raqam bekor qilindi.\n"
        f"💰 <b>{int(price):,} so'm</b> hisobingizga qaytarildi.".replace(",", " "),
        parse_mode="HTML"
    )
    await callback.answer("Muvaffaqiyatli bekor qilindi va mablag' qaytarildi!")
