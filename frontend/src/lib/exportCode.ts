import type { PageDsl } from '../api'
import { startCase } from './format'
import { getFieldPlaceholder } from './preview'

function buildExportColumns(dsl: PageDsl) {
  return dsl.fields
    .map((field) => {
      const renderSnippet =
        field.type === 'enum' ? ", render: (value) => <Tag color=\"blue\">{value}</Tag>" : ''
      return `    { title: '${field.label}', dataIndex: '${field.name}', key: '${field.name}'${renderSnippet} },`
    })
    .join('\n')
}

function buildExportFormFields(dsl: PageDsl) {
  return dsl.fields
    .slice(0, 3)
    .map((field) => {
      if (field.type === 'enum') {
        return `        <Form.Item label="${field.label}"><Select allowClear style={{ width: 160 }} placeholder="${getFieldPlaceholder(field)}" options={[${(field.options ?? [])
          .map((option) => `{ value: '${option}', label: '${option}' }`)
          .join(', ')}]} /></Form.Item>`
      }

      return `        <Form.Item label="${field.label}"><Input placeholder="${getFieldPlaceholder(field)}" /></Form.Item>`
    })
    .join('\n')
}

export function generateCode(dsl: PageDsl) {
  const exportColumns = buildExportColumns(dsl)
  const exportFormFields = buildExportFormFields(dsl)

  return [
    "import { Button, Form, Input, Modal, Popconfirm, Select, Space, Table, Tag } from 'antd'",
    "import { DeleteOutlined, EditOutlined, PlusOutlined, DownloadOutlined } from '@ant-design/icons'",
    '',
    `type TableRecord = { id: string; ${dsl.fields.map((field) => `${field.name}: string`).join('; ')} }`,
    '',
    `const columns = [`,
    exportColumns,
    ']',
    '',
    `// Generated from DSL: ${dsl.title}`,
    '// This is a simplified export artifact for the POC.',
    `export default function Generated${startCase(dsl.entity).replace(/\s+/g, '')}Page() {`,
    '  return (',
    '    <section>',
    `      <h1>${dsl.title}</h1>`,
    '      <Form layout="inline">',
    exportFormFields,
    '        <Button type="primary">查询</Button>',
    '        <Button>重置</Button>',
    '      </Form>',
    '      <Space style={{ margin: "16px 0" }}>',
    `        <Button type="primary" icon={<PlusOutlined />}>新增${dsl.title}</Button>`,
    '        <Button icon={<DownloadOutlined />}>导出</Button>',
    '      </Space>',
    '      <Table<TableRecord> rowKey="id" columns={columns} dataSource={[]} />',
    `      <Modal title="新增 / 编辑${dsl.title}" open={false}>`,
    '        <Form layout="vertical">',
    ...dsl.fields.map((field) => {
      if (field.type === 'enum') {
        return `          <Form.Item label="${field.label}" name="${field.name}"><Select options={[${(field.options ?? [])
          .map((option) => `{ value: '${option}', label: '${option}' }`)
          .join(', ')}]} /></Form.Item>`
      }
      const rules =
        field.type === 'phone'
          ? ` rules={[{ pattern: /^1[3-9]\\\\d{9}$/, message: '请输入有效的 11 位手机号' }]}`
          : ''
      return `          <Form.Item label="${field.label}" name="${field.name}"${rules}><Input /></Form.Item>`
    }),
    '        </Form>',
    '      </Modal>',
    `      <Popconfirm title="确认删除该${dsl.title}？"><Button danger icon={<DeleteOutlined />}>删除</Button></Popconfirm>`,
    '      <Button icon={<EditOutlined />}>编辑</Button>',
    `      <Tag color="blue">${dsl.pageType}</Tag>`,
    '    </section>',
    '  )',
    '}',
  ].join('\n')
}
