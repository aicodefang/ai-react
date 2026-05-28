from __future__ import annotations

from fastapi import APIRouter, Query

from ...config import get_settings
from ...responses import success
from .schema import SaveWarehouseRequest
from .service import create_warehouse, delete_warehouse, list_warehouses, update_warehouse


router = APIRouter(prefix="/warehouses", tags=["generated-warehouse"])


@router.get("")
async def list_warehouses_route(
    warehouse_name: str | None = Query(None, alias="warehouseName"),
    warehouse_type: str | None = Query(None, alias="warehouseType"),
):
    data = await list_warehouses(get_settings(), warehouse_name, warehouse_type)
    return success(data)


@router.post("")
async def create_warehouse_route(payload: SaveWarehouseRequest):
    data = await create_warehouse(get_settings(), payload)
    return success(data, message="仓库管理创建成功")


@router.put("/{warehouse_id}")
async def update_warehouse_route(warehouse_id: str, payload: SaveWarehouseRequest):
    data = await update_warehouse(get_settings(), warehouse_id, payload)
    return success(data, message="仓库管理更新成功")


@router.delete("/{warehouse_id}")
async def delete_warehouse_route(warehouse_id: str):
    await delete_warehouse(get_settings(), warehouse_id)
    return success({"id": warehouse_id}, message="仓库管理删除成功")
