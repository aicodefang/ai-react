from __future__ import annotations

import asyncio
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


def _build_context(run_id: str, prompt: str, contract: object) -> AgentContext:
    return AgentContext(
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


def _run_model(
    run_id: str,
    prompt: str,
    status: str,
    created_at: str,
    contract: object | None,
    steps: list[WorkflowStep],
    artifacts: list[WorkflowArtifact],
) -> WorkflowRun:
    return WorkflowRun(
        id=run_id,
        prompt=prompt,
        status=status,
        sharedContract=contract,
        steps=steps,
        artifacts=artifacts,
        createdAt=created_at,
        updatedAt=now_string(),
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


async def start_workflow_run(prompt: str, settings: Settings) -> WorkflowRun:
    run_id = f"wf-{uuid4().hex[:12]}"
    created_at = now_string()
    create_run_warning = await _safe_create_workflow_run(settings, run_id, prompt, "pending")

    run = _run_model(
        run_id=run_id,
        prompt=prompt,
        status="pending",
        created_at=created_at,
        contract=None,
        steps=[],
        artifacts=[],
    )

    if create_run_warning:
        failed_at = now_string()
        run.status = "failed"
        run.steps.append(
            WorkflowStep(
                id=f"{run_id}-system",
                runId=run_id,
                agentName="system",
                status="failed",
                summary="初始化工作流记录失败",
                output=None,
                warnings=[create_run_warning],
                errors=[create_run_warning],
                startedAt=failed_at,
                finishedAt=failed_at,
            )
        )
    return run


async def advance_workflow_to_sql(run_id: str, prompt: str, settings: Settings, created_at: str) -> WorkflowRun:
    persistence_warnings: list[str] = []
    update_warning = await _safe_update_workflow_run(settings, run_id, "running")
    if update_warning:
        persistence_warnings.append(update_warning)

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

    contract_update_warning = await _safe_update_workflow_run(settings, run_id, "running", contract.model_dump())
    if contract_update_warning:
        persistence_warnings.append(contract_update_warning)

    context = _build_context(run_id, prompt, contract)

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

    artifacts: list[WorkflowArtifact] = []
    artifacts.extend(await _materialize_artifacts(settings, run_id, frontend_result.agent_name, frontend_result.artifacts))
    artifacts.extend(await _materialize_artifacts(settings, run_id, service_result.agent_name, service_result.artifacts))

    waiting_update_warning = await _safe_update_workflow_run(settings, run_id, "waiting_for_sql", contract.model_dump())
    if waiting_update_warning:
        service_step.warnings.append(waiting_update_warning)

    if persistence_warnings:
        service_step.warnings.extend([warning for warning in persistence_warnings if warning not in service_step.warnings])

    return _run_model(
        run_id=run_id,
        prompt=prompt,
        status="waiting_for_sql",
        created_at=created_at,
        contract=contract,
        steps=[planner_step, frontend_step, service_step],
        artifacts=artifacts,
    )


async def finalize_workflow_after_sql(run: WorkflowRun, settings: Settings) -> WorkflowRun:
    if not run.sharedContract:
        raise ValueError("shared contract is required before finalizing workflow")

    context = _build_context(run.id, run.prompt, run.sharedContract)
    running_update_warning = await _safe_update_workflow_run(settings, run.id, "running", run.sharedContract.model_dump())

    frontend_output = next((step.output for step in run.steps if step.agentName == "frontend"), {}) or {}
    service_output = next((step.output for step in run.steps if step.agentName == "service"), {}) or {}

    qa_started = now_string()
    qa_result = run_qa(context, frontend_output, service_output)
    if running_update_warning:
        qa_result.warnings.append(running_update_warning)
    qa_step = _step_model(run.id, qa_result, qa_started)

    qa_warning = await _safe_persist_step(settings, qa_step)
    if qa_warning:
        qa_step.warnings.append(qa_warning)

    final_status = "succeeded" if qa_result.status == "succeeded" else "failed"
    final_update_warning = await _safe_update_workflow_run(settings, run.id, final_status, run.sharedContract.model_dump())
    if final_update_warning:
        qa_step.warnings.append(final_update_warning)

    return _run_model(
        run_id=run.id,
        prompt=run.prompt,
        status=final_status,
        created_at=run.createdAt,
        contract=run.sharedContract,
        steps=[*run.steps, qa_step],
        artifacts=run.artifacts,
    )


async def run_workflow(prompt: str, settings: Settings) -> WorkflowRun:
    initial_run = await start_workflow_run(prompt, settings)
    if initial_run.status == "failed":
        return initial_run
    staged_run = await advance_workflow_to_sql(initial_run.id, prompt, settings, initial_run.createdAt)
    return await finalize_workflow_after_sql(staged_run, settings)
