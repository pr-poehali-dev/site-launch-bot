"""
Создаёт платёж в ЮКассе для оплаты комиссии водителем.
Возвращает ссылку на оплату. v2
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


def create_payment(amount: float, order_id: str, description: str) -> dict:
    shop_id = os.environ["YUKASSA_SHOP_ID"]
    secret_key = os.environ["YUKASSA_SECRET_KEY"]

    credentials = base64.b64encode(f"{shop_id}:{secret_key}".encode()).decode()
    idempotence_key = str(uuid.uuid4())

    payload = {
        "amount": {
            "value": f"{amount:.2f}",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/"
        },
        "capture": True,
        "description": description,
        "metadata": {
            "order_id": order_id
        }
    }

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.yookassa.ru/v3/payments",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}",
            "Idempotence-Key": idempotence_key,
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[YK] HTTPError {e.code}: {body}")
        raise Exception(f"ЮКасса error {e.code}: {body}")


def handler(event: dict, context) -> dict:
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    body = json.loads(event.get("body") or "{}")
    order_id = body.get("order_id", "")
    amount = float(body.get("amount", 0))
    description = body.get("description", "Комиссия за заказ")

    if not order_id or amount <= 0:
        return {
            "statusCode": 400,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": "order_id and amount required"})
        }

    print(f"[YK] Creating payment: order_id={order_id}, amount={amount}")
    result = create_payment(amount, order_id, description)

    confirmation_url = result.get("confirmation", {}).get("confirmation_url", "")
    payment_id = result.get("id", "")
    print(f"[YK] Payment created: id={payment_id}, url={confirmation_url}")

    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({
            "ok": True,
            "payment_id": payment_id,
            "confirmation_url": confirmation_url,
        })
    }