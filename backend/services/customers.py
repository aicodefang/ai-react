from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from ..config import Settings
from ..models import CustomerListData, CustomerRecord, SaveCustomerRequest
from .supabase import ensure_supabase_env, is_supabase_table_missing, supabase_endpoint, supabase_headers


def row_to_customer(row: dict) -> CustomerRecord:
    return CustomerRecord(
        id=row["id"],
        customerName=row["customer_name"],
        level=row["level"],
        contactName=row["contact_name"],
        phone=row["phone"],
        region=row["region"],
        status=row["status"],
        createdAt=row["created_at"],
    )


def create_customer_payload(payload: SaveCustomerRequest) -> CustomerRecord:
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


def customer_to_row(customer: CustomerRecord) -> dict[str, str]:
    return {
        "id": customer.id,
        "customer_name": customer.customerName,
        "level": customer.level,
        "contact_name": customer.contactName,
        "phone": customer.phone,
        "region": customer.region,
        "status": customer.status,
        "created_at": customer.createdAt,
    }


async def list_customers(
    settings: Settings,
    customer_name: str | None,
    level: str | None,
    status: str | None,
) -> CustomerListData:
    ensure_supabase_env(settings)
    query_parts = ["select=*", "order=created_at.desc"]
    if customer_name:
        query_parts.append(f"customer_name=ilike.{quote(f'%{customer_name}%')}")
    if level:
        query_parts.append(f"level=eq.{quote(level)}")
    if status:
        query_parts.append(f"status=eq.{quote(status)}")
    query = "&".join(query_parts)

    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.get(
                supabase_endpoint(settings, settings.supabase_customers_table, query),
                headers={**supabase_headers(settings), "Prefer": "count=exact"},
            )
            response.raise_for_status()
            total = int(response.headers.get("content-range", "0-0/0").split("/")[-1] or 0)
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                return CustomerListData(list=[], total=0)
            raise

    return CustomerListData(list=[row_to_customer(row) for row in payload], total=total)


async def create_customer(settings: Settings, payload: SaveCustomerRequest) -> CustomerRecord:
    ensure_supabase_env(settings)
    customer = create_customer_payload(payload)

    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.post(
                supabase_endpoint(settings, settings.supabase_customers_table),
                headers={**supabase_headers(settings), "Prefer": "return=representation"},
                json=customer_to_row(customer),
            )
            response.raise_for_status()
            created = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {settings.supabase_customers_table} 不存在，请先建表") from exc
            raise

    return row_to_customer(created[0])


async def update_customer(settings: Settings, customer_id: str, payload: SaveCustomerRequest) -> CustomerRecord:
    ensure_supabase_env(settings)
    update_payload = {
        "customer_name": payload.customerName,
        "level": payload.level,
        "contact_name": payload.contactName,
        "phone": payload.phone,
        "region": payload.region,
        "status": payload.status,
    }
    if payload.createdAt:
        update_payload["created_at"] = payload.createdAt

    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.patch(
                supabase_endpoint(settings, settings.supabase_customers_table, f"id=eq.{quote(customer_id)}"),
                headers={**supabase_headers(settings), "Prefer": "return=representation"},
                json=update_payload,
            )
            response.raise_for_status()
            updated = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {settings.supabase_customers_table} 不存在，请先建表") from exc
            raise

    if not updated:
        raise HTTPException(status_code=404, detail="Customer not found")
    return row_to_customer(updated[0])


async def delete_customer(settings: Settings, customer_id: str) -> None:
    ensure_supabase_env(settings)

    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.delete(
                supabase_endpoint(settings, settings.supabase_customers_table, f"id=eq.{quote(customer_id)}"),
                headers={**supabase_headers(settings), "Prefer": "return=representation"},
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {settings.supabase_customers_table} 不存在，请先建表") from exc
            raise

    if not payload:
        raise HTTPException(status_code=404, detail="Customer not found")
