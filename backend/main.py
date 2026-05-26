from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from .exceptions import http_exception_handler, unhandled_exception_handler, validation_exception_handler
from .routers import apis, customers, dsl, health, pages


def create_app() -> FastAPI:
    app = FastAPI(title="AI Frontend Generator API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health.router)
    app.include_router(dsl.router)
    app.include_router(customers.router)
    app.include_router(apis.router)
    app.include_router(pages.router)
    return app


app = create_app()
