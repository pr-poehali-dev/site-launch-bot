"""
Telegram webhook для @zacazubot.
/start — меню подписок (1м/6м/12м).
/start accept_<order_id> — принять заказ, создать платёж комиссии.
/start sub_<plan> — купить подписку через ЮКассу.
"""
import json
import os
import uuid
import urllib.request
import urllib.error
import base64
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone, timedelta

WEBHOOK_URL = "https://functions.poehali.dev/06f62334-3744-4817-84a2-fee6b379c230"
BOT_USERNAME = "zacazubot"

PLANS = {
    "1m":  {"label": "1 месяц",   "amount": 1500.00, "months": 1},
    "6m":  {"label": "6 месяцев", "amount": 6000.00, "months": 6},
    "12m": {"label": "12 месяцев","amount": 10000.00,"months": 12},
}

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
}


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def tg(method: str, payload: dict) -> dict:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def tg_send(chat_id, text, parse_mode="HTML", reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg("sendMessage", payload)


def create_yukassa_payment(amount: float, description: str, metadata: dict, return_url: str) -> dict:
    shop_id = os.environ.get("YUKASSA_SHOP_ID", "").strip()
    secret_key = os.environ.get("YUKASSA_SECRET_KEY", "").strip()
    credentials = base64.b64encode(f"{shop_id}:{secret_key}".encode()).decode()
    payload = {
        "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": return_url},
        "capture": True,
        "description": description,
        "metadata": metadata,
    }
    req = urllib.request.Request(
        "https://api.yookassa.ru/v3/payments",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}",
            "Idempotence-Key": str(uuid.uuid4()),
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def get_active_subscription(cur, chat_id: int) -> dict | None:
    cur.execute(
        "SELECT * FROM t_p16564901_site_launch_bot.subscriptions WHERE driver_chat_id = %s AND status = 'active' AND expires_at > NOW() ORDER BY expires_at DESC LIMIT 1",
        (chat_id,)
    )
    row = cur.fetchone()
    return dict(row) if row else None


def send_subscription_menu(chat_id: int, sub: dict | None = None):
    if sub:
        expires = sub["expires_at"]
        if hasattr(expires, "strftime"):
            expires_str = expires.strftime("%d.%m.%Y")
        else:
            expires_str = str(expires)[:10]
        header = (
            f"✅ <b>Подписка активна</b>\n"
            f"Действует до: <b>{expires_str}</b>\n"
            f"Ваша комиссия: <b>10%</b>\n\n"
            f"Хотите продлить?"
        )
    else:
        header = "📋 Тарифы подписки:"

    tg_send(
        chat_id,
        header,
        reply_markup={
            "keyboard": [
                [{"text": "📅 1 месяц — 1 500 ₽"}],
                [{"text": "📆 6 месяцев — 6 000 ₽"}],
                [{"text": "🗓 12 месяцев — 10 000 ₽"}],
            ],
            "resize_keyboard": True,
            "one_time_keyboard": True,
        }
    )


def handle_subscribe(chat_id: int, plan_key: str, driver_name: str, driver_username: str):
    plan = PLANS.get(plan_key)
    if not plan:
        tg_send(chat_id, "❌ Неверный тариф.")
        return

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Проверяем не создан ли уже pending платёж для этого плана
    cur.execute(
        "SELECT * FROM t_p16564901_site_launch_bot.subscriptions WHERE driver_chat_id = %s AND plan = %s AND status = 'pending' AND created_at > NOW() - INTERVAL '1 hour' LIMIT 1",
        (chat_id, plan_key)
    )
    existing = cur.fetchone()
    if existing and existing["payment_url"]:
        tg_send(
            chat_id,
            f"💳 Счёт на оплату уже создан!\n\nТариф: <b>{plan['label']}</b>\nСумма: <b>{int(plan['amount'])} ₽</b>",
            reply_markup={"inline_keyboard": [[{"text": "💳 Оплатить подписку", "url": existing["payment_url"]}]]}
        )
        cur.close()
        conn.close()
        return

    try:
        payment = create_yukassa_payment(
            amount=plan["amount"],
            description=f"Подписка {plan['label']} — @{BOT_USERNAME}",
            metadata={"type": "subscription", "plan": plan_key, "driver_chat_id": str(chat_id)},
            return_url=f"https://t.me/{BOT_USERNAME}"
        )
        payment_id = payment.get("id", "")
        payment_url = payment.get("confirmation", {}).get("confirmation_url", "")

        cur.execute(
            "INSERT INTO t_p16564901_site_launch_bot.subscriptions (driver_chat_id, driver_name, driver_username, plan, amount, status, payment_id, payment_url) VALUES (%s, %s, %s, %s, %s, 'pending', %s, %s)",
            (chat_id, driver_name, driver_username, plan_key, plan["amount"], payment_id, payment_url)
        )
        conn.commit()

        tg_send(
            chat_id,
            f"✅ Счёт создан!\n\nТариф: <b>{plan['label']}</b>\nСумма: <b>{int(plan['amount'])} ₽</b>\n\nПосле оплаты комиссия снизится до <b>10%</b>.",
            reply_markup={"inline_keyboard": [[{"text": "💳 Оплатить подписку", "url": payment_url}]]}
        )
        print(f"[SUB] Created subscription payment plan={plan_key} chat_id={chat_id} payment_id={payment_id}")

    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"[SUB] Payment error {e.code}: {err}")
        tg_send(chat_id, f"❌ Ошибка создания платежа. Обратитесь к администратору.\n<code>{e.code}</code>")
    finally:
        cur.close()
        conn.close()


def handle_accept_order(chat_id: int, order_id: str, driver_name: str, driver_username: str):
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
        return

    order = dict(order)

    # Записываем данные водителя при первом клике
    if not order.get("driver_chat_id"):
        cur.execute(
            "UPDATE t_p16564901_site_launch_bot.orders SET driver_chat_id = %s, driver_username = %s, driver_name = %s WHERE id = %s::uuid",
            (chat_id, driver_username, driver_name, order_id)
        )
        conn.commit()

    # Проверяем активную подписку
    sub = get_active_subscription(cur, chat_id)
    commission_pct = 10 if sub else 15
    price = float(order.get("price") or 0)
    commission_amount = round(price * commission_pct / 100, 2)
    driver_gets = round(price - commission_amount, 2)

    sub_note = ""
    if sub:
        expires = sub["expires_at"]
        expires_str = expires.strftime("%d.%m.%Y") if hasattr(expires, "strftime") else str(expires)[:10]
        sub_note = f"\n✅ <b>Подписка активна</b> (до {expires_str}) — комиссия 10%"
    else:
        sub_note = f"\n💡 Оформите <a href='https://t.me/{BOT_USERNAME}'>подписку</a> и платите комиссию 10% вместо 15%"

    # Если платёж уже создан — отправляем сохранённую ссылку
    if order.get("payment_url"):
        tg_send(
            chat_id,
            f"📋 <b>Заказ уже принят</b>\n{order.get('pickup','—')} → {order.get('dropoff','—')}\n\n💳 Ссылка на оплату комиссии:{sub_note}",
            reply_markup={"inline_keyboard": [[{"text": "💳 Оплатить комиссию", "url": order["payment_url"]}]]}
        )
        cur.close()
        conn.close()
        return

    pickup = order.get("pickup", "")
    dropoff = order.get("dropoff", "")
    trip_date = str(order.get("trip_date", ""))
    trip_time = order.get("trip_time", "")
    datetime_str = trip_date + (f" в {trip_time}" if trip_time else "")

    order_info = (
        f"🚖 <b>Заказ принят!</b>\n"
        f"{'─'*28}\n"
        f"📍 {pickup} → {dropoff}\n"
        f"📅 {datetime_str}\n"
        f"💰 Стоимость: {int(price)} ₽\n"
        f"🤝 Вы получите: {int(driver_gets)} ₽\n"
        f"📊 Комиссия: {int(commission_amount)} ₽ ({commission_pct}%)\n"
        f"{sub_note}\n"
    )

    try:
        payment = create_yukassa_payment(
            amount=commission_amount,
            description=f"Комиссия {commission_pct}% за заказ {pickup} → {dropoff}",
            metadata={"type": "commission", "order_id": order_id},
            return_url=f"https://t.me/{BOT_USERNAME}"
        )
        payment_url = payment.get("confirmation", {}).get("confirmation_url", "")
        payment_id = payment.get("id", "")

        cur.execute(
            "UPDATE t_p16564901_site_launch_bot.orders SET payment_id = %s, payment_url = %s, status = 'accepted', driver_chat_id = %s, driver_username = %s, driver_name = %s WHERE id = %s::uuid",
            (payment_id, payment_url, chat_id, driver_username, driver_name, order_id)
        )
        conn.commit()

        tg_send(
            chat_id,
            order_info + f"Оплатите комиссию для подтверждения заказа:",
            reply_markup={"inline_keyboard": [[{"text": "💳 Оплатить комиссию", "url": payment_url}]]}
        )
        print(f"[ORDER] payment created order_id={order_id} commission={commission_pct}% amount={commission_amount}")

    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"[ORDER] Payment error {e.code}: {err}")
        tg_send(chat_id, f"❌ Ошибка создания платежа. Обратитесь к диспетчеру.\n<code>{e.code}</code>")
    finally:
        cur.close()
        conn.close()


def handle_subscription_paid(payment: dict, conn, cur):
    metadata = payment.get("metadata", {})
    plan = metadata.get("plan", "")
    chat_id = int(metadata.get("driver_chat_id", 0))
    payment_id = payment.get("id", "")

    if not chat_id or not plan:
        print(f"[SUB] Missing metadata chat_id={chat_id} plan={plan}")
        return

    months = PLANS.get(plan, {}).get("months", 1)
    label  = PLANS.get(plan, {}).get("label", plan)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=30 * months)
    expires_str = expires_at.strftime("%d.%m.%Y")

    cur.execute(
        "UPDATE t_p16564901_site_launch_bot.subscriptions SET status = 'expired' WHERE driver_chat_id = %s AND status = 'active'",
        (chat_id,)
    )
    cur.execute(
        "UPDATE t_p16564901_site_launch_bot.subscriptions SET status = 'active', started_at = %s, expires_at = %s WHERE payment_id = %s AND status = 'pending'",
        (now, expires_at, payment_id)
    )
    cur.execute(
        "SELECT id FROM t_p16564901_site_launch_bot.subscriptions WHERE payment_id = %s",
        (payment_id,)
    )
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO t_p16564901_site_launch_bot.subscriptions (driver_chat_id, plan, amount, status, payment_id, started_at, expires_at) VALUES (%s, %s, %s, 'active', %s, %s, %s)",
            (chat_id, plan, float(payment.get("amount", {}).get("value", 0)), payment_id, now, expires_at)
        )
    conn.commit()
    print(f"[SUB] Activated plan={plan} chat_id={chat_id} expires={expires_str}")

    tg_send(
        chat_id,
        f"🎉 <b>Подписка активирована!</b>\n"
        f"{'━' * 26}\n"
        f"📦 Тариф: <b>{label}</b>\n"
        f"📅 Действует до: <b>{expires_str}</b>\n"
        f"💸 Комиссия теперь: <b>10%</b> вместо 15%\n\n"
        f"Теперь с каждого заказа вы зарабатываете больше — "
        f"разница сразу остаётся у вас.\n\n"
        f"Удачи на дорогах! 🚗💨",
        reply_markup={"remove_keyboard": True}
    )


def handle_commission_paid(payment: dict, conn, cur):
    metadata = payment.get("metadata", {})
    order_id = metadata.get("order_id", "")
    if not order_id:
        return

    cur.execute(
        "UPDATE t_p16564901_site_launch_bot.orders SET status = 'paid' WHERE id = %s::uuid",
        (order_id,)
    )
    conn.commit()

    cur.execute(
        "SELECT * FROM t_p16564901_site_launch_bot.orders WHERE id = %s::uuid",
        (order_id,)
    )
    order = cur.fetchone()
    if not order:
        return
    order = dict(order)
    chat_id = order.get("driver_chat_id")
    if not chat_id:
        return

    pickup   = order.get("pickup", "—")
    dropoff  = order.get("dropoff", "—")
    price    = float(order.get("price") or 0)
    trip_date = str(order.get("trip_date", ""))
    trip_time = order.get("trip_time", "")
    dt_str = trip_date + (f" в {trip_time}" if trip_time else "")

    print(f"[COMMISSION] Paid order_id={order_id} chat_id={chat_id}")

    tg_send(
        chat_id,
        f"✅ <b>Комиссия оплачена — заказ подтверждён!</b>\n"
        f"{'━' * 26}\n"
        f"📍 {pickup} → {dropoff}\n"
        f"📅 {dt_str}\n"
        f"💰 Стоимость поездки: <b>{int(price)} ₽</b>\n\n"
        f"Заказ закреплён за вами. Счастливого пути! 🚀"
    )


def handler(event: dict, context) -> dict:
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    # GET /?register=1 — регистрируем webhook у Telegram
    if event.get("httpMethod") == "GET":
        params = event.get("queryStringParameters") or {}
        if params.get("register") == "1":
            token = os.environ["TELEGRAM_BOT_TOKEN"]
            url = f"https://api.telegram.org/bot{token}/setWebhook"
            payload = json.dumps({"url": WEBHOOK_URL}).encode()
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())
            print(f"[WEBHOOK] setWebhook: {result}")
            return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps(result)}
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    body = json.loads(event.get("body") or "{}")

    # Уведомление от ЮКассы (содержит поле "event")
    if "event" in body:
        print(f"[YUKASSA] notification: {json.dumps(body)[:800]}")
        event_type     = body.get("event", "")
        payment        = body.get("object", {})
        payment_status = payment.get("status", "")
        pay_type       = payment.get("metadata", {}).get("type", "")

        if event_type == "payment.succeeded" and payment_status == "succeeded":
            conn = get_conn()
            cur  = conn.cursor(cursor_factory=RealDictCursor)
            if pay_type == "subscription":
                handle_subscription_paid(payment, conn, cur)
            elif pay_type == "commission":
                handle_commission_paid(payment, conn, cur)
            cur.close()
            conn.close()

        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    print(f"[WEBHOOK] update: {json.dumps(body)[:600]}")

    # Обработка нажатия inline-кнопок (callback_query)
    callback = body.get("callback_query")
    if callback:
        cb_data = callback.get("data", "")
        cb_id = callback.get("id", "")
        from_info = callback.get("from", {})
        chat_id = callback.get("message", {}).get("chat", {}).get("id") or from_info.get("id")
        driver_username = from_info.get("username", "")
        first_name = from_info.get("first_name", "")
        last_name = from_info.get("last_name", "")
        driver_name = (first_name + " " + last_name).strip()

        # Отвечаем на callback чтобы убрать «часики» с кнопки
        try:
            tg("answerCallbackQuery", {"callback_query_id": cb_id})
        except Exception:
            pass

        if cb_data.startswith("sub_"):
            plan_key = cb_data.replace("sub_", "", 1)
            handle_subscribe(chat_id, plan_key, driver_name, driver_username)

        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    message = body.get("message") or body.get("edited_message")
    if not message:
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()
    from_info = message.get("from", {})
    driver_username = from_info.get("username", "")
    first_name = from_info.get("first_name", "")
    last_name = from_info.get("last_name", "")
    driver_name = (first_name + " " + last_name).strip()

    print(f"[WEBHOOK] chat_id={chat_id} text={text!r} name={driver_name}")

    # Кнопки подписки из ReplyKeyboard
    PLAN_BUTTONS = {
        "📅 1 месяц — 1 500 ₽":    "1m",
        "📆 6 месяцев — 6 000 ₽":  "6m",
        "🗓 12 месяцев — 10 000 ₽": "12m",
    }
    if text in PLAN_BUTTONS:
        handle_subscribe(chat_id, PLAN_BUTTONS[text], driver_name, driver_username)

    # /start accept_<order_id>
    elif text.startswith("/start accept_"):
        order_id = text.replace("/start accept_", "").strip()
        handle_accept_order(chat_id, order_id, driver_name, driver_username)

    # /start sub_<plan>
    elif text.startswith("/start sub_"):
        plan_key = text.replace("/start sub_", "").strip()
        handle_subscribe(chat_id, plan_key, driver_name, driver_username)

    # /start или /start без параметров — главное меню
    elif text.startswith("/start") or text == "/menu":
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        sub = get_active_subscription(cur, chat_id)
        cur.close()
        conn.close()
        send_subscription_menu(chat_id, sub)

    # /mystatus — статус подписки
    elif text == "/mystatus":
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        sub = get_active_subscription(cur, chat_id)
        cur.close()
        conn.close()
        if sub:
            expires = sub["expires_at"]
            expires_str = expires.strftime("%d.%m.%Y") if hasattr(expires, "strftime") else str(expires)[:10]
            tg_send(chat_id, f"✅ <b>Подписка активна</b>\nДо: <b>{expires_str}</b>\nКомиссия: <b>10%</b>")
        else:
            send_subscription_menu(chat_id)

    else:
        tg_send(chat_id, "Используй /start чтобы открыть меню подписок.")

    return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}