from __future__ import annotations

from .base import AgentContext, AgentExecutionResult


def to_snake_case(value: str) -> str:
    chars: list[str] = []
    for index, char in enumerate(value):
        if char.isupper() and index > 0:
            chars.append("_")
        chars.append(char.lower())
    return "".join(chars)


def to_pascal_case(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in value.replace("-", "_").split("_") if part)


def render_service_artifacts(context: AgentContext) -> AgentExecutionResult:
    contract = context.shared_contract
    entity = contract.entity
    entity_plural = f"{entity}s"
    entity_pascal = to_pascal_case(entity)
    table_setting_name = f"supabase_{entity_plural}_table"
    table_name = entity_plural
    save_model_name = f"Save{entity_pascal}Request"
    record_model_name = f"{entity_pascal}Record"
    list_model_name = f"{entity_pascal}ListData"

    row_model_fields = "\n".join([f"    {field.name}: str" for field in contract.fields])
    save_model_fields = "\n".join(
        [f"    {field.name}: str{' | None = None' if not field.required else ''}" for field in contract.fields]
    )
    row_to_record_fields = "\n".join([f'        {field.name}=row["{to_snake_case(field.name)}"],' for field in contract.fields])
    payload_to_record_fields = "\n".join(
        [
            f"        {field.name}=payload.{field.name}{' or datetime.now().strftime(\"%Y-%m-%d\")' if field.name == 'createdAt' else ''},"
            for field in contract.fields
        ]
    )
    record_to_row_fields = "\n".join([f'        "{to_snake_case(field.name)}": {entity}.{field.name},' for field in contract.fields])

    field_map = {field.name: field for field in contract.fields}
    query_params = []
    query_filter_lines = []
    for field_name in contract.queryFields:
        snake_name = to_snake_case(field_name)
        query_params.append(f"    {snake_name}: str | None,")
        if field_map.get(field_name) and field_map[field_name].type == "enum":
            query_filter_lines.append(f"    if {snake_name}:\n        query_parts.append(f\"{snake_name}=eq.{{quote({snake_name})}}\")")
        else:
            query_filter_lines.append(f"    if {snake_name}:\n        query_parts.append(f\"{snake_name}=ilike.{{quote(f'%{{{snake_name}}}%')}}\")")
    query_params_block = "\n".join(query_params)
    query_filter_block = "\n".join(query_filter_lines)

    update_fields = "\n".join(
        [
            f'        "{to_snake_case(field.name)}": payload.{field.name},'
            for field in contract.fields
            if field.name != "createdAt"
        ]
    )

    router_query_params = []
    router_service_args = []
    for field_name in contract.queryFields:
        alias = field_name
        snake_name = to_snake_case(field_name)
        router_query_params.append(f'    {snake_name}: str | None = Query(None, alias="{alias}"),')
        router_service_args.append(snake_name)

    router_query_block = "\n".join(router_query_params)
    router_service_args_block = ", ".join(["get_settings()"] + router_service_args)

    schema_content = f"""from __future__ import annotations

from pydantic import BaseModel


class {record_model_name}(BaseModel):
    id: str
{row_model_fields}


class {save_model_name}(BaseModel):
{save_model_fields}


class {list_model_name}(BaseModel):
    list: list[{record_model_name}]
    total: int
"""

    service_content = f"""from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from ...config import Settings
from ...services.supabase import ensure_supabase_env, is_supabase_table_missing, supabase_endpoint, supabase_headers
from .schema import {list_model_name}, {record_model_name}, {save_model_name}


def row_to_{entity}(row: dict) -> {record_model_name}:
    return {record_model_name}(
        id=row["id"],
{row_to_record_fields}
    )


def create_{entity}_payload(payload: {save_model_name}) -> {record_model_name}:
    return {record_model_name}(
        id=f"{entity}-{{int(datetime.now().timestamp() * 1000)}}",
{payload_to_record_fields}
    )


def {entity}_to_row({entity}: {record_model_name}) -> dict[str, str]:
    return {{
        "id": {entity}.id,
{record_to_row_fields}
    }}


async def list_{entity_plural}(
    settings: Settings,
{query_params_block}
) -> {list_model_name}:
    ensure_supabase_env(settings)
    query_parts = ["select=*", "order=created_at.desc"]
{query_filter_block}
    query = "&".join(query_parts)

    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.get(
                supabase_endpoint(settings, settings.{table_setting_name}, query),
                headers={{**supabase_headers(settings), "Prefer": "count=exact"}},
            )
            response.raise_for_status()
            total = int(response.headers.get("content-range", "0-0/0").split("/")[-1] or 0)
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {{settings.{table_setting_name}}} 不存在，请先执行 {entity} SQL") from exc
            raise

    return {list_model_name}(list=[row_to_{entity}(row) for row in payload], total=total)


async def create_{entity}(settings: Settings, payload: {save_model_name}) -> {record_model_name}:
    ensure_supabase_env(settings)
    {entity}_record = create_{entity}_payload(payload)

    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.post(
                supabase_endpoint(settings, settings.{table_setting_name}),
                headers={{**supabase_headers(settings), "Prefer": "return=representation"}},
                json={entity}_to_row({entity}_record),
            )
            response.raise_for_status()
            created = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {{settings.{table_setting_name}}} 不存在，请先执行 {entity} SQL") from exc
            raise

    return row_to_{entity}(created[0])


async def update_{entity}(settings: Settings, {entity}_id: str, payload: {save_model_name}) -> {record_model_name}:
    ensure_supabase_env(settings)
    update_payload = {{
{update_fields}
    }}
    if payload.createdAt:
        update_payload["created_at"] = payload.createdAt

    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.patch(
                supabase_endpoint(settings, settings.{table_setting_name}, f"id=eq.{{quote({entity}_id)}}"),
                headers={{**supabase_headers(settings), "Prefer": "return=representation"}},
                json=update_payload,
            )
            response.raise_for_status()
            updated = response.json()
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {{settings.{table_setting_name}}} 不存在，请先执行 {entity} SQL") from exc
            raise

    if not updated:
        raise HTTPException(status_code=404, detail="{entity_pascal} not found")
    return row_to_{entity}(updated[0])


async def delete_{entity}(settings: Settings, {entity}_id: str) -> None:
    ensure_supabase_env(settings)

    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        try:
            response = await client.delete(
                supabase_endpoint(settings, settings.{table_setting_name}, f"id=eq.{{quote({entity}_id)}}"),
                headers={{**supabase_headers(settings), "Prefer": "return=representation"}},
            )
            response.raise_for_status()
            payload = response.json() if response.text.strip() else []
        except httpx.HTTPStatusError as exc:
            if is_supabase_table_missing(exc):
                raise HTTPException(status_code=500, detail=f"Supabase 表 {{settings.{table_setting_name}}} 不存在，请先执行 {entity} SQL") from exc
            raise

    if response.text.strip() and not payload:
        raise HTTPException(status_code=404, detail="{entity_pascal} not found")
"""

    router_content = f"""from __future__ import annotations

from fastapi import APIRouter, Query

from ...config import get_settings
from ...responses import success
from .schema import {save_model_name}
from .service import create_{entity}, delete_{entity}, list_{entity_plural}, update_{entity}


router = APIRouter(prefix="/{entity_plural}", tags=["generated-{entity}"])


@router.get("")
async def list_{entity_plural}_route(
{router_query_block}
):
    data = await list_{entity_plural}({router_service_args_block})
    return success(data)


@router.post("")
async def create_{entity}_route(payload: {save_model_name}):
    data = await create_{entity}(get_settings(), payload)
    return success(data, message="{contract.title}创建成功")


@router.put("/{{{entity}_id}}")
async def update_{entity}_route({entity}_id: str, payload: {save_model_name}):
    data = await update_{entity}(get_settings(), {entity}_id, payload)
    return success(data, message="{contract.title}更新成功")


@router.delete("/{{{entity}_id}}")
async def delete_{entity}_route({entity}_id: str):
    await delete_{entity}(get_settings(), {entity}_id)
    return success({{"id": {entity}_id}}, message="{contract.title}删除成功")
"""

    sql_fields = ["id text primary key"]
    for field in contract.fields:
        sql_fields.append(f'{to_snake_case(field.name)} text{" not null" if field.required else ""}')
    sql_content = f"""create table if not exists public.{table_name} (
  """ + ",\n  ".join(sql_fields) + "\n);\n"

    init_content = "from .router import router\n\n__all__ = [\"router\"]\n"

    return AgentExecutionResult(
        agent_name="service",
        status="succeeded",
        summary=f"已生成基于 Supabase 的后端 CRUD 模板与 SQL：{entity}",
        output={
            "entity": entity,
            "table": table_name,
            "storage": "supabase",
            "sqlPath": f"backend/generated/{entity}/{entity}.sql",
            "runtimeApiBase": f"/api/generated/{table_name}",
        },
        artifacts=[
            {
                "artifactType": "backend-init",
                "targetPath": f"backend/generated/{entity}/__init__.py",
                "content": init_content,
            },
            {
                "artifactType": "backend-router",
                "targetPath": f"backend/generated/{entity}/router.py",
                "content": router_content,
            },
            {
                "artifactType": "backend-service",
                "targetPath": f"backend/generated/{entity}/service.py",
                "content": service_content,
            },
            {
                "artifactType": "backend-schema",
                "targetPath": f"backend/generated/{entity}/schema.py",
                "content": schema_content,
            },
            {
                "artifactType": "sql",
                "targetPath": f"backend/generated/{entity}/{entity}.sql",
                "content": sql_content,
            },
        ],
    )
