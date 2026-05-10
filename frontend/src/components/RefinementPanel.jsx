import { useState } from 'react'

const COLOR_OPTIONS = [
  { value: 0,  label: 'Off' },
  { value: 8,  label: '8' },
  { value: 16, label: '16' },
  { value: 32, label: '32' },
  { value: 64, label: '64' },
]

const DITHER_OPTIONS = [
  { value: 'none',  label: 'None' },
  { value: 'floyd', label: 'Floyd-Steinberg' },
  { value: 'bayer', label: 'Bayer' },
]

const POSTERIZE_OPTIONS = [
  { value: 0, label: 'Off' },
  { value: 2, label: '4 colours' },
  { value: 3, label: '8 colours' },
  { value: 4, label: '16 colours' },
]

export function RefinementPanel({ disabled, onRefined, onAnimationRefined, onSplitRefined, animConfig }) {
  const [upscale, setUpscale]           = useState(false)
  const [alphaCutoff, setAlphaCutoff]   = useState(16)
  const [colors, setColors]             = useState(0)
  const [ditherMode, setDitherMode]     = useState('none')
  const [posterizeBits, setPosterizeBits] = useState(0)
  const [outline, setOutline]           = useState(false)
  const [outlineColor, setOutlineColor] = useState('#000000')
  const [running, setRunning]           = useState(false)
  const [error, setError]               = useState(null)
  const [success, setSuccess]           = useState(false)

  const nothingToDo = !upscale && colors === 0 && !outline && posterizeBits === 0
  const isAnimation = !!animConfig?.isAnimation
  const isSplit     = animConfig?.bodyPart === 'split'
  const needsMerge  = isAnimation && !animConfig?.mergeSheets

  async function handleRefine() {
    setError(null)
    setSuccess(false)
    setRunning(true)
    try {
      const body = {
        upscale,
        colors,
        dither_mode:    ditherMode,
        alpha_cutoff:   alphaCutoff,
        outline,
        outline_color:  outlineColor,
        posterize_bits: posterizeBits,
        name:      animConfig?.name      || 'sprite_sheet',
        body_part: animConfig?.bodyPart  || 'full',
      }
      if (isAnimation) body.is_animation = true
      const res = await fetch('/api/refine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Refinement failed')
      setSuccess(true)
      if (isSplit) {
        onSplitRefined(data)
      } else if (isAnimation) {
        onAnimationRefined(data)
      } else {
        onRefined(`/api/output/${data.output}?t=${Date.now()}`)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className={`bg-white/5 border border-white/10 rounded-xl p-5 transition-opacity ${disabled ? 'opacity-40 pointer-events-none' : ''}`}>
      <h2 className="text-lg font-semibold text-white mb-4">3. Refinement</h2>

      {/* Quality pass toggle */}
      <div className="flex items-center gap-3 mb-4 cursor-pointer" onClick={() => setUpscale(v => !v)}>
        <div className={`w-10 h-5 rounded-full transition-colors shrink-0 ${upscale ? 'bg-violet-600' : 'bg-white/20'}`}>
          <div className={`w-4 h-4 rounded-full bg-white mt-0.5 transition-transform ${upscale ? 'translate-x-5' : 'translate-x-0.5'}`} />
        </div>
        <div>
          <span className="text-sm text-white">Pixel art refine</span>
          <p className="text-xs text-white/40">Internal ×4 pass — sharpens edges and flattens palette; output stays at render size</p>
        </div>
      </div>

      {/* Alpha cutoff slider */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-1">
          <p className="text-xs text-white/50 uppercase tracking-wider">Alpha cutoff</p>
          <span className="text-xs text-white/60 tabular-nums">{alphaCutoff}</span>
        </div>
        <input
          type="range"
          min={1} max={64} step={1}
          value={alphaCutoff}
          onChange={e => setAlphaCutoff(Number(e.target.value))}
          className="w-full accent-violet-500"
        />
        <p className="text-xs text-white/30 mt-1">Lower = keep more thin edges (sword blades); higher = cleaner but may drop fine detail</p>
      </div>

      {/* Posterize */}
      <div className="mb-4">
        <p className="text-xs text-white/50 mb-2 uppercase tracking-wider">Posterize</p>
        <div className="flex gap-2 flex-wrap">
          {POSTERIZE_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setPosterizeBits(opt.value)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                posterizeBits === opt.value
                  ? 'bg-violet-600 border-violet-500 text-white'
                  : 'bg-white/5 border-white/20 text-white/60 hover:border-white/40 hover:text-white'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Palette colors */}
      <div className="mb-4">
        <p className="text-xs text-white/50 mb-2 uppercase tracking-wider">Palette colors</p>
        <div className="flex gap-2 flex-wrap">
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

      {/* Dither mode — only shown when colors > 0 */}
      {colors > 0 && (
        <div className="mb-4">
          <p className="text-xs text-white/50 mb-2 uppercase tracking-wider">Dithering</p>
          <div className="flex gap-2">
            {DITHER_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => setDitherMode(opt.value)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                  ditherMode === opt.value
                    ? 'bg-violet-600 border-violet-500 text-white'
                    : 'bg-white/5 border-white/20 text-white/60 hover:border-white/40 hover:text-white'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Outline */}
      <div className="mb-4">
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => setOutline(v => !v)}>
          <div className={`w-10 h-5 rounded-full transition-colors shrink-0 ${outline ? 'bg-violet-600' : 'bg-white/20'}`}>
            <div className={`w-4 h-4 rounded-full bg-white mt-0.5 transition-transform ${outline ? 'translate-x-5' : 'translate-x-0.5'}`} />
          </div>
          <span className="text-sm text-white">Pixel outline</span>
        </div>
        {outline && (
          <div className="flex items-center gap-3 mt-2 ml-[52px]">
            <label className="text-xs text-white/50">Colour</label>
            <input
              type="color"
              value={outlineColor}
              onChange={e => setOutlineColor(e.target.value)}
              onClick={e => e.stopPropagation()}
              className="w-8 h-8 rounded cursor-pointer border border-white/20 bg-transparent"
            />
            <span className="text-xs text-white/40">{outlineColor}</span>
          </div>
        )}
      </div>

      {needsMerge && (
        <p className="text-xs text-amber-400 mb-3">
          Animation refinement requires "Merge 8-direction" to be enabled. Re-render with merge checked.
        </p>
      )}
      {error && <p className="text-xs text-red-400 mb-3">{error}</p>}
      {success && <p className="text-xs text-green-400 mb-3">Refinement complete ✓</p>}

      <button
        onClick={handleRefine}
        disabled={running || nothingToDo || disabled || needsMerge}
        className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-lg text-sm transition-colors"
      >
        {running
          ? (isSplit && isAnimation ? 'Refining split sheets...' : isSplit ? 'Refining both sheets...' : isAnimation ? 'Refining all sheets...' : 'Refining...')
          : nothingToDo
            ? 'Enable a refinement option'
            : isSplit && isAnimation ? 'Refine split sheets' : isSplit ? 'Refine both sheets' : isAnimation ? 'Refine all sheets' : 'Refine'}
      </button>
    </div>
  )
}
