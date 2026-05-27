import { DeleteOutlined, DownloadOutlined, EditOutlined, PlusOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Card, Empty, Form, Input, Modal, Popconfirm, Select, Space, Spin, Table, Tag, Typography, message } from 'antd'
import { useEffect, useState } from 'react'

type SupplierRow = {
  id: string
  supplierName: string
  supplierType: string
  contactName: string
  phone: string
  city: string
  cooperationStatus: string
  createdAt: string
}

type SupplierFormValues = Omit<SupplierRow, 'id'>

const SupplierTypeOptions = ['manufacturing', 'service', 'logistics', 'packaging'].map((value) => ({ value, label: value }))
const CooperationStatusOptions = ['active', 'pending', 'paused'].map((value) => ({ value, label: value }))

export function SupplierGeneratedPage() {
  const [rows, setRows] = useState<SupplierRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [supplierNameFilter, setSupplierNameFilter] = useState('')
  const [supplierTypeFilter, setSupplierTypeFilter] = useState<string | undefined>(undefined)
  const [contactNameFilter, setContactNameFilter] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [editing, setEditing] = useState<SupplierRow | null>(null)
  const [messageApi, contextHolder] = message.useMessage()
  const [form] = Form.useForm<SupplierFormValues>()

  const loadRows = async (params?: { supplierName: string | undefined; supplierType: string | undefined; contactName: string | undefined }) => {
    setLoading(true)
    setError('')
    try {
      const search = new URLSearchParams()
      if (params?.supplierName) search.set('supplierName', params.supplierName)
      if (params?.supplierType) search.set('supplierType', params.supplierType)
      if (params?.contactName) search.set('contactName', params.contactName)
      const response = await fetch(`/api/generated/suppliers${search.toString() ? `?${search.toString()}` : ''}`)
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
    { title: '供应商名称', dataIndex: 'supplierName', key: 'supplierName' },
    { title: '供应商类型', dataIndex: 'supplierType', key: 'supplierType', render: (value: string) => <Tag color="blue">{value}</Tag> },
    { title: '联系人', dataIndex: 'contactName', key: 'contactName' },
    { title: '手机号', dataIndex: 'phone', key: 'phone' },
    { title: '城市', dataIndex: 'city', key: 'city' },
    { title: '合作状态', dataIndex: 'cooperationStatus', key: 'cooperationStatus', render: (value: string) => <Tag color="blue">{value}</Tag> },
    { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt' },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: SupplierRow) => (
        <Space>
          <Button
            aria-label={`编辑${record.id}`}
            icon={<EditOutlined />}
            size="small"
            onClick={() => {
              setEditing(record)
              form.setFieldsValue({
                supplierName: record.supplierName,
                supplierType: record.supplierType,
                contactName: record.contactName,
                phone: record.phone,
                city: record.city,
                cooperationStatus: record.cooperationStatus,
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
                const response = await fetch(`/api/generated/suppliers/${record.id}`, { method: 'DELETE' })
                const payload = await response.json()
                if (!response.ok || payload.code !== 0) {
                  throw new Error(payload.message || '删除失败')
                }
                messageApi.success('删除成功')
                await loadRows({ supplierName: supplierNameFilter, supplierType: supplierTypeFilter, contactName: contactNameFilter })
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
      supplierName: supplierNameFilter, supplierType: supplierTypeFilter, contactName: contactNameFilter
    })
  }

  const handleReset = async () => {
    setSupplierNameFilter('')
    setSupplierTypeFilter(undefined)
    setContactNameFilter('')
    await loadRows()
  }

  const handleSubmit = async (values: SupplierFormValues) => {
    setSubmitting(true)
    try {
      const targetUrl = editing ? `/api/generated/suppliers/${editing.id}` : '/api/generated/suppliers'
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
      await loadRows({ supplierName: supplierNameFilter, supplierType: supplierTypeFilter, contactName: contactNameFilter })
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
    const header = ['supplierName', 'supplierType', 'contactName', 'phone', 'city', 'cooperationStatus', 'createdAt']
    const csvRows = [
      header.join(','),
      ...rows.map((row) =>
        header
          .map((key) => {
            const value = String(row[key as keyof SupplierRow] ?? '')
            return `"${value.replace(/"/g, '""')}"`
          })
          .join(','),
      ),
    ]
    const blob = new Blob(['\ufeff' + csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'suppliers-export.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="generated-runtime-page">
      {contextHolder}
      <Card className="generated-runtime-panel" title="供应商管理">
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Typography.Text>实体：supplier</Typography.Text>
          <div className="generated-runtime-search">
            <div className="generated-runtime-search-grid">
            <Input placeholder="供应商名称" value={supplierNameFilter} onChange={(event) => setSupplierNameFilter(event.target.value)} />
            <Select allowClear placeholder="供应商类型" value={supplierTypeFilter} options={SupplierTypeOptions} onChange={(value) => setSupplierTypeFilter(value)} />
            <Input placeholder="联系人" value={contactNameFilter} onChange={(event) => setContactNameFilter(event.target.value)} />
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
                  supplierName: '',
                  supplierType: 'manufacturing',
                  contactName: '',
                  phone: '',
                  city: '',
                  cooperationStatus: 'active',
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
            <Table<SupplierRow>
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
        title={editing ? `编辑供应商管理` : `新增供应商管理`}
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
          <Form.Item label="供应商名称" name="supplierName" rules={[{ required: true, message: '请输入供应商名称' }]}>
            <Input placeholder="请输入供应商名称" />
          </Form.Item>
          <Form.Item label="供应商类型" name="supplierType" rules={[{ required: true, message: '请输入供应商类型' }]}>
            <Select options={SupplierTypeOptions} />
          </Form.Item>
          <Form.Item label="联系人" name="contactName" rules={[{ required: true, message: '请输入联系人' }]}>
            <Input placeholder="请输入联系人" />
          </Form.Item>
          <Form.Item label="手机号" name="phone" rules={[{ required: true, message: '请输入手机号' }, { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的 11 位手机号' }]}>
            <Input placeholder="请输入手机号" />
          </Form.Item>
          <Form.Item label="城市" name="city" rules={[]}>
            <Input placeholder="请输入城市" />
          </Form.Item>
          <Form.Item label="合作状态" name="cooperationStatus" rules={[{ required: true, message: '请输入合作状态' }]}>
            <Select options={CooperationStatusOptions} />
          </Form.Item>
          <Form.Item label="创建时间" name="createdAt" rules={[]}>
            <Input placeholder="请输入创建时间" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
