from __future__ import annotations

import json
import re
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from ..config import Settings
from ..models import PageDsl


def ensure_xiaomi_env(settings: Settings) -> None:
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


def extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", cleaned, re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start : end + 1]

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"模型返回的 DSL 不是合法 JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="模型返回的 DSL 顶层结构必须是 JSON 对象")

    return payload


def flatten_rule_items(value: object, prefix: str = "") -> list[str]:
    if isinstance(value, dict):
        items: list[str] = []
        for key, nested in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            items.extend(flatten_rule_items(nested, next_prefix))
        return items
    if isinstance(value, list):
        items: list[str] = []
        for index, nested in enumerate(value, start=1):
            next_prefix = f"{prefix}[{index}]" if prefix else f"[{index}]"
            items.extend(flatten_rule_items(nested, next_prefix))
        return items
    if prefix:
        return [f"{prefix}: {value}"]
    return [str(value)]


def normalize_dsl_payload(payload: dict) -> dict:
    normalized = dict(payload)
    rules = normalized.get("rules")
    if isinstance(rules, dict):
        normalized["rules"] = flatten_rule_items(rules)
    elif isinstance(rules, list):
        normalized["rules"] = [str(item) for item in rules]
    elif rules is not None:
        normalized["rules"] = [str(rules)]

    fields = normalized.get("fields")
    if isinstance(fields, list):
        normalized["fields"] = [
            {**field, "required": field.get("required", False)}
            for field in fields
            if isinstance(field, dict)
        ]

    return normalized


async def generate_dsl_with_xiaomi(prompt: str, settings: Settings) -> PageDsl:
    ensure_xiaomi_env(settings)
    system_prompt = (
        "你是一个企业管理系统前端 DSL 生成器。"
        "请基于用户需求，输出一个严格合法的 JSON 对象，不要输出解释、不要输出 Markdown。"
        "JSON 必须满足以下规则："
        '1. 仅输出字段 pageType, entity, title, layout, features, fields, rules。'
        '2. pageType 固定为 "crud"，layout 固定为 "filter-table-modal"。'
        '3. fields 中每项必须包含 name, label, type，可选 required, options。'
        '4. type 只能是 string、enum、phone、date。'
        '5. features 只允许 search、create、edit、delete、export。'
        '6. rules 必须是字符串数组，每一项是一条业务校验、权限或交互约束。'
        "7. 输出内容必须能被 JSON.parse 直接解析。"
        "8. 当前 POC 面向后台管理系统页面生成。"
        "9. 不要把 rules 生成为对象。"
    )
    user_prompt = (
        "请根据下面的页面需求生成 DSL。\n"
        "当前业务规范参考：\n"
        "- 权限: customer:query, customer:create, customer:update, customer:delete, customer:export\n"
        "- API: GET /api/customers, POST /api/customers, PUT /api/customers/:id, DELETE /api/customers/:id\n"
        "- 适合输出管理系统的查询 + 表格 + 弹窗编辑模式\n\n"
        f"页面需求：{prompt}"
    )
    request_payload = {
        "model": settings.xiaomi_model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{settings.xiaomi_api_base}/chat/completions",
            headers=build_model_headers(settings),
            json=request_payload,
        )
        response.raise_for_status()
        payload = response.json()

    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="模型响应结构异常，无法提取 DSL") from exc

    parsed = normalize_dsl_payload(extract_json_object(content))
    try:
        return PageDsl.model_validate(parsed)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"模型返回的 DSL 校验失败: {exc}") from exc
