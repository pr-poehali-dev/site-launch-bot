"""
Webhook для Telegram бота. При нажатии кнопки 'Принять заказ' —
создаёт платёж в ЮКассе и отправляет водителю ссылку на оплату комиссии.
"""
import json
import os
import uuid
import base64
import urllib.request
import urllib.error
import psycopg2
from psycopg2.extras import RealDictCursor


def tg_api(method: str, payload: dict) -> dict:
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
        return {"ok": False}


def create_payment(amount: float, order_id: str, commission: str, return_url: str) -> str:
    shop_id = os.environ["YUKASSA_SHOP_ID"]
    secret_key = os.environ["YUKASSA_SECRET_KEY"]
    credentials = base64.b64encode(f"{shop_id}:{secret_key}".encode()).decode()

    payload = {
        "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "capture": True,
        "description": f"Комиссия {commission} за заказ #{order_id[:8]}",
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
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
        return result.get("confirmation", {}).get("confirmation_url", "")


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def handler(event: dict, context) -> dict:
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}, "body": ""}

    body = json.loads(event.get("body") or "{}")
    print(f"[WH] {json.dumps(body)[:300]}")

    callback = body.get("callback_query")
    if not callback:
        return {"statusCode": 200, "body": "ok"}

    callback_id = callback["id"]
    data = callback.get("data", "")
    user = callback.get("from", {})
    user_id = user.get("id")
    username = user.get("username", "") or user.get("first_name", "Водитель")
    message = callback.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", ""))
    message_id = message.get("message_id")
    original_text = message.get("text", "")

    # Формат data: "accept:{order_id}"
    if not data.startswith("accept:"):
        tg_api("answerCallbackQuery", {"callback_query_id": callback_id, "text": "Неизвестная команда"})
        return {"statusCode": 200, "body": "ok"}

    order_id = data.replace("accept:", "")
    print(f"[WH] Accept order_id={order_id} by @{username} (id={user_id})")

    # Получаем заказ из БД
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT id::text, price::text, commission FROM t_p16564901_site_launch_bot.orders WHERE id = %s::uuid",
        (order_id,)
    )
    order = cur.fetchone()
    cur.close()
    conn.close()

    if not order:
        tg_api("answerCallbackQuery", {"callback_query_id": callback_id, "text": "Заказ не найден"})
        return {"statusCode": 200, "body": "ok"}

    price = float(order["price"] or 0)
    commission_str = order["commission"] or "15%"
    comm_pct = float(commission_str.replace("%", "")) / 100
    commission_amount = round(price * comm_pct, 2)

    # Отвечаем на callback
    tg_api("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": "Создаю ссылку на оплату..."
    })

    # Получаем username бота для return_url
    bot_info = tg_api("getMe", {})
    bot_username = bot_info.get("result", {}).get("username", "")
    return_url = f"https://t.me/{bot_username}" if bot_username else "https://t.me/"

    try:
        pay_url = create_payment(commission_amount, order_id, commission_str, return_url)

        # Отправляем водителю ссылку в личку
        tg_api("sendMessage", {
            "chat_id": user_id,
            "text": (
                f"✅ <b>Вы приняли заказ!</b>\n\n"
                f"Для подтверждения оплатите комиссию:\n"
                f"<b>{commission_str}</b> от {int(price)} ₽ = <b>{commission_amount:.0f} ₽</b>\n\n"
                f"После оплаты заказ будет закреплён за вами."
            ),
            "parse_mode": "HTML",
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "💳 Оплатить комиссию", "url": pay_url}
                ]]
            }
        })

        # Редактируем сообщение в группе — убираем кнопку, добавляем пометку
        new_text = original_text + f"\n\n🔒 <b>Принят:</b> @{username}"
        tg_api("editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": new_text,
            "parse_mode": "HTML",
        })

        print(f"[WH] Payment {commission_amount} RUB sent to user {user_id}")

    except Exception as e:
        print(f"[WH] Error creating payment: {e}")
        tg_api("sendMessage", {
            "chat_id": user_id,
            "text": f"❌ Ошибка создания платежа. Обратитесь к диспетчеру.",
            "parse_mode": "HTML",
        })

    return {"statusCode": 200, "body": "ok"}
