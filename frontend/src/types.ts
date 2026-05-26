import type { ApiAction, ApiMethod, GeneratedPage, PageDsl, PageListData } from './api'

export type NewPageRouteState = {
  dsl?: PageDsl
}

export type SharedAppProps = {
  isPageListLoading: boolean
  pages: GeneratedPage[]
  pageListData: PageListData
  refreshPages: (pageNo?: number, pageSize?: number) => Promise<void>
}

export type PageProps = SharedAppProps

export type DataSourceMode = 'mock' | 'api'

export type ApiFormValues = {
  name: string
  entity: string
  method: ApiMethod
  path: string
  action: ApiAction
  status: 'draft' | 'published'
  requestSchemaText: string
  responseSchemaText: string
  mockDataText: string
}
