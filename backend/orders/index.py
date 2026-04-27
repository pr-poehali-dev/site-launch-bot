"""
API для управления заявками на поездки. GET — список, POST — создать заявку, PUT — обновить статус/поля.
"""
import json
import os
import urllib.request
import psycopg2
from psycopg2.extras import RealDictCursor

SCHEMA = "t_p16564901_site_launch_bot"
BOT_USERNAME = "zacazubot"


def tg_edit(chat_id, message_id, text, reply_markup=None):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[TG] editMessageText error: {e}")
        return None


def update_group_message_from_order(order: dict, cur, group_chat_id: str):
    msg_id = order.get("tg_group_message_id") or order.get("tg_message_id")
    if not msg_id or not group_chat_id:
        return

    cur.execute(
        f"SELECT * FROM {SCHEMA}.order_queue WHERE order_id = %s::uuid ORDER BY position ASC",
        (str(order["id"]),)
    )
    queue = [dict(r) for r in cur.fetchall()]

    pickup      = order.get("pickup", "—")
    dropoff     = order.get("dropoff", "—")
    from_city   = order.get("from_city", "")
    to_city     = order.get("to_city", "")
    trip_date   = str(order.get("trip_date", ""))
    trip_time   = order.get("trip_time", "")
    dt_str      = trip_date + (f" в {trip_time}" if trip_time else "")
    price       = float(order.get("price") or 0)
    tariff      = order.get("tariff", "—")
    commission  = order.get("commission", "15%")
    comm_pct    = float(commission.replace("%", "")) / 100
    driver_amount = round(price * (1 - comm_pct))
    passengers  = order.get("passengers", 1)
    luggage     = order.get("luggage", 1)

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

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
}


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def handler(event: dict, context) -> dict:
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    method = event.get("httpMethod", "GET")
    body = {}
    if event.get("body"):
        body = json.loads(event["body"])

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    if method == "GET":
        cur.execute(f"""
            SELECT id::text, from_city, to_city, pickup, dropoff, stops,
                   trip_date::text, trip_time, price::text, tariff, commission,
                   driver_amount::text, phone, passengers, luggage,
                   booster, child_seat, animal, comment, status, created_at::text,
                   tg_group_message_id, driver_chat_id, driver_name, driver_username, payment_url
            FROM {SCHEMA}.orders
            ORDER BY created_at DESC
        """)
        orders = [dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"orders": orders})}

    if method == "POST":
        required = ["pickup", "dropoff", "phone", "trip_date"]
        for field in required:
            if not body.get(field, "").strip() if isinstance(body.get(field), str) else not body.get(field):
                cur.close()
                conn.close()
                return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": f"{field} required"})}

        price = float(body.get("price", 0) or 0)
        commission_str = body.get("commission", "15%")
        commission_pct = float(commission_str.replace("%", "")) / 100
        driver_amount = round(price * (1 - commission_pct), 2)

        cur.execute("""
            INSERT INTO t_p16564901_site_launch_bot.orders
            (from_city, to_city, pickup, dropoff, stops, trip_date, trip_time,
             price, tariff, commission, driver_amount, phone, passengers, luggage,
             booster, child_seat, animal, comment)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id::text, pickup, dropoff, phone, tariff, price::text, status, created_at::text
        """, (
            body.get("from_city", ""),
            body.get("to_city", ""),
            body["pickup"],
            body["dropoff"],
            json.dumps(body.get("stops", [])),
            body["trip_date"],
            body.get("trip_time", ""),
            price,
            body.get("tariff", "Комфорт"),
            commission_str,
            driver_amount,
            body["phone"],
            int(body.get("passengers", 1)),
            int(body.get("luggage", 1)),
            bool(body.get("booster", False)),
            bool(body.get("child_seat", False)),
            bool(body.get("animal", False)),
            body.get("comment", ""),
        ))
        order = dict(cur.fetchone())
        conn.commit()
        cur.close()
        conn.close()
        return {"statusCode": 201, "headers": CORS_HEADERS, "body": json.dumps({"order": order})}

    if method == "PUT":
        order_id = body.get("id")
        if not order_id:
            cur.close(); conn.close()
            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "id required"})}

        # Если передан только статус — быстрое обновление
        if list(body.keys()) == ["id", "status"]:
            status = body.get("status")
            cur.execute(
                "UPDATE t_p16564901_site_launch_bot.orders SET status = %s WHERE id = %s::uuid RETURNING id::text, status",
                (status, order_id)
            )
            row = cur.fetchone()
            conn.commit(); cur.close(); conn.close()
            if not row:
                return {"statusCode": 404, "headers": CORS_HEADERS, "body": json.dumps({"error": "not found"})}
            return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"order": dict(row)})}

        # Полное обновление заказа
        price = float(body.get("price", 0) or 0)
        commission_str = body.get("commission", "15%")
        commission_pct = float(commission_str.replace("%", "")) / 100
        driver_amount = round(price * (1 - commission_pct), 2)

        fields = {
            "from_city":     body.get("from_city", ""),
            "to_city":       body.get("to_city", ""),
            "pickup":        body.get("pickup", ""),
            "dropoff":       body.get("dropoff", ""),
            "trip_date":     body.get("trip_date", ""),
            "trip_time":     body.get("trip_time", ""),
            "price":         price,
            "tariff":        body.get("tariff", ""),
            "commission":    commission_str,
            "driver_amount": driver_amount,
            "phone":         body.get("phone", ""),
            "passengers":    int(body.get("passengers", 1)),
            "luggage":       int(body.get("luggage", 1)),
            "booster":       bool(body.get("booster", False)),
            "child_seat":    bool(body.get("child_seat", False)),
            "animal":        bool(body.get("animal", False)),
            "comment":       body.get("comment", ""),
        }
        if body.get("status"):
            fields["status"] = body["status"]

        set_clause = ", ".join(f"{k} = %s" for k in fields)
        values = list(fields.values()) + [order_id]

        cur.execute(
            f"UPDATE {SCHEMA}.orders SET {set_clause} WHERE id = %s::uuid RETURNING id::text",
            values
        )
        row = cur.fetchone()
        conn.commit()
        if not row:
            cur.close(); conn.close()
            return {"statusCode": 404, "headers": CORS_HEADERS, "body": json.dumps({"error": "not found"})}

        # Обновляем сообщение в Telegram-группе если заказ уже там опубликован
        cur.execute(
            f"SELECT *, id::text as id, trip_date::text as trip_date FROM {SCHEMA}.orders WHERE id = %s::uuid",
            (order_id,)
        )
        updated_order = dict(cur.fetchone())
        group_chat_id = os.environ.get("TELEGRAM_GROUP_ID", "")
        update_group_message_from_order(updated_order, cur, group_chat_id)

        cur.close(); conn.close()
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    if method == "DELETE":
        order_id = body.get("id")
        if not order_id:
            cur.close()
            conn.close()
            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "id required"})}

        # Получаем заказ до удаления, чтобы отредактировать сообщение в группе
        cur.execute(
            f"SELECT * FROM {SCHEMA}.orders WHERE id = %s::uuid",
            (order_id,)
        )
        row = cur.fetchone()
        if row:
            order = dict(row)
            msg_id = order.get("tg_group_message_id") or order.get("tg_message_id")
            group_chat_id = os.environ.get("TELEGRAM_GROUP_ID", "")
            if msg_id and group_chat_id:
                pickup   = order.get("pickup", "—")
                dropoff  = order.get("dropoff", "—")
                from_city = order.get("from_city", "")
                to_city   = order.get("to_city", "")
                trip_date = str(order.get("trip_date", ""))
                trip_time = order.get("trip_time", "")
                dt_str    = trip_date + (f" в {trip_time}" if trip_time else "")
                price     = float(order.get("price") or 0)
                route_line = f"  🟢 {from_city or pickup}\n  🔴 {to_city or dropoff}"
                cancelled_text = (
                    f"🚫 <b>ЗАКАЗ ОТМЕНЁН ДИСПЕТЧЕРОМ</b>\n"
                    f"{'─'*28}\n"
                    f"📍 <b>Маршрут:</b>\n{route_line}\n"
                    f"{'─'*28}\n"
                    f"📅 <b>Дата:</b> {dt_str}\n"
                    f"💰 <b>Стоимость:</b> {int(price)} ₽"
                )
                tg_edit(group_chat_id, msg_id, cancelled_text, reply_markup=None)

        cur.execute("DELETE FROM t_p16564901_site_launch_bot.orders WHERE id = %s::uuid", (order_id,))
        conn.commit()
        cur.close()
        conn.close()
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    cur.close()
    conn.close()
    return {"statusCode": 405, "headers": CORS_HEADERS, "body": json.dumps({"error": "method not allowed"})}