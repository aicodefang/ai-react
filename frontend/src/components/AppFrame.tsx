import { ApiOutlined, AppstoreOutlined, ExperimentOutlined, LinkOutlined, ThunderboltFilled } from '@ant-design/icons'
import { Layout, Menu, Typography } from 'antd'
import type { ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

export function AppFrame({ children }: { children: ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()
  const selectedKey = location.pathname.startsWith('/page-apis')
    ? '/page-apis'
    : location.pathname.startsWith('/pages')
      ? '/pages'
      : location.pathname.startsWith('/apis')
        ? '/apis'
        : '/generator'

  return (
    <Layout className="admin-layout">
      <Layout.Sider className="admin-sider" width={248}>
        <div className="brand">
          <span className="mark">
            <ThunderboltFilled />
          </span>
          <div>
            <Typography.Text className="brand-title">AI 前端工厂</Typography.Text>
            <Typography.Text className="brand-subtitle">Generator Console</Typography.Text>
          </div>
        </div>
        <Menu
          className="side-menu"
          items={[
            { key: '/generator', icon: <ExperimentOutlined />, label: 'AI 生成工作台' },
            { key: '/pages', icon: <AppstoreOutlined />, label: '页面管理' },
            { key: '/page-apis', icon: <LinkOutlined />, label: '页面接口管理' },
            { key: '/apis', icon: <ApiOutlined />, label: '接口管理' },
          ]}
          mode="inline"
          selectedKeys={[selectedKey]}
          onClick={({ key }) => navigate(key)}
        />
      </Layout.Sider>
      <Layout>
        <Layout.Header className="admin-header" />
        <Layout.Content className="admin-content">{children}</Layout.Content>
      </Layout>
    </Layout>
  )
}
