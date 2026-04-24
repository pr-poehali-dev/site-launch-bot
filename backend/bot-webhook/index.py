"""
Webhook для Telegram бота. Обрабатывает нажатие кнопки Принять:
создаёт платёж в ЮКассе, отправляет ссылку водителю в личку,
и убирает кнопку из сообщения в группе.
"""
import json
import os
import uuid
import base64
import urllib.request
import urllib.error
import psycopg2
from psycopg2.extras import RealDictCursor


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
}


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def tg_request(method: str, payload: dict) -> dict:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[TG] {method} error {e.code}: {body}")
        return {"ok": False, "error": body}


def create_yukassa_payment(amount: float, order_id: str, description: str) -> str:
    shop_id = os.environ["YUKASSA_SHOP_ID"]
    secret_key = os.environ["YUKASSA_SECRET_KEY"]
    credentials = base64.b64encode(f"{shop_id}:{secret_key}".encode()).decode()

    payload = {
        "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": f"https://t.me/{os.environ.get('BOT_USERNAME', '')}"},
        "capture": True,
        "description": description,
        "metadata": {"order_id": order_id}
    }

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.yookassa.ru/v3/payments",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}",
            "Idempotence-Key": str(uuid.uuid4()),
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            return result.get("confirmation", {}).get("confirmation_url", ""), result.get("id", "")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[YK] Payment error {e.code}: {body}")
        return "", ""


def handler(event: dict, context) -> dict:
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    body = json.loads(event.get("body") or "{}")
    print(f"[WEBHOOK] {json.dumps(body)[:500]}")

    # Обрабатываем callback_query (нажатие inline-кнопки)
    callback = body.get("callback_query")
    if not callback:
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    callback_id = callback.get("id")
    user = callback.get("from", {})
    user_id = user.get("id")
    username = user.get("username", "")
    first_name = user.get("first_name", "")
    data = callback.get("data", "")
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    # Ожидаем data вида: "accept:{order_id}"
    if not data.startswith("accept:"):
        tg_request("answerCallbackQuery", {"callback_query_id": callback_id, "text": "Неизвестная команда"})
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    order_id = data.replace("accept:", "").strip()
    print(f"[WEBHOOK] Driver {user_id} accepting order {order_id}")

    # Проверяем заказ в БД
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT * FROM t_p16564901_site_launch_bot.orders WHERE id = %s::uuid",
        (order_id,)
    )
    order = cur.fetchone()

    if not order:
        tg_request("answerCallbackQuery", {"callback_query_id": callback_id, "text": "Заказ не найден"})
        cur.close(); conn.close()
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    # Проверяем что заказ ещё не принят
    if order["status"] not in ("on_sale", "new"):
        tg_request("answerCallbackQuery", {
            "callback_query_id": callback_id,
            "text": "Этот заказ уже принят другим водителем",
            "show_alert": True
        })
        cur.close(); conn.close()
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    # Считаем сумму комиссии
    price = float(order["price"] or 0)
    commission_str = order["commission"] or "15%"
    commission_pct = float(commission_str.replace("%", "")) / 100
    commission_amount = round(price * commission_pct, 2)

    driver_amount = round(price * (1 - commission_pct), 2)

    # Создаём платёж в ЮКассе
    description = f"Комиссия за заказ {order['pickup']} → {order['dropoff']}"
    payment_url, payment_id = create_yukassa_payment(commission_amount, order_id, description)

    if not payment_url:
        tg_request("answerCallbackQuery", {
            "callback_query_id": callback_id,
            "text": "Ошибка создания платежа. Обратитесь к диспетчеру.",
            "show_alert": True
        })
        cur.close(); conn.close()
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    # Сохраняем payment_id и меняем статус
    cur.execute(
        """UPDATE t_p16564901_site_launch_bot.orders
           SET status = 'in_progress', payment_id = %s, payment_url = %s
           WHERE id = %s::uuid""",
        (payment_id, payment_url, order_id)
    )
    conn.commit()
    cur.close(); conn.close()

    # Отвечаем на callback
    tg_request("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": "Заказ принят! Проверьте личные сообщения для оплаты.",
        "show_alert": False
    })

    # Редактируем сообщение в группе — убираем кнопку, добавляем пометку
    driver_name = f"@{username}" if username else first_name
    tg_request("editMessageReplyMarkup", {
        "chat_id": chat_id,
        "message_id": message_id,
        "reply_markup": {"inline_keyboard": []}
    })
    tg_request("sendMessage", {
        "chat_id": chat_id,
        "text": f"✅ Заказ принят водителем {driver_name}\n📍 {order['pickup']} → {order['dropoff']}",
        "parse_mode": "HTML",
        "reply_to_message_id": message_id
    })

    # Отправляем водителю в личку ссылку на оплату
    tg_request("sendMessage", {
        "chat_id": user_id,
        "text": (
            f"🚖 <b>Вы приняли заказ!</b>\n\n"
            f"📍 {order['pickup']} → {order['dropoff']}\n"
            f"📅 {order['trip_date']}"
            + (f" в {order['trip_time']}" if order.get('trip_time') else "") + "\n"
            f"💰 Стоимость: <b>{int(price)} ₽</b>\n"
            f"🤝 Ваш заработок: <b>{int(driver_amount)} ₽</b>\n"
            f"📞 Клиент: <b>{order['phone']}</b>\n\n"
            f"{'─' * 28}\n"
            f"💳 Для активации заказа оплатите комиссию: <b>{commission_amount} ₽</b>"
        ),
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[
                {"text": f"💳 Оплатить комиссию {int(commission_amount)} ₽", "url": payment_url}
            ]]
        }
    })

    return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}
