import { useEffect } from 'react'

import { refreshSession } from '../api/auth'
import { useAuthStore } from '../stores/authStore'

let pendingRefresh: ReturnType<typeof refreshSession> | null = null

function restoreSession() {
  pendingRefresh ??= refreshSession().finally(() => {
    pendingRefresh = null
  })
  return pendingRefresh
}

export function useAuthBootstrap() {
  const status = useAuthStore((state) => state.status)
  const accessTokenExpiresAt = useAuthStore((state) => state.accessTokenExpiresAt)
  const setSession = useAuthStore((state) => state.setSession)
  const clearSession = useAuthStore((state) => state.clearSession)

  useEffect(() => {
    if (status !== 'checking') return
    let active = true
    void restoreSession()
      .then((session) => { if (active) setSession(session) })
      .catch(() => { if (active) clearSession() })
    return () => { active = false }
  }, [clearSession, setSession, status])

  useEffect(() => {
    if (status !== 'authenticated' || accessTokenExpiresAt === null) return
    const refreshIn = Math.max(accessTokenExpiresAt - Date.now() - 60_000, 1_000)
    const timer = window.setTimeout(() => {
      void restoreSession().then(setSession).catch(clearSession)
    }, refreshIn)
    return () => window.clearTimeout(timer)
  }, [accessTokenExpiresAt, clearSession, setSession, status])
}
