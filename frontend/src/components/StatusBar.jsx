import { useEffect } from 'react'
import { useJobStatus } from '../hooks/useJobStatus'

export function StatusBar({ jobId, onDone, onError }) {
  const status = useJobStatus(jobId)

  const isDone  = status?.status === 'done'
  const isError = status?.status === 'error'

  useEffect(() => {
    if (isDone && onDone) onDone(status)
  }, [isDone]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (isError && onError) onError(status?.error)
  }, [isError]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!jobId || !status) return null

  const color = isError ? 'var(--pf-err)' : isDone ? 'var(--pf-good)' : 'var(--pf-accent)'
  const bg    = isError ? 'rgba(248,113,113,0.08)' : isDone ? 'rgba(52,211,153,0.08)' : 'rgba(139,92,246,0.08)'
  const bd    = isError ? 'rgba(248,113,113,0.25)' : isDone ? 'rgba(52,211,153,0.25)' : 'rgba(139,92,246,0.25)'

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '7px 10px',
      borderRadius: 'var(--pf-radius)',
      background: bg,
      border: `1px solid ${bd}`,
      fontSize: '0.8em',
      color,
    }}>
      {!isDone && !isError && (
        <span style={{
          display: 'inline-block', width: 7, height: 7, borderRadius: '50%',
          background: color, flexShrink: 0, animation: 'pulse 1.5s ease-in-out infinite',
        }} />
      )}
      {isDone  && <span style={{ flexShrink: 0 }}>✓</span>}
      {isError && <span style={{ flexShrink: 0 }}>✗</span>}
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {isError ? (status.error || status.progress_msg || 'An error occurred.') : status.progress_msg}
      </span>
    </div>
  )
}
