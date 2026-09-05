import { Result, Spin } from 'antd'
import { Navigate, Outlet, useLocation } from 'react-router-dom'

import type { UserRole } from '../api/types'
import { useAuthStore } from '../stores/authStore'

type ProtectedRouteProps = {
  allowedRoles?: UserRole[]
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const location = useLocation()
  const status = useAuthStore((state) => state.status)
  const user = useAuthStore((state) => state.user)

  if (status === 'checking') {
    return <div className="centered-state"><Spin size="large" /></div>
  }
  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  if (allowedRoles && (!user || !allowedRoles.includes(user.role))) {
    return <Result status="403" title="Driver access required" subTitle="This workspace is available to registered drivers." />
  }
  return <Outlet />
}
