import { useState, useEffect } from 'react'

const COLOR_OPTIONS = [
  { value: 0,  label: 'Off' },
  { value: 8,  label: '8' },
  { value: 16, label: '16' },
  { value: 32, label: '32' },
  { value: 64, label: '64' },
]

export function RefinementPanel({ disabled, onRefined }) {
  const [upscale, setUpscale]         = useState(false)
  const [colors, setColors]           = useState(0)
  const [dither, setDither]           = useState(false)
  const [running, setRunning]         = useState(false)
  const [error, setError]             = useState(null)
  const [success, setSuccess]         = useState(false)
  const [esrganAvailable, setEsrganAvailable] = useState(null) // null = checking

  useEffect(() => {
    fetch('/api/check-esrgan')
      .then(r => r.json())
      .then(d => setEsrganAvailable(d.available))
      .catch(() => setEsrganAvailable(false))
  }, [])

  const effectiveUpscale = upscale && esrganAvailable === true
  const nothingToDo = !effectiveUpscale && colors === 0

  async function handleRefine() {
    setError(null)
    setSuccess(false)
    setRunning(true)
    try {
      const res = await fetch('/api/refine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ upscale: effectiveUpscale, colors, dither }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Refinement failed')
      setSuccess(true)
      onRefined(`/api/output/${data.output}?t=${Date.now()}`)
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className={`bg-white/5 border border-white/10 rounded-xl p-5 transition-opacity ${disabled ? 'opacity-40 pointer-events-none' : ''}`}>
      <h2 className="text-lg font-semibold text-white mb-4">3. Refinement</h2>

      {/* Upscale toggle */}
      <div className={`flex items-center gap-3 mb-4 ${esrganAvailable === false ? 'opacity-50' : 'cursor-pointer'}`}>
        <div
          onClick={() => esrganAvailable && setUpscale(v => !v)}
          className={`w-10 h-5 rounded-full transition-colors shrink-0 ${upscale && esrganAvailable ? 'bg-violet-600' : 'bg-white/20'} ${esrganAvailable ? 'cursor-pointer' : 'cursor-not-allowed'}`}
        >
          <div className={`w-4 h-4 rounded-full bg-white mt-0.5 transition-transform ${upscale && esrganAvailable ? 'translate-x-5' : 'translate-x-0.5'}`} />
        </div>
        <div>
          <span className="text-sm text-white">Real-ESRGAN ×4 upscale</span>
          {esrganAvailable === false ? (
            <p className="text-xs text-amber-400">
              Binary not found —{' '}
              <a
                href="https://github.com/xinntao/Real-ESRGAN/releases"
                target="_blank"
                rel="noreferrer"
                className="underline hover:text-amber-300"
              >
                download realesrgan-ncnn-vulkan-*-windows.zip
              </a>
              {' '}and extract to <code className="font-mono">tools/realesrgan-ncnn-vulkan/</code>
            </p>
          ) : (
            <p className="text-xs text-white/40">Pixel art anime model — requires binary in tools/</p>
          )}
        </div>
      </div>

      {/* Palette colors */}
      <div className="mb-4">
        <p className="text-xs text-white/50 mb-2 uppercase tracking-wider">Palette colors</p>
        <div className="flex gap-2">
          {COLOR_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setColors(opt.value)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                colors === opt.value
                  ? 'bg-violet-600 border-violet-500 text-white'
                  : 'bg-white/5 border-white/20 text-white/60 hover:border-white/40 hover:text-white'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Dither (only shown when colors > 0) */}
      {colors > 0 && (
        <label className="flex items-center gap-3 mb-4 cursor-pointer">
          <input
            type="checkbox"
            checked={dither}
            onChange={e => setDither(e.target.checked)}
            className="w-4 h-4 accent-violet-500"
          />
          <span className="text-sm text-white/70">Floyd-Steinberg dithering</span>
        </label>
      )}

      {error && <p className="text-xs text-red-400 mb-3">{error}</p>}
      {success && <p className="text-xs text-green-400 mb-3">Refinement complete ✓</p>}

      <button
        onClick={handleRefine}
        disabled={running || nothingToDo || disabled}
        className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-lg text-sm transition-colors"
      >
        {running ? 'Refining...' : nothingToDo ? 'Enable upscale or palette to refine' : 'Refine'}
      </button>
    </div>
  )
}
