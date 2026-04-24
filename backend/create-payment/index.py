"""
Создаёт платёж в ЮКассе для оплаты комиссии водителем. v6
"""
import json
import os
import uuid
import urllib.request
import urllib.error
import base64

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
}


def handler(event: dict, context) -> dict:
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    # Диагностика переменных окружения
    yk_keys = {k: v[:6] + "..." for k, v in os.environ.items() if "YUK" in k or "KASS" in k.upper()}
    print(f"[YK] env keys: {yk_keys}")

    shop_id = os.environ.get("YUKASSA_SHOP_ID", "").strip()
    secret_key = os.environ.get("YUKASSA_SECRET_KEY", "").strip()
    print(f"[YK] shop_id='{shop_id}' secret_key_len={len(secret_key)} starts='{secret_key[:10]}'")

    body = json.loads(event.get("body") or "{}")
    order_id = body.get("order_id", "")
    amount = float(body.get("amount", 0))
    description = body.get("description", "Комиссия за заказ")

    if not order_id or amount <= 0:
        return {"statusCode": 400, "headers": CORS_HEADERS, "body": json.dumps({"error": "order_id and amount required"})}

    if not shop_id or not secret_key:
        return {"statusCode": 500, "headers": CORS_HEADERS, "body": json.dumps({"error": f"Missing: shop_id={bool(shop_id)} secret={bool(secret_key)}"})}

    credentials = base64.b64encode(f"{shop_id}:{secret_key}".encode()).decode()
    idempotence_key = str(uuid.uuid4())

    payload = {
        "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
        "confirmation": {"type": "redirect", "return_url": "https://t.me/"},
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

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            confirmation_url = result.get("confirmation", {}).get("confirmation_url", "")
            payment_id = result.get("id", "")
            print(f"[YK] Payment OK: id={payment_id}")
            return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps({"ok": True, "payment_id": payment_id, "confirmation_url": confirmation_url})}
    except urllib.error.HTTPError as e:
        body_err = e.read().decode()
        print(f"[YK] HTTPError {e.code}: {body_err}")
        return {"statusCode": 502, "headers": CORS_HEADERS, "body": json.dumps({"ok": False, "error": f"ЮКасса {e.code}: {body_err}"})}