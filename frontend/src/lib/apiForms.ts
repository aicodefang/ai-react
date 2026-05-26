import type { ApiDefinition, ApiSchemaField } from '../api'
import type { ApiFormValues } from '../types'
import { stringifyJson } from './format'

export function parseApiSchema(text: string, label: string): ApiSchemaField[] {
  const trimmed = text.trim()
  if (!trimmed) return []

  let parsed: unknown
  try {
    parsed = JSON.parse(trimmed)
  } catch {
    throw new Error(`${label} 必须是合法 JSON`)
  }

  if (!Array.isArray(parsed)) {
    throw new Error(`${label} 必须是数组`)
  }

  return parsed.map((item, index) => {
    if (!item || typeof item !== 'object') {
      throw new Error(`${label} 第 ${index + 1} 项格式不正确`)
    }

    const field = item as Partial<ApiSchemaField>
    if (!field.name || !field.type) {
      throw new Error(`${label} 第 ${index + 1} 项缺少 name 或 type`)
    }

    return {
      name: String(field.name),
      type: field.type,
      required: Boolean(field.required),
    }
  })
}

export function parseMockData(text: string) {
  const trimmed = text.trim()
  if (!trimmed) return undefined

  try {
    return JSON.parse(trimmed)
  } catch {
    throw new Error('Mock 返回示例必须是合法 JSON')
  }
}

export function getApiFormInitialValues(api?: ApiDefinition | null): ApiFormValues {
  return {
    name: api?.name ?? '',
    entity: api?.entity ?? 'customer',
    method: api?.method ?? 'GET',
    path: api?.path ?? '/api/customers',
    action: api?.action ?? 'list',
    status: api?.status ?? 'draft',
    requestSchemaText: stringifyJson(api?.requestSchema ?? []),
    responseSchemaText: stringifyJson(api?.responseSchema ?? []),
    mockDataText: stringifyJson(api?.mockData),
  }
}
