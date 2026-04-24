"""
CRUD API для управления ботами. Поддерживает: список, создание, обновление статуса, удаление.
"""
import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
}


def handler(event: dict, context) -> dict:
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    method = event.get("httpMethod", "GET")
    params = event.get("queryStringParameters") or {}
    body = {}
    if event.get("body"):
        body = json.loads(event["body"])

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # GET /  — список всех ботов
    if method == "GET":
        cur.execute(
            "SELECT id::text, name, status, version, uptime, requests, cpu, memory, last_deploy, environment, description, created_at::text, updated_at::text FROM t_p16564901_site_launch_bot.bots ORDER BY created_at DESC"
        )
        bots = [dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"bots": bots})}

    # POST / — создать бота
    if method == "POST":
        name = body.get("name", "").strip()
        version = body.get("version", "v1.0.0").strip()
        environment = body.get("environment", "production").strip()
        description = body.get("description", "").strip()
        if not name:
            cur.close()
            conn.close()
            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "name required"})}
        cur.execute(
            "INSERT INTO t_p16564901_site_launch_bot.bots (name, version, environment, description) VALUES (%s, %s, %s, %s) RETURNING id::text, name, status, version, uptime, requests, cpu, memory, last_deploy, environment, description, created_at::text",
            (name, version, environment, description),
        )
        bot = dict(cur.fetchone())
        conn.commit()
        cur.close()
        conn.close()
        return {"statusCode": 201, "headers": CORS_HEADERS, "body": json.dumps({"bot": bot})}

    # PUT / — обновить бота (статус, параметры)
    if method == "PUT":
        bot_id = body.get("id")
        if not bot_id:
            cur.close()
            conn.close()
            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "id required"})}

        updates = []
        values = []
        allowed = ["status", "version", "uptime", "requests", "cpu", "memory", "last_deploy", "environment", "description", "name"]
        for field in allowed:
            if field in body:
                updates.append(f"{field} = %s")
                values.append(body[field])
        if not updates:
            cur.close()
            conn.close()
            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "nothing to update"})}

        updates.append("updated_at = NOW()")
        values.append(bot_id)
        cur.execute(
            f"UPDATE t_p16564901_site_launch_bot.bots SET {', '.join(updates)} WHERE id = %s::uuid RETURNING id::text, name, status, version, uptime, requests, cpu, memory, last_deploy, environment, description",
            values,
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if not row:
            return {"statusCode": 404, "headers": CORS_HEADERS, "body": json.dumps({"error": "not found"})}
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"bot": dict(row)})}

    # DELETE / — удалить бота
    if method == "DELETE":
        bot_id = body.get("id") or params.get("id")
        if not bot_id:
            cur.close()
            conn.close()
            return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "id required"})}
        cur.execute("DELETE FROM t_p16564901_site_launch_bot.bots WHERE id = %s::uuid", (bot_id,))
        conn.commit()
        cur.close()
        conn.close()
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True})}

    cur.close()
    conn.close()
    return {"statusCode": 405, "headers": CORS_HEADERS, "body": json.dumps({"error": "method not allowed"})}
