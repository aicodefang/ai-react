from __future__ import annotations

import json
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from ..config import Settings


def ensure_model_env(settings: Settings) -> None:
    if not settings.xiaomi_api_base or not settings.xiaomi_api_key or not settings.xiaomi_model:
        raise HTTPException(status_code=500, detail="模型环境变量未配置")


def build_model_headers(settings: Settings) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    host = urlparse(settings.xiaomi_api_base).netloc.lower()
    if "deepseek.com" in host:
        headers["Authorization"] = f"Bearer {settings.xiaomi_api_key}"
        return headers
    headers["api-key"] = settings.xiaomi_api_key
    return headers


async def chat_completion(settings: Settings, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> dict:
    ensure_model_env(settings)
    request_payload = {
        "model": settings.xiaomi_model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
        response = await client.post(
            f"{settings.xiaomi_api_base}/chat/completions",
            headers=build_model_headers(settings),
            json=request_payload,
        )
        response.raise_for_status()
        return response.json()


def extract_message_content(payload: dict) -> str:
    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="模型响应结构异常，无法提取内容") from exc


def extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if "\n" in cleaned:
            cleaned = cleaned.split("\n", 1)[1]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"模型返回的 JSON 非法: {exc}") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="模型返回内容必须是 JSON 对象")
    return payload
