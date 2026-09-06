import { CheckCircleFilled, CloudServerOutlined, DeploymentUnitOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Card, Col, Row, Space, Tag, Typography } from 'antd'

import { getHealth } from '../api/health'

const { Title, Paragraph, Text } = Typography

export function HomePage() {
  const health = useQuery({ queryKey: ['health'], queryFn: ({ signal }) => getHealth(signal) })

  return (
    <main>
      <section className="hero">
        <Tag color="cyan" icon={<DeploymentUnitOutlined />}>Phase 4 · Ride lifecycle</Tag>
        <Title className="hero-title">Movement, thoughtfully engineered.</Title>
        <Paragraph className="hero-copy">
          RideFlow is a production-minded ride-sharing platform built one reliable domain at a time.
        </Paragraph>
        <Button type="primary" size="large" href="http://localhost:8000/docs">
          Explore the API
        </Button>
      </section>

      <Row gutter={[20, 20]} className="status-grid">
        <Col xs={24} md={12}>
          <Card title={<Space><CloudServerOutlined />API status</Space>} bordered={false}>
            {health.isPending && <Text type="secondary">Connecting to the RideFlow API…</Text>}
            {health.isSuccess && (
              <Alert
                type="success"
                showIcon
                icon={<CheckCircleFilled />}
                message="API online"
                description="Ride estimates, requests, assignment, trip transitions, and history are online."
              />
            )}
            {health.isError && (
              <Alert
                type="warning"
                showIcon
                message="API unavailable"
                description="Start the local stack with docker compose up --build."
              />
            )}
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="Foundation boundaries" bordered={false}>
            <Space wrap>
              <Tag>FastAPI</Tag><Tag>PostgreSQL</Tag><Tag>PostGIS</Tag>
              <Tag>React</Tag><Tag>TypeScript</Tag><Tag>Ant Design</Tag>
            </Space>
            <Paragraph className="card-copy">
              The API, database, and web client run as separate containers while the backend remains one modular deployment.
            </Paragraph>
          </Card>
        </Col>
      </Row>
    </main>
  )
}
