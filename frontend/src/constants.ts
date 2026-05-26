import type { ApiAction, ApiMethod } from './api'

export const initialPrompt =
  `请生成一个客户管理 CRUD 页面，页面实体必须是 customer。

请严格使用以下字段 key，不要改名：
- customerName：客户名称，string，必填
- level：客户等级，enum，可选值 A / B / C，必填
- contactName：联系人，string，必填
- phone：手机号，phone，必填
- region：所属区域，enum，可选值 华东 / 华北 / 华南 / 西南
- status：客户状态，enum，可选值 active / pending / disabled
- createdAt：创建时间，date

页面要求：
1. 查询区包含 customerName、level、contactName
2. 表格列必须展示 customerName、level、contactName、phone、region、status、createdAt
3. 支持查询、新增、编辑、删除、导出
4. 手机号需要校验
5. 客户等级必须限定为 A/B/C
6. 删除需要 customer:delete 权限
7. 输出字段名时必须与接口返回字段完全一致，尤其是 customerName 和 contactName，不能使用 name、customer、contact 等替代字段`

export const businessSpec = {
  permissions: ['customer:query', 'customer:create', 'customer:update', 'customer:delete', 'customer:export'],
  api: ['GET /api/customers', 'POST /api/customers', 'PUT /api/customers/:id', 'DELETE /api/customers/:id'],
}

export const apiMethodOptions: { label: ApiMethod; value: ApiMethod }[] = [
  { label: 'GET', value: 'GET' },
  { label: 'POST', value: 'POST' },
  { label: 'PUT', value: 'PUT' },
  { label: 'DELETE', value: 'DELETE' },
]

export const apiActionOptions: { label: string; value: ApiAction }[] = [
  { label: '列表查询', value: 'list' },
  { label: '新建', value: 'create' },
  { label: '编辑', value: 'update' },
  { label: '删除', value: 'delete' },
]

export const apiStatusOptions = [
  { label: '草稿', value: 'draft' },
  { label: '已发布', value: 'published' },
]
