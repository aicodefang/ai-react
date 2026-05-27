from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class FieldSpec(BaseModel):
    name: str
    label: str
    type: Literal["string", "enum", "phone", "date"]
    required: bool | None = None
    options: list[str] | None = None


class PageDsl(BaseModel):
    pageType: Literal["crud"]
    entity: str
    title: str
    layout: Literal["filter-table-modal"]
    features: list[str]
    fields: list[FieldSpec]
    rules: list[str]


class GeneratedPage(BaseModel):
    id: str
    name: str
    entity: str
    route: str
    status: Literal["draft", "verified"]
    createdAt: str
    dsl: PageDsl


class SavePageRequest(BaseModel):
    dsl: PageDsl


class GenerateDslRequest(BaseModel):
    prompt: str


class ApiSchemaField(BaseModel):
    name: str
    type: Literal["string", "number", "boolean", "date"]
    required: bool | None = None


class ApiDefinition(BaseModel):
    id: str
    name: str
    entity: str
    method: Literal["GET", "POST", "PUT", "DELETE"]
    path: str
    action: Literal["list", "create", "update", "delete"]
    requestSchema: list[ApiSchemaField]
    responseSchema: list[ApiSchemaField]
    mockData: object | list[object] | None = None
    status: Literal["draft", "published"]
    createdAt: str


class SaveApiRequest(BaseModel):
    name: str
    entity: str
    method: Literal["GET", "POST", "PUT", "DELETE"]
    path: str
    action: Literal["list", "create", "update", "delete"]
    requestSchema: list[ApiSchemaField] = []
    responseSchema: list[ApiSchemaField] = []
    mockData: object | list[object] | None = None
    status: Literal["draft", "published"]


class ApiListData(BaseModel):
    list: list[ApiDefinition]
    total: int
    pageNo: int
    pageSize: int


class PageApiBinding(BaseModel):
    pageId: str
    listApiId: str | None = None
    createApiId: str | None = None
    updateApiId: str | None = None
    deleteApiId: str | None = None
    updatedAt: str


class SavePageBindingRequest(BaseModel):
    listApiId: str | None = None
    createApiId: str | None = None
    updateApiId: str | None = None
    deleteApiId: str | None = None


class CustomerRecord(BaseModel):
    id: str
    customerName: str
    level: str
    contactName: str
    phone: str
    region: str
    status: str
    createdAt: str


class SaveCustomerRequest(BaseModel):
    customerName: str
    level: str
    contactName: str
    phone: str
    region: str
    status: str
    createdAt: str | None = None


class CustomerListData(BaseModel):
    list: list[CustomerRecord]
    total: int


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
    city: str
    cooperationStatus: str
    createdAt: str | None = None


class SupplierListData(BaseModel):
    list: list[SupplierRecord]
    total: int


class ApiResponse(BaseModel, Generic[T]):
    code: int
    message: str
    data: T | None = None


class PageListData(BaseModel):
    list: list[GeneratedPage]
    total: int
    pageNo: int
    pageSize: int
