from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..config import get_settings
from ..models import GenerateDslRequest, PageDsl
from ..responses import success
from ..services.dsl import generate_dsl_with_xiaomi


router = APIRouter(prefix="/dsl", tags=["dsl"])


@router.post("/generate")
async def generate_dsl(payload: GenerateDslRequest):
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="页面需求不能为空")
    dsl = await generate_dsl_with_xiaomi(prompt, get_settings())
    return success(dsl, message="DSL 生成成功")
