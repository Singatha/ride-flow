import { EnvironmentOutlined } from '@ant-design/icons'
import { Descriptions, Space, Tag, Typography } from 'antd'

import type { Ride } from '../api/types'
import { rideStatusColour } from './ridePresentation'

export function RideSummary({ ride }: { ride: Ride }) {
  return (
    <Descriptions size="small" column={{ xs: 1, sm: 2 }}>
      <Descriptions.Item label="Status"><Tag color={rideStatusColour(ride.status)}>{ride.status.replaceAll('_', ' ')}</Tag></Descriptions.Item>
      <Descriptions.Item label="Type">{ride.ride_type}</Descriptions.Item>
      <Descriptions.Item label={<Space><EnvironmentOutlined />Pickup</Space>}>
        <Typography.Text code>{ride.pickup.latitude.toFixed(4)}, {ride.pickup.longitude.toFixed(4)}</Typography.Text>
      </Descriptions.Item>
      <Descriptions.Item label="Destination">
        <Typography.Text code>{ride.destination.latitude.toFixed(4)}, {ride.destination.longitude.toFixed(4)}</Typography.Text>
      </Descriptions.Item>
      <Descriptions.Item label="Estimate">{ride.currency} {ride.estimated_fare}</Descriptions.Item>
      <Descriptions.Item label="Trip">{ride.estimated_distance_km} km · {ride.estimated_duration_minutes} min</Descriptions.Item>
      {ride.driver && <Descriptions.Item label="Driver">{ride.driver.first_name} {ride.driver.last_name}</Descriptions.Item>}
      {ride.vehicle && <Descriptions.Item label="Vehicle">{ride.vehicle.color} {ride.vehicle.make} {ride.vehicle.model} · {ride.vehicle.license_plate}</Descriptions.Item>}
    </Descriptions>
  )
}
