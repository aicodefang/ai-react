from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .shared_contract import SharedContract


WorkflowStatus = Literal["pending", "running", "succeeded", "failed"]


class WorkflowGenerateRequest(BaseModel):
    prompt: str


class WorkflowArtifact(BaseModel):
    id: str
    runId: str
    agentName: str
    artifactType: str
    targetPath: str
    contentPreview: str
    createdAt: str


class WorkflowStep(BaseModel):
    id: str
    runId: str
    agentName: str
    status: WorkflowStatus
    summary: str
    output: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    startedAt: str
    finishedAt: str | None = None


class WorkflowRun(BaseModel):
    id: str
    prompt: str
    status: WorkflowStatus
    sharedContract: SharedContract | None = None
    steps: list[WorkflowStep] = Field(default_factory=list)
    artifacts: list[WorkflowArtifact] = Field(default_factory=list)
    createdAt: str
    updatedAt: str
