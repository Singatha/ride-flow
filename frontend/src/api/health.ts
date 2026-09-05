export type HealthStatus = {
  status: 'ok' | 'ready'
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export async function getHealth(signal?: AbortSignal): Promise<HealthStatus> {
  const response = await fetch(`${apiBaseUrl.replace(/\/api\/v1\/?$/, '')}/health`, { signal })

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`)
  }

  return (await response.json()) as HealthStatus
}
