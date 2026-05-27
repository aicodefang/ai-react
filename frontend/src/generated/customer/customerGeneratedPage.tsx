import { DeleteOutlined, DownloadOutlined, EditOutlined, PlusOutlined, ReloadOutlined, SearchOutlined, UserOutlined } from '@ant-design/icons'
import { Button, Card, Col, Empty, Form, Input, Modal, Popconfirm, Row, Select, Space, Spin, Statistic, Table, Tag, Typography, message } from 'antd'
import { useEffect, useMemo, useState } from 'react'

type CustomerRow = {
  id: string
  customerName: string
  level: string
  contactName: string
  phone: string
  region: string
  status: string
  createdAt: string
}

type CustomerFormValues = Omit<CustomerRow, 'id'>

const LEVEL_OPTIONS = ['A', 'B', 'C'].map((value) => ({ value, label: value }))
const REGION_OPTIONS = ['华东', '华北', '华南', '西南'].map((value) => ({ value, label: value }))
const STATUS_OPTIONS = ['active', 'pending', 'disabled'].map((value) => ({ value, label: value }))
const STATUS_COLOR_MAP: Record<string, string> = {
  active: 'green',
  pending: 'gold',
  disabled: 'default',
}

export function CustomerGeneratedPage() {
  const [rows, setRows] = useState<CustomerRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [keyword, setKeyword] = useState('')
  const [levelFilter, setLevelFilter] = useState<string | undefined>()
  const [contactFilter, setContactFilter] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [editing, setEditing] = useState<CustomerRow | null>(null)
  const [messageApi, contextHolder] = message.useMessage()
  const [form] = Form.useForm<CustomerFormValues>()

  const loadRows = async (params?: { customerName?: string; level?: string; contactName?: string }) => {
    setLoading(true)
    setError('')
    try {
      const search = new URLSearchParams()
      if (params?.customerName) search.set('customerName', params.customerName)
      if (params?.level) search.set('level', params.level)
      const response = await fetch(`/api/generated/customers${search.toString() ? `?${search.toString()}` : ''}`)
      const payload = await response.json()
      if (!response.ok || payload.code !== 0) {
        throw new Error(payload.message || '加载客户数据失败')
      }
      let nextRows: CustomerRow[] = payload.data?.list ?? []
      if (params?.contactName) {
        const normalizedKeyword = params.contactName.trim().toLowerCase()
        nextRows = nextRows.filter((row) => row.contactName.toLowerCase().includes(normalizedKeyword))
      }
      setRows(nextRows)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '加载客户数据失败')
      setRows([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      await loadRows()
    }
    if (!cancelled) {
      void load()
    }
    return () => {
      cancelled = true
    }
  }, [])

  const filteredRows = useMemo(() => {
    const value = keyword.trim().toLowerCase()
    if (!value) return rows
    return rows.filter((row) =>
      [row.customerName, row.contactName, row.phone, row.region, row.status].some((item) => item.toLowerCase().includes(value)),
    )
  }, [keyword, rows])

  const columns = [
    { title: '客户名称', dataIndex: 'customerName', key: 'customerName' },
    { title: '客户等级', dataIndex: 'level', key: 'level', render: (value: string) => <Tag color="blue">{value}</Tag> },
    { title: '联系人', dataIndex: 'contactName', key: 'contactName' },
    { title: '手机号', dataIndex: 'phone', key: 'phone' },
    { title: '所属区域', dataIndex: 'region', key: 'region' },
    { title: '客户状态', dataIndex: 'status', key: 'status', render: (value: string) => <Tag color={STATUS_COLOR_MAP[value]}>{value}</Tag> },
    { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt' },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: CustomerRow) => (
        <Space>
          <Button
            aria-label={`编辑${record.customerName}`}
            icon={<EditOutlined />}
            size="small"
            onClick={() => {
              setEditing(record)
              form.setFieldsValue({
                customerName: record.customerName,
                level: record.level,
                contactName: record.contactName,
                phone: record.phone,
                region: record.region,
                status: record.status,
                createdAt: record.createdAt,
              })
              setModalOpen(true)
            }}
          />
          <Popconfirm
            title={`确认删除客户 ${record.customerName}？`}
            okText="删除"
            cancelText="取消"
            onConfirm={async () => {
              try {
                const response = await fetch(`/api/generated/customers/${record.id}`, { method: 'DELETE' })
                const payload = await response.json()
                if (!response.ok || payload.code !== 0) {
                  throw new Error(payload.message || '删除客户失败')
                }
                messageApi.success('客户删除成功')
                await loadRows({ customerName: keyword, level: levelFilter, contactName: contactFilter })
              } catch (requestError) {
                messageApi.error(requestError instanceof Error ? requestError.message : '删除客户失败')
              }
            }}
          >
            <Button danger aria-label={`删除${record.customerName}`} icon={<DeleteOutlined />} size="small" />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const handleSearch = async () => {
    await loadRows({
      customerName: keyword,
      level: levelFilter,
      contactName: contactFilter,
    })
  }

  const handleReset = async () => {
    setKeyword('')
    setLevelFilter(undefined)
    setContactFilter('')
    await loadRows()
  }

  const handleSubmit = async (values: CustomerFormValues) => {
    setSubmitting(true)
    try {
      const targetUrl = editing ? `/api/generated/customers/${editing.id}` : '/api/generated/customers'
      const response = await fetch(targetUrl, {
        body: JSON.stringify(values),
        headers: { 'Content-Type': 'application/json' },
        method: editing ? 'PUT' : 'POST',
      })
      const payload = await response.json()
      if (!response.ok || payload.code !== 0) {
        throw new Error(payload.message || '保存客户失败')
      }
      messageApi.success(editing ? '客户更新成功' : '客户创建成功')
      setModalOpen(false)
      setEditing(null)
      form.resetFields()
      await loadRows({ customerName: keyword, level: levelFilter, contactName: contactFilter })
    } catch (requestError) {
      messageApi.error(requestError instanceof Error ? requestError.message : '保存客户失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleExport = () => {
    if (!filteredRows.length) {
      messageApi.warning('当前没有可导出的客户数据')
      return
    }
    const header = ['customerName', 'level', 'contactName', 'phone', 'region', 'status', 'createdAt']
    const csvRows = [
      header.join(','),
      ...filteredRows.map((row) =>
        header
          .map((key) => {
            const value = String(row[key as keyof CustomerRow] ?? '')
            return `"${value.replace(/"/g, '""')}"`
          })
          .join(','),
      ),
    ]
    const blob = new Blob(['\ufeff' + csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'customers-export.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  const totalCount = filteredRows.length
  const activeCount = filteredRows.filter((item) => item.status === 'active').length
  const pendingCount = filteredRows.filter((item) => item.status === 'pending').length

  return (
    <div className="generated-runtime-page">
      {contextHolder}
      <Card className="generated-runtime-hero" bordered={false}>
        <div className="generated-runtime-hero-head">
          <div>
            <Typography.Title level={3}>客户管理</Typography.Title>
            <Typography.Paragraph>
              运行实体 `customer`，字段、查询条件和 CRUD 行为都已经接入生成运行时。
            </Typography.Paragraph>
            <Space wrap>
              <Tag>search</Tag>
              <Tag>create</Tag>
              <Tag>edit</Tag>
              <Tag>delete</Tag>
              <Tag>export</Tag>
            </Space>
          </div>
          <div className="generated-runtime-hero-mark">
            <UserOutlined />
          </div>
        </div>
        <Row gutter={[12, 12]} className="generated-runtime-stats">
          <Col xs={24} md={8}>
            <Card size="small" className="generated-runtime-stat-card">
              <Statistic title="当前结果" value={totalCount} suffix="条" />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card size="small" className="generated-runtime-stat-card">
              <Statistic title="活跃客户" value={activeCount} suffix="条" />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card size="small" className="generated-runtime-stat-card">
              <Statistic title="待跟进" value={pendingCount} suffix="条" />
            </Card>
          </Col>
        </Row>
      </Card>

      <Card className="generated-runtime-panel" title="查询条件">
        <div className="generated-runtime-search">
          <div className="generated-runtime-search-grid">
            <Input placeholder="客户名称" value={keyword} onChange={(event) => setKeyword(event.target.value)} />
            <Select allowClear placeholder="客户等级" value={levelFilter} options={LEVEL_OPTIONS} onChange={(value) => setLevelFilter(value)} />
            <Input placeholder="联系人" value={contactFilter} onChange={(event) => setContactFilter(event.target.value)} />
          </div>
          <div className="generated-runtime-action-group">
            <Button icon={<SearchOutlined />} type="primary" onClick={() => void handleSearch()}>
              查询
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => void handleReset()}>
              重置
            </Button>
          </div>
          <div className="generated-runtime-operation-group">
            <Button
              icon={<PlusOutlined />}
              type="primary"
              onClick={() => {
                setEditing(null)
                form.resetFields()
                form.setFieldsValue({
                  customerName: '',
                  level: 'A',
                  contactName: '',
                  phone: '',
                  region: '华东',
                  status: 'active',
                  createdAt: new Date().toISOString().slice(0, 10),
                })
                setModalOpen(true)
              }}
            >
              新增客户
            </Button>
            <Button icon={<DownloadOutlined />} onClick={handleExport}>
              导出结果
            </Button>
          </div>
        </div>
      </Card>

      <Card className="generated-runtime-panel" title="客户列表">
        {loading ? (
          <div className="generated-runtime-loading">
            <Spin />
          </div>
        ) : error ? (
          <Empty description={error} />
        ) : (
          <Table<CustomerRow>
            columns={columns}
            dataSource={filteredRows}
            pagination={{ pageSize: 8 }}
            rowKey="id"
            scroll={{ x: 'max-content' }}
          />
        )}
      </Card>

      <Modal
        title={editing ? `编辑客户：${editing.customerName}` : '新增客户'}
        open={modalOpen}
        confirmLoading={submitting}
        okText="保存"
        cancelText="取消"
        onCancel={() => {
          setModalOpen(false)
          setEditing(null)
        }}
        onOk={() => void form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={(values) => void handleSubmit(values)}>
          <Form.Item label="客户名称" name="customerName" rules={[{ required: true, message: '请输入客户名称' }]}>
            <Input placeholder="请输入客户名称" />
          </Form.Item>
          <Form.Item label="客户等级" name="level" rules={[{ required: true, message: '请选择客户等级' }]}>
            <Select options={LEVEL_OPTIONS} />
          </Form.Item>
          <Form.Item label="联系人" name="contactName" rules={[{ required: true, message: '请输入联系人' }]}>
            <Input placeholder="请输入联系人" />
          </Form.Item>
          <Form.Item
            label="手机号"
            name="phone"
            rules={[
              { required: true, message: '请输入手机号' },
              { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的 11 位手机号' },
            ]}
          >
            <Input placeholder="请输入手机号" />
          </Form.Item>
          <Form.Item label="所属区域" name="region">
            <Select options={REGION_OPTIONS} />
          </Form.Item>
          <Form.Item label="客户状态" name="status" rules={[{ required: true, message: '请选择客户状态' }]}>
            <Select options={STATUS_OPTIONS} />
          </Form.Item>
          <Form.Item label="创建时间" name="createdAt">
            <Input placeholder="YYYY-MM-DD" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
