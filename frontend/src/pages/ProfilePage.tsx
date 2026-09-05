import { useMutation, useQuery } from '@tanstack/react-query'
import { Alert, Button, Card, Descriptions, Form, Input, Skeleton, Typography, message } from 'antd'

import { getProfile, updateProfile, type UpdateProfileInput } from '../api/auth'
import { useAuthStore } from '../stores/authStore'

export function ProfilePage() {
  const accessToken = useAuthStore((state) => state.accessToken)!
  const cachedUser = useAuthStore((state) => state.user)
  const setUser = useAuthStore((state) => state.setUser)
  const [messageApi, contextHolder] = message.useMessage()
  const profile = useQuery({
    queryKey: ['profile'],
    queryFn: () => getProfile(accessToken),
    initialData: cachedUser ?? undefined,
  })
  const mutation = useMutation({
    mutationFn: (input: UpdateProfileInput) => updateProfile(accessToken, input),
    onSuccess: (user) => {
      setUser(user)
      void messageApi.success('Profile updated')
    },
  })

  if (profile.isPending) return <Skeleton active className="profile-shell" />
  if (profile.isError || !profile.data) return <Alert type="error" showIcon message="Unable to load your profile" />

  const user = profile.data
  return (
    <section className="profile-shell">
      {contextHolder}
      <Typography.Title level={1}>Your profile</Typography.Title>
      <Descriptions bordered column={{ xs: 1, sm: 2 }} className="profile-summary">
        <Descriptions.Item label="Email">{user.email}</Descriptions.Item>
        <Descriptions.Item label="Role">{user.role}</Descriptions.Item>
      </Descriptions>
      <Card bordered={false} title="Personal details">
        {mutation.isError && <Alert type="error" showIcon message="The profile could not be updated" />}
        <Form<UpdateProfileInput>
          layout="vertical"
          initialValues={{ first_name: user.first_name, last_name: user.last_name, phone_number: user.phone_number ?? undefined }}
          onFinish={(values) => mutation.mutate({
            ...values,
            phone_number: values.phone_number || null,
          })}
        >
          <div className="form-row">
            <Form.Item label="First name" name="first_name" rules={[{ required: true, whitespace: true }]}><Input size="large" /></Form.Item>
            <Form.Item label="Last name" name="last_name" rules={[{ required: true, whitespace: true }]}><Input size="large" /></Form.Item>
          </div>
          <Form.Item label="Phone number" name="phone_number" rules={[{ min: 7, max: 32 }]}><Input size="large" /></Form.Item>
          <Button type="primary" htmlType="submit" loading={mutation.isPending}>Save changes</Button>
        </Form>
      </Card>
    </section>
  )
}
