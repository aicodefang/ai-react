from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SharedFieldSpec(BaseModel):
    name: str
    label: str
    type: Literal["string", "enum", "phone", "date"]
    required: bool = False
    options: list[str] | None = None


class ApiContractSpec(BaseModel):
    method: Literal["GET", "POST", "PUT", "DELETE"]
    path: str


class SharedPermissions(BaseModel):
    query: str | None = None
    create: str | None = None
    update: str | None = None
    delete: str | None = None
    export: str | None = None


class SharedApis(BaseModel):
    list: ApiContractSpec
    create: ApiContractSpec
    update: ApiContractSpec
    delete: ApiContractSpec


class SharedContract(BaseModel):
    entity: str
    title: str
    route: str
    pageType: Literal["crud"] = "crud"
    layout: Literal["filter-table-modal"] = "filter-table-modal"
    dataSource: Literal["mock", "api"] = "api"
    fields: list[SharedFieldSpec]
    queryFields: list[str]
    tableColumns: list[str]
    formFields: list[str]
    features: list[str]
    permissions: SharedPermissions
    apis: SharedApis
    rules: list[str] = Field(default_factory=list)
