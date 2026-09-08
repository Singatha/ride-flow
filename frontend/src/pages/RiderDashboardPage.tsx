import { CarOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  Form,
  InputNumber,
  List,
  Row,
  Select,
  Space,
  Statistic,
  Typography,
  message,
} from 'antd'

import {
  cancelRide,
  estimateRide,
  listMyRides,
  requestRide,
  type RideRequestInput,
} from '../api/rides'
import { isActiveRide } from '../components/ridePresentation'
import { RideSummary } from '../components/RideSummary'
import { useAuthStore } from '../stores/authStore'

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'The request could not be completed'
}

const initialCoordinates = {
  pickup: { latitude: -26.2041, longitude: 28.0473 },
  destination: { latitude: -26.1076, longitude: 28.0567 },
  ride_type: 'STANDARD' as const,
}

export function RiderDashboardPage() {
  const accessToken = useAuthStore((state) => state.accessToken)!
  const queryClient = useQueryClient()
  const [messageApi, contextHolder] = message.useMessage()
  const rides = useQuery({
    queryKey: ['my-rides'],
    queryFn: () => listMyRides(accessToken),
    refetchInterval: 5_000,
  })
  const estimate = useMutation({
    mutationFn: (input: RideRequestInput) => estimateRide(accessToken, input),
  })
  const request = useMutation({
    mutationFn: (input: RideRequestInput) => requestRide(accessToken, input),
    onSuccess: (created) => {
      queryClient.setQueryData(['my-rides'], (current: typeof rides.data) => [
        created,
        ...(current ?? []),
      ])
      void messageApi.success('Ride requested')
    },
  })
  const cancellation = useMutation({
    mutationFn: (rideId: string) => cancelRide(accessToken, rideId),
    onSuccess: (cancelled) => queryClient.setQueryData(
      ['my-rides'],
      (current: typeof rides.data) => current?.map((ride) => ride.id === cancelled.id ? cancelled : ride),
    ),
  })
  const activeRide = rides.data?.find(isActiveRide)

  return (
    <section className="ride-shell">
      {contextHolder}
      <Typography.Title level={1}>Where are you going?</Typography.Title>
      <Typography.Paragraph type="secondary">
        Direct coordinates drive proximity matching today. Address search and routing providers can plug into this contract later.
      </Typography.Paragraph>
      <Row gutter={[20, 20]}>
        <Col xs={24} lg={14}>
          <Card bordered={false} title="Plan a ride">
            {activeRide && <Alert type="info" showIcon message="Finish or cancel your active ride before requesting another." />}
            {estimate.isError && <Alert type="error" showIcon message={errorMessage(estimate.error)} />}
            <Form<RideRequestInput>
              layout="vertical"
              initialValues={initialCoordinates}
              onFinish={(values) => estimate.mutate(values)}
            >
              <Typography.Title level={5}>Pickup</Typography.Title>
              <div className="coordinate-row">
                <Form.Item label="Latitude" name={['pickup', 'latitude']} rules={[{ required: true }]}><InputNumber min={-90} max={90} precision={6} /></Form.Item>
                <Form.Item label="Longitude" name={['pickup', 'longitude']} rules={[{ required: true }]}><InputNumber min={-180} max={180} precision={6} /></Form.Item>
              </div>
              <Typography.Title level={5}>Destination</Typography.Title>
              <div className="coordinate-row">
                <Form.Item label="Latitude" name={['destination', 'latitude']} rules={[{ required: true }]}><InputNumber min={-90} max={90} precision={6} /></Form.Item>
                <Form.Item label="Longitude" name={['destination', 'longitude']} rules={[{ required: true }]}><InputNumber min={-180} max={180} precision={6} /></Form.Item>
              </div>
              <Form.Item label="Ride type" name="ride_type"><Select options={['STANDARD', 'PREMIUM', 'XL'].map((value) => ({ value, label: value }))} /></Form.Item>
              <Button type="primary" htmlType="submit" loading={estimate.isPending} disabled={Boolean(activeRide)}>Get estimate</Button>
            </Form>
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card bordered={false} title={<Space><CarOutlined />Fare estimate</Space>}>
            {!estimate.data || !estimate.variables ? <Empty description="Enter your trip to calculate a fare" /> : (
              <>
                <Statistic title="Estimated fare" prefix={estimate.data.currency} value={estimate.data.estimated_fare} />
                <Typography.Paragraph>{estimate.data.estimated_distance_km} km · approximately {estimate.data.estimated_duration_minutes} minutes</Typography.Paragraph>
                <Typography.Paragraph type="secondary">{estimate.data.available_driver_count} compatible drivers currently within 5 km</Typography.Paragraph>
                {request.isError && <Alert type="error" showIcon message={errorMessage(request.error)} />}
                <Button type="primary" block loading={request.isPending} onClick={() => request.mutate(estimate.variables!)}>Request this ride</Button>
              </>
            )}
          </Card>
        </Col>
      </Row>
      <Card bordered={false} title="Your rides" className="ride-history-card">
        {rides.isError && <Alert type="error" showIcon message={errorMessage(rides.error)} />}
        <List
          loading={rides.isPending}
          dataSource={rides.data ?? []}
          locale={{ emptyText: <Empty description="No rides yet" /> }}
          renderItem={(ride) => (
            <List.Item actions={isActiveRide(ride) && ride.status !== 'IN_PROGRESS' ? [<Button danger key="cancel" loading={cancellation.isPending} onClick={() => cancellation.mutate(ride.id)}>Cancel ride</Button>] : []}>
              <List.Item.Meta title={`Ride ${ride.id.slice(0, 8)}`} description={<RideSummary ride={ride} />} />
            </List.Item>
          )}
        />
      </Card>
    </section>
  )
}
