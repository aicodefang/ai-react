import { Navigate, Route, Routes } from 'react-router-dom'
import type { SharedAppProps } from '../types'

type AppRoutesProps = SharedAppProps & {
  ApiManagementPage: React.ComponentType
  GeneratedPageDetail: React.ComponentType<SharedAppProps>
  GeneratorPage: React.ComponentType<SharedAppProps>
  PageApiManagement: React.ComponentType<SharedAppProps>
  PageManagement: React.ComponentType<SharedAppProps>
}

export function AppRoutes({
  ApiManagementPage,
  GeneratedPageDetail,
  GeneratorPage,
  PageApiManagement,
  PageManagement,
  isPageListLoading,
  pageListData,
  pages,
  refreshPages,
}: AppRoutesProps) {
  const sharedProps = {
    isPageListLoading,
    pageListData,
    pages,
    refreshPages,
  }

  return (
    <Routes>
      <Route element={<Navigate replace to="/generator" />} path="/" />
      <Route element={<GeneratorPage {...sharedProps} />} path="/generator" />
      <Route element={<PageManagement {...sharedProps} />} path="/pages" />
      <Route element={<ApiManagementPage />} path="/apis" />
      <Route element={<PageApiManagement {...sharedProps} />} path="/page-apis" />
      <Route element={<PageApiManagement {...sharedProps} />} path="/page-apis/:pageId" />
      <Route element={<GeneratedPageDetail {...sharedProps} />} path="/pages/:pageId" />
      <Route element={<Navigate replace to="/generator" />} path="*" />
    </Routes>
  )
}
