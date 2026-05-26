from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..models import CustomerRecord, SaveCustomerRequest


def default_customers() -> list[CustomerRecord]:
    return [
        CustomerRecord(
            id="customer-001",
            customerName="星河制造集团",
            level="A",
            contactName="林悦",
            phone="13800138001",
            region="华东",
            status="active",
            createdAt="2026-05-20",
        ),
        CustomerRecord(
            id="customer-002",
            customerName="北辰供应链",
            level="B",
            contactName="周明",
            phone="13900139002",
            region="华北",
            status="pending",
            createdAt="2026-05-22",
        ),
        CustomerRecord(
            id="customer-003",
            customerName="蓝鲸能源",
            level="C",
            contactName="陈安",
            phone="13700137003",
            region="华南",
            status="disabled",
            createdAt="2026-05-23",
        ),
    ]


def ensure_customers_file(customers_file: Path) -> None:
    if customers_file.exists():
        return
    customers_file.write_text(
        json.dumps([item.model_dump() for item in default_customers()], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def read_customers(customers_file: Path) -> list[CustomerRecord]:
    ensure_customers_file(customers_file)
    payload = json.loads(customers_file.read_text(encoding="utf-8"))
    return [CustomerRecord.model_validate(item) for item in payload]


def write_customers(customers_file: Path, customers: list[CustomerRecord]) -> None:
    customers_file.write_text(
        json.dumps([item.model_dump() for item in customers], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def create_customer_record(payload: SaveCustomerRequest) -> CustomerRecord:
    return CustomerRecord(
        id=f"customer-{int(datetime.now().timestamp() * 1000)}",
        customerName=payload.customerName,
        level=payload.level,
        contactName=payload.contactName,
        phone=payload.phone,
        region=payload.region,
        status=payload.status,
        createdAt=payload.createdAt or datetime.now().strftime("%Y-%m-%d"),
    )
