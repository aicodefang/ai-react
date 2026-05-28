from __future__ import annotations

from pydantic import BaseModel


class WarehouseRecord(BaseModel):
    id: str
    warehouseName: str
    warehouseType: str
    managerName: str
    phone: str
    city: str
    status: str
    createdAt: str


class SaveWarehouseRequest(BaseModel):
    warehouseName: str
    warehouseType: str | None = None
    managerName: str
    phone: str
    city: str | None = None
    status: str
    createdAt: str | None = None


class WarehouseListData(BaseModel):
    list: list[WarehouseRecord]
    total: int
