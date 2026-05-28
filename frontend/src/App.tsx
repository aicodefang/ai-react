import {
  ApiOutlined,
  AppstoreOutlined,
  CheckCircleFilled,
  DeleteOutlined,
  LinkOutlined,
  DownloadOutlined,
  EditOutlined,
  ExperimentOutlined,
  EyeOutlined,
  FileTextOutlined,
  PlusOutlined,
  ReloadOutlined,
  TableOutlined,
} from '@ant-design/icons'
import {
  App as AntApp,
  Button,
  Card,
  ConfigProvider,
  Divider,
  Empty,
  Flex,
  Form,
  Input,
  List,
  Skeleton,
  Modal,
  Popconfirm,
  Radio,
  Select,
  Space,
  Statistic,
  Steps,
  Table,
  Tag,
  Typography,
  message,
  theme,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useMemo, useRef, useState } from 'react'
import { BrowserRouter, useLocation, useNavigate, useParams } from 'react-router-dom'
import { buildRuntimePath, continueWorkflowRun, createApi, createPage, createWorkflowRun, deletePage, getPage, getPageBindings, getWorkflowRun, invokeRuntimeApi, listApis, listWorkflowRuns, removeApi, savePageBindings, updateApi } from './api'
import { AppFrame } from './components/AppFrame'
import { apiActionOptions, apiMethodOptions, apiStatusOptions, businessSpec, initialPrompt } from './constants'
import { usePagesStore } from './hooks/usePagesStore'
import { getApiFormInitialValues, parseApiSchema, parseMockData } from './lib/apiForms'
import { downloadFile } from './lib/download'
import { generateCode } from './lib/exportCode'
import { createPreviewRows, extractListRows, getFieldPlaceholder, normalizePreviewRecord, renderFieldValue, resolveMockRowsFromApi } from './lib/preview'
import { AppRoutes } from './routes/AppRoutes'
import type { ApiFormValues, DataSourceMode, NewPageRouteState, PageProps, SharedAppProps } from './types'
import './App.css'
import type { ApiAction, ApiDefinition, GeneratedPage, PageApiBinding, PreviewRecord, SaveApiRequest, WorkflowArtifact, WorkflowRun, WorkflowStep, FieldSpec } from './api'

function GeneratorPage({ isPageListLoading, pages }: SharedAppProps) {
  const [prompt, setPrompt] = useState(initialPrompt)
  const [currentRun, setCurrentRun] = useState<WorkflowRun | null>(null)
  const [recentRuns, setRecentRuns] = useState<Record<string, unknown>[]>([])
  const [isGeneratingWorkflow, setIsGeneratingWorkflow] = useState(false)
  const [isContinuingWorkflow, setIsContinuingWorkflow] = useState(false)
  const [isLoadingRuns, setIsLoadingRuns] = useState(false)
  const [messageApi, contextHolder] = message.useMessage()
  const pollingTimerRef = useRef<number | null>(null)

  const refreshRuns = async () => {
    setIsLoadingRuns(true)
    try {
      const runs = await listWorkflowRuns()
      setRecentRuns(runs)
    } catch {
      setRecentRuns([])
    } finally {
      setIsLoadingRuns(false)
    }
  }

  useEffect(() => {
    void refreshRuns()
  }, [])

  useEffect(() => {
    if (pollingTimerRef.current) {
      window.clearTimeout(pollingTimerRef.current)
      pollingTimerRef.current = null
    }

    if (!currentRun || !['pending', 'running'].includes(currentRun.status)) {
      return
    }

    pollingTimerRef.current = window.setTimeout(() => {
      void (async () => {
        try {
          const detail = await getWorkflowRun(currentRun.id)
          setCurrentRun(detail)
          if (detail.status !== currentRun.status) {
            void refreshRuns()
          }
        } catch {
          // ignore polling errors and retry on next cycle
        }
      })()
    }, 1500)

    return () => {
      if (pollingTimerRef.current) {
        window.clearTimeout(pollingTimerRef.current)
        pollingTimerRef.current = null
      }
    }
  }, [currentRun, currentRun?.id, currentRun?.status])

  const getRunTagColor = (status?: WorkflowRun['status']) => {
    if (status === 'succeeded') return 'green'
    if (status === 'failed') return 'red'
    if (status === 'waiting_for_sql') return 'gold'
    if (status === 'running') return 'blue'
    return 'default'
  }

  const getStepTagColor = (status: WorkflowStep['status']) => {
    if (status === 'succeeded') return 'green'
    if (status === 'failed') return 'red'
    if (status === 'waiting_for_sql') return 'gold'
    if (status === 'running') return 'blue'
    return 'default'
  }

  const getStepsCurrent = () => {
    if (!currentRun) return 0
    if (currentRun.status === 'pending') return 0
    if (currentRun.status === 'running') {
      const runningIndex = currentRun.steps.findIndex((step) => step.status === 'running')
      return runningIndex >= 0 ? runningIndex : Math.max(currentRun.steps.length - 1, 0)
    }
    if (currentRun.status === 'waiting_for_sql') return 2
    return 3
  }

  const handleGenerateWorkflow = async () => {
    if (!prompt.trim()) {
      messageApi.warning('请先输入页面需求')
      return
    }

    setIsGeneratingWorkflow(true)
    try {
      const result = await createWorkflowRun(prompt)
      setCurrentRun(result)
      await refreshRuns()
      messageApi.success('多 Agent 工作流已启动')
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '工作流执行失败，请稍后重试'
      messageApi.error(errorMessage)
    } finally {
      setIsGeneratingWorkflow(false)
    }
  }

  const handleOpenRun = async (runId: string) => {
    try {
      const detail = await getWorkflowRun(runId)
      setCurrentRun(detail)
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : '加载工作流详情失败')
    }
  }

  const handleContinueWorkflow = async () => {
    if (!currentRun) return
    setIsContinuingWorkflow(true)
    try {
      const run = await continueWorkflowRun(currentRun.id)
      setCurrentRun(run)
      await refreshRuns()
      messageApi.success('工作流已继续执行，正在进入 QA 校验阶段')
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : '继续执行失败')
    } finally {
      setIsContinuingWorkflow(false)
    }
  }

  const sqlArtifacts = currentRun?.artifacts.filter((artifact: WorkflowArtifact) => artifact.artifactType === 'sql') ?? []
  const runtimeEntity = currentRun?.sharedContract?.entity
  const runtimePageUrl = runtimeEntity ? `/generated/${runtimeEntity}` : ''
  const runtimeApiPath = runtimeEntity ? `/api/generated/${runtimeEntity}s` : ''
  const hasQaStep = currentRun?.steps.some((step) => step.agentName === 'qa') ?? false
  const canContinueAfterSql = Boolean(currentRun && sqlArtifacts.length > 0 && !hasQaStep && (currentRun.status === 'waiting_for_sql' || currentRun.status === 'running'))

  return (
    <AppFrame>
      {contextHolder}
      <section className="page-section">
        <div className="page-title">
          <Space align="center">
            <FileTextOutlined />
            <Typography.Title level={2}>多 Agent 工作台</Typography.Title>
          </Space>
          <Typography.Text type="secondary">输入自然语言需求，由 Planner、Frontend、Service、QA 四个 Agent 串行/并行完成协议生成、代码草稿和契约校验。</Typography.Text>
        </div>

        <Card className="flow-card">
          <Steps
            current={getStepsCurrent()}
            items={[
              { title: 'Planner', description: '自然语言转共享协议' },
              { title: 'Frontend', description: '生成页面与路由草稿' },
              { title: 'Service', description: '生成接口与 SQL 草稿，等待建表' },
              { title: 'QA', description: '校验字段与契约一致性' },
            ]}
          />
        </Card>

        <div className="dashboard-grid">
          <Card
            className="panel prompt-panel"
            title={
              <Space>
                <FileTextOutlined />
                <span>工作流需求</span>
              </Space>
            }
            extra={<Tag color={currentRun ? getRunTagColor(currentRun.status) : 'blue'}>{currentRun ? currentRun.status : '待执行'}</Tag>}
          >
            <Input.TextArea value={prompt} onChange={(event) => setPrompt(event.target.value)} rows={10} />
            <Button block icon={<ExperimentOutlined />} loading={isGeneratingWorkflow} type="primary" onClick={handleGenerateWorkflow}>
              启动多 Agent 工作流
            </Button>
            <Divider />
            <Typography.Text strong>当前命中的业务规范</Typography.Text>
            <div className="spec-list">
              {businessSpec.permissions.map((item) => (
                <Tag key={item}>{item}</Tag>
              ))}
            </div>
            <div className="api-list">
              {businessSpec.api.map((item) => (
                <Typography.Text code key={item}>
                  {item}
                </Typography.Text>
              ))}
            </div>
          </Card>

          <div className="metric-stack">
            <Card className="metric-card">
              <Statistic loading={isPageListLoading} prefix={<AppstoreOutlined />} title="已生成页面" value={pages.length} />
            </Card>
            <Card className="metric-card">
              <Statistic
                prefix={<CheckCircleFilled />}
                title="最近工作流"
                value={recentRuns.length}
              />
            </Card>
            <Card className="metric-card">
              <Typography.Text strong>生成落点</Typography.Text>
              <Typography.Paragraph type="secondary">首版会将前后端代码草稿直接写入 generated 目录，并把 workflow 执行记录写入 Supabase。</Typography.Paragraph>
            </Card>
          </div>
        </div>

        <div className="dashboard-grid workflow-grid">
          <Card className="panel" title="最近运行">
            <List
              loading={isLoadingRuns}
              dataSource={recentRuns}
              locale={{ emptyText: '暂无工作流记录' }}
              renderItem={(item) => {
                const run = item as { id: string; prompt: string; status: string; created_at: string }
                return (
                  <List.Item
                    actions={[
                      <Button key="view" size="small" type="link" onClick={() => void handleOpenRun(run.id)}>
                        查看
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta description={run.created_at} title={run.prompt.slice(0, 28)} />
                    <Tag color={getRunTagColor(run.status as WorkflowRun['status'])}>{run.status}</Tag>
                  </List.Item>
                )
              }}
            />
          </Card>

          <Card className="panel workflow-output-panel" title="工作流详情">
            {currentRun ? (
              <div className="workflow-detail">
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  <div className="workflow-meta-row">
                    <Tag color={getRunTagColor(currentRun.status)}>{currentRun.status}</Tag>
                    <Typography.Text type="secondary">{currentRun.id}</Typography.Text>
                  </div>

                  <div>
                    <Typography.Text strong>共享协议</Typography.Text>
                    <pre className="dsl-view">{JSON.stringify(currentRun.sharedContract, null, 2)}</pre>
                  </div>

                  <div>
                    <Typography.Text strong>Agent 步骤</Typography.Text>
                    <div className="workflow-step-list">
                      {currentRun.steps.map((step: WorkflowStep) => (
                        <Card key={step.id} size="small">
                          <Flex justify="space-between">
                            <Space>
                              <Typography.Text strong>{step.agentName}</Typography.Text>
                              <Tag color={getStepTagColor(step.status)}>{step.status}</Tag>
                            </Space>
                            <Typography.Text type="secondary">{step.finishedAt ?? step.startedAt}</Typography.Text>
                          </Flex>
                          <Typography.Paragraph>{step.summary}</Typography.Paragraph>
                          {step.warnings.length > 0 && (
                            <Space wrap>
                              {step.warnings.map((warning) => (
                                <Tag color="orange" key={warning}>
                                  {warning}
                                </Tag>
                              ))}
                            </Space>
                          )}
                        </Card>
                      ))}
                    </div>
                  </div>

                  <div>
                    <Typography.Text strong>生成产物</Typography.Text>
                    {sqlArtifacts.length > 0 && (
                      <Card className="workflow-sql-card" size="small">
                        <Space direction="vertical" size={10} style={{ width: '100%' }}>
                          <div className="workflow-meta-row">
                            <Tag color="gold">先执行 SQL</Tag>
                            <Typography.Text strong>生成完成后，先去 Supabase 建表</Typography.Text>
                          </div>
                          <Typography.Paragraph type="secondary">
                            这一步完成后，生成页面就能直接串通查询、新增、编辑、删除整条操作链路。
                          </Typography.Paragraph>
                          <div className="workflow-next-steps">
                            <div className="workflow-next-step">
                              <Typography.Text strong>1. 在 Supabase SQL Editor 执行下面的建表 SQL</Typography.Text>
                            </div>
                            <div className="workflow-next-step">
                              <Typography.Text strong>2. 建表成功后，点击“我已建表，继续执行”</Typography.Text>
                            </div>
                            <div className="workflow-next-step">
                              <Typography.Text strong>3. QA 完成后，再打开生成运行页验证 CRUD 链路</Typography.Text>
                              {runtimePageUrl && <Typography.Text code>{runtimePageUrl}</Typography.Text>}
                              {runtimeApiPath && <Typography.Text code>{runtimeApiPath}</Typography.Text>}
                            </div>
                          </div>
                          {canContinueAfterSql && (
                            <Button icon={<ReloadOutlined />} loading={isContinuingWorkflow} type="primary" onClick={handleContinueWorkflow}>
                              我已建表，继续执行
                            </Button>
                          )}
                          {sqlArtifacts.map((artifact: WorkflowArtifact) => (
                            <Card key={`${artifact.id}-sql`} size="small">
                              <Space direction="vertical" size={6} style={{ width: '100%' }}>
                                <Space>
                                  <Tag>{artifact.agentName}</Tag>
                                  <Tag color="blue">{artifact.artifactType}</Tag>
                                </Space>
                                <Typography.Text code>{artifact.targetPath}</Typography.Text>
                                <pre className="dsl-view artifact-preview">{artifact.contentPreview}</pre>
                              </Space>
                            </Card>
                          ))}
                        </Space>
                      </Card>
                    )}
                    <div className="workflow-artifact-list">
                      {currentRun.artifacts
                        .filter((artifact: WorkflowArtifact) => artifact.artifactType !== 'sql')
                        .map((artifact: WorkflowArtifact) => (
                        <Card key={artifact.id} size="small">
                          <Space direction="vertical" size={6} style={{ width: '100%' }}>
                            <Space>
                              <Tag>{artifact.agentName}</Tag>
                              <Tag color="blue">{artifact.artifactType}</Tag>
                            </Space>
                            <Typography.Text code>{artifact.targetPath}</Typography.Text>
                            <pre className="dsl-view artifact-preview">{artifact.contentPreview}</pre>
                          </Space>
                        </Card>
                      ))}
                    </div>
                  </div>
                </Space>
              </div>
            ) : (
              <Empty description="执行工作流后，可在这里查看协议、步骤和代码摘要" />
            )}
          </Card>
        </div>
      </section>
    </AppFrame>
  )
}

function PageManagement({ isPageListLoading, pageListData, pages, refreshPages }: PageProps) {
  const navigate = useNavigate()
  const [messageApi, contextHolder] = message.useMessage()

  const handleExportPage = (page: GeneratedPage) => {
    downloadFile(`${page.entity}-page.tsx`, generateCode(page.dsl), 'text/typescript;charset=utf-8')
    downloadFile(`${page.entity}-dsl.json`, JSON.stringify(page.dsl, null, 2), 'application/json;charset=utf-8')
    messageApi.success('已导出页面代码和 DSL')
  }

  const columns: ColumnsType<GeneratedPage> = [
    {
      title: '页面名称',
      dataIndex: 'name',
      render: (name, record) => (
        <Space direction="vertical" size={0}>
          <Button type="link" onClick={() => navigate(`/pages/${record.id}`)}>
            {name}
          </Button>
          <Typography.Text type="secondary">{record.route}</Typography.Text>
        </Space>
      ),
    },
    { title: '业务实体', dataIndex: 'entity', width: 130 },
    {
      title: '页面类型',
      dataIndex: ['dsl', 'pageType'],
      width: 120,
      render: (value) => <Tag color="blue">{value}</Tag>,
    },
    {
      title: '功能',
      dataIndex: ['dsl', 'features'],
      render: (features: string[]) => (
        <Space wrap>
          {features.map((feature) => (
            <Tag key={feature}>{feature}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 120,
      render: (status: GeneratedPage['status']) => <Tag color={status === 'verified' ? 'green' : 'orange'}>{status === 'verified' ? '已验证' : '草稿'}</Tag>,
    },
    { title: '创建时间', dataIndex: 'createdAt', width: 170 },
    {
      title: '操作',
      key: 'action',
      fixed: 'right',
      width: 250,
      render: (_, record) => (
        <Space>
          <Button icon={<EyeOutlined />} size="small" onClick={() => navigate(`/pages/${record.id}`)}>
            预览
          </Button>
          <Button icon={<DownloadOutlined />} size="small" onClick={() => handleExportPage(record)}>
            导出
          </Button>
          <Popconfirm
            title="确认删除该页面资产？"
            okText="删除"
            cancelText="取消"
            onConfirm={async () => {
              try {
                await deletePage(record.id)
                await refreshPages()
                messageApi.success('页面已删除')
              } catch {
                messageApi.error('删除失败，请检查服务端状态')
              }
            }}
          >
            <Button danger icon={<DeleteOutlined />} size="small" />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <AppFrame>
      {contextHolder}
      <section className="page-section">
        <div className="page-title">
          <Flex align="center" justify="space-between">
            <Space align="center">
              <AppstoreOutlined />
              <Typography.Title level={2}>页面管理</Typography.Title>
            </Space>
            <Button icon={<PlusOutlined />} type="primary" onClick={() => navigate('/generator')}>
              新生成页面
            </Button>
          </Flex>
          <Typography.Text type="secondary">生成好的页面统一沉淀在这里，支持预览、导出和后续接入仓库变更包。</Typography.Text>
        </div>

        <Card className="preview-card">
          {pages.length ? (
            <Table<GeneratedPage>
              columns={columns}
              dataSource={pages}
              loading={isPageListLoading}
              pagination={{
                current: pageListData.pageNo,
                pageSize: pageListData.pageSize,
                showSizeChanger: true,
                total: pageListData.total,
                onChange: (pageNo, pageSize) => {
                  void refreshPages(pageNo, pageSize)
                },
              }}
              rowKey="id"
              scroll={{ x: 980 }}
            />
          ) : (
            <Empty
              description="暂无生成页面"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            >
              <Button type="primary" onClick={() => navigate('/generator')}>
                去生成第一个页面
              </Button>
            </Empty>
          )}
        </Card>
      </section>
    </AppFrame>
  )
}

function ApiManagementPage() {
  const [apis, setApis] = useState<ApiDefinition[]>([])
  const [apiListData, setApiListData] = useState<{ list: ApiDefinition[]; pageNo: number; pageSize: number; total: number }>({
    list: [],
    pageNo: 1,
    pageSize: 10,
    total: 0,
  })
  const [isLoading, setIsLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [editingApi, setEditingApi] = useState<ApiDefinition | null>(null)
  const [form] = Form.useForm<ApiFormValues>()
  const [messageApi, contextHolder] = message.useMessage()

  const refreshApiList = async (pageNo = apiListData.pageNo, pageSize = apiListData.pageSize) => {
    setIsLoading(true)
    try {
      const result = await listApis(pageNo, pageSize)
      setApis(result.list)
      setApiListData(result)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '接口列表加载失败'
      messageApi.error(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false

    const bootstrap = async () => {
      try {
        const result = await listApis(1, 10)
        if (!cancelled) {
          setApis(result.list)
          setApiListData(result)
        }
      } catch (error) {
        if (!cancelled) {
          const errorMessage = error instanceof Error ? error.message : '接口列表加载失败'
          messageApi.error(errorMessage)
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void bootstrap()

    return () => {
      cancelled = true
    }
  }, [messageApi])

  const openCreateModal = () => {
    setEditingApi(null)
    form.setFieldsValue(getApiFormInitialValues())
    setIsModalOpen(true)
  }

  const openEditModal = (apiDefinition: ApiDefinition) => {
    setEditingApi(apiDefinition)
    form.setFieldsValue(getApiFormInitialValues(apiDefinition))
    setIsModalOpen(true)
  }

  const handleSubmit = async (values: ApiFormValues) => {
    let payload: SaveApiRequest
    try {
      payload = {
        name: values.name.trim(),
        entity: values.entity.trim(),
        method: values.method,
        path: values.path.trim(),
        action: values.action,
        status: values.status,
        requestSchema: parseApiSchema(values.requestSchemaText, '请求 Schema'),
        responseSchema: parseApiSchema(values.responseSchemaText, '响应 Schema'),
        mockData: parseMockData(values.mockDataText),
      }
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : '表单解析失败')
      return
    }

    setIsSubmitting(true)
    try {
      if (editingApi) {
        await updateApi(editingApi.id, payload)
        messageApi.success('接口已更新')
      } else {
        await createApi(payload)
        messageApi.success('接口已创建')
      }
      setIsModalOpen(false)
      form.resetFields()
      await refreshApiList()
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : '接口保存失败')
    } finally {
      setIsSubmitting(false)
    }
  }

  const columns: ColumnsType<ApiDefinition> = [
    {
      title: '接口名称',
      dataIndex: 'name',
      render: (name, record) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{name}</Typography.Text>
          <Typography.Text type="secondary">
            {record.method} {record.path}
          </Typography.Text>
        </Space>
      ),
    },
    { title: '业务实体', dataIndex: 'entity', width: 120 },
    {
      title: '动作',
      dataIndex: 'action',
      width: 120,
      render: (action: ApiDefinition['action']) => <Tag color="blue">{apiActionOptions.find((item) => item.value === action)?.label ?? action}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 120,
      render: (status: ApiDefinition['status']) => <Tag color={status === 'published' ? 'green' : 'orange'}>{status === 'published' ? '已发布' : '草稿'}</Tag>,
    },
    { title: '创建时间', dataIndex: 'createdAt', width: 170 },
    {
      title: '操作',
      key: 'action',
      width: 170,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button icon={<EditOutlined />} size="small" onClick={() => openEditModal(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除该接口定义？"
            okText="删除"
            cancelText="取消"
            onConfirm={async () => {
              try {
                await removeApi(record.id)
                await refreshApiList()
                messageApi.success('接口已删除')
              } catch (error) {
                messageApi.error(error instanceof Error ? error.message : '接口删除失败')
              }
            }}
          >
            <Button danger icon={<DeleteOutlined />} size="small" />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <AppFrame>
      {contextHolder}
      <section className="page-section">
        <div className="page-title">
          <Flex align="center" justify="space-between">
            <Space align="center">
              <ApiOutlined />
              <Typography.Title level={2}>接口管理</Typography.Title>
            </Space>
            <Button icon={<PlusOutlined />} type="primary" onClick={openCreateModal}>
              新增接口
            </Button>
          </Flex>
          <Typography.Text type="secondary">集中维护页面查询、创建、编辑、删除所依赖的接口定义，并为页面绑定真实契约。</Typography.Text>
        </div>

        <Card className="preview-card">
          <Table<ApiDefinition>
            columns={columns}
            dataSource={apis}
            loading={isLoading}
            pagination={{
              current: apiListData.pageNo,
              pageSize: apiListData.pageSize,
              showSizeChanger: true,
              total: apiListData.total,
              onChange: (pageNo, pageSize) => {
                void refreshApiList(pageNo, pageSize)
              },
            }}
            rowKey="id"
            scroll={{ x: 980 }}
          />
        </Card>
      </section>

      <Modal
        centered
        confirmLoading={isSubmitting}
        destroyOnHidden
        okText={editingApi ? '保存修改' : '创建接口'}
        open={isModalOpen}
        title={editingApi ? '编辑接口定义' : '新增接口定义'}
        width={860}
        onCancel={() => setIsModalOpen(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={(values) => void handleSubmit(values)}>
          <div className="api-form-grid">
            <Form.Item label="接口名称" name="name" rules={[{ required: true, message: '请输入接口名称' }]}>
              <Input placeholder="如：客户列表查询接口" />
            </Form.Item>
            <Form.Item label="业务实体" name="entity" rules={[{ required: true, message: '请输入业务实体' }]}>
              <Input placeholder="如：customer" />
            </Form.Item>
            <Form.Item label="请求方法" name="method" rules={[{ required: true, message: '请选择请求方法' }]}>
              <Radio.Group optionType="button" buttonStyle="solid" options={apiMethodOptions} />
            </Form.Item>
            <Form.Item label="接口动作" name="action" rules={[{ required: true, message: '请选择接口动作' }]}>
              <Select options={apiActionOptions} />
            </Form.Item>
            <Form.Item className="full-width" label="接口路径" name="path" rules={[{ required: true, message: '请输入接口路径' }]}>
              <Input placeholder="/api/customers" />
            </Form.Item>
            <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择状态' }]}>
              <Select options={apiStatusOptions} />
            </Form.Item>
            <Form.Item className="full-width" extra='示例：[{"name":"keyword","type":"string","required":false}]' label="请求 Schema JSON" name="requestSchemaText">
              <Input.TextArea rows={6} />
            </Form.Item>
            <Form.Item className="full-width" extra='示例：[{"name":"customerName","type":"string"}]' label="响应 Schema JSON" name="responseSchemaText">
              <Input.TextArea rows={6} />
            </Form.Item>
            <Form.Item className="full-width" extra='可填写对象或数组，作为联调前的返回示例' label="Mock 返回示例 JSON" name="mockDataText">
              <Input.TextArea rows={8} />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </AppFrame>
  )
}

function PageApiManagement({ isPageListLoading, pages }: SharedAppProps) {
  const { pageId: routePageId } = useParams()
  const navigate = useNavigate()
  const [selectedPageId, setSelectedPageId] = useState(routePageId ?? '')
  const selectedPage = pages.find((item) => item.id === selectedPageId) ?? null
  const [apiOptions, setApiOptions] = useState<ApiDefinition[]>([])
  const [isApiOptionsLoading, setIsApiOptionsLoading] = useState(true)
  const [isBindingLoading, setIsBindingLoading] = useState(false)
  const [isBindingSaving, setIsBindingSaving] = useState(false)
  const [binding, setBinding] = useState<PageApiBinding | null>(null)
  const [form] = Form.useForm<Omit<PageApiBinding, 'pageId' | 'updatedAt'>>()
  const [messageApi, contextHolder] = message.useMessage()

  useEffect(() => {
    if (routePageId) {
      setSelectedPageId(routePageId)
    }
  }, [routePageId])

  useEffect(() => {
    let cancelled = false
    void listApis(1, 100)
      .then((result) => {
        if (!cancelled) {
          setApiOptions(result.list)
        }
      })
      .catch((error) => {
        if (!cancelled) {
          messageApi.error(error instanceof Error ? error.message : '接口列表加载失败')
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsApiOptionsLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [messageApi])

  useEffect(() => {
    if (!selectedPageId) {
      setBinding(null)
      form.resetFields()
      return
    }

    let cancelled = false
    const loadBindings = async () => {
      setIsBindingLoading(true)
      try {
        const result = await getPageBindings(selectedPageId)
        if (!cancelled) {
          setBinding(result)
          form.setFieldsValue({
            listApiId: result.listApiId,
            createApiId: result.createApiId,
            updateApiId: result.updateApiId,
            deleteApiId: result.deleteApiId,
          })
        }
      } catch (error) {
        if (!cancelled) {
          setBinding(null)
          form.resetFields()
          messageApi.error(error instanceof Error ? error.message : '页面绑定加载失败')
        }
      } finally {
        if (!cancelled) {
          setIsBindingLoading(false)
        }
      }
    }

    void loadBindings()

    return () => {
      cancelled = true
    }
  }, [form, messageApi, selectedPageId])

  const filteredApiOptions = useMemo(() => {
    if (!selectedPage) return apiOptions
    return apiOptions.filter((item) => item.entity === selectedPage.entity)
  }, [apiOptions, selectedPage])

  const buildActionOptions = (action: ApiAction) =>
    filteredApiOptions
      .filter((item) => item.action === action)
      .map((item) => ({
        label: `${item.name} (${item.method} ${item.path})`,
        value: item.id,
      }))

  const handlePageChange = (value: string) => {
    setSelectedPageId(value)
    navigate(`/page-apis/${value}`, { replace: true })
  }

  const handleSaveBindings = async () => {
    if (!selectedPageId) {
      messageApi.warning('请先选择页面')
      return
    }

    setIsBindingSaving(true)
    try {
      const result = await savePageBindings(selectedPageId, form.getFieldsValue())
      setBinding(result)
      messageApi.success('页面接口绑定已保存')
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : '页面接口绑定保存失败')
    } finally {
      setIsBindingSaving(false)
    }
  }

  return (
    <AppFrame>
      {contextHolder}
      <section className="page-section">
        <div className="page-title">
          <Flex align="center" justify="space-between">
            <Space align="center">
              <LinkOutlined />
              <Typography.Title level={2}>页面接口管理</Typography.Title>
            </Space>
            <Button icon={<ApiOutlined />} onClick={() => navigate('/apis')}>
              接口定义
            </Button>
          </Flex>
          <Typography.Text type="secondary">集中维护页面和接口资产之间的绑定关系，页面详情只负责预览数据源切换。</Typography.Text>
        </div>

        <Card className="preview-card">
          <Form form={form} layout="vertical">
            <Form.Item label="选择页面">
              <Select
                loading={isPageListLoading}
                options={pages.map((item) => ({
                  label: `${item.name} (${item.entity})`,
                  value: item.id,
                }))}
                placeholder="请选择需要绑定接口的页面"
                value={selectedPageId || undefined}
                onChange={handlePageChange}
              />
            </Form.Item>

            {selectedPage ? (
              <>
                <div className="page-api-summary">
                  <Tag color="blue">{selectedPage.entity}</Tag>
                  <Typography.Text type="secondary">系统路由：{selectedPage.route}</Typography.Text>
                  {binding?.updatedAt && <Typography.Text type="secondary">最近保存：{binding.updatedAt}</Typography.Text>}
                </div>
                <div className="binding-grid">
                  <Form.Item label="列表查询接口" name="listApiId">
                    <Select allowClear loading={isApiOptionsLoading || isBindingLoading} options={buildActionOptions('list')} placeholder="请选择列表接口" />
                  </Form.Item>
                  <Form.Item label="新增接口" name="createApiId">
                    <Select allowClear loading={isApiOptionsLoading || isBindingLoading} options={buildActionOptions('create')} placeholder="请选择新增接口" />
                  </Form.Item>
                  <Form.Item label="编辑接口" name="updateApiId">
                    <Select allowClear loading={isApiOptionsLoading || isBindingLoading} options={buildActionOptions('update')} placeholder="请选择编辑接口" />
                  </Form.Item>
                  <Form.Item label="删除接口" name="deleteApiId">
                    <Select allowClear loading={isApiOptionsLoading || isBindingLoading} options={buildActionOptions('delete')} placeholder="请选择删除接口" />
                  </Form.Item>
                </div>
                <Space>
                  <Button icon={<LinkOutlined />} loading={isBindingSaving} type="primary" onClick={() => void handleSaveBindings()}>
                    保存绑定
                  </Button>
                  <Button icon={<EyeOutlined />} onClick={() => navigate(`/pages/${selectedPage.id}`)}>
                    打开页面预览
                  </Button>
                </Space>
              </>
            ) : (
              <Empty description="请选择一个页面后维护接口绑定" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Form>
        </Card>
      </section>
    </AppFrame>
  )
}

function GeneratedPageDetail({ pages, refreshPages }: SharedAppProps) {
  const { pageId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const routeDsl = (location.state as NewPageRouteState | null)?.dsl
  const isDraftPreview = pageId === 'new'
  const existingPage = pageId ? pages.find((item) => item.id === pageId) ?? null : null
  const [page, setPage] = useState<GeneratedPage | null>(existingPage)
  const [isSavingPage, setIsSavingPage] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<PreviewRecord | null>(null)
  const [form] = Form.useForm<PreviewRecord>()
  const [searchForm] = Form.useForm<Record<string, string>>()
  const [messageApi, contextHolder] = message.useMessage()
  const resolvedPage = existingPage ?? page
  const dsl = resolvedPage?.dsl ?? routeDsl
  const dslKey = useMemo(() => (dsl ? JSON.stringify(dsl) : 'empty'), [dsl])
  const previewSeed = useMemo(() => (dsl ? createPreviewRows(dsl) : []), [dsl])
  const [dataByDslKey, setDataByDslKey] = useState<Record<string, PreviewRecord[]>>({})
  const data = dataByDslKey[dslKey] ?? previewSeed
  const [apiOptions, setApiOptions] = useState<ApiDefinition[]>([])
  const [isApiOptionsLoading, setIsApiOptionsLoading] = useState(true)
  const [binding, setBinding] = useState<PageApiBinding | null>(null)
  const [isBindingLoading, setIsBindingLoading] = useState(Boolean(pageId && !isDraftPreview))
  const [dataSourceMode, setDataSourceMode] = useState<DataSourceMode>('mock')
  const [isQueryRunning, setIsQueryRunning] = useState(false)
  const [isMutatingData, setIsMutatingData] = useState(false)
  const isDetailLoading = Boolean(pageId) && !isDraftPreview && !resolvedPage

  useEffect(() => {
    if (isDraftPreview || !pageId) return
    if (existingPage) {
      return
    }

    let cancelled = false
    void getPage(pageId)
      .then((result) => {
        if (!cancelled) {
          setPage(result)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPage(null)
        }
      })

    return () => {
      cancelled = true
    }
  }, [existingPage, isDraftPreview, pageId, pages])

  useEffect(() => {
    let cancelled = false
    void listApis(1, 100)
      .then((result) => {
        if (!cancelled) {
          setApiOptions(result.list)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setApiOptions([])
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsApiOptionsLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [messageApi])

  useEffect(() => {
    if (!pageId || isDraftPreview) {
      setBinding(null)
      return
    }

    let cancelled = false
    const loadBindings = async () => {
      try {
        setIsBindingLoading(true)
        const result = await getPageBindings(pageId)
        if (!cancelled) {
          setBinding(result)
        }
      } catch (error) {
        if (!cancelled) {
          messageApi.error(error instanceof Error ? error.message : '页面绑定加载失败')
        }
      } finally {
        if (!cancelled) {
          setIsBindingLoading(false)
        }
      }
    }

    void loadBindings()

    return () => {
      cancelled = true
    }
  }, [isDraftPreview, messageApi, pageId])

  const filteredApiOptions = useMemo(() => {
    if (!dsl) return apiOptions
    return apiOptions.filter((item) => item.entity === dsl.entity)
  }, [apiOptions, dsl])

  const listApi = filteredApiOptions.find((item) => item.id === binding?.listApiId)
  const createApi = filteredApiOptions.find((item) => item.id === binding?.createApiId)
  const updateApi = filteredApiOptions.find((item) => item.id === binding?.updateApiId)
  const deleteApiDefinition = filteredApiOptions.find((item) => item.id === binding?.deleteApiId)

  const columns = useMemo<ColumnsType<PreviewRecord>>(() => {
    if (!dsl) return []

    return [
      ...dsl.fields.map((field: FieldSpec, index: number) => ({
        title: field.label,
        dataIndex: field.name,
        key: field.name,
        ellipsis: true,
        width: index === 0 ? 160 : field.type === 'phone' ? 150 : field.type === 'date' ? 130 : 140,
        render: (value: string) => renderFieldValue(field, value),
      })),
      {
        title: '操作',
        key: 'action',
        width: 120,
        render: (_: unknown, record: PreviewRecord) => (
          <Space>
            <Button
              aria-label={`编辑${dsl.title}`}
              icon={<EditOutlined />}
              size="small"
              onClick={() => {
                setEditing(record)
                form.setFieldsValue(record)
                setModalOpen(true)
              }}
            />
            <Popconfirm
              title={`确认删除该${dsl.title}？`}
              okText="删除"
              cancelText="取消"
              onConfirm={async () => {
                try {
                  if (dataSourceMode === 'api' && deleteApiDefinition) {
                    await invokeRuntimeApi(buildRuntimePath(deleteApiDefinition.path, record.id), deleteApiDefinition.method)
                    messageApi.success(`已调用 ${deleteApiDefinition.method} ${deleteApiDefinition.path} 完成删除`)
                  } else {
                    messageApi.info('已在 Mock 数据中删除当前记录')
                  }

                  setDataByDslKey((current) => ({
                    ...current,
                    [dslKey]: data.filter((item) => item.id !== record.id),
                  }))
                } catch (error) {
                  messageApi.error(error instanceof Error ? error.message : '删除失败')
                }
              }}
            >
              <Button aria-label={`删除${dsl.title}`} danger icon={<DeleteOutlined />} size="small" />
            </Popconfirm>
          </Space>
        ),
      },
    ]
  }, [data, deleteApiDefinition, dsl, dslKey, form, messageApi])

  const handleSavePage = () => {
    if (!dsl || !isDraftPreview) return
    setIsSavingPage(true)
    void createPage(dsl)
      .then(async (savedPage) => {
        await refreshPages()
        messageApi.success('页面已保存到页面管理')
        navigate(`/pages/${savedPage.id}`, { replace: true })
      })
      .catch(() => {
        messageApi.error('保存失败，请检查服务端状态')
      })
      .finally(() => {
        setIsSavingPage(false)
      })
  }

  const handleSubmit = async (values: PreviewRecord) => {
    const normalizedValues = dsl
      ? dsl.fields.reduce<PreviewRecord>(
          (accumulator: PreviewRecord, field: FieldSpec) => {
            accumulator[field.name] = values[field.name] ?? ''
            return accumulator
          },
          { id: editing?.id ?? `${dsl.entity}-${Date.now()}` },
        )
      : values

    setIsMutatingData(true)
    try {
      if (editing) {
        if (dataSourceMode === 'api' && updateApi) {
          const response = await invokeRuntimeApi<Record<string, unknown>>(
            buildRuntimePath(updateApi.path, editing.id),
            updateApi.method,
            { body: normalizedValues },
          )
          const updatedRecord = dsl ? normalizePreviewRecord(response, dsl, editing.id) : normalizedValues
          setDataByDslKey((current) => ({
            ...current,
            [dslKey]: data.map((item) => (item.id === editing.id ? updatedRecord : item)),
          }))
          messageApi.success(`已调用 ${updateApi.method} ${updateApi.path} 完成编辑`)
        } else {
          setDataByDslKey((current) => ({
            ...current,
            [dslKey]: data.map((item) => (item.id === editing.id ? { ...item, ...normalizedValues } : item)),
          }))
          messageApi.info('已保存到当前 Mock 预览数据')
        }
      } else {
        if (dataSourceMode === 'api' && createApi) {
          const response = await invokeRuntimeApi<Record<string, unknown>>(createApi.path, createApi.method, {
            body: normalizedValues,
          })
          const createdRecord = dsl ? normalizePreviewRecord(response, dsl, normalizedValues.id) : normalizedValues
          setDataByDslKey((current) => ({
            ...current,
            [dslKey]: [createdRecord, ...data],
          }))
          messageApi.success(`已调用 ${createApi.method} ${createApi.path} 完成新增`)
        } else {
          setDataByDslKey((current) => ({
            ...current,
            [dslKey]: [normalizedValues, ...data],
          }))
          messageApi.info('已新增到当前 Mock 预览数据')
        }
      }
      setModalOpen(false)
      setEditing(null)
      form.resetFields()
    } catch (error) {
      messageApi.error(error instanceof Error ? error.message : '数据操作失败')
    } finally {
      setIsMutatingData(false)
    }
  }

  const handleQuery = async () => {
    if (!dsl) return

    const filters = searchForm.getFieldsValue()
    setIsQueryRunning(true)
    try {
      if (dataSourceMode === 'api' && listApi) {
        const response = await invokeRuntimeApi<unknown>(listApi.path, listApi.method, { params: filters })
        const records = extractListRows(response).map((item: Record<string, unknown>, index: number) => normalizePreviewRecord(item, dsl, `${dsl.entity}-query-${index + 1}`))
        setDataByDslKey((current) => ({
          ...current,
          [dslKey]: records,
        }))
        messageApi.success(`已调用 ${listApi.method} ${listApi.path} 完成查询`)
      } else {
        const mockRows = resolveMockRowsFromApi(listApi, dsl) ?? createPreviewRows(dsl)
        const filteredRows = mockRows.filter((row) =>
          dsl.fields.slice(0, 3).every((field: FieldSpec) => {
            const keyword = String(filters[field.name] ?? '').trim()
            if (!keyword) return true
            return String(row[field.name] ?? '').toLowerCase().includes(keyword.toLowerCase())
          }),
        )

        setDataByDslKey((current) => ({
          ...current,
          [dslKey]: filteredRows,
        }))
        messageApi.info('已使用 Mock 数据完成查询预览')
      }
    } catch (error) {
      const fallbackRows = resolveMockRowsFromApi(listApi, dsl) ?? createPreviewRows(dsl)
      setDataByDslKey((current) => ({
        ...current,
        [dslKey]: fallbackRows,
      }))
      messageApi.warning(error instanceof Error ? `${error.message}，已回退到 Mock/示例数据` : '查询失败，已回退到 Mock/示例数据')
    } finally {
      setIsQueryRunning(false)
    }
  }

  const handleResetQuery = () => {
    if (!dsl) return
    searchForm.resetFields()
    if (dataSourceMode === 'api' && listApi) {
      void handleQuery()
      return
    }
    setDataByDslKey((current) => ({
      ...current,
      [dslKey]: resolveMockRowsFromApi(listApi, dsl) ?? createPreviewRows(dsl),
    }))
  }

  const hasApiBindings = Boolean(listApi || createApi || updateApi || deleteApiDefinition)

  return (
    <AppFrame>
      {contextHolder}
      <section className="page-section">
        <div className="preview-shell">
          <Card className="preview-meta-card">
            <Flex align="center" className="preview-header" justify="space-between">
              <Space direction="vertical" size={4}>
                <Button icon={<TableOutlined />} type="text" onClick={() => navigate('/pages')}>
                  返回页面管理
                </Button>
                <Space>
                  <CheckCircleFilled className={dsl ? 'success-icon' : 'muted-icon'} />
                  <Typography.Title level={2}>{page?.name ?? dsl?.title ?? '页面不存在'}</Typography.Title>
                  {isDraftPreview && dsl && <Tag color="orange">未保存</Tag>}
                  {page && <Tag color={page.status === 'verified' ? 'green' : 'orange'}>{page.status === 'verified' ? '已验证' : '草稿'}</Tag>}
                </Space>
                {isDraftPreview && dsl && <Typography.Text type="secondary">当前为预览态，点击保存后才会进入页面管理。</Typography.Text>}
              </Space>
              <Space>
                {isDraftPreview && (
                  <Button disabled={!dsl} type="primary" onClick={handleSavePage}>
                    {isSavingPage ? '保存中...' : '保存到页面管理'}
                  </Button>
                )}
                {isDraftPreview && !dsl && (
                  <Button disabled type="primary">
                    保存到页面管理
                  </Button>
                )}
              </Space>
            </Flex>

            {!isDraftPreview && page && (
              <div className="preview-meta-grid">
                <div className="preview-meta-item">
                  <Typography.Text type="secondary">系统路由</Typography.Text>
                  <Typography.Text>{page.route}</Typography.Text>
                </div>
                <div className="preview-meta-item">
                  <Typography.Text type="secondary">生成时间</Typography.Text>
                  <Typography.Text>{page.createdAt}</Typography.Text>
                </div>
                <div className="preview-meta-item preview-meta-item-wide">
                  <div className="preview-meta-inline">
                    <div className="preview-meta-copy">
                      <Typography.Text type="secondary">预览数据源</Typography.Text>
                      <Typography.Text>
                        {dataSourceMode === 'api' && hasApiBindings
                          ? '当前查询、新增、编辑、删除会优先调用已绑定接口。'
                          : '当前使用 Mock 数据，仅在页面外验证页面交互与字段规则。'}
                      </Typography.Text>
                    </div>
                    <div className="preview-meta-actions">
                      <Button icon={<LinkOutlined />} onClick={() => navigate(`/page-apis/${pageId}`)}>
                        管理接口
                      </Button>
                      <Radio.Group
                        optionType="button"
                        value={dataSourceMode}
                        options={[
                          { label: 'Mock 数据', value: 'mock' },
                          { label: '接口数据', value: 'api', disabled: isApiOptionsLoading || isBindingLoading || !hasApiBindings },
                        ]}
                        onChange={(event) => setDataSourceMode(event.target.value)}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </Card>

          <Card className="preview-card">
            <div className="preview-canvas-head">
              <Typography.Text className="preview-canvas-label">页面预览</Typography.Text>
            </div>

            <Divider />

            {isDetailLoading ? (
              <Skeleton active paragraph={{ rows: 8 }} title />
            ) : dsl ? (
              <>
                <div className="preview-toolbar">
                  <Form className="search-form" form={searchForm} layout="vertical">
                    <div className="search-fields-grid">
                      {dsl.fields.slice(0, 3).map((field: FieldSpec) => (
                        <Form.Item key={field.name} label={field.label} name={field.name}>
                          {field.type === 'enum' ? (
                            <Select
                              allowClear
                              placeholder={getFieldPlaceholder(field)}
                              options={(field.options ?? []).map((value: string) => ({ value, label: value }))}
                            />
                          ) : (
                            <Input placeholder={getFieldPlaceholder(field)} />
                          )}
                        </Form.Item>
                      ))}
                    </div>
                    <div className="search-form-actions">
                      <Button className="toolbar-button" loading={isQueryRunning} type="primary" onClick={() => void handleQuery()}>
                        查询
                      </Button>
                      <Button className="toolbar-button" onClick={handleResetQuery}>
                        重置
                      </Button>
                    </div>
                  </Form>

                  <div className="preview-action-row">
                    <Button
                      className="toolbar-button"
                      disabled={!dsl}
                      icon={<PlusOutlined />}
                      loading={isMutatingData}
                      type="primary"
                      onClick={() => {
                        setEditing(null)
                        form.resetFields()
                        setModalOpen(true)
                      }}
                    >
                      新增数据
                    </Button>
                  </div>
                </div>
                <div className="preview-table-wrap">
                  <Table<PreviewRecord> columns={columns} dataSource={data} pagination={false} rowKey="id" tableLayout="fixed" />
                </div>
                <Divider />
                <Card size="small" title="业务规则">
                  <Space wrap>
                    {dsl.rules.map((rule: string) => (
                      <Tag key={rule}>{rule}</Tag>
                    ))}
                  </Space>
                </Card>
              </>
            ) : (
              <Empty description={isDetailLoading ? '正在加载页面数据...' : '未找到页面资产，请返回页面管理或重新生成'} />
            )}
          </Card>
        </div>
      </section>

      <Modal
        title={editing ? `编辑${dsl?.title ?? '数据'}` : `新增${dsl?.title ?? '数据'}`}
        open={modalOpen}
        confirmLoading={isMutatingData}
        okText="保存"
        cancelText="取消"
        onCancel={() => setModalOpen(false)}
        onOk={() => void form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={(values) => void handleSubmit(values)}>
          {dsl?.fields.map((field: FieldSpec) => (
            <Form.Item
              key={field.name}
              label={field.label}
              name={field.name}
              rules={[
                ...(field.required ? [{ required: true, message: getFieldPlaceholder(field) }] : []),
                ...(field.type === 'phone' ? [{ pattern: /^1[3-9]\d{9}$/, message: '请输入有效的 11 位手机号' }] : []),
              ]}
            >
              {field.type === 'enum' ? (
                <Select options={(field.options ?? []).map((value: string) => ({ value, label: value }))} placeholder={getFieldPlaceholder(field)} />
              ) : (
                <Input placeholder={getFieldPlaceholder(field)} />
              )}
            </Form.Item>
          ))}
        </Form>
      </Modal>
    </AppFrame>
  )
}

function AppContent() {
  const { isPageListLoading, pageListData, pages, refreshPages } = usePagesStore()

  return (
    <AppRoutes
      ApiManagementPage={ApiManagementPage}
      GeneratedPageDetail={GeneratedPageDetail}
      GeneratorPage={GeneratorPage}
      PageApiManagement={PageApiManagement}
      PageManagement={PageManagement}
      isPageListLoading={isPageListLoading}
      pageListData={pageListData}
      pages={pages}
      refreshPages={refreshPages}
    />
  )
}

function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          borderRadius: 8,
          colorPrimary: '#1769e0',
          fontFamily: 'Microsoft YaHei, Segoe UI, sans-serif',
        },
      }}
    >
      <AntApp>
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  )
}

export default App
