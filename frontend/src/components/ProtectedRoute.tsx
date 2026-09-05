import { Spin } from 'antd'
import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuthStore } from '../stores/authStore'

export function ProtectedRoute() {
  const location = useLocation()
  const status = useAuthStore((state) => state.status)

  if (status === 'checking') {
    return <div className="centered-state"><Spin size="large" /></div>
  }
  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}
