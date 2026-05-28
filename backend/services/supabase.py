from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from ..config import Settings
from ..models import (
    ApiDefinition,
    ApiListData,
    ApiSchemaField,
    GeneratedPage,
    PageApiBinding,
    PageDsl,
    PageListData,
    SaveApiRequest,
)


def ensure_supabase_env(settings: Settings) -> None:
    if not settings.supabase_url or not settings.supabase_key:
        raise HTTPException(status_code=500, detail="Supabase 环境变量未配置")


def is_supabase_table_missing(error: httpx.HTTPStatusError) -> bool:
    return error.response.status_code == 404


def supabase_headers(settings: Settings) -> dict[str, str]:
    headers = {
        "apikey": settings.supabase_key,
        "Content-Type": "application/json",
    }
    # New Supabase secret/publishable keys are opaque strings, not JWTs.
    # Only legacy anon/service_role keys should be sent as Bearer tokens.
    if not settings.supabase_key.startswith(("sb_secret_", "sb_publishable_")):
        headers["Authorization"] = f"Bearer {settings.supabase_key}"
    return headers


def supabase_endpoint(settings: Settings, table: str, query: str = "") -> str:
    base = f"{settings.supabase_url}/rest/v1/{table}"
    return f"{base}?{query}" if query else base


def row_to_page(row: dict) -> GeneratedPage:
    return GeneratedPage(
        id=row["id"],
        name=row["name"],
        entity=row["entity"],
        route=row["route"],
        status=row["status"],
        createdAt=row["created_at"],
        dsl=PageDsl.model_validate(row["dsl_json"]),
    )


def row_to_api_definition(row: dict) -> ApiDefinition:
    return ApiDefinition(
        id=row["id"],
        name=row["name"],
        entity=row["entity"],
        method=row["method"],
        path=row["path"],
        action=row["action"],
        requestSchema=[ApiSchemaField.model_validate(item) for item in row.get("request_schema", [])],
        responseSchema=[ApiSchemaField.model_validate(item) for item in row.get("response_schema", [])],
        mockData=row.get("mock_data"),
        status=row["status"],
        createdAt=row["created_at"],
    )


def row_to_page_binding(row: dict) -> PageApiBinding:
    return PageApiBinding(
        pageId=row["page_id"],
        listApiId=row.get("list_api_id"),
        createApiId=row.get("create_api_id"),
        updateApiId=row.get("update_api_id"),
        deleteApiId=row.get("delete_api_id"),
        updatedAt=row["updated_at"],
    )


def create_page_payload(dsl: PageDsl) -> GeneratedPage:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    page_id = f"{dsl.entity}-{int(datetime.now().timestamp() * 1000)}"
    return GeneratedPage(
        id=page_id,
        name=dsl.title,
        entity=dsl.entity,
        route=f"/generated/{dsl.entity}",
        status="verified",
        createdAt=timestamp,
        dsl=dsl,
    )


def create_api_payload(payload: SaveApiRequest) -> ApiDefinition:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    api_id = f"{payload.entity}-{payload.action}-{int(datetime.now().timestamp() * 1000)}"
    return ApiDefinition(
        id=api_id,
        name=payload.name,
        entity=payload.entity,
        method=payload.method,
        path=payload.path,
        action=payload.action,
        requestSchema=payload.requestSchema,
        responseSchema=payload.responseSchema,
        mockData=payload.mockData,
        status=payload.status,
        createdAt=timestamp,
    )


async def list_pages(settings: Settings, page_no: int, page_size: int) -> PageListData:
    ensure_supabase_env(settings)
    start = (page_no - 1) * page_size
    query = f"select=*&order=created_at.desc&offset={start}&limit={page_size}"

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            supabase_endpoint(settings, settings.supabase_pages_table, query),
            headers={**supabase_headers(settings), "Prefer": "count=exact"},
        )
        response.raise_for_status()
        total = int(response.headers.get("content-range", "0-0/0").split("/")[-1] or 0)
        payload = response.json()

    return PageListData(list=[row_to_page(row) for row in payload], total=total, pageNo=page_no, pageSize=page_size)


async def get_page(settings: Settings, page_id: str) -> GeneratedPage:
    ensure_supabase_env(settings)
    query = f"select=*&id=eq.{quote(page_id)}"

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            supabase_endpoint(settings, settings.supabase_pages_table, query),
            headers=supabase_headers(settings),
        )
        response.raise_for_status()
        payload = response.json()

    if not payload:
        raise HTTPException(status_code=404, detail="Page not found")
    return row_to_page(payload[0])


async def create_page(settings: Settings, dsl: PageDsl) -> GeneratedPage:
    ensure_supabase_env(settings)
    page = create_page_payload(dsl)
    insert_payload = {
        "id": page.id,
        "name": page.name,
        "entity": page.entity,
        "route": page.route,
        "status": page.status,
        "created_at": page.createdAt,
        "dsl_json": page.dsl.model_dump(),
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            supabase_endpoint(settings, settings.supabase_pages_table),
            headers={**supabase_headers(settings), "Prefer": "return=representation"},
            json=insert_payload,
        )
        response.raise_for_status()

    return page


async def delete_page(settings: Settings, page_id: str) -> None:
    ensure_supabase_env(settings)
    query = f"id=eq.{quote(page_id)}"

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.delete(
            supabase_endpoint(settings, settings.supabase_pages_table, query),
            headers={**supabase_headers(settings), "Prefer": "return=representation"},
        )
        response.raise_for_status()
        payload = response.json()

    if not payload:
        raise HTTPException(status_code=404, detail="Page not found")


async def list_apis(settings: Settings, page_no: int, page_size: int) -> ApiListData:
    ensure_supabase_env(settings)
    start = (page_no - 1) * page_size
    query = f"select=*&order=created_at.desc&offset={start}&limit={page_size}"

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.get(
                supabase_endpoint(settings, settings.supabase_apis_table, query),
                headers={**supabase_headers(settings), "Prefer": "count=exact"},
            )
            response.raise_for_status()
            total = int(response.headers.get("content-range", "0-0/0").split("/")[-1] or 0)
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                return ApiListData(list=[], total=0, pageNo=page_no, pageSize=page_size)
            raise

    return ApiListData(list=[row_to_api_definition(row) for row in payload], total=total, pageNo=page_no, pageSize=page_size)


async def create_api(settings: Settings, payload: SaveApiRequest) -> ApiDefinition:
    ensure_supabase_env(settings)
    api_definition = create_api_payload(payload)
    insert_payload = {
        "id": api_definition.id,
        "name": api_definition.name,
        "entity": api_definition.entity,
        "method": api_definition.method,
        "path": api_definition.path,
        "action": api_definition.action,
        "request_schema": [item.model_dump() for item in api_definition.requestSchema],
        "response_schema": [item.model_dump() for item in api_definition.responseSchema],
        "mock_data": api_definition.mockData,
        "status": api_definition.status,
        "created_at": api_definition.createdAt,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.post(
                supabase_endpoint(settings, settings.supabase_apis_table),
                headers={**supabase_headers(settings), "Prefer": "return=representation"},
                json=insert_payload,
            )
            response.raise_for_status()
            created = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {settings.supabase_apis_table} 不存在，请先建表") from exc
            raise

    return row_to_api_definition(created[0])


async def update_api(settings: Settings, api_id: str, payload: SaveApiRequest) -> ApiDefinition:
    ensure_supabase_env(settings)
    update_payload = {
        "name": payload.name,
        "entity": payload.entity,
        "method": payload.method,
        "path": payload.path,
        "action": payload.action,
        "request_schema": [item.model_dump() for item in payload.requestSchema],
        "response_schema": [item.model_dump() for item in payload.responseSchema],
        "mock_data": payload.mockData,
        "status": payload.status,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.patch(
                supabase_endpoint(settings, settings.supabase_apis_table, f"id=eq.{quote(api_id)}"),
                headers={**supabase_headers(settings), "Prefer": "return=representation"},
                json=update_payload,
            )
            response.raise_for_status()
            updated = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {settings.supabase_apis_table} 不存在，请先建表") from exc
            raise

    if not updated:
        raise HTTPException(status_code=404, detail="Api not found")
    return row_to_api_definition(updated[0])


async def delete_api(settings: Settings, api_id: str) -> None:
    ensure_supabase_env(settings)

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.delete(
                supabase_endpoint(settings, settings.supabase_apis_table, f"id=eq.{quote(api_id)}"),
                headers={**supabase_headers(settings), "Prefer": "return=representation"},
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {settings.supabase_apis_table} 不存在，请先建表") from exc
            raise

    if not payload:
        raise HTTPException(status_code=404, detail="Api not found")


async def get_page_bindings(settings: Settings, page_id: str) -> PageApiBinding:
    ensure_supabase_env(settings)
    query = f"select=*&page_id=eq.{quote(page_id)}"

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.get(
                supabase_endpoint(settings, settings.supabase_bindings_table, query),
                headers=supabase_headers(settings),
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                payload = []
            else:
                raise

    if not payload:
        return PageApiBinding(pageId=page_id, updatedAt=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return row_to_page_binding(payload[0])


async def upsert_page_bindings(settings: Settings, page_id: str, payload: dict) -> PageApiBinding:
    ensure_supabase_env(settings)
    binding = PageApiBinding(pageId=page_id, updatedAt=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), **payload)
    upsert_payload = {
        "page_id": binding.pageId,
        "list_api_id": binding.listApiId,
        "create_api_id": binding.createApiId,
        "update_api_id": binding.updateApiId,
        "delete_api_id": binding.deleteApiId,
        "updated_at": binding.updatedAt,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.post(
                supabase_endpoint(settings, settings.supabase_bindings_table),
                headers={**supabase_headers(settings), "Prefer": "resolution=merge-duplicates,return=representation"},
                json=upsert_payload,
            )
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {settings.supabase_bindings_table} 不存在，请先建表") from exc
            raise

    if not result:
        return binding
    return row_to_page_binding(result[0])
