from __future__ import annotations

from pathlib import Path

from ..config import Settings


def artifact_preview(content: str, limit: int = 500) -> str:
    normalized = content.strip()
    return normalized[:limit] + ("..." if len(normalized) > limit else "")


def write_artifact(settings: Settings, relative_path: str, content: str) -> Path:
    target = settings.repo_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target
