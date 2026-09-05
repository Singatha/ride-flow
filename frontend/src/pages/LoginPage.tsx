import { useMutation } from '@tanstack/react-query'
import { Alert, Button, Card, Form, Input, Typography } from 'antd'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'

import { login, type LoginInput } from '../api/auth'
import { ApiError } from '../api/client'
import { useAuthStore } from '../stores/authStore'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const status = useAuthStore((state) => state.status)
  const setSession = useAuthStore((state) => state.setSession)
  const mutation = useMutation({
    mutationFn: login,
    onSuccess: (session) => {
      setSession(session)
      const destination = (location.state as { from?: string } | null)?.from ?? '/profile'
      navigate(destination, { replace: true })
    },
  })

  if (status === 'authenticated') return <Navigate to="/profile" replace />

  return (
    <section className="auth-page">
      <Card className="auth-card" bordered={false}>
        <Typography.Title level={2}>Welcome back</Typography.Title>
        <Typography.Paragraph type="secondary">Sign in to continue to RideFlow.</Typography.Paragraph>
        {mutation.isError && (
          <Alert type="error" showIcon message={mutation.error instanceof ApiError ? mutation.error.message : 'Unable to sign in'} />
        )}
        <Form<LoginInput> layout="vertical" requiredMark="optional" onFinish={(values) => mutation.mutate(values)}>
          <Form.Item label="Email" name="email" rules={[{ required: true }, { type: 'email' }]}>
            <Input autoComplete="email" size="large" />
          </Form.Item>
          <Form.Item label="Password" name="password" rules={[{ required: true }]}>
            <Input.Password autoComplete="current-password" size="large" />
          </Form.Item>
          <Button block type="primary" htmlType="submit" size="large" loading={mutation.isPending}>Sign in</Button>
        </Form>
        <Typography.Paragraph className="auth-switch">New to RideFlow? <Link to="/register">Create an account</Link></Typography.Paragraph>
      </Card>
    </section>
  )
}
