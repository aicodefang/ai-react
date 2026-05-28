from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from ...config import Settings
from ...services.supabase import ensure_supabase_env, is_supabase_table_missing, supabase_endpoint, supabase_headers
from .schema import WarehouseListData, WarehouseRecord, SaveWarehouseRequest


def row_to_warehouse(row: dict) -> WarehouseRecord:
    return WarehouseRecord(
        id=row["id"],
        warehouseName=row["warehouse_name"],
        warehouseType=row["warehouse_type"],
        managerName=row["manager_name"],
        phone=row["phone"],
        city=row["city"],
        status=row["status"],
        createdAt=row["created_at"],
    )


def create_warehouse_payload(payload: SaveWarehouseRequest) -> WarehouseRecord:
    return WarehouseRecord(
        id=f"warehouse-{int(datetime.now().timestamp() * 1000)}",
        warehouseName=payload.warehouseName,
        warehouseType=payload.warehouseType,
        managerName=payload.managerName,
        phone=payload.phone,
        city=payload.city,
        status=payload.status,
        createdAt=payload.createdAt or datetime.now().strftime("%Y-%m-%d"),
    )


def warehouse_to_row(warehouse: WarehouseRecord) -> dict[str, str]:
    return {
        "id": warehouse.id,
        "warehouse_name": warehouse.warehouseName,
        "warehouse_type": warehouse.warehouseType,
        "manager_name": warehouse.managerName,
        "phone": warehouse.phone,
        "city": warehouse.city,
        "status": warehouse.status,
        "created_at": warehouse.createdAt,
    }


async def list_warehouses(
    settings: Settings,
    warehouse_name: str | None,
    warehouse_type: str | None,
) -> WarehouseListData:
    ensure_supabase_env(settings)
    query_parts = ["select=*", "order=created_at.desc"]
    if warehouse_name:
        query_parts.append(f"warehouse_name=ilike.{quote(f'%{warehouse_name}%')}")
    if warehouse_type:
        query_parts.append(f"warehouse_type=eq.{quote(warehouse_type)}")
    query = "&".join(query_parts)

    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.get(
                supabase_endpoint(settings, settings.supabase_warehouses_table, query),
                headers={**supabase_headers(settings), "Prefer": "count=exact"},
            )
            response.raise_for_status()
            total = int(response.headers.get("content-range", "0-0/0").split("/")[-1] or 0)
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {settings.supabase_warehouses_table} 不存在，请先执行 warehouse SQL") from exc
            raise

    return WarehouseListData(list=[row_to_warehouse(row) for row in payload], total=total)


async def create_warehouse(settings: Settings, payload: SaveWarehouseRequest) -> WarehouseRecord:
    ensure_supabase_env(settings)
    warehouse_record = create_warehouse_payload(payload)

    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.post(
                supabase_endpoint(settings, settings.supabase_warehouses_table),
                headers={**supabase_headers(settings), "Prefer": "return=representation"},
                json=warehouse_to_row(warehouse_record),
            )
            response.raise_for_status()
            created = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {settings.supabase_warehouses_table} 不存在，请先执行 warehouse SQL") from exc
            raise

    return row_to_warehouse(created[0])


async def update_warehouse(settings: Settings, warehouse_id: str, payload: SaveWarehouseRequest) -> WarehouseRecord:
    ensure_supabase_env(settings)
    update_payload = {
        "warehouse_name": payload.warehouseName,
        "warehouse_type": payload.warehouseType,
        "manager_name": payload.managerName,
        "phone": payload.phone,
        "city": payload.city,
        "status": payload.status,
    }
    if payload.createdAt:
        update_payload["created_at"] = payload.createdAt

    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.patch(
                supabase_endpoint(settings, settings.supabase_warehouses_table, f"id=eq.{quote(warehouse_id)}"),
                headers={**supabase_headers(settings), "Prefer": "return=representation"},
                json=update_payload,
            )
            response.raise_for_status()
            updated = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {settings.supabase_warehouses_table} 不存在，请先执行 warehouse SQL") from exc
            raise

    if not updated:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return row_to_warehouse(updated[0])


async def delete_warehouse(settings: Settings, warehouse_id: str) -> None:
    ensure_supabase_env(settings)

    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.delete(
                supabase_endpoint(settings, settings.supabase_warehouses_table, f"id=eq.{quote(warehouse_id)}"),
                headers={**supabase_headers(settings), "Prefer": "return=representation"},
            )
            response.raise_for_status()
            payload = response.json() if response.text.strip() else []
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {settings.supabase_warehouses_table} 不存在，请先执行 warehouse SQL") from exc
            raise

    if response.text.strip() and not payload:
        raise HTTPException(status_code=404, detail="Warehouse not found")
