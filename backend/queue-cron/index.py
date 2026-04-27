"""
Крон-задача: каждую минуту проверяет истёкшие платежи в очереди и передаёт заказ следующему водителю.
"""
import json
import os
import urllib.request
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone, timedelta

SCHEMA = "t_p16564901_site_launch_bot"
BOT_USERNAME = "zacazubot"
PAYMENT_TIMEOUT_MINUTES = 5

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


def tg_edit(chat_id, message_id, text, parse_mode="HTML", reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    try:
        return tg("editMessageText", payload)
    except Exception as e:
        print(f"[TG] editMessageText error: {e}")
        return None


def get_queue_list(cur, order_id: str):
    cur.execute(
        f"SELECT * FROM {SCHEMA}.order_queue WHERE order_id = %s::uuid ORDER BY position ASC",
        (order_id,)
    )
    return [dict(r) for r in cur.fetchall()]


def update_group_message(order: dict, queue: list, group_chat_id: str):
    msg_id = order.get("tg_group_message_id") or order.get("tg_message_id")
    if not msg_id or not group_chat_id:
        return

    pickup     = order.get("pickup", "—")
    dropoff    = order.get("dropoff", "—")
    from_city  = order.get("from_city", "")
    to_city    = order.get("to_city", "")
    trip_date  = str(order.get("trip_date", ""))
    trip_time  = order.get("trip_time", "")
    dt_str     = trip_date + (f" в {trip_time}" if trip_time else "")
    price      = float(order.get("price") or 0)
    tariff     = order.get("tariff", "—")
    commission = order.get("commission", "15%")
    comm_pct   = float(commission.replace("%", "")) / 100
    driver_amount = round(price * (1 - comm_pct))
    passengers = order.get("passengers", 1)
    luggage    = order.get("luggage", 1)
    route_line = f"  🟢 {from_city or pickup}\n  🔴 {to_city or dropoff}"

    queue_lines = []
    for q in queue:
        uname = q.get("driver_username", "")
        name  = q.get("driver_name", "")
        disp  = f"@{uname}" if uname else name or "Водитель"
        st    = q.get("status", "waiting")
        mark  = {"paying": "⏳", "paid": "✅", "expired": "❌"}.get(st, "👆")
        queue_lines.append(f"{mark} {disp}")
    queue_block = ("\n" + "─" * 28 + "\n" + "\n".join(queue_lines)) if queue_lines else ""

    order_status = order.get("status", "new")
    status_label = {"paid": "✅ <b>ЗАКАЗ ВЫКУПЛЕН</b>", "accepted": "🔒 <b>ОЖИДАЕТ ОПЛАТЫ</b>"}.get(order_status, "📋 <b>ЗАЯВКА</b>")

    text = (
        f"{status_label}\n"
        f"{'─'*28}\n"
        f"📍 <b>Маршрут:</b>\n{route_line}\n"
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
        reply_markup = {"inline_keyboard": [[{"text": "✅ Принять заказ", "url": deep_link}]]}

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

    cur.execute(
        f"SELECT * FROM {SCHEMA}.order_queue WHERE order_id = %s::uuid AND status = 'waiting' ORDER BY position ASC LIMIT 1",
        (order_id,)
    )
    next_driver = cur.fetchone()
    if not next_driver:
        print(f"[CRON] No more drivers in queue for order_id={order_id}")
        cur.close(); conn.close()
        return
    next_driver = dict(next_driver)

    driver_chat_id = next_driver["driver_chat_id"]

    try:
        import uuid as _uuid
        import base64 as _base64
        import urllib.error as _urlerr

        yukassa_shop_id = os.environ.get("YUKASSA_SHOP_ID", "")
        yukassa_secret  = os.environ.get("YUKASSA_SECRET_KEY", "")
        price      = float(order.get("price") or 0)
        commission = order.get("commission", "15%")
        comm_pct   = float(commission.replace("%", "")) / 100

        sub_conn = get_conn()
        sub_cur = sub_conn.cursor(cursor_factory=RealDictCursor)
        sub_cur.execute(
            f"SELECT * FROM {SCHEMA}.subscriptions WHERE driver_chat_id = %s AND status = 'active' AND expires_at > NOW() LIMIT 1",
            (driver_chat_id,)
        )
        sub = sub_cur.fetchone()
        sub_cur.close(); sub_conn.close()

        if sub:
            comm_pct = 0.10

        commission_amount = round(price * comm_pct, 2)
        commission_pct    = int(comm_pct * 100)
        driver_gets       = round(price - commission_amount)

        idempotency_key = str(_uuid.uuid4())
        payment_payload = {
            "amount": {"value": f"{commission_amount:.2f}", "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": f"https://t.me/{BOT_USERNAME}"},
            "capture": True,
            "description": f"Комиссия за заказ {order_id[:8]}",
            "metadata": {"order_id": order_id, "driver_chat_id": str(driver_chat_id)},
        }
        creds = _base64.b64encode(f"{yukassa_shop_id}:{yukassa_secret}".encode()).decode()
        req = urllib.request.Request(
            "https://api.yookassa.ru/v3/payments",
            data=json.dumps(payment_payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Basic {creds}",
                "Idempotence-Key": idempotency_key,
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            pay_data = json.loads(resp.read())

        payment_id  = pay_data["id"]
        payment_url = pay_data["confirmation"]["confirmation_url"]
        expires_at  = datetime.now(timezone.utc) + timedelta(minutes=PAYMENT_TIMEOUT_MINUTES)

        cur.execute(
            f"""UPDATE {SCHEMA}.order_queue
                SET status = 'paying', payment_id = %s, payment_url = %s, payment_expires_at = %s
                WHERE id = %s""",
            (payment_id, payment_url, expires_at, next_driver["id"])
        )
        cur.execute(
            f"UPDATE {SCHEMA}.orders SET active_queue_driver_chat_id = %s WHERE id = %s::uuid",
            (driver_chat_id, order_id)
        )
        conn.commit()

        pickup   = order.get("pickup", "")
        dropoff  = order.get("dropoff", "")
        trip_date = str(order.get("trip_date", ""))
        trip_time = order.get("trip_time", "")
        dt_str   = trip_date + (f" в {trip_time}" if trip_time else "")

        sub_note = ""
        if not sub:
            sub_note = f"\n💡 Оформите <a href='https://t.me/{BOT_USERNAME}'>подписку</a> и платите 10% вместо 15%"

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

        sent = tg_send(
            driver_chat_id,
            order_info,
            reply_markup={"inline_keyboard": [[{"text": "💳 Оплатить комиссию", "url": payment_url}]]}
        )
        driver_msg_id = sent.get("result", {}).get("message_id") if sent else None
        if driver_msg_id:
            cur.execute(
                f"UPDATE {SCHEMA}.order_queue SET driver_message_id = %s WHERE id = %s",
                (driver_msg_id, next_driver["id"])
            )
            conn.commit()

        queue = get_queue_list(cur, order_id)
        update_group_message(order, queue, group_chat_id)

        print(f"[CRON] Notified driver chat_id={driver_chat_id} for order_id={order_id} payment={payment_id}")

    except Exception as e:
        print(f"[CRON] Payment error for driver={driver_chat_id} order={order_id}: {e}")
        tg_send(driver_chat_id, f"❌ Ошибка создания платежа. Обратитесь к диспетчеру.")
    finally:
        cur.close()
        conn.close()


def run_check():
    group_chat_id = os.environ.get("TELEGRAM_GROUP_ID", "")
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    now = datetime.now(timezone.utc)
    warn_at = now + timedelta(minutes=1)

    # Автопереход in_progress → done через 1 час после времени подачи
    cur.execute(
        f"""
        SELECT id, trip_date, trip_time FROM {SCHEMA}.orders
        WHERE status = 'in_progress'
          AND trip_date IS NOT NULL
          AND trip_time IS NOT NULL
          AND trip_time != ''
        """
    )
    in_progress_orders = [dict(r) for r in cur.fetchall()]
    for order in in_progress_orders:
        try:
            trip_dt_str = f"{order['trip_date']} {order['trip_time']}"
            trip_dt = datetime.strptime(trip_dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            done_at = trip_dt + timedelta(hours=1)
            if now >= done_at:
                cur.execute(
                    f"UPDATE {SCHEMA}.orders SET status = 'done' WHERE id = %s",
                    (order["id"],)
                )
                print(f"[CRON] Order {order['id']} auto-completed (trip_time+1h passed)")
        except Exception as e:
            print(f"[CRON] Error parsing trip_time for order {order['id']}: {e}")
    conn.commit()

    # Уведомляем следующего за ~1 минуту до истечения
    cur.execute(
        f"""
        SELECT oq.order_id, o.pickup, o.dropoff
        FROM {SCHEMA}.order_queue oq
        JOIN {SCHEMA}.orders o ON o.id = oq.order_id
        WHERE oq.status = 'paying'
          AND oq.payment_expires_at > %s
          AND oq.payment_expires_at <= %s
          AND o.status != 'paid'
        """,
        (now, warn_at)
    )
    paying_soon = [dict(r) for r in cur.fetchall()]

    for item in paying_soon:
        order_id = str(item["order_id"])
        cur.execute(
            f"""
            SELECT driver_chat_id FROM {SCHEMA}.order_queue
            WHERE order_id = %s::uuid AND status = 'waiting'
            ORDER BY position ASC LIMIT 1
            """,
            (order_id,)
        )
        next_row = cur.fetchone()
        if next_row:
            pickup  = item.get("pickup", "")
            dropoff = item.get("dropoff", "")
            tg_send(
                next_row["driver_chat_id"],
                f"⚡️ <b>Вы следующий!</b>\n\nЧерез ~1 минуту вам придёт ссылка на оплату заказа <b>{pickup} → {dropoff}</b>.\n\nБудьте готовы!"
            )
            print(f"[CRON] Warned next driver={next_row['driver_chat_id']} for order={order_id}")

    # Обрабатываем истёкшие платежи
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
        order_id      = str(item["order_id"])
        driver_chat_id = item["driver_chat_id"]
        print(f"[CRON] Payment expired for driver={driver_chat_id} order={order_id}")

        conn2 = get_conn()
        cur2  = conn2.cursor(cursor_factory=RealDictCursor)
        cur2.execute(
            f"UPDATE {SCHEMA}.order_queue SET status = 'expired' WHERE id = %s",
            (item["id"],)
        )
        cur2.execute(
            f"UPDATE {SCHEMA}.orders SET active_queue_driver_chat_id = NULL WHERE id = %s::uuid AND active_queue_driver_chat_id = %s",
            (order_id, driver_chat_id)
        )
        conn2.commit()

        # Обновляем сообщение в группе — убираем ник водителя (статус expired)
        cur2.execute(f"SELECT * FROM {SCHEMA}.orders WHERE id = %s::uuid", (order_id,))
        order_row = cur2.fetchone()
        if order_row:
            queue_upd = get_queue_list(cur2, order_id)
            update_group_message(dict(order_row), queue_upd, group_chat_id)

        cur2.close(); conn2.close()

        driver_msg_id = item.get("driver_message_id")
        expired_text  = "⏰ <b>Время оплаты истекло</b>\n\nЗаказ передан следующему водителю."
        if driver_msg_id:
            tg_edit(driver_chat_id, driver_msg_id, expired_text, reply_markup={"inline_keyboard": []})
        else:
            tg_send(driver_chat_id, expired_text)

        notify_next_in_queue(order_id, group_chat_id)


def handler(event: dict, context) -> dict:
    """Крон-проверка истёкших платежей в очереди водителей."""
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    run_check()
    return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}