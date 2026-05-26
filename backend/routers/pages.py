from __future__ import annotations

from fastapi import APIRouter, Query

from ..config import get_settings
from ..models import SavePageBindingRequest, SavePageRequest
from ..responses import success
from ..services import supabase


router = APIRouter(prefix="/pages", tags=["pages"])


@router.get("")
async def list_pages(
    page_no: int = Query(1, alias="pageNo", ge=1),
    page_size: int = Query(10, alias="pageSize", ge=1, le=100),
):
    data = await supabase.list_pages(get_settings(), page_no, page_size)
    return success(data)


@router.get("/{page_id}")
async def get_page(page_id: str):
    data = await supabase.get_page(get_settings(), page_id)
    return success(data)


@router.post("")
async def create_page(payload: SavePageRequest):
    data = await supabase.create_page(get_settings(), payload.dsl)
    return success(data, message="页面保存成功")


@router.delete("/{page_id}")
async def delete_page(page_id: str):
    await supabase.delete_page(get_settings(), page_id)
    return success(message="页面删除成功")


@router.get("/{page_id}/bindings")
async def get_page_bindings(page_id: str):
    data = await supabase.get_page_bindings(get_settings(), page_id)
    return success(data)


@router.put("/{page_id}/bindings")
async def upsert_page_bindings(page_id: str, payload: SavePageBindingRequest):
    data = await supabase.upsert_page_bindings(get_settings(), page_id, payload.model_dump())
    return success(data, message="页面接口绑定已保存")
