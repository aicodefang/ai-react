from __future__ import annotations

from fastapi import APIRouter, Query

from ..config import get_settings
from ..models import SaveCustomerRequest
from ..responses import success
from ..services import customers


router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("")
async def list_customers(
    customer_name: str | None = Query(None, alias="customerName"),
    level: str | None = Query(None),
    status: str | None = Query(None),
):
    data = await customers.list_customers(get_settings(), customer_name, level, status)
    return success(data)


@router.post("")
async def create_customer(payload: SaveCustomerRequest):
    customer = await customers.create_customer(get_settings(), payload)
    return success(customer, message="客户创建成功")


@router.put("/{customer_id}")
async def update_customer(customer_id: str, payload: SaveCustomerRequest):
    updated = await customers.update_customer(get_settings(), customer_id, payload)
    return success(updated, message="客户更新成功")


@router.delete("/{customer_id}")
async def delete_customer(customer_id: str):
    await customers.delete_customer(get_settings(), customer_id)
    return success({"id": customer_id}, message="客户删除成功")
