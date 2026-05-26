export type FieldType = 'string' | 'enum' | 'phone' | 'date'
export type ApiFieldType = 'string' | 'number' | 'boolean' | 'date'
export type ApiMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'
export type ApiAction = 'list' | 'create' | 'update' | 'delete'

export type FieldSpec = {
  name: string
  label: string
  type: FieldType
  required?: boolean
  options?: string[]
}

export type PageDsl = {
  pageType: 'crud'
  entity: string
  title: string
  layout: 'filter-table-modal'
  features: string[]
  fields: FieldSpec[]
  rules: string[]
}

export type PreviewRecord = Record<string, string> & {
  id: string
}

export type ApiSchemaField = {
  name: string
  type: ApiFieldType
  required?: boolean
}

export type GeneratedPage = {
  id: string
  name: string
  entity: string
  route: string
  status: 'draft' | 'verified'
  createdAt: string
  dsl: PageDsl
}

export type PageListData = {
  list: GeneratedPage[]
  total: number
  pageNo: number
  pageSize: number
}

export type ApiDefinition = {
  id: string
  name: string
  entity: string
  method: ApiMethod
  path: string
  action: ApiAction
  requestSchema: ApiSchemaField[]
  responseSchema: ApiSchemaField[]
  mockData?: unknown
  status: 'draft' | 'published'
  createdAt: string
}

export type ApiListData = {
  list: ApiDefinition[]
  total: number
  pageNo: number
  pageSize: number
}

export type SaveApiRequest = Omit<ApiDefinition, 'id' | 'createdAt'>

export type PageApiBinding = {
  pageId: string
  listApiId?: string
  createApiId?: string
  updateApiId?: string
  deleteApiId?: string
  updatedAt?: string
}

export type RuntimeApiParams = Record<string, string | number | boolean | undefined | null>

export function buildRuntimePath(path: string, recordId?: string) {
  const trimmed = path.trim()
  if (!recordId) return trimmed
  if (trimmed.includes(':id')) return trimmed.replace(':id', encodeURIComponent(recordId))
  return trimmed
}

export type GenerateDslRequest = {
  prompt: string
}

type ApiResponse<T> = {
  code: number
  message: string
  data: T
}

async function request<T>(input: string, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  const payload = (await response.json()) as ApiResponse<T>

  if (!response.ok) {
    throw new Error(payload.message || `Request failed: ${response.status}`)
  }

  if (payload.code !== 0) {
    throw new Error(payload.message || 'Request failed')
  }

  return payload.data
}

export function listPages(pageNo = 1, pageSize = 10) {
  return request<PageListData>(`/api/pages?pageNo=${pageNo}&pageSize=${pageSize}`)
}

export function getPage(pageId: string) {
  return request<GeneratedPage>(`/api/pages/${pageId}`)
}

export function createPage(dsl: PageDsl) {
  return request<GeneratedPage>('/api/pages', {
    body: JSON.stringify({ dsl }),
    method: 'POST',
  })
}

export function deletePage(pageId: string) {
  return request<void>(`/api/pages/${pageId}`, {
    method: 'DELETE',
  })
}

export function generateDsl(prompt: string) {
  return request<PageDsl>('/api/dsl/generate', {
    body: JSON.stringify({ prompt } satisfies GenerateDslRequest),
    method: 'POST',
  })
}

export function listApis(pageNo = 1, pageSize = 10) {
  return request<ApiListData>(`/api/apis?pageNo=${pageNo}&pageSize=${pageSize}`)
}

export function createApi(payload: SaveApiRequest) {
  return request<ApiDefinition>('/api/apis', {
    body: JSON.stringify(payload),
    method: 'POST',
  })
}

export function updateApi(apiId: string, payload: SaveApiRequest) {
  return request<ApiDefinition>(`/api/apis/${apiId}`, {
    body: JSON.stringify(payload),
    method: 'PUT',
  })
}

export function removeApi(apiId: string) {
  return request<void>(`/api/apis/${apiId}`, {
    method: 'DELETE',
  })
}

export function getPageBindings(pageId: string) {
  return request<PageApiBinding>(`/api/pages/${pageId}/bindings`)
}

export function savePageBindings(pageId: string, payload: Omit<PageApiBinding, 'pageId' | 'updatedAt'>) {
  return request<PageApiBinding>(`/api/pages/${pageId}/bindings`, {
    body: JSON.stringify(payload),
    method: 'PUT',
  })
}

export function invokeRuntimeApi<T>(path: string, method: ApiMethod, options?: { body?: unknown; params?: RuntimeApiParams }) {
  const url = new URL(path, window.location.origin)
  if (options?.params) {
    Object.entries(options.params).forEach(([key, value]) => {
      if (value == null || value === '') return
      url.searchParams.set(key, String(value))
    })
  }

  return request<T>(url.pathname + url.search, {
    body: options?.body ? JSON.stringify(options.body) : undefined,
    method,
  })
}
