import { useState } from 'react'

const SIZES = [16, 32, 64, 128, 256]

export function RenderSettings({ meshFilename, onRenderStarted, isRendering, disabled }) {
  const [spriteSize, setSpriteSize] = useState(64)
  const [error, setError] = useState(null)

  async function handleRender() {
    setError(null)
    try {
      const res = await fetch('/api/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sprite_size: spriteSize,
          mesh_path: meshFilename || null,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Render request failed')
      onRenderStarted(data.job_id)
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className={`bg-white/5 border border-white/10 rounded-xl p-5 transition-opacity ${disabled ? 'opacity-40 pointer-events-none' : ''}`}>
      <h2 className="text-lg font-semibold text-white mb-4">2. Render Settings</h2>

      <div className="mb-4">
        <p className="text-xs text-white/50 mb-2 uppercase tracking-wider">Sprite size (px)</p>
        <div className="flex gap-2 flex-wrap">
          {SIZES.map(size => (
            <button
              key={size}
              onClick={() => setSpriteSize(size)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                spriteSize === size
                  ? 'bg-violet-600 border-violet-500 text-white'
                  : 'bg-white/5 border-white/20 text-white/60 hover:border-white/40 hover:text-white'
              }`}
            >
              {size}×{size}
            </button>
          ))}
        </div>
        <p className="text-xs text-white/30 mt-2">
          Blender renders at {spriteSize * 4}px internally, downscaled to {spriteSize}px output.
        </p>
      </div>

      <div className="mb-4 text-xs text-white/50">
        Mesh: <span className="text-white/80">{meshFilename || '(test primitive — humanoid capsule)'}</span>
      </div>

      {error && <p className="text-xs text-red-400 mb-3">{error}</p>}

      <button
        onClick={handleRender}
        disabled={isRendering || disabled}
        className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-lg text-sm transition-colors"
      >
        {isRendering ? 'Rendering...' : 'Render Sprite Sheet'}
      </button>
    </div>
  )
}
