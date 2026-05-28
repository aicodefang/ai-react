from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from ..agents.orchestrator import advance_workflow_to_sql, finalize_workflow_after_sql, start_workflow_run
from ..config import get_settings
from ..responses import success
from ..schemas.shared_contract import SharedContract
from ..schemas.workflow import WorkflowArtifact, WorkflowGenerateRequest, WorkflowRun, WorkflowStep
from ..services.workflow_store import list_workflow_artifacts, list_workflow_runs, list_workflow_steps, update_workflow_run


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


def hydrate_workflow_run(run_row: dict, step_rows: list[dict], artifact_rows: list[dict]) -> WorkflowRun:
    shared_contract_payload = run_row.get("shared_contract_json")
    steps = [WorkflowStep.model_validate(map_step_row(step)) for step in step_rows]
    artifacts = [WorkflowArtifact.model_validate(map_artifact_row(artifact)) for artifact in artifact_rows]
    status = run_row["status"]
    has_sql_artifact = any(artifact.artifactType == "sql" for artifact in artifacts)
    has_qa_step = any(step.agentName == "qa" for step in steps)
    if status == "running" and has_sql_artifact and not has_qa_step:
        status = "waiting_for_sql"

    return WorkflowRun(
        id=run_row["id"],
        prompt=run_row["prompt"],
        status=status,
        sharedContract=SharedContract.model_validate(shared_contract_payload) if shared_contract_payload else None,
        steps=steps,
        artifacts=artifacts,
        createdAt=run_row["created_at"],
        updatedAt=run_row["updated_at"],
    )


@router.post("/generate")
async def generate_workflow(payload: WorkflowGenerateRequest):
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="页面需求不能为空")
    settings = get_settings()
    workflow = await start_workflow_run(prompt, settings)
    if workflow.status != "failed":
        asyncio.create_task(advance_workflow_to_sql(workflow.id, prompt, settings, workflow.createdAt))
    return success(workflow, message="多 Agent 工作流已启动")


@router.post("/{run_id}/continue")
async def continue_workflow(run_id: str):
    settings = get_settings()
    runs = await list_workflow_runs(settings)
    run = next((item for item in runs if item.get("id") == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    steps = await list_workflow_steps(settings, run_id)
    artifacts = await list_workflow_artifacts(settings, run_id)
    workflow = hydrate_workflow_run(run, steps, artifacts)
    if workflow.status != "waiting_for_sql":
        raise HTTPException(status_code=400, detail="当前工作流不处于待建表继续状态")
    await update_workflow_run(settings, run_id, "running", workflow.sharedContract.model_dump() if workflow.sharedContract else None)
    workflow.status = "running"
    asyncio.create_task(finalize_workflow_after_sql(run=workflow, settings=settings))
    return success(workflow, message="工作流已继续执行")


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
    return success(hydrate_workflow_run(run, steps, artifacts))
