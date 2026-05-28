from __future__ import annotations

from datetime import datetime
from urllib.parse import quote
import asyncio

import httpx

from ..config import Settings
from .supabase import ensure_supabase_env, supabase_endpoint, supabase_headers


def now_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def _get_with_retry(url: str, headers: dict[str, str], attempts: int = 3) -> list[dict]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except (httpx.ConnectError, httpx.HTTPStatusError) as exc:
            last_error = exc
            status_code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
            if status_code not in (401, 408, 429, 500, 502, 503, 504) and not isinstance(exc, httpx.ConnectError):
                raise
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(0.4 * (attempt + 1))
    if last_error:
        raise last_error
    return []


async def create_workflow_run(settings: Settings, run_id: str, prompt: str, status: str) -> None:
    ensure_supabase_env(settings)
    payload = {
        "id": run_id,
        "prompt": prompt,
        "status": status,
        "shared_contract_json": None,
        "created_at": now_string(),
        "updated_at": now_string(),
    }
    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        response = await client.post(
            supabase_endpoint(settings, settings.supabase_workflow_runs_table),
            headers={**supabase_headers(settings), "Prefer": "return=minimal"},
            json=payload,
        )
        response.raise_for_status()


async def update_workflow_run(settings: Settings, run_id: str, status: str, shared_contract: dict | None = None) -> None:
    ensure_supabase_env(settings)
    payload: dict[str, object] = {
        "status": status,
        "updated_at": now_string(),
    }
    if shared_contract is not None:
        payload["shared_contract_json"] = shared_contract
    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        response = await client.patch(
            supabase_endpoint(settings, settings.supabase_workflow_runs_table, f"id=eq.{run_id}"),
            headers={**supabase_headers(settings), "Prefer": "return=minimal"},
            json=payload,
        )
        response.raise_for_status()


async def upsert_workflow_step(
    settings: Settings,
    step_id: str,
    run_id: str,
    agent_name: str,
    status: str,
    summary: str,
    output_json: dict | None,
    error_message: str | None,
    started_at: str,
    finished_at: str | None,
) -> None:
    ensure_supabase_env(settings)
    payload = {
        "id": step_id,
        "run_id": run_id,
        "agent_name": agent_name,
        "status": status,
        "summary": summary,
        "output_json": output_json,
        "error_message": error_message,
        "started_at": started_at,
        "finished_at": finished_at,
    }
    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        response = await client.post(
            supabase_endpoint(settings, settings.supabase_workflow_steps_table),
            headers={**supabase_headers(settings), "Prefer": "resolution=merge-duplicates,return=minimal"},
            json=payload,
        )
        response.raise_for_status()


async def create_workflow_artifact(
    settings: Settings,
    artifact_id: str,
    run_id: str,
    agent_name: str,
    artifact_type: str,
    target_path: str,
    content_preview: str,
) -> None:
    ensure_supabase_env(settings)
    payload = {
        "id": artifact_id,
        "run_id": run_id,
        "agent_name": agent_name,
        "artifact_type": artifact_type,
        "target_path": target_path,
        "content_preview": content_preview,
        "created_at": now_string(),
    }
    async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
        response = await client.post(
            supabase_endpoint(settings, settings.supabase_workflow_artifacts_table),
            headers={**supabase_headers(settings), "Prefer": "return=minimal"},
            json=payload,
        )
        response.raise_for_status()


async def list_workflow_runs(settings: Settings) -> list[dict]:
    ensure_supabase_env(settings)
    query = "select=*&order=created_at.desc&limit=20"
    return await _get_with_retry(
        supabase_endpoint(settings, settings.supabase_workflow_runs_table, query),
        supabase_headers(settings),
    )


async def list_workflow_steps(settings: Settings, run_id: str) -> list[dict]:
    ensure_supabase_env(settings)
    query = f"select=*&run_id=eq.{quote(run_id)}&order=started_at.asc"
    return await _get_with_retry(
        supabase_endpoint(settings, settings.supabase_workflow_steps_table, query),
        supabase_headers(settings),
    )


async def list_workflow_artifacts(settings: Settings, run_id: str) -> list[dict]:
    ensure_supabase_env(settings)
    query = f"select=*&run_id=eq.{quote(run_id)}&order=created_at.asc"
    return await _get_with_retry(
        supabase_endpoint(settings, settings.supabase_workflow_artifacts_table, query),
        supabase_headers(settings),
    )
