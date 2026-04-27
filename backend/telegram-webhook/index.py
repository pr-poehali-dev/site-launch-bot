"""
Telegram webhook для @zacazubot. v3
/start — меню подписок (1м/6м/12м).
/start accept_<order_id> — водитель нажал «Принять заказ».
  — добавляется в очередь, первому создаётся платёж на 5 минут.
  — если не оплатил за 5 мин — платёж передаётся следующему в очереди.
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
PAYMENT_TIMEOUT_MINUTES = 5

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

SCHEMA = "t_p16564901_site_launch_bot"


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


def tg_edit(chat_id, message_id, text, parse_mode="HTML", reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        return tg("editMessageText", payload)
    except Exception as e:
        print(f"[TG] editMessageText error: {e}")
        return None


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
        f"SELECT * FROM {SCHEMA}.subscriptions WHERE driver_chat_id = %s AND status = 'active' AND expires_at > NOW() ORDER BY expires_at DESC LIMIT 1",
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
        header = "­"

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
            "one_time_keyboard": False,
            "persistent": True,
        }
    )


def get_queue_list(cur, order_id: str) -> list:
    cur.execute(
        f"SELECT * FROM {SCHEMA}.order_queue WHERE order_id = %s::uuid ORDER BY position ASC",
        (order_id,)
    )
    return [dict(r) for r in cur.fetchall()]


def format_queue_text(queue: list) -> str:
    if not queue:
        return ""
    lines = []
    for i, q in enumerate(queue):
        username = q.get("driver_username", "")
        name = q.get("driver_name", "")
        display = f"@{username}" if username else name or "Водитель"
        status = q.get("status", "waiting")
        if status == "paying":
            mark = "⏳"
        elif status == "paid":
            mark = "✅"
        elif status == "expired":
            mark = "❌"
        else:
            mark = "👆"
        lines.append(f"{mark} {display}")
    return "\n".join(lines)


def update_group_message(order: dict, queue: list, group_chat_id: str):
    msg_id = order.get("tg_group_message_id") or order.get("tg_message_id")
    if not msg_id:
        return

    pickup = order.get("pickup", "—")
    dropoff = order.get("dropoff", "—")
    from_city = order.get("from_city", "")
    to_city = order.get("to_city", "")
    trip_date = str(order.get("trip_date", ""))
    trip_time = order.get("trip_time", "")
    dt_str = trip_date + (f" в {trip_time}" if trip_time else "")
    price = float(order.get("price") or 0)
    tariff = order.get("tariff", "—")
    commission = order.get("commission", "15%")
    comm_pct = float(commission.replace("%", "")) / 100
    driver_amount = round(price * (1 - comm_pct))
    passengers = order.get("passengers", 1)
    luggage = order.get("luggage", 1)

    route_line = f"  🟢 {from_city or pickup}\n  🔴 {to_city or dropoff}"

    queue_text = format_queue_text(queue)
    queue_block = f"\n{'─'*28}\n{queue_text}" if queue_text else ""

    order_status = order.get("status", "new")
    if order_status == "paid":
        status_label = "✅ <b>ЗАКАЗ ВЫКУПЛЕН</b>"
    elif order_status == "accepted":
        status_label = "🔒 <b>ОЖИДАЕТ ОПЛАТЫ</b>"
    else:
        status_label = "📋 <b>ЗАЯВКА</b>"

    text = (
        f"{status_label}\n"
        f"{'─'*28}\n"
        f"📍 <b>Маршрут:</b>\n"
        f"{route_line}\n"
        f"{'─'*28}\n"
        f"📅 <b>Дата:</b> {dt_str}\n"
        f"🚖 <b>Тариф:</b> {tariff}\n"
        f"💰 <b>Стоимость:</b> {int(price)} ₽\n"
        f"🤝 <b>Водитель получит:</b> {int(driver_amount)} ₽ (комиссия {commission})\n"
        f"👥 <b>Пассажиры:</b> {passengers} чел. | 🧳 {luggage} мест"
        f"{queue_block}"
    )

    deep_link = f"https://t.me/{BOT_USERNAME}?start=accept_{order['id']}"
    reply_markup = None
    if order_status not in ("paid",):
        reply_markup = {
            "inline_keyboard": [[{"text": "✅ Принять заказ", "url": deep_link}]]
        }

    tg_edit(group_chat_id, msg_id, text, reply_markup=reply_markup)


def notify_next_in_queue(order_id: str, group_chat_id: str):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(f"SELECT * FROM {SCHEMA}.orders WHERE id = %s::uuid", (order_id,))
    order = cur.fetchone()
    if not order:
        cur.close(); conn.close()
        return
    order = dict(order)

    if order.get("status") == "paid":
        cur.close(); conn.close()
        return

    queue = get_queue_list(cur, order_id)

    # Ищем следующего в очереди со статусом 'waiting'
    next_driver = None
    for q in queue:
        if q["status"] == "waiting":
            next_driver = q
            break

    if not next_driver:
        print(f"[QUEUE] No more drivers in queue for order_id={order_id}")
        # Сбрасываем статус заказа на new чтобы кнопка снова работала
        cur.execute(
            f"UPDATE {SCHEMA}.orders SET status = 'new', active_queue_driver_chat_id = NULL WHERE id = %s::uuid",
            (order_id,)
        )
        conn.commit()
        update_group_message(order, queue, group_chat_id)
        cur.close(); conn.close()
        return

    driver_chat_id = next_driver["driver_chat_id"]
    driver_username = next_driver["driver_username"]
    driver_name = next_driver["driver_name"]

    sub = get_active_subscription(cur, driver_chat_id)
    commission_pct = 10 if sub else 15
    price = float(order.get("price") or 0)
    commission_amount = round(price * commission_pct / 100, 2)
    driver_gets = round(price - commission_amount, 2)

    pickup = order.get("pickup", "")
    dropoff = order.get("dropoff", "")

    try:
        payment = create_yukassa_payment(
            amount=commission_amount,
            description=f"Комиссия {commission_pct}% за заказ {pickup} → {dropoff}",
            metadata={"type": "commission", "order_id": order_id, "driver_chat_id": str(driver_chat_id)},
            return_url=f"https://t.me/{BOT_USERNAME}"
        )
        payment_url = payment.get("confirmation", {}).get("confirmation_url", "")
        payment_id = payment.get("id", "")
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=PAYMENT_TIMEOUT_MINUTES)

        cur.execute(
            f"UPDATE {SCHEMA}.order_queue SET status = 'paying', payment_id = %s, payment_url = %s, payment_expires_at = %s WHERE id = %s",
            (payment_id, payment_url, expires_at, next_driver["id"])
        )
        cur.execute(
            f"UPDATE {SCHEMA}.orders SET status = 'accepted', active_queue_driver_chat_id = %s, payment_id = %s, payment_url = %s, driver_chat_id = %s, driver_username = %s, driver_name = %s WHERE id = %s::uuid",
            (driver_chat_id, payment_id, payment_url, driver_chat_id, driver_username, driver_name, order_id)
        )
        conn.commit()

        sub_note = ""
        if sub:
            expires = sub["expires_at"]
            expires_str = expires.strftime("%d.%m.%Y") if hasattr(expires, "strftime") else str(expires)[:10]
            sub_note = f"\n✅ <b>Подписка активна</b> (до {expires_str}) — комиссия 10%"
        else:
            sub_note = f"\n💡 Оформите <a href='https://t.me/{BOT_USERNAME}'>подписку</a> и платите 10% вместо 15%"

        trip_date = str(order.get("trip_date", ""))
        trip_time = order.get("trip_time", "")
        dt_str = trip_date + (f" в {trip_time}" if trip_time else "")

        order_info = (
            f"🚖 <b>Заказ ждёт оплаты!</b>\n"
            f"{'─'*28}\n"
            f"📍 {pickup} → {dropoff}\n"
            f"📅 {dt_str}\n"
            f"💰 Стоимость: {int(price)} ₽\n"
            f"🤝 Вы получите: {int(driver_gets)} ₽\n"
            f"📊 Комиссия: {int(commission_amount)} ₽ ({commission_pct}%)\n"
            f"{sub_note}\n\n"
            f"⏳ <b>У вас {PAYMENT_TIMEOUT_MINUTES} минут для оплаты!</b>"
        )

        tg_send(
            driver_chat_id,
            order_info,
            reply_markup={"inline_keyboard": [[{"text": "💳 Оплатить комиссию", "url": payment_url}]]}
        )

        # Обновляем сообщение в группе
        queue = get_queue_list(cur, order_id)
        update_group_message(order, queue, group_chat_id)

        print(f"[QUEUE] Notified driver chat_id={driver_chat_id} for order_id={order_id} payment={payment_id}")

    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"[QUEUE] Payment error {e.code}: {err}")
        tg_send(driver_chat_id, f"❌ Ошибка создания платежа. Обратитесь к диспетчеру.\n<code>{e.code}</code>")
    finally:
        cur.close()
        conn.close()


def handle_accept_order(chat_id: int, order_id: str, driver_name: str, driver_username: str):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(f"SELECT * FROM {SCHEMA}.orders WHERE id = %s::uuid", (order_id,))
    order = cur.fetchone()

    if not order:
        cur.close(); conn.close()
        tg_send(chat_id, "❌ Заказ не найден. Возможно, он уже был принят или отменён.")
        return

    order = dict(order)

    if order.get("status") == "paid":
        cur.close(); conn.close()
        tg_send(chat_id, "✅ Этот заказ уже выкуплен другим водителем.")
        return

    # Проверяем — уже в очереди? (только активные записи)
    cur.execute(
        f"SELECT * FROM {SCHEMA}.order_queue WHERE order_id = %s::uuid AND driver_chat_id = %s AND status NOT IN ('expired')",
        (order_id, chat_id)
    )
    existing_queue = cur.fetchone()

    if existing_queue:
        existing_queue = dict(existing_queue)
        status = existing_queue.get("status")
        if status == "paying" and existing_queue.get("payment_url"):
            # Уже платит — проверяем не истёк ли таймаут
            expires_at = existing_queue.get("payment_expires_at")
            now = datetime.now(timezone.utc)
            if expires_at and now < expires_at:
                cur.close(); conn.close()
                tg_send(
                    chat_id,
                    f"⏳ <b>Оплатите комиссию</b>\n\nУ вас ещё есть время. Ссылка на оплату:",
                    reply_markup={"inline_keyboard": [[{"text": "💳 Оплатить комиссию", "url": existing_queue["payment_url"]}]]}
                )
                return
            else:
                cur.close(); conn.close()
                tg_send(chat_id, "❌ Время оплаты истекло. Заказ передан следующему водителю.")
                return
        elif status == "paid":
            cur.close(); conn.close()
            tg_send(chat_id, "✅ Вы уже оплатили комиссию по этому заказу.")
            return
        else:
            cur.close(); conn.close()
            tg_send(chat_id, "👆 Вы уже в очереди на этот заказ. Ожидайте своей очереди.")
            return

    # Добавляем в очередь
    cur.execute(
        f"SELECT COALESCE(MAX(position), 0) + 1 AS next_pos FROM {SCHEMA}.order_queue WHERE order_id = %s::uuid",
        (order_id,)
    )
    row = cur.fetchone()
    position = row["next_pos"] if row else 1

    cur.execute(
        f"INSERT INTO {SCHEMA}.order_queue (order_id, driver_chat_id, driver_username, driver_name, position) VALUES (%s::uuid, %s, %s, %s, %s)",
        (order_id, chat_id, driver_username or "", driver_name or "", position)
    )
    conn.commit()

    queue = get_queue_list(cur, order_id)

    group_chat_id = os.environ.get("TELEGRAM_GROUP_ID", "")
    update_group_message(order, queue, group_chat_id)

    # Если никто сейчас не платит — назначаем этого водителя
    paying_exists = any(q["status"] == "paying" for q in queue)
    accepted_driver = order.get("active_queue_driver_chat_id")

    if not paying_exists and not accepted_driver:
        cur.close(); conn.close()
        notify_next_in_queue(order_id, group_chat_id)
    else:
        # Сообщаем водителю что он в очереди
        display = f"@{driver_username}" if driver_username else driver_name or "Вы"
        tg_send(
            chat_id,
            f"👆 <b>{display}, вы в очереди!</b>\n\n"
            f"Вы на позиции #{position}. Если первый водитель не оплатит в течение {PAYMENT_TIMEOUT_MINUTES} минут, заказ перейдёт к вам."
        )
        cur.close(); conn.close()


def check_expired_payments(group_chat_id: str):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    now = datetime.now(timezone.utc)
    cur.execute(
        f"""
        SELECT oq.*, o.status as order_status
        FROM {SCHEMA}.order_queue oq
        JOIN {SCHEMA}.orders o ON o.id = oq.order_id
        WHERE oq.status = 'paying'
          AND oq.payment_expires_at < %s
          AND o.status != 'paid'
        """,
        (now,)
    )
    expired = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()

    for item in expired:
        order_id = str(item["order_id"])
        driver_chat_id = item["driver_chat_id"]
        print(f"[QUEUE] Payment expired for driver={driver_chat_id} order={order_id}")

        conn2 = get_conn()
        cur2 = conn2.cursor(cursor_factory=RealDictCursor)
        cur2.execute(
            f"UPDATE {SCHEMA}.order_queue SET status = 'expired' WHERE id = %s",
            (item["id"],)
        )
        cur2.execute(
            f"UPDATE {SCHEMA}.orders SET active_queue_driver_chat_id = NULL WHERE id = %s::uuid AND active_queue_driver_chat_id = %s",
            (order_id, driver_chat_id)
        )
        conn2.commit()
        cur2.close(); conn2.close()

        tg_send(driver_chat_id, f"⏰ Время оплаты истекло. Заказ передан следующему водителю.")
        notify_next_in_queue(order_id, group_chat_id)


def handle_subscribe(chat_id: int, plan_key: str, driver_name: str, driver_username: str):
    plan = PLANS.get(plan_key)
    if not plan:
        tg_send(chat_id, "❌ Неверный тариф.")
        return

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        f"SELECT * FROM {SCHEMA}.subscriptions WHERE driver_chat_id = %s AND plan = %s AND status = 'pending' AND created_at > NOW() - INTERVAL '1 hour' LIMIT 1",
        (chat_id, plan_key)
    )
    existing = cur.fetchone()
    if existing and existing["payment_url"]:
        tg_send(
            chat_id,
            f"💳 Счёт на оплату уже создан!\n\nТариф: <b>{plan['label']}</b>\nСумма: <b>{int(plan['amount'])} ₽</b>",
            reply_markup={"inline_keyboard": [[{"text": "💳 Оплатить подписку", "url": existing["payment_url"]}]]}
        )
        cur.close(); conn.close()
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
            f"INSERT INTO {SCHEMA}.subscriptions (driver_chat_id, driver_name, driver_username, plan, amount, status, payment_id, payment_url) VALUES (%s, %s, %s, %s, %s, 'pending', %s, %s)",
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
        cur.close(); conn.close()


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
        f"UPDATE {SCHEMA}.subscriptions SET status = 'expired' WHERE driver_chat_id = %s AND status = 'active'",
        (chat_id,)
    )
    cur.execute(
        f"UPDATE {SCHEMA}.subscriptions SET status = 'active', started_at = %s, expires_at = %s WHERE payment_id = %s AND status = 'pending'",
        (now, expires_at, payment_id)
    )
    cur.execute(
        f"SELECT id FROM {SCHEMA}.subscriptions WHERE payment_id = %s",
        (payment_id,)
    )
    if not cur.fetchone():
        cur.execute(
            f"INSERT INTO {SCHEMA}.subscriptions (driver_chat_id, plan, amount, status, payment_id, started_at, expires_at) VALUES (%s, %s, %s, 'active', %s, %s, %s)",
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
        f"Теперь с каждого заказа вы зарабатываете больше!\n\n"
        f"Удачи на дорогах! 🚗💨",
        reply_markup={"remove_keyboard": True}
    )


def handle_commission_paid(payment: dict, conn, cur):
    metadata = payment.get("metadata", {})
    order_id = metadata.get("order_id", "")
    driver_chat_id_meta = metadata.get("driver_chat_id", "")
    if not order_id:
        return

    cur.execute(f"SELECT * FROM {SCHEMA}.orders WHERE id = %s::uuid", (order_id,))
    order = cur.fetchone()
    if not order:
        return
    order = dict(order)

    # Помечаем заказ оплаченным
    cur.execute(
        f"UPDATE {SCHEMA}.orders SET status = 'paid' WHERE id = %s::uuid",
        (order_id,)
    )

    # Помечаем в очереди кто оплатил
    if driver_chat_id_meta:
        cur.execute(
            f"UPDATE {SCHEMA}.order_queue SET status = 'paid' WHERE order_id = %s::uuid AND driver_chat_id = %s",
            (order_id, int(driver_chat_id_meta))
        )
    else:
        # fallback — помечаем того кто был в статусе paying
        cur.execute(
            f"UPDATE {SCHEMA}.order_queue SET status = 'paid' WHERE order_id = %s::uuid AND status = 'paying'",
            (order_id,)
        )
    conn.commit()

    chat_id = order.get("driver_chat_id")
    if not chat_id:
        return

    pickup     = order.get("pickup", "—")
    dropoff    = order.get("dropoff", "—")
    from_city  = order.get("from_city", "")
    to_city    = order.get("to_city", "")
    price      = float(order.get("price") or 0)
    trip_date  = str(order.get("trip_date", ""))
    trip_time  = order.get("trip_time", "")
    dt_str     = trip_date + (f" в {trip_time}" if trip_time else "")
    phone      = order.get("phone", "—")
    passengers = order.get("passengers", 1)
    luggage    = order.get("luggage", 1)
    comment    = order.get("comment", "")
    stops      = order.get("stops") or []
    tariff     = order.get("tariff", "—")
    commission = order.get("commission", "15%")
    driver_amount = float(order.get("driver_amount") or 0)

    route_line = f"{from_city} → {to_city}\n" if (from_city or to_city) else ""
    stops_text = ""
    if stops:
        stop_list = "\n".join(f"  ↪️ {s.get('address', '')}" for s in stops if s.get("address"))
        if stop_list:
            stops_text = f"\n{stop_list}"

    extras = []
    if order.get("booster"):
        extras.append("Бустер")
    if order.get("child_seat"):
        extras.append("Детское кресло")
    if order.get("animal"):
        extras.append("Животное")
    extras_text = f"\n➕ <b>Доп:</b> {', '.join(extras)}" if extras else ""
    comment_text = f"\n💬 <b>Комментарий:</b> {comment}" if comment else ""

    print(f"[COMMISSION] Paid order_id={order_id} chat_id={chat_id}")

    text = (
        f"✅ <b>Комиссия оплачена — заказ подтверждён!</b>\n"
        f"{'━' * 26}\n"
        f"📍 <b>Маршрут:</b>\n"
        f"{route_line}"
        f"  🟢 {pickup}{stops_text}\n"
        f"  🔴 {dropoff}\n"
        f"{'━' * 26}\n"
        f"📅 <b>Дата:</b> {dt_str}\n"
        f"🚖 <b>Тариф:</b> {tariff}\n"
        f"💰 <b>Стоимость:</b> {int(price)} ₽\n"
        f"🤝 <b>Вы получите:</b> {int(driver_amount)} ₽ (комиссия {commission})\n"
        f"{'━' * 26}\n"
        f"📞 <b>Клиент:</b> {phone}\n"
        f"👥 <b>Пассажиры:</b> {passengers} чел.\n"
        f"🧳 <b>Багаж:</b> {luggage} мест"
        f"{extras_text}"
        f"{comment_text}"
    )

    tg_send(chat_id, text)

    # Обновляем сообщение в группе
    group_chat_id = os.environ.get("TELEGRAM_GROUP_ID", "")
    queue = get_queue_list(cur, order_id)
    update_group_message(order | {"status": "paid"}, queue, group_chat_id)


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

        if params.get("checkexpired") == "1":
            group_chat_id = os.environ.get("TELEGRAM_GROUP_ID", "")
            check_expired_payments(group_chat_id)
            return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

        if params.get("testpay") == "1":
            try:
                payment = create_yukassa_payment(
                    amount=1.00,
                    description="Тестовый платёж — проверка подключения ЮКассы",
                    metadata={"type": "test"},
                    return_url=f"https://t.me/{BOT_USERNAME}"
                )
                return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True, "payment_id": payment.get("id"), "url": payment.get("confirmation", {}).get("confirmation_url")})}
            except urllib.error.HTTPError as e:
                err = e.read().decode()
                return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": False, "error": err})}

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
            cur.close(); conn.close()

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
        if not order_id:
            tg_send(chat_id, "❌ Неверная ссылка на заказ. Попробуйте нажать кнопку ещё раз.")
        else:
            group_chat_id = os.environ.get("TELEGRAM_GROUP_ID", "")
            check_expired_payments(group_chat_id)
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
        cur.close(); conn.close()
        send_subscription_menu(chat_id, sub)

    # /mystatus — статус подписки
    elif text == "/mystatus":
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        sub = get_active_subscription(cur, chat_id)
        cur.close(); conn.close()
        if sub:
            expires = sub["expires_at"]
            expires_str = expires.strftime("%d.%m.%Y") if hasattr(expires, "strftime") else str(expires)[:10]
            tg_send(chat_id, f"✅ <b>Подписка активна</b>\nДо: <b>{expires_str}</b>\nКомиссия: <b>10%</b>")
        else:
            send_subscription_menu(chat_id)

    else:
        tg_send(chat_id, "Используй /start чтобы открыть меню подписок.")

    return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}