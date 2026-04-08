import { useState, useEffect, useRef } from 'react'

export function useJobStatus(jobId) {
  const [status, setStatus] = useState(null)
  const intervalRef = useRef(null)

  useEffect(() => {
    setStatus(null) // always clear when jobId changes (prevents stale state on server restart)
    if (!jobId) return

    const poll = async () => {
      try {
        const res = await fetch(`/api/status/${jobId}`)
        if (!res.ok) return
        const data = await res.json()
        setStatus(data)
        if (data.status === 'done' || data.status === 'error') {
          clearInterval(intervalRef.current)
        }
      } catch {
        // Network error — keep polling
      }
    }

    poll() // immediate first check
    intervalRef.current = setInterval(poll, 2000)

    return () => clearInterval(intervalRef.current)
  }, [jobId])

  return status
}
