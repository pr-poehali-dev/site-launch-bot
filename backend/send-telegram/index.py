"""
Отправляет заявку на поездку в Telegram-группу диспетчеров.
Режим: 'now' — сразу в работу, 'moderation' — на модерацию.
"""
import json
import os
import urllib.request
import urllib.parse


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
}


def tg_send(text: str, parse_mode: str = "HTML") -> dict:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_GROUP_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


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

    date = order.get("date", "—")
    time_val = order.get("time", "")
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

    return (
        f"{mode_label}\n"
        f"{'─' * 28}\n"
        f"📍 <b>Маршрут:</b>\n"
        f"{route_cities}"
        f"  🟢 {pickup}{stops_text}\n"
        f"  🔴 {dropoff}\n"
        f"{'─' * 28}\n"
        f"📅 <b>Дата:</b> {datetime_str}\n"
        f"🚖 <b>Тариф:</b> {tariff}\n"
        f"💰 <b>Стоимость:</b> {int(float(price or 0)):,} ₽\n"
        f"🤝 <b>Водитель получит:</b> {driver_amount:,} ₽ (комиссия {commission})\n"
        f"{'─' * 28}\n"
        f"📞 <b>Клиент:</b> {phone}\n"
        f"👥 <b>Пассажиры:</b> {passengers} чел.\n"
        f"🧳 <b>Багаж:</b> {luggage} мест"
        f"{extras_text}"
        f"{comment_text}"
    ).replace(",", " ")


def handler(event: dict, context) -> dict:
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    body = json.loads(event.get("body") or "{}")
    order = body.get("order", {})
    mode = body.get("mode", "moderation")  # 'now' или 'moderation'

    if not order:
        return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "order required"})}

    text = format_order(order, mode)
    result = tg_send(text)

    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({"ok": True, "message_id": result.get("result", {}).get("message_id")}),
    }
