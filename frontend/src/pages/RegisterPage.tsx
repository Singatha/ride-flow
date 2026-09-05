import { useMutation } from '@tanstack/react-query'
import { Alert, Button, Card, Form, Input, Radio, Typography } from 'antd'
import { Link, Navigate, useNavigate } from 'react-router-dom'

import { register, type RegisterInput } from '../api/auth'
import { ApiError } from '../api/client'
import { useAuthStore } from '../stores/authStore'

export function RegisterPage() {
  const navigate = useNavigate()
  const status = useAuthStore((state) => state.status)
  const setSession = useAuthStore((state) => state.setSession)
  const mutation = useMutation({
    mutationFn: register,
    onSuccess: (session) => {
      setSession(session)
      navigate('/profile', { replace: true })
    },
  })

  if (status === 'authenticated') return <Navigate to="/profile" replace />

  return (
    <section className="auth-page">
      <Card className="auth-card auth-card-wide" bordered={false}>
        <Typography.Title level={2}>Create your account</Typography.Title>
        <Typography.Paragraph type="secondary">Start as a rider or prepare to drive with RideFlow.</Typography.Paragraph>
        {mutation.isError && (
          <Alert type="error" showIcon message={mutation.error instanceof ApiError ? mutation.error.message : 'Unable to register'} />
        )}
        <Form<RegisterInput>
          layout="vertical"
          requiredMark="optional"
          initialValues={{ role: 'RIDER' }}
          onFinish={(values) => mutation.mutate({
            ...values,
            phone_number: values.phone_number || undefined,
          })}
        >
          <Form.Item label="Account type" name="role" rules={[{ required: true }]}>
            <Radio.Group optionType="button" buttonStyle="solid" options={[{ label: 'Rider', value: 'RIDER' }, { label: 'Driver', value: 'DRIVER' }]} />
          </Form.Item>
          <div className="form-row">
            <Form.Item label="First name" name="first_name" rules={[{ required: true, whitespace: true }]}>
              <Input autoComplete="given-name" size="large" />
            </Form.Item>
            <Form.Item label="Last name" name="last_name" rules={[{ required: true, whitespace: true }]}>
              <Input autoComplete="family-name" size="large" />
            </Form.Item>
          </div>
          <Form.Item label="Email" name="email" rules={[{ required: true }, { type: 'email' }]}>
            <Input autoComplete="email" size="large" />
          </Form.Item>
          <Form.Item label="Phone number" name="phone_number" rules={[{ min: 7, max: 32 }]}>
            <Input autoComplete="tel" size="large" />
          </Form.Item>
          <Form.Item label="Password" name="password" extra="Use at least 12 characters." rules={[{ required: true }, { min: 12, max: 128 }]}>
            <Input.Password autoComplete="new-password" size="large" />
          </Form.Item>
          <Button block type="primary" htmlType="submit" size="large" loading={mutation.isPending}>Create account</Button>
        </Form>
        <Typography.Paragraph className="auth-switch">Already registered? <Link to="/login">Sign in</Link></Typography.Paragraph>
      </Card>
    </section>
  )
}
