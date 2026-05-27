from __future__ import annotations

from pydantic import BaseModel


class SupplierRecord(BaseModel):
    id: str
    supplierName: str
    supplierType: str
    contactName: str
    phone: str
    city: str
    cooperationStatus: str
    createdAt: str


class SaveSupplierRequest(BaseModel):
    supplierName: str
    supplierType: str
    contactName: str
    phone: str
    city: str | None = None
    cooperationStatus: str
    createdAt: str | None = None


class SupplierListData(BaseModel):
    list: list[SupplierRecord]
    total: int
