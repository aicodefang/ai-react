from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from ...config import Settings
from ...services.supabase import ensure_supabase_env, is_supabase_table_missing, supabase_endpoint, supabase_headers
from .schema import SupplierListData, SupplierRecord, SaveSupplierRequest


def row_to_supplier(row: dict) -> SupplierRecord:
    return SupplierRecord(
        id=row["id"],
        supplierName=row["supplier_name"],
        supplierType=row["supplier_type"],
        contactName=row["contact_name"],
        phone=row["phone"],
        city=row["city"],
        cooperationStatus=row["cooperation_status"],
        createdAt=row["created_at"],
    )


def create_supplier_payload(payload: SaveSupplierRequest) -> SupplierRecord:
    return SupplierRecord(
        id=f"supplier-{int(datetime.now().timestamp() * 1000)}",
        supplierName=payload.supplierName,
        supplierType=payload.supplierType,
        contactName=payload.contactName,
        phone=payload.phone,
        city=payload.city,
        cooperationStatus=payload.cooperationStatus,
        createdAt=payload.createdAt or datetime.now().strftime("%Y-%m-%d"),
    )


def supplier_to_row(supplier: SupplierRecord) -> dict[str, str]:
    return {
        "id": supplier.id,
        "supplier_name": supplier.supplierName,
        "supplier_type": supplier.supplierType,
        "contact_name": supplier.contactName,
        "phone": supplier.phone,
        "city": supplier.city,
        "cooperation_status": supplier.cooperationStatus,
        "created_at": supplier.createdAt,
    }


async def list_suppliers(
    settings: Settings,
    supplier_name: str | None,
    supplier_type: str | None,
    contact_name: str | None,
) -> SupplierListData:
    ensure_supabase_env(settings)
    query_parts = ["select=*", "order=created_at.desc"]
    if supplier_name:
        query_parts.append(f"supplier_name=ilike.{quote(f'%{supplier_name}%')}")
    if supplier_type:
        query_parts.append(f"supplier_type=eq.{quote(supplier_type)}")
    if contact_name:
        query_parts.append(f"contact_name=ilike.{quote(f'%{contact_name}%')}")
    query = "&".join(query_parts)

    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.get(
                supabase_endpoint(settings, settings.supabase_suppliers_table, query),
                headers={**supabase_headers(settings), "Prefer": "count=exact"},
            )
            response.raise_for_status()
            total = int(response.headers.get("content-range", "0-0/0").split("/")[-1] or 0)
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {settings.supabase_suppliers_table} 不存在，请先执行 supplier SQL") from exc
            raise

    return SupplierListData(list=[row_to_supplier(row) for row in payload], total=total)


async def create_supplier(settings: Settings, payload: SaveSupplierRequest) -> SupplierRecord:
    ensure_supabase_env(settings)
    supplier_record = create_supplier_payload(payload)

    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.post(
                supabase_endpoint(settings, settings.supabase_suppliers_table),
                headers={**supabase_headers(settings), "Prefer": "return=representation"},
                json=supplier_to_row(supplier_record),
            )
            response.raise_for_status()
            created = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {settings.supabase_suppliers_table} 不存在，请先执行 supplier SQL") from exc
            raise

    return row_to_supplier(created[0])


async def update_supplier(settings: Settings, supplier_id: str, payload: SaveSupplierRequest) -> SupplierRecord:
    ensure_supabase_env(settings)
    update_payload = {
        "supplier_name": payload.supplierName,
        "supplier_type": payload.supplierType,
        "contact_name": payload.contactName,
        "phone": payload.phone,
        "city": payload.city,
        "cooperation_status": payload.cooperationStatus,
    }
    if payload.createdAt:
        update_payload["created_at"] = payload.createdAt

    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.patch(
                supabase_endpoint(settings, settings.supabase_suppliers_table, f"id=eq.{quote(supplier_id)}"),
                headers={**supabase_headers(settings), "Prefer": "return=representation"},
                json=update_payload,
            )
            response.raise_for_status()
            updated = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {settings.supabase_suppliers_table} 不存在，请先执行 supplier SQL") from exc
            raise

    if not updated:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return row_to_supplier(updated[0])


async def delete_supplier(settings: Settings, supplier_id: str) -> None:
    ensure_supabase_env(settings)

    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.delete(
                supabase_endpoint(settings, settings.supabase_suppliers_table, f"id=eq.{quote(supplier_id)}"),
                headers={**supabase_headers(settings), "Prefer": "return=representation"},
            )
            response.raise_for_status()
            payload = response.json() if response.text.strip() else []
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {settings.supabase_suppliers_table} 不存在，请先执行 supplier SQL") from exc
            raise

    if response.text.strip() and not payload:
        raise HTTPException(status_code=404, detail="Supplier not found")
