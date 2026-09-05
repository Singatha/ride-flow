import { CarOutlined } from '@ant-design/icons'
import { Layout, Space, Typography } from 'antd'
import { Link, Outlet } from 'react-router-dom'

const { Header, Content, Footer } = Layout

export function AppLayout() {
  return (
    <Layout className="app-shell">
      <Header className="app-header">
        <Link to="/" aria-label="RideFlow home">
          <Space size="middle">
            <span className="brand-mark"><CarOutlined /></span>
            <Typography.Title level={3} className="brand-name">RideFlow</Typography.Title>
          </Space>
        </Link>
      </Header>
      <Content className="app-content">
        <Outlet />
      </Content>
      <Footer className="app-footer">RideFlow · Built for learning real-world systems</Footer>
    </Layout>
  )
}

