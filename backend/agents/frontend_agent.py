from __future__ import annotations

from .base import AgentContext, AgentExecutionResult


def to_pascal_case(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in value.replace("-", "_").split("_") if part)


def render_frontend_page(context: AgentContext) -> AgentExecutionResult:
    contract = context.shared_contract
    entity = contract.entity
    entity_plural = f"{entity}s"
    entity_pascal = to_pascal_case(entity)
    component_name = f"{entity_pascal}GeneratedPage"
    row_type_name = f"{entity_pascal}Row"
    form_type_name = f"{entity_pascal}FormValues"
    route_const_name = f"generated{entity_pascal}GeneratedPageRoute"
    title = contract.title

    row_fields = "\n".join([f"  {field.name}: string" for field in contract.fields])

    option_blocks: list[str] = []
    option_names: dict[str, str] = {}
    for field in contract.fields:
        if field.type == "enum":
            option_name = f"{field.name[:1].upper()}{field.name[1:]}Options"
            option_names[field.name] = option_name
            values = field.options or []
            option_values = ", ".join([f"'{value}'" for value in values])
            option_blocks.append(f"const {option_name} = [{option_values}].map((value) => ({{ value, label: value }}))")

    state_blocks: list[str] = []
    param_blocks: list[str] = []
    load_arg_fields: list[str] = []
    reset_blocks: list[str] = []
    search_inputs: list[str] = []

    for field_name in contract.queryFields:
        field = next((item for item in contract.fields if item.name == field_name), None)
        if not field:
            continue
        state_name = f"{field_name}Filter"
        setter_name = f"set{field_name[:1].upper()}{field_name[1:]}Filter"
        if field.type == "enum":
            state_blocks.append(f"  const [{state_name}, {setter_name}] = useState<string | undefined>(undefined)")
            reset_blocks.append(f"    {setter_name}(undefined)")
            search_inputs.append(
                f"""            <Select allowClear placeholder="{field.label}" value={{{state_name}}} options={{{option_names[field.name]}}} onChange={{(value) => {setter_name}(value)}} />"""
            )
        else:
            state_blocks.append(f"  const [{state_name}, {setter_name}] = useState('')")
            reset_blocks.append(f"    {setter_name}('')")
            search_inputs.append(
                f"""            <Input placeholder="{field.label}" value={{{state_name}}} onChange={{(event) => {setter_name}(event.target.value)}} />"""
            )
        param_blocks.append(f"      if (params?.{field_name}) search.set('{field_name}', params.{field_name})")
        load_arg_fields.append(f"{field_name}: {state_name}")

    params_type = " | ".join(["string", "undefined"])
    load_params_type = "; ".join([f"{field}: {params_type}" for field in contract.queryFields]) or "never: string"

    table_columns: list[str] = []
    for field_name in contract.tableColumns:
        field = next((item for item in contract.fields if item.name == field_name), None)
        if not field:
            continue
        if field.type == "enum":
            table_columns.append(
                f"""    {{ title: '{field.label}', dataIndex: '{field.name}', key: '{field.name}', render: (value: string) => <Tag color="blue">{{value}}</Tag> }},"""
            )
        else:
            table_columns.append(f"    {{ title: '{field.label}', dataIndex: '{field.name}', key: '{field.name}' }},")

    edit_form_lines = [f"                {field.name}: record.{field.name}," for field in contract.fields]

    default_form_lines = []
    for field in contract.fields:
        if field.type == "enum" and field.options:
            default_value = f"'{field.options[0]}'"
        elif field.name == "createdAt":
            default_value = "new Date().toISOString().slice(0, 10)"
        else:
            default_value = "''"
        default_form_lines.append(f"                  {field.name}: {default_value},")

    form_items: list[str] = []
    for field in contract.fields:
        rule_items: list[str] = []
        if field.required:
            rule_items.append(f"{{ required: true, message: '请输入{field.label}' }}")
        if field.type == "phone":
            rule_items.append("{ pattern: /^1[3-9]\\d{9}$/, message: '请输入有效的 11 位手机号' }")
        rules_text = "[" + ", ".join(rule_items) + "]"

        if field.type == "enum":
            form_items.append(
                f"""          <Form.Item label="{field.label}" name="{field.name}" rules={{{rules_text}}}>
            <Select options={{{option_names[field.name]}}} />
          </Form.Item>"""
            )
        else:
            form_items.append(
                f"""          <Form.Item label="{field.label}" name="{field.name}" rules={{{rules_text}}}>
            <Input placeholder="请输入{field.label}" />
          </Form.Item>"""
            )

    header_values = ", ".join([f"'{field}'" for field in contract.tableColumns])

    content = f"""import {{ DeleteOutlined, DownloadOutlined, EditOutlined, PlusOutlined, ReloadOutlined, SearchOutlined }} from '@ant-design/icons'
import {{ Button, Card, Empty, Form, Input, Modal, Popconfirm, Select, Space, Spin, Table, Tag, Typography, message }} from 'antd'
import {{ useEffect, useState }} from 'react'

type {row_type_name} = {{
  id: string
{row_fields}
}}

type {form_type_name} = Omit<{row_type_name}, 'id'>

{chr(10).join(option_blocks)}

export function {component_name}() {{
  const [rows, setRows] = useState<{row_type_name}[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
{chr(10).join(state_blocks)}
  const [modalOpen, setModalOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [editing, setEditing] = useState<{row_type_name} | null>(null)
  const [messageApi, contextHolder] = message.useMessage()
  const [form] = Form.useForm<{form_type_name}>()

  const loadRows = async (params?: {{ {load_params_type} }}) => {{
    setLoading(true)
    setError('')
    try {{
      const search = new URLSearchParams()
{chr(10).join(param_blocks)}
      const response = await fetch(`/api/generated/{entity_plural}${{search.toString() ? `?${{search.toString()}}` : ''}}`)
      const payload = await response.json()
      if (!response.ok || payload.code !== 0) {{
        throw new Error(payload.message || '加载数据失败')
      }}
      setRows(payload.data?.list ?? [])
    }} catch (requestError) {{
      setError(requestError instanceof Error ? requestError.message : '加载数据失败')
      setRows([])
    }} finally {{
      setLoading(false)
    }}
  }}

  useEffect(() => {{
    void loadRows()
  }}, [])

  const columns = [
{chr(10).join(table_columns)}
    {{
      title: '操作',
      key: 'action',
      render: (_: unknown, record: {row_type_name}) => (
        <Space>
          <Button
            aria-label={{`编辑${{record.id}}`}}
            icon={{<EditOutlined />}}
            size="small"
            onClick={{() => {{
              setEditing(record)
              form.setFieldsValue({{
{chr(10).join(edit_form_lines)}
              }})
              setModalOpen(true)
            }}}}
          />
          <Popconfirm
            title="确认删除当前记录？"
            okText="删除"
            cancelText="取消"
            onConfirm={{async () => {{
              try {{
                const response = await fetch(`/api/generated/{entity_plural}/${{record.id}}`, {{ method: 'DELETE' }})
                const payload = await response.json()
                if (!response.ok || payload.code !== 0) {{
                  throw new Error(payload.message || '删除失败')
                }}
                messageApi.success('删除成功')
                await loadRows({{ {", ".join(load_arg_fields)} }})
              }} catch (requestError) {{
                messageApi.error(requestError instanceof Error ? requestError.message : '删除失败')
              }}
            }}}}
          >
            <Button danger aria-label={{`删除${{record.id}}`}} icon={{<DeleteOutlined />}} size="small" />
          </Popconfirm>
        </Space>
      ),
    }},
  ]

  const handleSearch = async () => {{
    await loadRows({{
      {", ".join(load_arg_fields)}
    }})
  }}

  const handleReset = async () => {{
{chr(10).join(reset_blocks)}
    await loadRows()
  }}

  const handleSubmit = async (values: {form_type_name}) => {{
    setSubmitting(true)
    try {{
      const targetUrl = editing ? `/api/generated/{entity_plural}/${{editing.id}}` : '/api/generated/{entity_plural}'
      const response = await fetch(targetUrl, {{
        body: JSON.stringify(values),
        headers: {{ 'Content-Type': 'application/json' }},
        method: editing ? 'PUT' : 'POST',
      }})
      const payload = await response.json()
      if (!response.ok || payload.code !== 0) {{
        throw new Error(payload.message || '保存失败')
      }}
      messageApi.success(editing ? '更新成功' : '创建成功')
      setModalOpen(false)
      setEditing(null)
      form.resetFields()
      await loadRows({{ {", ".join(load_arg_fields)} }})
    }} catch (requestError) {{
      messageApi.error(requestError instanceof Error ? requestError.message : '保存失败')
    }} finally {{
      setSubmitting(false)
    }}
  }}

  const handleExport = () => {{
    if (!rows.length) {{
      messageApi.warning('当前没有可导出的数据')
      return
    }}
    const header = [{header_values}]
    const csvRows = [
      header.join(','),
      ...rows.map((row) =>
        header
          .map((key) => {{
            const value = String(row[key as keyof {row_type_name}] ?? '')
            return `"${{value.replace(/"/g, '""')}}"`
          }})
          .join(','),
      ),
    ]
    const blob = new Blob(['\\ufeff' + csvRows.join('\\n')], {{ type: 'text/csv;charset=utf-8;' }})
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = '{entity_plural}-export.csv'
    link.click()
    URL.revokeObjectURL(url)
  }}

  return (
    <div className="generated-runtime-page">
      {{contextHolder}}
      <Card className="generated-runtime-panel" title="{title}">
        <Space direction="vertical" size={{12}} style={{{{ width: '100%' }}}}>
          <Typography.Text>实体：{entity}</Typography.Text>
          <div className="generated-runtime-search">
            <div className="generated-runtime-search-grid">
{chr(10).join(search_inputs)}
            </div>
            <div className="generated-runtime-action-group">
              <Button icon={{<SearchOutlined />}} type="primary" onClick={{() => void handleSearch()}}>
                查询
              </Button>
              <Button icon={{<ReloadOutlined />}} onClick={{() => void handleReset()}}>
                重置
              </Button>
            </div>
            <div className="generated-runtime-operation-group">
              <Button
                icon={{<PlusOutlined />}}
                type="primary"
                onClick={{() => {{
                  setEditing(null)
                  form.resetFields()
                  form.setFieldsValue({{
{chr(10).join(default_form_lines)}
                  }})
                  setModalOpen(true)
                }}}}
              >
                新增数据
              </Button>
              <Button icon={{<DownloadOutlined />}} onClick={{handleExport}}>
                导出结果
              </Button>
            </div>
          </div>
          {{loading ? (
            <div className="generated-runtime-loading">
              <Spin />
            </div>
          ) : error ? (
            <Empty description={{error}} />
          ) : (
            <Table<{row_type_name}>
              columns={{columns}}
              dataSource={{rows}}
              pagination={{{{ pageSize: 8 }}}}
              rowKey="id"
              scroll={{{{ x: 'max-content' }}}}
            />
          )}}
        </Space>
      </Card>

      <Modal
        title={{editing ? `编辑{title}` : `新增{title}`}}
        open={{modalOpen}}
        confirmLoading={{submitting}}
        okText="保存"
        cancelText="取消"
        onCancel={{() => {{
          setModalOpen(false)
          setEditing(null)
        }}}}
        onOk={{() => void form.submit()}}
      >
        <Form form={{form}} layout="vertical" onFinish={{(values) => void handleSubmit(values)}}>
{chr(10).join(form_items)}
        </Form>
      </Modal>
    </div>
  )
}}
"""

    route_content = f"""export const {route_const_name} = {{
  path: "{contract.route}",
  title: "{title}",
}}
"""

    index_content = f"""export {{ {component_name} }} from './{entity}GeneratedPage'
export {{ {route_const_name} }} from './{entity}Route'
"""

    return AgentExecutionResult(
        agent_name="frontend",
        status="succeeded",
        summary=f"已生成可运行的前端 CRUD 页面模板：{title}",
        output={
            "componentName": component_name,
            "route": contract.route,
            "runtimeApiBase": f"/api/generated/{entity_plural}",
        },
        artifacts=[
            {
                "artifactType": "frontend-page",
                "targetPath": f"frontend/src/generated/{entity}/{entity}GeneratedPage.tsx",
                "content": content,
            },
            {
                "artifactType": "frontend-route",
                "targetPath": f"frontend/src/generated/{entity}/{entity}Route.ts",
                "content": route_content,
            },
            {
                "artifactType": "frontend-index",
                "targetPath": f"frontend/src/generated/{entity}/index.ts",
                "content": index_content,
            },
        ],
    )
