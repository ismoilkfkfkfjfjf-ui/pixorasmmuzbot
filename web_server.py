import os
from pathlib import Path
from aiohttp import web
from config import BASE_DIR, ASSETS_DIR, WEB_HOST, WEB_PORT
from database import db
from seen_api import seen_client, DEFAULT_NUMBER_COUNTRIES

async def health_handler(request):
    return web.json_response({"status": "ok", "service": "Pixora SMM Bot", "running": True})

async def index_handler(request):
    index_file = BASE_DIR / "webapp" / "index.html"
    return web.FileResponse(index_file)

async def api_user_handler(request):
    user_id = int(request.query.get("user_id", 0))
    username = request.query.get("username", "")
    first_name = request.query.get("first_name", "")

    if not user_id:
        return web.json_response({"error": "user_id talab qilinadi"}, status=400)

    user = await db.get_or_create_user(user_id, username, first_name)
    card_number = await db.get_setting("card_number", "8600 0000 0000 0000")
    card_holder = await db.get_setting("card_holder", "Pixora SMM")

    return web.json_response({
        **user,
        "card_number": card_number,
        "card_holder": card_holder
    })

async def api_services_handler(request):
    cat = request.query.get("category")
    services = await db.get_services(cat)
    if not services:
        services = await seen_client.fetch_services()

    margin = float(await db.get_setting("margin_percent", "20.0"))
    
    # Apply margin to rates
    result = []
    for s in services:
        rate = float(s.get("rate", 0.0))
        final_rate = round(rate * (1 + margin / 100))
        result.append({
            **s,
            "rate": final_rate
        })
    return web.json_response(result)

async def api_order_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        service_id = int(data.get("service_id", 0))
        link = data.get("link", "").strip()
        quantity = int(data.get("quantity", 0))

        if not user_id or not service_id or not link or quantity <= 0:
            return web.json_response({"error": "Noto'g'ri parametrlar"}, status=400)

        user = await db.get_user(user_id)
        if not user:
            return web.json_response({"error": "Foydalanuvchi topilmadi"}, status=404)

        service = await db.get_service(service_id)
        if not service:
            return web.json_response({"error": "Xizmat topilmadi"}, status=404)

        margin = float(await db.get_setting("margin_percent", "20.0"))
        rate = float(service.get("rate", 0.0))
        final_rate = round(rate * (1 + margin / 100))
        total_price = round((quantity / 1000) * final_rate)

        if user["balance"] < total_price:
            return web.json_response({"error": "Mablag' yetarli emas"}, status=400)

        # Send to API
        api_res = await seen_client.add_order(service_id, link, quantity)
        api_order_id = api_res.get("order") if isinstance(api_res, dict) else None

        # Deduct balance
        await db.update_balance(user_id, -total_price)

        # Save order
        order_id = await db.add_order(
            user_id=user_id,
            service_id=service_id,
            service_name=service["name"],
            category=service["category"],
            link=link,
            quantity=quantity,
            price=total_price,
            api_order_id=api_order_id
        )

        return web.json_response({
            "success": True,
            "order_id": order_id,
            "charge": total_price,
            "balance": user["balance"] - total_price
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def api_numbers_services_handler(request):
    services = await seen_client.get_numbers_services()
    return web.json_response(services)

async def api_numbers_countries_handler(request):
    service_code = request.query.get("service", "tg")
    countries = await seen_client.get_numbers_countries(service_code)
    return web.json_response(countries)

async def api_numbers_buy_handler(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        service_code = data.get("service", "tg")
        country_code = int(data.get("country", 1))
        price = float(data.get("price", 8500))

        user = await db.get_user(user_id)
        if not user or user["balance"] < price:
            return web.json_response({"error": "Mablag' yetarli emas"}, status=400)

        res = await seen_client.buy_number(country_code, service_code)
        if not isinstance(res, dict) or ("phone" not in res and "id" not in res):
            return web.json_response({"error": res.get("error", "Raqam olishda xatolik")}, status=400)

        phone = res.get("phone", "+998901234567")
        order_id = res.get("id", 1001)

        # Deduct balance
        await db.update_balance(user_id, -price)

        # Save number
        num_id = await db.add_number(
            user_id=user_id,
            order_id=order_id,
            service_code=service_code,
            service_title=service_code.upper(),
            country_code=country_code,
            country_title=f"Davlat #{country_code}",
            phone=phone,
            price=price,
            expires_at="20 daqiqa"
        )

        return web.json_response({
            "success": True,
            "number_id": num_id,
            "phone": phone
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def api_numbers_active_handler(request):
    user_id = int(request.query.get("user_id", 0))
    numbers = await db.get_user_numbers(user_id, limit=5)

    # Check status for each waiting number
    for n in numbers:
        if n["status"] == "WAIT_CODE" and n.get("order_id"):
            stat = await seen_client.get_number_status(n["order_id"])
            if isinstance(stat, dict) and stat.get("status") == "RECEIVED" and stat.get("code"):
                await db.update_number_sms(n["id"], stat["code"])
                n["sms_code"] = stat["code"]
                n["status"] = "RECEIVED"

    return web.json_response(numbers)

async def api_user_orders_handler(request):
    user_id = int(request.query.get("user_id", 0))
    orders = await db.get_user_orders(user_id, limit=20)
    return web.json_response(orders)


def create_web_app():
    app = web.Application()

    # Routes
    app.router.add_get("/", index_handler)
    app.router.add_get("/health", health_handler)
    app.router.add_get("/api/user", api_user_handler)
    app.router.add_get("/api/services", api_services_handler)
    app.router.add_post("/api/order", api_order_handler)
    app.router.add_get("/api/numbers/services", api_numbers_services_handler)
    app.router.add_get("/api/numbers/countries", api_numbers_countries_handler)
    app.router.add_post("/api/numbers/buy", api_numbers_buy_handler)
    app.router.add_get("/api/numbers/active", api_numbers_active_handler)
    app.router.add_get("/api/user/orders", api_user_orders_handler)

    # Static assets
    app.router.add_static("/static", path=str(BASE_DIR / "webapp"), name="webapp_static")
    if ASSETS_DIR.exists():
        app.router.add_static("/static", path=str(ASSETS_DIR), name="assets_static")

    return app
