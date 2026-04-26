"""
Telegram webhook для @zacazubot.
Обрабатывает /start accept_<order_id> — создаёт платёж и отправляет ссылку водителю.
"""
import json
import os
import uuid
import urllib.request
import urllib.error
import base64
import psycopg2
from psycopg2.extras import RealDictCursor


WEBHOOK_URL = "https://functions.poehali.dev/06f62334-3744-4817-84a2-fee6b379c230"

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
}


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def register_webhook() -> dict:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/setWebhook"
    payload = json.dumps({"url": WEBHOOK_URL}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def tg_send(chat_id, text, parse_mode="HTML", reply_markup=None):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def create_payment(order_id: str, amount: float, description: str) -> dict:
    shop_id = os.environ.get("YUKASSA_SHOP_ID", "").strip()
    secret_key = os.environ.get("YUKASSA_SECRET_KEY", "").strip()
    credentials = base64.b64encode(f"{shop_id}:{secret_key}".encode()).decode()
    idempotence_key = str(uuid.uuid4())

    payload = {
        "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": "https://t.me/zacazubot"},
        "capture": True,
        "description": description,
        "metadata": {"order_id": order_id}
    }
    req = urllib.request.Request(
        "https://api.yookassa.ru/v3/payments",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}",
            "Idempotence-Key": idempotence_key,
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def format_order_info(order: dict) -> str:
    price = float(order.get("price") or 0)
    driver_amount = float(order.get("driver_amount") or 0)
    commission_str = order.get("commission", "15%")
    comm_val = round(price - driver_amount)

    pickup = order.get("pickup", "—")
    dropoff = order.get("dropoff", "—")
    trip_date = str(order.get("trip_date", "—"))
    trip_time = order.get("trip_time", "")
    tariff = order.get("tariff", "—")
    phone = order.get("phone", "—")

    datetime_str = trip_date + (f" в {trip_time}" if trip_time else "")

    return (
        f"🚖 <b>Заказ принят!</b>\n"
        f"{'─' * 28}\n"
        f"📍 {pickup} → {dropoff}\n"
        f"📅 {datetime_str}\n"
        f"🚗 Тариф: {tariff}\n"
        f"📞 Клиент: {phone}\n"
        f"{'─' * 28}\n"
        f"💰 Стоимость: {int(price)} ₽\n"
        f"🤝 Вы получите: {int(driver_amount)} ₽\n"
        f"📊 Комиссия сервиса: {int(comm_val)} ₽ ({commission_str})\n"
    )


def handler(event: dict, context) -> dict:
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    # GET /?register=1 — регистрируем webhook у Telegram
    if event.get("httpMethod") == "GET":
        params = event.get("queryStringParameters") or {}
        if params.get("register") == "1":
            result = register_webhook()
            print(f"[WEBHOOK] setWebhook result: {result}")
            return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps(result)}
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True, "hint": "add ?register=1 to register webhook"})}

    body = json.loads(event.get("body") or "{}")
    print(f"[WEBHOOK] update: {json.dumps(body)[:500]}")

    message = body.get("message") or body.get("edited_message")
    if not message:
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    # Обрабатываем /start accept_<order_id>
    if not text.startswith("/start accept_"):
        tg_send(chat_id, "👋 Привет! Нажми кнопку <b>«Принять заказ»</b> в группе диспетчеров, чтобы получить ссылку на оплату комиссии.")
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    order_id = text.replace("/start accept_", "").strip()
    print(f"[WEBHOOK] Driver accepting order_id={order_id} chat_id={chat_id}")

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT * FROM t_p16564901_site_launch_bot.orders WHERE id = %s::uuid",
        (order_id,)
    )
    order = cur.fetchone()

    if not order:
        cur.close()
        conn.close()
        tg_send(chat_id, "❌ Заказ не найден. Возможно, он уже был принят или отменён.")
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    order = dict(order)

    # Если платёж уже создан — отправляем сохранённую ссылку
    if order.get("payment_url"):
        info = format_order_info(order)
        tg_send(
            chat_id,
            info + f"\n💳 <b>Ссылка на оплату комиссии уже создана:</b>",
            reply_markup={"inline_keyboard": [[{"text": "💳 Оплатить комиссию", "url": order["payment_url"]}]]}
        )
        cur.close()
        conn.close()
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    # Создаём новый платёж
    driver_amount = float(order.get("driver_amount") or 0)
    price = float(order.get("price") or 0)
    commission_amount = round(price - driver_amount, 2)

    if commission_amount <= 0:
        cur.close()
        conn.close()
        tg_send(chat_id, "⚠️ Не удалось рассчитать сумму комиссии. Обратитесь к диспетчеру.")
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    pickup = order.get("pickup", "")
    dropoff = order.get("dropoff", "")
    description = f"Комиссия за заказ {pickup} → {dropoff}"

    try:
        payment = create_payment(order_id, commission_amount, description)
        confirmation_url = payment.get("confirmation", {}).get("confirmation_url", "")
        payment_id = payment.get("id", "")
        print(f"[WEBHOOK] Payment created: id={payment_id} url={confirmation_url}")

        # Сохраняем payment_id и url в БД
        cur.execute(
            "UPDATE t_p16564901_site_launch_bot.orders SET payment_id = %s, payment_url = %s, status = 'accepted' WHERE id = %s::uuid",
            (payment_id, confirmation_url, order_id)
        )
        conn.commit()
        cur.close()
        conn.close()

        info = format_order_info(order)
        tg_send(
            chat_id,
            info + f"\n💳 Сумма комиссии: <b>{int(commission_amount)} ₽</b>\nОплатите для подтверждения заказа:",
            reply_markup={"inline_keyboard": [[{"text": "💳 Оплатить комиссию", "url": confirmation_url}]]}
        )

    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        print(f"[WEBHOOK] Payment error {e.code}: {err_body}")
        cur.close()
        conn.close()
        tg_send(chat_id, f"❌ Ошибка создания платежа. Обратитесь к диспетчеру.\n<code>{e.code}</code>")

    return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}