import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Card, Empty, List, Space, Typography, message } from 'antd'

import {
  listAvailableRides,
  listMyRides,
  performDriverRideAction,
  type DriverRideAction,
} from '../api/rides'
import type { DriverProfile, Ride } from '../api/types'
import { isActiveRide } from './ridePresentation'
import { RideSummary } from './RideSummary'

const nextAction: Partial<Record<Ride['status'], { action: DriverRideAction; label: string }>> = {
  DRIVER_ASSIGNED: { action: 'arriving', label: 'Drive to pickup' },
  DRIVER_ARRIVING: { action: 'arrive', label: 'Mark arrived' },
  DRIVER_ARRIVED: { action: 'start', label: 'Start trip' },
  IN_PROGRESS: { action: 'complete', label: 'Complete trip' },
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'The request could not be completed'
}

export function DriverRidePanel({ accessToken, profile }: { accessToken: string; profile: DriverProfile }) {
  const queryClient = useQueryClient()
  const [messageApi, contextHolder] = message.useMessage()
  const assigned = useQuery({
    queryKey: ['my-rides'],
    queryFn: () => listMyRides(accessToken),
    refetchInterval: 5_000,
  })
  const available = useQuery({
    queryKey: ['available-rides'],
    queryFn: () => listAvailableRides(accessToken),
    enabled: profile.status === 'AVAILABLE',
    refetchInterval: 5_000,
  })
  const action = useMutation({
    mutationFn: ({ rideId, operation }: { rideId: string; operation: DriverRideAction }) => performDriverRideAction(accessToken, rideId, operation),
    onSuccess: () => {
      void Promise.all([
        queryClient.invalidateQueries({ queryKey: ['driver-profile'] }),
        queryClient.invalidateQueries({ queryKey: ['my-rides'] }),
        queryClient.invalidateQueries({ queryKey: ['available-rides'] }),
      ])
      void messageApi.success('Ride updated')
    },
  })
  const activeRide = assigned.data?.find(isActiveRide)
  const operation = activeRide ? nextAction[activeRide.status] : undefined

  return (
    <div className="driver-rides">
      {contextHolder}
      {action.isError && <Alert type="error" showIcon message={errorMessage(action.error)} />}
      {activeRide && (
        <Card bordered={false} title="Active ride">
          <RideSummary ride={activeRide} />
          {operation && <Button type="primary" size="large" loading={action.isPending} onClick={() => action.mutate({ rideId: activeRide.id, operation: operation.action })}>{operation.label}</Button>}
        </Card>
      )}
      <Card bordered={false} title="Open ride requests">
        {profile.status !== 'AVAILABLE' ? (
          <Alert type="info" showIcon message="Go online to view compatible ride requests." />
        ) : (
          <List
            loading={available.isPending}
            dataSource={available.data ?? []}
            locale={{ emptyText: <Empty description="No open requests" /> }}
            renderItem={(ride) => (
              <List.Item actions={[<Button type="primary" key="accept" loading={action.isPending} onClick={() => action.mutate({ rideId: ride.id, operation: 'accept' })}>Accept</Button>]}>
                <List.Item.Meta title={<Space><Typography.Text strong>{ride.ride_type} ride</Typography.Text><Typography.Text type="secondary">{ride.estimated_distance_km} km</Typography.Text></Space>} description={<RideSummary ride={ride} />} />
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  )
}
