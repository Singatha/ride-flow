import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Card, Empty, Space, Statistic, message } from 'antd'

import {
  getCurrentRideOffer,
  listMyRides,
  performDriverRideAction,
  rejectRideOffer,
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
  const [currentTime, setCurrentTime] = useState<number | null>(null)
  useEffect(() => {
    const updateCurrentTime = () => setCurrentTime(Date.now())
    updateCurrentTime()
    const interval = window.setInterval(updateCurrentTime, 1_000)
    return () => window.clearInterval(interval)
  }, [])
  const assigned = useQuery({
    queryKey: ['my-rides'],
    queryFn: () => listMyRides(accessToken),
    refetchInterval: 5_000,
  })
  const activeRide = assigned.data?.find(isActiveRide)
  const offer = useQuery({
    queryKey: ['current-ride-offer'],
    queryFn: () => getCurrentRideOffer(accessToken),
    enabled: profile.status === 'AVAILABLE' && !activeRide,
    refetchInterval: 1_000,
  })
  const action = useMutation({
    mutationFn: ({ rideId, operation }: { rideId: string; operation: DriverRideAction }) => performDriverRideAction(accessToken, rideId, operation),
    onSuccess: () => {
      void Promise.all([
        queryClient.invalidateQueries({ queryKey: ['driver-profile'] }),
        queryClient.invalidateQueries({ queryKey: ['my-rides'] }),
        queryClient.invalidateQueries({ queryKey: ['current-ride-offer'] }),
      ])
      void messageApi.success('Ride updated')
    },
  })
  const rejection = useMutation({
    mutationFn: (rideId: string) => rejectRideOffer(accessToken, rideId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['current-ride-offer'] })
      void messageApi.info('Offer declined')
    },
  })
  const operation = activeRide ? nextAction[activeRide.status] : undefined
  const currentOffer = offer.data
  const secondsRemaining = currentOffer && currentTime !== null
    ? Math.max(0, Math.ceil((Date.parse(currentOffer.expires_at) - currentTime) / 1_000))
    : 0
  const offerDistanceKm = currentOffer
    ? (Number(currentOffer.distance_m) / 1_000).toFixed(2)
    : null

  return (
    <div className="driver-rides">
      {contextHolder}
      {action.isError && <Alert type="error" showIcon message={errorMessage(action.error)} />}
      {rejection.isError && <Alert type="error" showIcon message={errorMessage(rejection.error)} />}
      {activeRide && (
        <Card bordered={false} title="Active ride">
          <RideSummary ride={activeRide} />
          {operation && <Button type="primary" size="large" loading={action.isPending} onClick={() => action.mutate({ rideId: activeRide.id, operation: operation.action })}>{operation.label}</Button>}
        </Card>
      )}
      <Card bordered={false} title="Current ride offer">
        {profile.status !== 'AVAILABLE' ? (
          <Alert type="info" showIcon message="Go online to receive nearby ride offers." />
        ) : activeRide ? (
          <Alert type="info" showIcon message="Complete your active ride before receiving another offer." />
        ) : currentOffer ? (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Space wrap size="large">
              <Statistic title="Pickup distance" value={offerDistanceKm ?? '0.00'} suffix="km" />
              <Statistic title="Respond within" value={secondsRemaining} suffix="seconds" />
            </Space>
            <RideSummary ride={currentOffer.ride} />
            <Space>
              <Button
                type="primary"
                size="large"
                loading={action.isPending}
                disabled={secondsRemaining === 0 || rejection.isPending}
                onClick={() => action.mutate({ rideId: currentOffer.ride.id, operation: 'accept' })}
              >
                Accept ride
              </Button>
              <Button
                size="large"
                loading={rejection.isPending}
                disabled={secondsRemaining === 0 || action.isPending}
                onClick={() => rejection.mutate(currentOffer.ride.id)}
              >
                Decline
              </Button>
            </Space>
          </Space>
        ) : (
          <Empty description={offer.isPending ? 'Checking for nearby requests…' : 'No ride offer right now'} />
        )}
      </Card>
    </div>
  )
}
