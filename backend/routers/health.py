from __future__ import annotations

from fastapi import APIRouter

from ..responses import success


router = APIRouter()


@router.get("/health")
def health():
    return success({"status": "ok"})
