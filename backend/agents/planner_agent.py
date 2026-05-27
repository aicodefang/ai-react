from __future__ import annotations

from fastapi import HTTPException

from ..config import Settings
from ..schemas.shared_contract import SharedContract
from ..services.llm import chat_completion, extract_json_object, extract_message_content


REQUIRED_FEATURES = ["search", "create", "edit", "delete", "export"]


def _normalize_features(value: object) -> list[str]:
    normalized: list[str] = []
    if isinstance(value, list):
        normalized = [str(item).lower() for item in value]
    elif isinstance(value, dict):
        normalized = [str(key).lower() for key, enabled in value.items() if enabled]
    allowed = [feature for feature in normalized if feature in REQUIRED_FEATURES]
    return allowed or REQUIRED_FEATURES.copy()


def _normalize_permissions(value: object) -> dict[str, str | None]:
    defaults = {
        "query": None,
        "create": None,
        "update": None,
        "delete": None,
        "export": None,
    }
    if not isinstance(value, dict):
        return defaults
    normalized: dict[str, str | None] = {}
    for key in defaults:
        item = value.get(key)
        if isinstance(item, str):
            normalized[key] = item
        elif item:
            normalized[key] = f"{key}"
        else:
            normalized[key] = None
    return normalized


def _normalize_field_type(value: object) -> str:
    mapping = {
        "text": "string",
        "input": "string",
        "select": "enum",
        "tel": "phone",
        "datetime": "date",
        "time": "date",
    }
    string_value = str(value or "string").lower()
    return mapping.get(string_value, string_value)


def _normalize_options(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    normalized: list[str] = []
    for item in value:
        if isinstance(item, dict):
            option_value = item.get("value") or item.get("label")
            if option_value is not None:
                normalized.append(str(option_value))
        else:
            normalized.append(str(item))
    return normalized or None


def _normalize_contract_payload(payload: dict) -> dict:
    normalized = dict(payload)
    normalized["features"] = _normalize_features(payload.get("features"))
    normalized["permissions"] = _normalize_permissions(payload.get("permissions"))
    if isinstance(payload.get("rules"), list):
        normalized["rules"] = [str(rule) for rule in payload.get("rules", [])]
    elif payload.get("rules"):
        normalized["rules"] = [str(payload.get("rules"))]
    else:
        normalized["rules"] = []
    fields = []
    for field in payload.get("fields", []):
        if not isinstance(field, dict):
            continue
        fields.append(
            {
                **field,
                "type": _normalize_field_type(field.get("type")),
                "required": bool(field.get("required", False)),
                "options": _normalize_options(field.get("options")),
            }
        )
    normalized["fields"] = fields
    field_by_name = {field["name"]: field for field in fields if field.get("name")}

    if "phone" in field_by_name:
        field_by_name["phone"]["type"] = "phone"
        field_by_name["phone"]["label"] = "手机号"

    if "createdAt" in field_by_name:
        field_by_name["createdAt"]["type"] = "date"
        field_by_name["createdAt"]["label"] = "创建时间"

    if "customerName" in field_by_name:
        field_by_name["customerName"]["label"] = "客户名称"
        field_by_name["customerName"]["required"] = True

    if "contactName" in field_by_name:
        field_by_name["contactName"]["label"] = "联系人"
        field_by_name["contactName"]["required"] = True

    if "level" in field_by_name:
        field_by_name["level"]["type"] = "enum"
        field_by_name["level"]["label"] = "客户等级"
        field_by_name["level"]["options"] = ["A", "B", "C"]
        field_by_name["level"]["required"] = True

    if "region" in field_by_name:
        field_by_name["region"]["type"] = "enum"
        field_by_name["region"]["label"] = "所属区域"
        field_by_name["region"]["options"] = ["华东", "华北", "华南", "西南"]

    if "status" in field_by_name:
        field_by_name["status"]["type"] = "enum"
        field_by_name["status"]["label"] = "客户状态"
        field_by_name["status"]["options"] = ["active", "pending", "disabled"]
        field_by_name["status"]["required"] = True

    normalized["fields"] = list(field_by_name.values())

    if normalized.get("entity") == "customer":
        normalized["queryFields"] = ["customerName", "level", "contactName"]
        normalized["tableColumns"] = [
            "customerName",
            "level",
            "contactName",
            "phone",
            "region",
            "status",
            "createdAt",
        ]
        normalized["formFields"] = [field["name"] for field in normalized["fields"]]
        normalized["permissions"] = {
            "query": "customer:query",
            "create": "customer:create",
            "update": "customer:update",
            "delete": "customer:delete",
            "export": "customer:export",
        }
        normalized["apis"] = {
            "list": {"method": "GET", "path": "/api/customers"},
            "create": {"method": "POST", "path": "/api/customers"},
            "update": {"method": "PUT", "path": "/api/customers/{id}"},
            "delete": {"method": "DELETE", "path": "/api/customers/{id}"},
        }

        existing_rules = [str(rule) for rule in normalized.get("rules", [])]
        normalized["rules"] = existing_rules or [
            "手机号必须符合 11 位手机号格式",
            "客户等级必须限定为 A/B/C",
            "删除操作需要 customer:delete 权限",
        ]
    return normalized


async def generate_shared_contract(prompt: str, settings: Settings) -> SharedContract:
    system_prompt = (
        "你是一个多 Agent 工作流的规划器。"
        "请将用户需求转换为严格合法的 JSON 对象，不要输出解释、不要输出 Markdown。"
        "顶层字段必须只有：entity,title,route,pageType,layout,dataSource,fields,queryFields,tableColumns,formFields,features,permissions,apis,rules。"
        "pageType 固定为 crud，layout 固定为 filter-table-modal，dataSource 固定为 api。"
        "fields 中每项包含 name,label,type,required,options。"
        "permissions 必须是 query/create/update/delete/export 五个 key 的对象。"
        "apis 必须是 list/create/update/delete 四个 key 的对象，每项包含 method,path。"
        "queryFields/tableColumns/formFields 必须是字段 name 数组。"
        "不要更改用户指定的字段 key。"
        "如果出现 phone 字段，type 必须是 phone。"
        "如果出现 createdAt 字段，type 必须是 date。"
        "如果实体是 customer 且出现 level 字段，options 必须是 A/B/C。"
        "features 必须包含 search,create,edit,delete,export。"
        "所有新实体默认使用 Supabase 持久化，不允许规划本地 JSON 文件存储。"
        "如果实体是 customer，permissions 必须输出 customer:query,customer:create,customer:update,customer:delete,customer:export。"
    )
    user_prompt = (
        "请根据下面需求生成前后端共享协议 JSON。\n"
        "当前技术栈：React 19 + Ant Design 6 + TypeScript 6 + Vite 8 + FastAPI + Supabase。\n"
        "当前后端接口前缀是 /api。\n"
        f"用户需求：{prompt}"
    )
    payload = await chat_completion(settings, system_prompt, user_prompt)
    parsed = _normalize_contract_payload(extract_json_object(extract_message_content(payload)))
    try:
        return SharedContract.model_validate(parsed)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"共享协议校验失败: {exc}") from exc
