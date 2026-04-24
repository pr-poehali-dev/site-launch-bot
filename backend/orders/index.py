"""
API для управления заявками на поездки. GET — список, POST — создать заявку, PUT — обновить статус.
"""
import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor

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
        cur.execute("""
            SELECT id::text, from_city, to_city, pickup, dropoff, stops,
                   trip_date::text, trip_time, price::text, tariff, commission,
                   driver_amount::text, phone, passengers, luggage,
                   booster, child_seat, animal, comment, status, created_at::text
            FROM t_p16564901_site_launch_bot.orders
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
        status = body.get("status")
        if not order_id or not status:
            cur.close()
            conn.close()
            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "id and status required"})}
        cur.execute(
            "UPDATE t_p16564901_site_launch_bot.orders SET status = %s WHERE id = %s::uuid RETURNING id::text, status",
            (status, order_id)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if not row:
            return {"statusCode": 404, "headers": CORS_HEADERS, "body": json.dumps({"error": "not found"})}
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"order": dict(row)})}

    if method == "DELETE":
        order_id = body.get("id")
        if not order_id:
            cur.close()
            conn.close()
            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "id required"})}
        cur.execute("DELETE FROM t_p16564901_site_launch_bot.orders WHERE id = %s::uuid", (order_id,))
        conn.commit()
        cur.close()
        conn.close()
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    cur.close()
    conn.close()
    return {"statusCode": 405, "headers": CORS_HEADERS, "body": json.dumps({"error": "method not allowed"})}
