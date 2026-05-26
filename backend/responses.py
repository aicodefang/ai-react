from __future__ import annotations

from .models import ApiResponse, T


def success(data: T | None = None, message: str = "success", code: int = 0) -> ApiResponse[T]:
    return ApiResponse(code=code, message=message, data=data)
