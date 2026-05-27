from __future__ import annotations

from .base import AgentContext, AgentExecutionResult


def run_qa(context: AgentContext, frontend_output: dict, service_output: dict) -> AgentExecutionResult:
    contract = context.shared_contract
    warnings: list[str] = []
    field_names = [field.name for field in contract.fields]
    field_map = {field.name: field for field in contract.fields}
    for field_name in contract.queryFields + contract.tableColumns + contract.formFields:
        if field_name not in field_names:
            warnings.append(f"字段 {field_name} 未在 fields 中声明")
    if contract.apis.list.path == contract.apis.create.path and contract.apis.list.method == contract.apis.create.method:
        warnings.append("列表与新建接口路径/方法重复，请确认是否符合预期")

    required_features = {"search", "create", "edit", "delete", "export"}
    missing_features = sorted(required_features - set(contract.features))
    if missing_features:
        warnings.append(f"features 缺失: {', '.join(missing_features)}")

    if "phone" in field_map and field_map["phone"].type != "phone":
        warnings.append("字段 phone 的 type 必须为 phone")
    if "createdAt" in field_map and field_map["createdAt"].type != "date":
        warnings.append("字段 createdAt 的 type 必须为 date")
    if "level" in field_map and (field_map["level"].options or []) != ["A", "B", "C"]:
        warnings.append("字段 level 的 options 必须为 A/B/C")
    if "region" in field_map and (field_map["region"].options or []) != ["华东", "华北", "华南", "西南"]:
        warnings.append("字段 region 的 options 必须为 华东/华北/华南/西南")
    if "status" in field_map and (field_map["status"].options or []) != ["active", "pending", "disabled"]:
        warnings.append("字段 status 的 options 必须为 active/pending/disabled")
    if contract.entity == "customer" and contract.permissions.delete != "customer:delete":
        warnings.append("删除权限必须为 customer:delete")

    if service_output.get("storage") != "supabase":
        warnings.append("新实体后端必须使用 Supabase 持久化")
    if not service_output.get("sqlPath"):
        warnings.append("必须输出可执行的 SQL 产物路径")
    if not service_output.get("runtimeApiBase"):
        warnings.append("必须输出生成运行时接口路径")

    status = "succeeded" if not warnings else "failed"
    return AgentExecutionResult(
        agent_name="qa",
        status=status,
        summary="静态契约校验完成" if not warnings else "静态契约校验发现问题",
        output={
            "frontend": frontend_output,
            "service": service_output,
            "checkedFields": field_names,
        },
        warnings=warnings,
        errors=[] if not warnings else warnings,
    )
