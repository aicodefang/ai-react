from __future__ import annotations

from fastapi import APIRouter, Query

from ...config import get_settings
from ...responses import success
from .schema import SaveSupplierRequest
from .service import create_supplier, delete_supplier, list_suppliers, update_supplier


router = APIRouter(prefix="/suppliers", tags=["generated-supplier"])


@router.get("")
async def list_suppliers_route(
    supplier_name: str | None = Query(None, alias="supplierName"),
    supplier_type: str | None = Query(None, alias="supplierType"),
    contact_name: str | None = Query(None, alias="contactName"),
):
    data = await list_suppliers(get_settings(), supplier_name, supplier_type, contact_name)
    return success(data)


@router.post("")
async def create_supplier_route(payload: SaveSupplierRequest):
    data = await create_supplier(get_settings(), payload)
    return success(data, message="供应商管理创建成功")


@router.put("/{supplier_id}")
async def update_supplier_route(supplier_id: str, payload: SaveSupplierRequest):
    data = await update_supplier(get_settings(), supplier_id, payload)
    return success(data, message="供应商管理更新成功")


@router.delete("/{supplier_id}")
async def delete_supplier_route(supplier_id: str):
    await delete_supplier(get_settings(), supplier_id)
    return success({"id": supplier_id}, message="供应商管理删除成功")
