import { useEffect } from 'react'
import { useJobStatus } from '../hooks/useJobStatus'

export function StatusBar({ jobId, onDone, onError }) {
  const status = useJobStatus(jobId)

  const isDone  = status?.status === 'done'
  const isError = status?.status === 'error'

  // Call callbacks in effects — never during render
  useEffect(() => {
    if (isDone && onDone) onDone()
  }, [isDone]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (isError && onError) onError(status?.error)
  }, [isError]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!jobId || !status) return null

  return (
    <div className={`rounded-lg px-4 py-3 text-sm flex items-center gap-3 ${
      isError
        ? 'bg-red-500/10 border border-red-500/30 text-red-400'
        : isDone
        ? 'bg-green-500/10 border border-green-500/30 text-green-400'
        : 'bg-violet-500/10 border border-violet-500/30 text-violet-300'
    }`}>
      {!isDone && !isError && (
        <span className="inline-block w-3 h-3 rounded-full bg-violet-400 animate-pulse shrink-0" />
      )}
      {isDone && <span className="shrink-0">✓</span>}
      {isError && <span className="shrink-0">✗</span>}
      <span>{isError ? (status.error || 'An error occurred.') : status.progress_msg}</span>
    </div>
  )
}
