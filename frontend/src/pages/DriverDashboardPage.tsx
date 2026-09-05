import { AimOutlined, CarOutlined, PoweroffOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  Row,
  Select,
  Space,
  Tag,
  Typography,
  message,
} from 'antd'

import { ApiError } from '../api/client'
import {
  activateVehicle,
  createDriverProfile,
  createVehicle,
  getDriverProfile,
  listVehicles,
  setDriverAvailability,
  updateDriverLocation,
  type CreateDriverProfileInput,
  type CreateVehicleInput,
} from '../api/drivers'
import type { DriverProfile } from '../api/types'
import { useAuthStore } from '../stores/authStore'

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'The request could not be completed'
}

function ProfileSetup({ accessToken }: { accessToken: string }) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (input: CreateDriverProfileInput) => createDriverProfile(accessToken, input),
    onSuccess: (profile) => queryClient.setQueryData(['driver-profile'], profile),
  })

  return (
    <Card title="Complete driver onboarding" bordered={false}>
      <Typography.Paragraph type="secondary">
        Add your driving licence. An administrator must approve it before you can go online.
      </Typography.Paragraph>
      {mutation.isError && <Alert type="error" showIcon message={errorMessage(mutation.error)} />}
      <Form<CreateDriverProfileInput> layout="vertical" onFinish={(values) => mutation.mutate(values)}>
        <Form.Item label="Licence number" name="license_number" rules={[{ required: true, min: 3 }]}>
          <Input size="large" autoComplete="off" />
        </Form.Item>
        <Form.Item label="Licence expiry" name="license_expiry" rules={[{ required: true }]}>
          <Input size="large" type="date" />
        </Form.Item>
        <Button type="primary" htmlType="submit" loading={mutation.isPending}>Create driver profile</Button>
      </Form>
    </Card>
  )
}

function VehiclePanel({ accessToken, profile }: { accessToken: string; profile: DriverProfile }) {
  const queryClient = useQueryClient()
  const vehicles = useQuery({
    queryKey: ['driver-vehicles'],
    queryFn: () => listVehicles(accessToken),
  })
  const createMutation = useMutation({
    mutationFn: (input: CreateVehicleInput) => createVehicle(accessToken, input),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['driver-vehicles'] }),
  })
  const activateMutation = useMutation({
    mutationFn: (vehicleId: string) => activateVehicle(accessToken, vehicleId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['driver-vehicles'] }),
  })
  const canEdit = profile.status === 'OFFLINE'

  return (
    <Card title={<Space><CarOutlined />Vehicles</Space>} bordered={false}>
      {!canEdit && <Alert type="info" showIcon message="Go offline before changing vehicles." />}
      {vehicles.isError && <Alert type="error" showIcon message={errorMessage(vehicles.error)} />}
      <List
        loading={vehicles.isPending}
        dataSource={vehicles.data ?? []}
        locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No vehicles yet" /> }}
        renderItem={(vehicle) => (
          <List.Item
            actions={vehicle.is_active ? [<Tag color="green" key="active">Active</Tag>] : [
              <Button key="activate" disabled={!canEdit} loading={activateMutation.isPending} onClick={() => activateMutation.mutate(vehicle.id)}>Make active</Button>,
            ]}
          >
            <List.Item.Meta title={`${vehicle.year} ${vehicle.make} ${vehicle.model}`} description={`${vehicle.license_plate} · ${vehicle.color} · ${vehicle.category}`} />
          </List.Item>
        )}
      />
      {createMutation.isError && <Alert type="error" showIcon message={errorMessage(createMutation.error)} />}
      <Typography.Title level={4}>Add a vehicle</Typography.Title>
      <Form<CreateVehicleInput>
        layout="vertical"
        initialValues={{ category: 'STANDARD', year: new Date().getFullYear() }}
        disabled={!canEdit}
        onFinish={(values) => createMutation.mutate(values)}
      >
        <div className="form-row">
          <Form.Item label="Make" name="make" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="Model" name="model" rules={[{ required: true }]}><Input /></Form.Item>
        </div>
        <div className="vehicle-form-row">
          <Form.Item label="Year" name="year" rules={[{ required: true }]}><InputNumber min={1980} max={new Date().getFullYear() + 1} /></Form.Item>
          <Form.Item label="Colour" name="color" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="Licence plate" name="license_plate" rules={[{ required: true, min: 2 }]}><Input /></Form.Item>
          <Form.Item label="Category" name="category"><Select options={['STANDARD', 'PREMIUM', 'XL'].map((value) => ({ value, label: value }))} /></Form.Item>
        </div>
        <Button htmlType="submit" loading={createMutation.isPending}>Add vehicle</Button>
      </Form>
    </Card>
  )
}

export function DriverDashboardPage() {
  const accessToken = useAuthStore((state) => state.accessToken)!
  const queryClient = useQueryClient()
  const [messageApi, contextHolder] = message.useMessage()
  const profile = useQuery({
    queryKey: ['driver-profile'],
    queryFn: () => getDriverProfile(accessToken),
    retry: false,
  })
  const availability = useMutation({
    mutationFn: (online: boolean) => setDriverAvailability(accessToken, online),
    onSuccess: (updated) => queryClient.setQueryData(['driver-profile'], updated),
  })
  const location = useMutation({
    mutationFn: async () => {
      const position = await new Promise<GeolocationPosition>((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10_000,
        }),
      )
      return updateDriverLocation(accessToken, {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        heading: position.coords.heading,
        speed_kph: position.coords.speed === null ? null : position.coords.speed * 3.6,
        accuracy_m: position.coords.accuracy,
        recorded_at: new Date(position.timestamp).toISOString(),
      })
    },
    onSuccess: () => void messageApi.success('Current location published'),
  })

  if (profile.isPending) return <div className="centered-state">Loading driver workspace…</div>
  if (profile.error instanceof ApiError && profile.error.status === 404) {
    return <section className="driver-shell"><Typography.Title level={1}>Driver workspace</Typography.Title><ProfileSetup accessToken={accessToken} /></section>
  }
  if (profile.isError || !profile.data) return <Alert type="error" showIcon message="Unable to load the driver workspace" />

  const driver = profile.data
  const isOnline = driver.status !== 'OFFLINE'
  const verificationColour = driver.verification_status === 'APPROVED' ? 'green' : driver.verification_status === 'PENDING' ? 'gold' : 'red'

  return (
    <section className="driver-shell">
      {contextHolder}
      <div className="driver-heading">
        <div>
          <Typography.Title level={1}>Driver workspace</Typography.Title>
          <Typography.Paragraph type="secondary">Manage your availability, location, and vehicle.</Typography.Paragraph>
        </div>
        <Button
          type={isOnline ? 'default' : 'primary'}
          danger={isOnline}
          size="large"
          icon={<PoweroffOutlined />}
          loading={availability.isPending}
          onClick={() => availability.mutate(!isOnline)}
        >
          Go {isOnline ? 'offline' : 'online'}
        </Button>
      </div>
      {availability.isError && <Alert type="error" showIcon message={errorMessage(availability.error)} />}
      <Row gutter={[20, 20]} className="driver-overview">
        <Col xs={24} md={12}>
          <Card bordered={false} title="Driver status">
            <Descriptions column={1}>
              <Descriptions.Item label="Availability"><Tag color={isOnline ? 'green' : 'default'}>{driver.status}</Tag></Descriptions.Item>
              <Descriptions.Item label="Verification"><Tag color={verificationColour}>{driver.verification_status}</Tag></Descriptions.Item>
              <Descriptions.Item label="Licence">{driver.license_number}</Descriptions.Item>
              <Descriptions.Item label="Expires">{driver.license_expiry}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card bordered={false} title={<Space><AimOutlined />Location</Space>}>
            <Typography.Paragraph type="secondary">
              Publish a fresh GPS point before going online. Your browser will ask for location permission.
            </Typography.Paragraph>
            {!navigator.geolocation && <Alert type="warning" showIcon message="Geolocation is unavailable in this browser." />}
            <Button disabled={!navigator.geolocation} loading={location.isPending} onClick={() => location.mutate()}>Publish current location</Button>
            {location.isError && <Alert type="error" showIcon message={errorMessage(location.error)} />}
          </Card>
        </Col>
      </Row>
      <VehiclePanel accessToken={accessToken} profile={driver} />
    </section>
  )
}
