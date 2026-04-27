"""
Отправляет заявку на поездку в Telegram-группу с inline-кнопкой «Принять заказ».
"""
import json
import os
import urllib.request
import urllib.error

BOT_USERNAME = "zacazubot"

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
}


def tg_request(method: str, payload: dict) -> dict:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[TG] HTTPError {e.code}: {body}")
        raise Exception(f"Telegram API error {e.code}: {body}")


def format_order(order: dict, mode: str) -> str:
    mode_label = "🚀 <b>СРОЧНАЯ ЗАЯВКА</b>" if mode == "now" else "📋 <b>ЗАЯВКА НА МОДЕРАЦИЮ</b>"

    from_city = order.get("from_city", "")
    to_city = order.get("to_city", "")
    route_cities = f"{from_city} → {to_city}\n" if from_city or to_city else ""

    pickup = order.get("pickup", "—")
    dropoff = order.get("dropoff", "—")
    stops = order.get("stops", [])

    stops_text = ""
    if stops:
        stop_list = "\n".join(f"  ↪️ {s.get('address', '')}" for s in stops if s.get("address"))
        if stop_list:
            stops_text = f"\n{stop_list}"

    date = order.get("date", order.get("trip_date", "—"))
    time_val = order.get("time", order.get("trip_time", ""))
    datetime_str = f"{date}" + (f" в {time_val}" if time_val else "")

    price = order.get("price", "0")
    tariff = order.get("tariff", "—")
    commission = order.get("commission", "15%")
    comm_pct = float(commission.replace("%", "")) / 100
    driver_amount = round(float(price or 0) * (1 - comm_pct))

    phone = order.get("phone", "—")
    passengers = order.get("passengers", 1)
    luggage = order.get("luggage", 1)

    extras = []
    if order.get("booster"):
        extras.append("Бустер")
    if order.get("child_seat") or order.get("childSeat"):
        extras.append("Детское кресло")
    if order.get("animal"):
        extras.append("Животное")
    extras_text = f"\n➕ <b>Доп:</b> {', '.join(extras)}" if extras else ""

    comment = order.get("comment", "")
    comment_text = f"\n💬 <b>Комментарий:</b> {comment}" if comment else ""

    price_fmt = str(int(float(price or 0)))
    driver_fmt = str(driver_amount)

    return (
        f"{mode_label}\n"
        f"{'─' * 28}\n"
        f"📍 <b>Маршрут:</b>\n"
        f"  🟢 {from_city or pickup}\n"
        f"  🔴 {to_city or dropoff}\n"
        f"{'─' * 28}\n"
        f"📅 <b>Дата:</b> {datetime_str}\n"
        f"🚖 <b>Тариф:</b> {tariff}\n"
        f"💰 <b>Стоимость:</b> {price_fmt} ₽\n"
        f"🤝 <b>Водитель получит:</b> {driver_fmt} ₽ (комиссия {commission})\n"
        f"{'─' * 28}\n"
        f"👥 <b>Пассажиры:</b> {passengers} чел.\n"
        f"🧳 <b>Багаж:</b> {luggage} мест"
        f"{extras_text}"
    )


def handler(event: dict, context) -> dict:
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    body = json.loads(event.get("body") or "{}")
    order = body.get("order", {})
    mode = body.get("mode", "moderation")

    if not order:
        return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "order required"})}

    chat_id = os.environ["TELEGRAM_GROUP_ID"]
    order_id = order.get("id", "")
    text = format_order(order, mode)

    # Формируем deep link — водитель нажимает кнопку, открывается бот с параметром заказа
    deep_link = f"https://t.me/{BOT_USERNAME}?start=accept_{order_id}"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[
                {
                    "text": "✅ Принять заказ",
                    "url": deep_link
                }
            ]]
        }
    }

    try:
        result = tg_request("sendMessage", payload)
        msg_id = result.get("result", {}).get("message_id")
        print(f"[TG] Sent message_id={msg_id} with accept button order_id={order_id}")
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"ok": True, "message_id": msg_id}),
        }
    except Exception as e:
        print(f"[TG] Failed: {e}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"ok": False, "error": str(e)}),
        }