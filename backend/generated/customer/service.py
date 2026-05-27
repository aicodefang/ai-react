def build_customer_payload(payload: dict) -> dict:
    return {
        "customerName": payload.get("customerName"),
        "level": payload.get("level"),
        "contactName": payload.get("contactName"),
        "phone": payload.get("phone"),
        "region": payload.get("region"),
        "status": payload.get("status"),
        "createdAt": payload.get("createdAt"),
    }
