import { lazy, Suspense, type ReactNode } from 'react'
import { createBrowserRouter } from 'react-router-dom'

import { AppLayout } from '../components/AppLayout'
import { ProtectedRoute } from '../components/ProtectedRoute'

const HomePage = lazy(() => import('../pages/HomePage').then((module) => ({ default: module.HomePage })))
const DriverDashboardPage = lazy(() => import('../pages/DriverDashboardPage').then((module) => ({ default: module.DriverDashboardPage })))
const LoginPage = lazy(() => import('../pages/LoginPage').then((module) => ({ default: module.LoginPage })))
const NotFoundPage = lazy(() => import('../pages/NotFoundPage').then((module) => ({ default: module.NotFoundPage })))
const ProfilePage = lazy(() => import('../pages/ProfilePage').then((module) => ({ default: module.ProfilePage })))
const RegisterPage = lazy(() => import('../pages/RegisterPage').then((module) => ({ default: module.RegisterPage })))

function deferred(element: ReactNode) {
  return <Suspense fallback={null}>{element}</Suspense>
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: deferred(<HomePage />) },
      { path: 'login', element: deferred(<LoginPage />) },
      { path: 'register', element: deferred(<RegisterPage />) },
      {
        element: <ProtectedRoute />,
        children: [{ path: 'profile', element: deferred(<ProfilePage />) }],
      },
      {
        element: <ProtectedRoute allowedRoles={['DRIVER']} />,
        children: [{ path: 'driver', element: deferred(<DriverDashboardPage />) }],
      },
      { path: '*', element: deferred(<NotFoundPage />) },
    ],
  },
])
