import { Button, Result } from 'antd'
import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <Result
      status="404"
      title="Page not found"
      subTitle="This part of RideFlow has not arrived yet."
      extra={<Link to="/"><Button type="primary">Back home</Button></Link>}
    />
  )
}

