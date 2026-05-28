import { DeleteOutlined, DownloadOutlined, EditOutlined, PlusOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Card, Empty, Form, Input, Modal, Popconfirm, Select, Space, Spin, Table, Tag, Typography, message } from 'antd'
import { useEffect, useState } from 'react'

type WarehouseRow = {
  id: string
  warehouseName: string
  warehouseType: string
  managerName: string
  phone: string
  city: string
  status: string
  createdAt: string
}

type WarehouseFormValues = Omit<WarehouseRow, 'id'>

const WarehouseTypeOptions = ['自营', '合作', '临时'].map((value) => ({ value, label: value }))
const StatusOptions = ['active', 'pending', 'disabled'].map((value) => ({ value, label: value }))

export function WarehouseGeneratedPage() {
  const [rows, setRows] = useState<WarehouseRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [warehouseNameFilter, setWarehouseNameFilter] = useState('')
  const [warehouseTypeFilter, setWarehouseTypeFilter] = useState<string | undefined>(undefined)
  const [modalOpen, setModalOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [editing, setEditing] = useState<WarehouseRow | null>(null)
  const [messageApi, contextHolder] = message.useMessage()
  const [form] = Form.useForm<WarehouseFormValues>()

  const loadRows = async (params?: { warehouseName: string | undefined; warehouseType: string | undefined }) => {
    setLoading(true)
    setError('')
    try {
      const search = new URLSearchParams()
      if (params?.warehouseName) search.set('warehouseName', params.warehouseName)
      if (params?.warehouseType) search.set('warehouseType', params.warehouseType)
      const response = await fetch(`/api/generated/warehouses${search.toString() ? `?${search.toString()}` : ''}`)
      const payload = await response.json()
      if (!response.ok || payload.code !== 0) {
        throw new Error(payload.message || '加载数据失败')
      }
      setRows(payload.data?.list ?? [])
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '加载数据失败')
      setRows([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadRows()
  }, [])

  const columns = [
    { title: '仓库名称', dataIndex: 'warehouseName', key: 'warehouseName' },
    { title: '仓库类型', dataIndex: 'warehouseType', key: 'warehouseType', render: (value: string) => <Tag color="blue">{value}</Tag> },
    { title: '负责人', dataIndex: 'managerName', key: 'managerName' },
    { title: '手机号', dataIndex: 'phone', key: 'phone' },
    { title: '所在城市', dataIndex: 'city', key: 'city' },
    { title: '客户状态', dataIndex: 'status', key: 'status', render: (value: string) => <Tag color="blue">{value}</Tag> },
    { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt' },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: WarehouseRow) => (
        <Space>
          <Button
            aria-label={`编辑${record.id}`}
            icon={<EditOutlined />}
            size="small"
            onClick={() => {
              setEditing(record)
              form.setFieldsValue({
                warehouseName: record.warehouseName,
                warehouseType: record.warehouseType,
                managerName: record.managerName,
                phone: record.phone,
                city: record.city,
                status: record.status,
                createdAt: record.createdAt,
              })
              setModalOpen(true)
            }}
          />
          <Popconfirm
            title="确认删除当前记录？"
            okText="删除"
            cancelText="取消"
            onConfirm={async () => {
              try {
                const response = await fetch(`/api/generated/warehouses/${record.id}`, { method: 'DELETE' })
                const payload = await response.json()
                if (!response.ok || payload.code !== 0) {
                  throw new Error(payload.message || '删除失败')
                }
                messageApi.success('删除成功')
                await loadRows({ warehouseName: warehouseNameFilter, warehouseType: warehouseTypeFilter })
              } catch (requestError) {
                messageApi.error(requestError instanceof Error ? requestError.message : '删除失败')
              }
            }}
          >
            <Button danger aria-label={`删除${record.id}`} icon={<DeleteOutlined />} size="small" />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const handleSearch = async () => {
    await loadRows({
      warehouseName: warehouseNameFilter, warehouseType: warehouseTypeFilter
    })
  }

  const handleReset = async () => {
    setWarehouseNameFilter('')
    setWarehouseTypeFilter(undefined)
    await loadRows()
  }

  const handleSubmit = async (values: WarehouseFormValues) => {
    setSubmitting(true)
    try {
      const targetUrl = editing ? `/api/generated/warehouses/${editing.id}` : '/api/generated/warehouses'
      const response = await fetch(targetUrl, {
        body: JSON.stringify(values),
        headers: { 'Content-Type': 'application/json' },
        method: editing ? 'PUT' : 'POST',
      })
      const payload = await response.json()
      if (!response.ok || payload.code !== 0) {
        throw new Error(payload.message || '保存失败')
      }
      messageApi.success(editing ? '更新成功' : '创建成功')
      setModalOpen(false)
      setEditing(null)
      form.resetFields()
      await loadRows({ warehouseName: warehouseNameFilter, warehouseType: warehouseTypeFilter })
    } catch (requestError) {
      messageApi.error(requestError instanceof Error ? requestError.message : '保存失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleExport = () => {
    if (!rows.length) {
      messageApi.warning('当前没有可导出的数据')
      return
    }
    const header = ['warehouseName', 'warehouseType', 'managerName', 'phone', 'city', 'status', 'createdAt']
    const csvRows = [
      header.join(','),
      ...rows.map((row) =>
        header
          .map((key) => {
            const value = String(row[key as keyof WarehouseRow] ?? '')
            return `"${value.replace(/"/g, '""')}"`
          })
          .join(','),
      ),
    ]
    const blob = new Blob(['\ufeff' + csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'warehouses-export.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="generated-runtime-page">
      {contextHolder}
      <Card className="generated-runtime-panel" title="仓库管理">
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Typography.Text>实体：warehouse</Typography.Text>
          <div className="generated-runtime-search">
            <div className="generated-runtime-search-grid">
            <Input placeholder="仓库名称" value={warehouseNameFilter} onChange={(event) => setWarehouseNameFilter(event.target.value)} />
            <Select allowClear placeholder="仓库类型" value={warehouseTypeFilter} options={WarehouseTypeOptions} onChange={(value) => setWarehouseTypeFilter(value)} />
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
                  warehouseName: '',
                  warehouseType: '自营',
                  managerName: '',
                  phone: '',
                  city: '',
                  status: 'active',
                  createdAt: new Date().toISOString().slice(0, 10),
                  })
                  setModalOpen(true)
                }}
              >
                新增数据
              </Button>
              <Button icon={<DownloadOutlined />} onClick={handleExport}>
                导出结果
              </Button>
            </div>
          </div>
          {loading ? (
            <div className="generated-runtime-loading">
              <Spin />
            </div>
          ) : error ? (
            <Empty description={error} />
          ) : (
            <Table<WarehouseRow>
              columns={columns}
              dataSource={rows}
              pagination={{ pageSize: 8 }}
              rowKey="id"
              scroll={{ x: 'max-content' }}
            />
          )}
        </Space>
      </Card>

      <Modal
        title={editing ? `编辑仓库管理` : `新增仓库管理`}
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
          <Form.Item label="仓库名称" name="warehouseName" rules={[{ required: true, message: '请输入仓库名称' }]}>
            <Input placeholder="请输入仓库名称" />
          </Form.Item>
          <Form.Item label="仓库类型" name="warehouseType" rules={[]}>
            <Select options={WarehouseTypeOptions} />
          </Form.Item>
          <Form.Item label="负责人" name="managerName" rules={[{ required: true, message: '请输入负责人' }]}>
            <Input placeholder="请输入负责人" />
          </Form.Item>
          <Form.Item label="手机号" name="phone" rules={[{ required: true, message: '请输入手机号' }, { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的 11 位手机号' }]}>
            <Input placeholder="请输入手机号" />
          </Form.Item>
          <Form.Item label="所在城市" name="city" rules={[]}>
            <Input placeholder="请输入所在城市" />
          </Form.Item>
          <Form.Item label="客户状态" name="status" rules={[{ required: true, message: '请输入客户状态' }]}>
            <Select options={StatusOptions} />
          </Form.Item>
          <Form.Item label="创建时间" name="createdAt" rules={[]}>
            <Input placeholder="请输入创建时间" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
