from __future__ import annotations

from fastapi import FastAPI

from .customer import router as customer_router
from .supplier import router as supplier_router
from .warehouse import router as warehouse_router


def register_generated_routers(app: FastAPI) -> None:
    app.include_router(customer_router, prefix="/generated")
    app.include_router(supplier_router, prefix="/generated")
    app.include_router(warehouse_router, prefix="/generated")
