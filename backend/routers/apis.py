from __future__ import annotations

from fastapi import APIRouter, Query

from ..config import get_settings
from ..models import SaveApiRequest
from ..responses import success
from ..services import supabase


router = APIRouter(prefix="/apis", tags=["apis"])


@router.get("")
async def list_apis(
    page_no: int = Query(1, alias="pageNo", ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
):
    data = await supabase.list_apis(get_settings(), page_no, page_size)
    return success(data)


@router.post("")
async def create_api(payload: SaveApiRequest):
    data = await supabase.create_api(get_settings(), payload)
    return success(data, message="接口保存成功")


@router.put("/{api_id}")
async def update_api(api_id: str, payload: SaveApiRequest):
    data = await supabase.update_api(get_settings(), api_id, payload)
    return success(data, message="接口更新成功")


@router.delete("/{api_id}")
async def delete_api(api_id: str):
    await supabase.delete_api(get_settings(), api_id)
    return success(message="接口删除成功")
