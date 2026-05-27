from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..schemas.shared_contract import SharedContract


@dataclass
class AgentContext:
    run_id: str
    user_prompt: str
    shared_contract: SharedContract
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentExecutionResult:
    agent_name: str
    status: str
    summary: str
    output: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    artifacts: list[dict[str, str]] = field(default_factory=list)
