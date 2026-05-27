from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import uuid4

from ..config import Settings
from ..schemas.workflow import WorkflowArtifact, WorkflowRun, WorkflowStep
from ..services.artifacts import artifact_preview, write_artifact
from ..services.workflow_store import create_workflow_artifact, create_workflow_run, now_string, update_workflow_run, upsert_workflow_step
from .base import AgentContext, AgentExecutionResult
from .frontend_agent import render_frontend_page
from .planner_agent import generate_shared_contract
from .qa_agent import run_qa
from .service_agent import render_service_artifacts


def _step_model(run_id: str, result: AgentExecutionResult, started_at: str, finished_at: str | None = None) -> WorkflowStep:
    return WorkflowStep(
        id=f"{run_id}-{result.agent_name}",
        runId=run_id,
        agentName=result.agent_name,
        status=result.status,
        summary=result.summary,
        output=result.output,
        warnings=result.warnings,
        errors=result.errors,
        startedAt=started_at,
        finishedAt=finished_at or now_string(),
    )


async def _safe_create_workflow_run(settings: Settings, run_id: str, prompt: str, status: str) -> str | None:
    try:
        await create_workflow_run(settings, run_id, prompt, status)
        return None
    except Exception as exc:
        return f"workflow_runs 落库失败: {exc}"


async def _safe_update_workflow_run(settings: Settings, run_id: str, status: str, shared_contract: dict | None = None) -> str | None:
    try:
        await update_workflow_run(settings, run_id, status, shared_contract)
        return None
    except Exception as exc:
        return f"workflow_runs 更新失败: {exc}"


async def _persist_step(settings: Settings, step: WorkflowStep) -> None:
    await upsert_workflow_step(
        settings,
        step.id,
        step.runId,
        step.agentName,
        step.status,
        step.summary,
        step.output,
        "\n".join(step.errors) if step.errors else None,
        step.startedAt,
        step.finishedAt,
    )


async def _safe_persist_step(settings: Settings, step: WorkflowStep) -> str | None:
    try:
        await _persist_step(settings, step)
        return None
    except Exception as exc:
        return f"{step.agentName} step 落库失败: {exc}"


async def _materialize_artifacts(settings: Settings, run_id: str, agent_name: str, artifacts: list[dict[str, str]]) -> list[WorkflowArtifact]:
    created: list[WorkflowArtifact] = []
    for index, artifact in enumerate(artifacts, start=1):
        content = artifact["content"]
        target_path = artifact["targetPath"]
        write_artifact(settings, target_path, content)
        artifact_id = f"{run_id}-{agent_name}-{index}"
        preview = artifact_preview(content)
        created.append(
            WorkflowArtifact(
                id=artifact_id,
                runId=run_id,
                agentName=agent_name,
                artifactType=artifact["artifactType"],
                targetPath=target_path,
                contentPreview=preview,
                createdAt=now_string(),
            )
        )
        try:
            await create_workflow_artifact(settings, artifact_id, run_id, agent_name, artifact["artifactType"], target_path, preview)
        except Exception:
            pass
    return created


async def run_workflow(prompt: str, settings: Settings) -> WorkflowRun:
    run_id = f"wf-{uuid4().hex[:12]}"
    created_at = now_string()
    persistence_warnings: list[str] = []
    create_run_warning = await _safe_create_workflow_run(settings, run_id, prompt, "running")
    if create_run_warning:
        persistence_warnings.append(create_run_warning)

    planner_started = now_string()
    contract = await generate_shared_contract(prompt, settings)
    planner_result = AgentExecutionResult(
        agent_name="planner",
        status="succeeded",
        summary=f"已生成共享协议：{contract.title}",
        output=contract.model_dump(),
    )
    planner_step = _step_model(run_id, planner_result, planner_started)
    planner_warning = await _safe_persist_step(settings, planner_step)
    if planner_warning:
        planner_step.warnings.append(planner_warning)
        persistence_warnings.append(planner_warning)
    update_warning = await _safe_update_workflow_run(settings, run_id, "running", contract.model_dump())
    if update_warning:
        persistence_warnings.append(update_warning)

    context = AgentContext(
        run_id=run_id,
        user_prompt=prompt,
        shared_contract=contract,
        context={
            "stack": "React 19 + Ant Design 6 + TypeScript 6 + Vite 8 + FastAPI + Supabase",
            "constraints": [
                "仅写 generated 目录",
                "保持字段 key 一致",
                "新实体后端默认必须使用 Supabase 持久化",
                "禁止生成本地 JSON 文件作为正式存储",
            ],
        },
    )

    frontend_started = now_string()
    service_started = now_string()
    frontend_result, service_result = await asyncio.gather(
        asyncio.to_thread(render_frontend_page, context),
        asyncio.to_thread(render_service_artifacts, context),
    )
    frontend_step = _step_model(run_id, frontend_result, frontend_started)
    service_step = _step_model(run_id, service_result, service_started)
    frontend_warning = await _safe_persist_step(settings, frontend_step)
    if frontend_warning:
        frontend_step.warnings.append(frontend_warning)
        persistence_warnings.append(frontend_warning)
    service_warning = await _safe_persist_step(settings, service_step)
    if service_warning:
        service_step.warnings.append(service_warning)
        persistence_warnings.append(service_warning)

    artifacts = []
    artifacts.extend(await _materialize_artifacts(settings, run_id, frontend_result.agent_name, frontend_result.artifacts))
    artifacts.extend(await _materialize_artifacts(settings, run_id, service_result.agent_name, service_result.artifacts))

    qa_started = now_string()
    qa_result = run_qa(context, frontend_result.output or {}, service_result.output or {})
    qa_result.warnings.extend(persistence_warnings)
    qa_step = _step_model(run_id, qa_result, qa_started)
    qa_warning = await _safe_persist_step(settings, qa_step)
    if qa_warning:
        qa_step.warnings.append(qa_warning)

    final_status = "succeeded" if qa_result.status == "succeeded" else "failed"
    final_update_warning = await _safe_update_workflow_run(settings, run_id, final_status, contract.model_dump())
    if final_update_warning:
        qa_step.warnings.append(final_update_warning)

    return WorkflowRun(
        id=run_id,
        prompt=prompt,
        status=final_status,
        sharedContract=contract,
        steps=[planner_step, frontend_step, service_step, qa_step],
        artifacts=artifacts,
        createdAt=created_at,
        updatedAt=now_string(),
    )
