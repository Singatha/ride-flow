import { CarOutlined } from '@ant-design/icons'
import { Button, Layout, Space, Typography } from 'antd'
import { Link, Outlet, useNavigate } from 'react-router-dom'

import { logout } from '../api/auth'
import { useAuthBootstrap } from '../app/useAuthBootstrap'
import { useAuthStore } from '../stores/authStore'

const { Header, Content, Footer } = Layout

export function AppLayout() {
  useAuthBootstrap()
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const status = useAuthStore((state) => state.status)
  const clearSession = useAuthStore((state) => state.clearSession)

  const signOut = async () => {
    try { await logout() } finally {
      clearSession()
      navigate('/')
    }
  }

  return (
    <Layout className="app-shell">
      <Header className="app-header">
        <Link to="/" aria-label="RideFlow home">
          <Space size="middle">
            <span className="brand-mark"><CarOutlined /></span>
            <Typography.Title level={3} className="brand-name">RideFlow</Typography.Title>
          </Space>
        </Link>
        <Space className="app-nav">
          {user ? (
            <>
              <Button type="text"><Link to="/profile">{user.first_name}</Link></Button>
              <Button onClick={() => void signOut()}>Sign out</Button>
            </>
          ) : status === 'anonymous' ? (
            <>
              <Button type="text"><Link to="/login">Sign in</Link></Button>
              <Button type="primary"><Link to="/register">Register</Link></Button>
            </>
          ) : null}
        </Space>
      </Header>
      <Content className="app-content">
        <Outlet />
      </Content>
      <Footer className="app-footer">RideFlow · Built for learning real-world systems</Footer>
    </Layout>
  )
}
