import { Tag } from 'antd'
import type { ApiDefinition, FieldSpec, PageDsl, PreviewRecord } from '../api'

export function getFieldPlaceholder(field: FieldSpec) {
  return field.type === 'enum' ? `请选择${field.label}` : `请输入${field.label}`
}

function getSampleValue(field: FieldSpec, rowIndex: number) {
  if (field.options?.length) {
    return field.options[rowIndex % field.options.length]
  }

  if (field.type === 'phone') {
    return `1380000${String(120 + rowIndex).padStart(4, '0')}`
  }

  if (field.type === 'date') {
    return `2026-05-${String(12 + rowIndex).padStart(2, '0')}`
  }

  if (/status|state/i.test(field.name)) {
    return ['进行中', '待处理', '已完成'][rowIndex % 3]
  }

  if (/region|area|zone/i.test(field.name)) {
    return ['华东', '华南', '华北'][rowIndex % 3]
  }

  return `${field.label}${rowIndex + 1}`
}

export function createPreviewRows(dsl: PageDsl): PreviewRecord[] {
  return Array.from({ length: 3 }, (_, index) => {
    const row: PreviewRecord = {
      id: `${dsl.entity}-${index + 1}`,
    }

    dsl.fields.forEach((field) => {
      row[field.name] = getSampleValue(field, index)
    })

    return row
  })
}

export function normalizePreviewRecord(raw: Record<string, unknown>, dsl: PageDsl, fallbackId: string): PreviewRecord {
  return dsl.fields.reduce<PreviewRecord>(
    (accumulator, field) => {
      const rawValue = raw[field.name]
      accumulator[field.name] = rawValue == null ? '' : String(rawValue)
      return accumulator
    },
    {
      id: raw.id == null ? fallbackId : String(raw.id),
    },
  )
}

export function resolveMockRowsFromApi(apiDefinition: ApiDefinition | undefined, dsl: PageDsl): PreviewRecord[] | null {
  if (!apiDefinition?.mockData) return null

  const source = apiDefinition.mockData
  const candidateList = Array.isArray(source)
    ? source
    : typeof source === 'object' && source !== null && Array.isArray((source as { list?: unknown }).list)
      ? ((source as { list: unknown[] }).list ?? [])
      : null

  if (!candidateList) {
    return null
  }

  return candidateList
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object' && !Array.isArray(item))
    .map((item, index) => normalizePreviewRecord(item, dsl, `${dsl.entity}-mock-${index + 1}`))
}

export function extractListRows(payload: unknown): Record<string, unknown>[] {
  if (Array.isArray(payload)) {
    return payload.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object' && !Array.isArray(item))
  }

  if (payload && typeof payload === 'object') {
    const candidateList = (payload as { list?: unknown }).list
    if (Array.isArray(candidateList)) {
      return candidateList.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object' && !Array.isArray(item))
    }
  }

  return []
}

export function renderFieldValue(field: FieldSpec, value?: string) {
  if (!value) return '-'
  if (field.type === 'enum') {
    const color =
      /status|state/i.test(field.name)
        ? ['green', 'orange', 'red'][Math.abs(value.length) % 3]
        : 'blue'

    return <Tag color={color}>{value}</Tag>
  }

  return value
}
