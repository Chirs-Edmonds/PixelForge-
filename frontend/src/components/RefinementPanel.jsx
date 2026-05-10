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
  { value: 'floyd', label: 'Floyd-S' },
  { value: 'bayer', label: 'Bayer' },
]

const POSTERIZE_OPTIONS = [
  { value: 0, label: 'Off' },
  { value: 2, label: '4 col' },
  { value: 3, label: '8 col' },
  { value: 4, label: '16 col' },
]

function Toggle({ on, onChange, label, hint }) {
  return (
    <div
      style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer' }}
      onClick={() => onChange(!on)}
    >
      <div className={`pf-toggle-track${on ? ' on' : ''}`} style={{ marginTop: 1 }}>
        <div className="pf-toggle-thumb" />
      </div>
      <div>
        <span style={{ fontSize: '0.85em' }}>{label}</span>
        {hint && <span className="field-hint" style={{ marginTop: 2 }}>{hint}</span>}
      </div>
    </div>
  )
}

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
    <div
      className="panel"
      style={disabled ? { opacity: 0.4, pointerEvents: 'none' } : undefined}
    >
      <span className="eyebrow">Refinement</span>

      {/* Pixel art refine toggle */}
      <div className="pf-group">
        <Toggle
          on={upscale}
          onChange={setUpscale}
          label="Pixel art ×4 upscale"
          hint="Nearest-neighbour — preserves hard pixel edges"
        />
      </div>

      {/* Alpha cutoff */}
      <div className="pf-group">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <span className="eyebrow" style={{ marginBottom: 0 }}>Alpha cutoff</span>
          <span style={{ fontSize: '0.72em', color: 'var(--pf-mute)', fontVariantNumeric: 'tabular-nums' }}>
            {alphaCutoff}
          </span>
        </div>
        <input
          type="range"
          min={1} max={64} step={1}
          value={alphaCutoff}
          onChange={e => setAlphaCutoff(Number(e.target.value))}
          style={{ width: '100%', accentColor: 'var(--pf-accent)' }}
        />
        <span className="field-hint">Lower = keep more thin edges; higher = cleaner but may drop fine detail</span>
      </div>

      {/* Posterize */}
      <div className="pf-group">
        <span className="eyebrow">Posterize</span>
        <div className="seg seg-full">
          {POSTERIZE_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setPosterizeBits(opt.value)}
              className={`seg-item${posterizeBits === opt.value ? ' active' : ''}`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Palette colors */}
      <div className="pf-group">
        <span className="eyebrow">Palette colors</span>
        <div className="seg seg-full">
          {COLOR_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setColors(opt.value)}
              className={`seg-item${colors === opt.value ? ' active' : ''}`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Dither mode — only when colors > 0 */}
      {colors > 0 && (
        <div className="pf-group">
          <span className="eyebrow">Dithering</span>
          <div className="seg seg-full">
            {DITHER_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => setDitherMode(opt.value)}
                className={`seg-item${ditherMode === opt.value ? ' active' : ''}`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Outline */}
      <div className="pf-group">
        <Toggle
          on={outline}
          onChange={setOutline}
          label="Pixel outline"
        />
        {outline && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 8, marginLeft: 46 }}>
            <span style={{ fontSize: '0.72em', color: 'var(--pf-mute)' }}>Colour</span>
            <input
              type="color"
              value={outlineColor}
              onChange={e => setOutlineColor(e.target.value)}
              onClick={e => e.stopPropagation()}
              style={{
                width: 28, height: 28, borderRadius: 5, cursor: 'pointer',
                border: '1px solid var(--pf-border)', background: 'transparent', padding: 2,
              }}
            />
            <span style={{ fontSize: '0.72em', color: 'var(--pf-dim)', fontFamily: "'Geist Mono', monospace" }}>
              {outlineColor}
            </span>
          </div>
        )}
      </div>

      {needsMerge && (
        <p style={{ fontSize: '0.75em', color: 'var(--pf-warn)', margin: '0 0 10px' }}>
          Animation refinement requires "Merge 8-direction" to be enabled. Re-render with merge checked.
        </p>
      )}
      {error && (
        <p style={{ fontSize: '0.75em', color: 'var(--pf-err)', margin: '0 0 10px' }}>{error}</p>
      )}
      {success && (
        <p style={{ fontSize: '0.75em', color: 'var(--pf-good)', margin: '0 0 10px' }}>
          Refinement complete ✓
        </p>
      )}

      <button
        onClick={handleRefine}
        disabled={running || nothingToDo || disabled || needsMerge}
        className="btn-primary"
      >
        {running
          ? (isSplit && isAnimation ? 'Refining split sheets…' : isSplit ? 'Refining both sheets…' : isAnimation ? 'Refining all sheets…' : 'Refining…')
          : nothingToDo
            ? 'Enable a refinement option'
            : isSplit && isAnimation ? 'Refine split sheets' : isSplit ? 'Refine both sheets' : isAnimation ? 'Refine all sheets' : 'Refine'}
      </button>
    </div>
  )
}
