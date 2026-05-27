from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..agents import run_workflow
from ..config import get_settings
from ..responses import success
from ..schemas.workflow import WorkflowGenerateRequest
from ..services.workflow_store import list_workflow_artifacts, list_workflow_runs, list_workflow_steps


router = APIRouter(prefix="/workflows", tags=["workflows"])


def map_run_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "prompt": row["prompt"],
        "status": row["status"],
        "sharedContract": row.get("shared_contract_json"),
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def map_step_row(row: dict) -> dict:
    error_message = row.get("error_message") or ""
    return {
        "id": row["id"],
        "runId": row["run_id"],
        "agentName": row["agent_name"],
        "status": row["status"],
        "summary": row["summary"],
        "output": row.get("output_json"),
        "warnings": [],
        "errors": [error_message] if error_message else [],
        "startedAt": row["started_at"],
        "finishedAt": row.get("finished_at"),
    }


def map_artifact_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "runId": row["run_id"],
        "agentName": row["agent_name"],
        "artifactType": row["artifact_type"],
        "targetPath": row["target_path"],
        "contentPreview": row["content_preview"],
        "createdAt": row["created_at"],
    }


@router.post("/generate")
async def generate_workflow(payload: WorkflowGenerateRequest):
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="页面需求不能为空")
    workflow = await run_workflow(prompt, get_settings())
    return success(workflow, message="多 Agent 工作流执行完成")


@router.get("")
async def get_workflows():
    rows = await list_workflow_runs(get_settings())
    return success([map_run_row(row) for row in rows])


@router.get("/{run_id}")
async def get_workflow_detail(run_id: str):
    settings = get_settings()
    runs = await list_workflow_runs(settings)
    run = next((item for item in runs if item.get("id") == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    steps = await list_workflow_steps(settings, run_id)
    artifacts = await list_workflow_artifacts(settings, run_id)
    return success(
        {
            **map_run_row(run),
            "steps": [map_step_row(step) for step in steps],
            "artifacts": [map_artifact_row(artifact) for artifact in artifacts],
        }
    )
