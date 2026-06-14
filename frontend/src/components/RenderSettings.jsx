import { useState, useEffect } from 'react'

const SIZES = [16, 32, 64, 128, 256]
const PRESETS = [
  { label: 'RPG 32',    size: 32 },
  { label: 'Mobile 64', size: 64 },
  { label: 'HD 128',    size: 128 },
  { label: 'Src 256',   size: 256 },
]
const LS_OUTPUT_DIR = 'pixelforge_output_dir'
const LS_ORTHO_SCALE = 'pixelforge_ortho_scale'

export function RenderSettings({ meshFilename, onRenderStarted, onRenderAttempting, isRendering, disabled, onPreviewParamsChange }) {
  const [spriteSize, setSpriteSize] = useState(64)
  const [isAnimation, setIsAnimation] = useState(false)
  const [frameStart, setFrameStart] = useState(1)
  const [frameEnd, setFrameEnd] = useState(24)
  const [outputName, setOutputName] = useState('')
  const [outputDir, setOutputDir] = useState('')
  const [mergeSheets, setMergeSheets] = useState(false)
  const [bodyPart, setBodyPart] = useState('full')
  const [error, setError] = useState(null)
  const [isPosting, setIsPosting] = useState(false)
  const [supersample, setSupersample] = useState(1)
  const [orthoScale, setOrthoScale] = useState('')
  const [blendActions, setBlendActions] = useState([])
  const [selectedAction, setSelectedAction] = useState('')
  const [loadingActions, setLoadingActions] = useState(false)

  useEffect(() => {
    const saved = localStorage.getItem(LS_OUTPUT_DIR)
    if (saved) setOutputDir(saved)
    const savedOrtho = localStorage.getItem(LS_ORTHO_SCALE)
    if (savedOrtho) setOrthoScale(savedOrtho)
  }, [])

  useEffect(() => {
    if (!meshFilename || !meshFilename.toLowerCase().endsWith('.blend')) {
      setBlendActions([])
      setSelectedAction('')
      return
    }
    setLoadingActions(true)
    fetch(`/api/blend-info?filename=${encodeURIComponent(meshFilename)}`)
      .then(r => r.json())
      .then(data => {
        const actions = data.actions || []
        setBlendActions(actions)
        if (actions.length > 0) {
          setSelectedAction(actions[0].name)
          setFrameStart(actions[0].frame_start)
          setFrameEnd(actions[0].frame_end)
        } else {
          setSelectedAction('')
        }
      })
      .catch(() => { setBlendActions([]); setSelectedAction('') })
      .finally(() => setLoadingActions(false))
  }, [meshFilename])

  // Notify parent whenever the preview-relevant params change so it can re-fetch the 3D preview
  useEffect(() => {
    onPreviewParamsChange?.(selectedAction, bodyPart)
  }, [selectedAction, bodyPart]) // eslint-disable-line react-hooks/exhaustive-deps

  function handleActionChange(name) {
    setSelectedAction(name)
    const action = blendActions.find(a => a.name === name)
    if (action) {
      setFrameStart(action.frame_start)
      setFrameEnd(action.frame_end)
    }
  }

  function handleOutputDirChange(val) {
    setOutputDir(val)
    localStorage.setItem(LS_OUTPUT_DIR, val)
  }

  function handleOrthoScaleChange(val) {
    setOrthoScale(val)
    localStorage.setItem(LS_ORTHO_SCALE, val)
  }

  async function handleRender() {
    setError(null)
    if (isAnimation && frameEnd <= frameStart) {
      setError('End frame must be greater than start frame.')
      return
    }
    if (onRenderAttempting) onRenderAttempting()
    setIsPosting(true)
    try {
      const body = {
        sprite_size: spriteSize,
        supersample,
        mesh_path: meshFilename || null,
        name: outputName.trim() || 'sprite_sheet',
        output_dir: outputDir.trim() || null,
        merge_sheets: isAnimation && mergeSheets,
        body_part: bodyPart,
        action_name: selectedAction || null,
        ortho_scale: parseFloat(orthoScale) || 0,
      }
      if (isAnimation) {
        body.frame_start = frameStart
        body.frame_end = frameEnd
      }
      const res = await fetch('/api/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `Server error ${res.status}`)
      onRenderStarted(data.job_id, { isAnimation, frameStart, frameEnd, spriteSize, supersample, name: outputName.trim() || 'sprite_sheet', mergeSheets: isAnimation && mergeSheets, bodyPart })
    } catch (e) {
      const msg = e.message === 'Failed to fetch'
        ? 'Cannot reach the backend. Is the PixelForge Backend window open and running?'
        : e.message
      setError(msg)
    } finally {
      setIsPosting(false)
    }
  }

  const frameCount = isAnimation && frameEnd > frameStart ? frameEnd - frameStart + 1 : null

  return (
    <div
      className="panel"
      style={disabled ? { opacity: 0.4, pointerEvents: 'none' } : undefined}
    >
      <span className="eyebrow">Render Settings</span>

      {/* Preset strip */}
      <div className="preset-strip">
        {PRESETS.map(p => (
          <button
            key={p.size}
            onClick={() => setSpriteSize(p.size)}
            className={`preset-btn${spriteSize === p.size ? ' active' : ''}`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Sprite size */}
      <div className="pf-group">
        <span className="eyebrow">Sprite size (px)</span>
        <div className="seg seg-full">
          {SIZES.map(size => (
            <button
              key={size}
              onClick={() => setSpriteSize(size)}
              className={`seg-item${spriteSize === size ? ' active' : ''}`}
            >
              {size}
            </button>
          ))}
        </div>
        <span className="field-hint">
          Renders at {spriteSize}×{spriteSize}px.
          {supersample > 1 && ` (${spriteSize * supersample}px → ${spriteSize}px with super-sampling)`}
        </span>
      </div>

      {/* Super-sampling */}
      <div className="pf-group">
        <span className="eyebrow">Super-sampling</span>
        <div className="seg seg-full">
          {[1, 2, 4].map(n => (
            <button
              key={n}
              onClick={() => setSupersample(n)}
              className={`seg-item${supersample === n ? ' active' : ''}`}
            >
              {n === 1 ? 'Off' : `${n}×`}
            </button>
          ))}
        </div>
      </div>

      {/* Camera scale lock — keeps every animation in a set at the same size */}
      <div className="pf-group">
        <span className="eyebrow">Camera scale (lock)</span>
        <input
          type="number"
          min={0}
          step="0.1"
          placeholder="0 = auto-fit"
          value={orthoScale}
          onChange={e => handleOrthoScaleChange(e.target.value)}
          className="pf-input"
          style={{ width: 120 }}
        />
        <span className="field-hint">
          0 = auto-fit (scale varies per pose/scene). Set a fixed value (e.g. <code>8.6</code>) to
          lock the camera so every animation renders at the same size. Remembered between sessions.
        </span>
      </div>

      {/* Action selector — .blend files only */}
      {meshFilename && meshFilename.toLowerCase().endsWith('.blend') && (
        <div className="pf-group">
          <span className="eyebrow">Action</span>
          {loadingActions ? (
            <span className="field-hint">Reading actions…</span>
          ) : blendActions.length === 0 ? (
            <span className="field-hint">No actions found in this .blend file.</span>
          ) : (
            <>
              <select
                value={selectedAction}
                onChange={e => handleActionChange(e.target.value)}
                className="pf-select"
              >
                {blendActions.map(a => (
                  <option key={a.name} value={a.name}>{a.name}</option>
                ))}
              </select>
              {selectedAction && (() => {
                const a = blendActions.find(x => x.name === selectedAction)
                return a ? (
                  <span className="field-hint">
                    Frames {a.frame_start}–{a.frame_end} ({a.frame_end - a.frame_start + 1} frames)
                  </span>
                ) : null
              })()}
            </>
          )}
        </div>
      )}

      {/* Output mode */}
      <div className="pf-group">
        <span className="eyebrow">Output mode</span>
        <div className="seg seg-full" style={{ marginBottom: 10 }}>
          <button
            onClick={() => setIsAnimation(false)}
            className={`seg-item${!isAnimation ? ' active' : ''}`}
          >
            Single Frame
          </button>
          <button
            onClick={() => setIsAnimation(true)}
            className={`seg-item${isAnimation ? ' active' : ''}`}
          >
            Animation
          </button>
        </div>

        {isAnimation && (
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div>
              <span className="eyebrow" style={{ marginBottom: 4 }}>From frame</span>
              <input
                type="number"
                min={0}
                value={frameStart}
                onChange={e => setFrameStart(Number(e.target.value))}
                className="pf-input"
                style={{ width: 72, textAlign: 'center' }}
              />
            </div>
            <div>
              <span className="eyebrow" style={{ marginBottom: 4 }}>To frame</span>
              <input
                type="number"
                min={1}
                value={frameEnd}
                onChange={e => setFrameEnd(Number(e.target.value))}
                className="pf-input"
                style={{ width: 72, textAlign: 'center' }}
              />
            </div>
            {frameCount && (
              <span style={{ fontSize: '0.72em', color: 'var(--pf-mute)', paddingBottom: 6 }}>
                {frameCount} frames × 8 directions
              </span>
            )}
          </div>
        )}
      </div>

      {/* Body part */}
      <div className="pf-group">
        <span className="eyebrow">Body part</span>
        <div className="seg seg-full">
          {[
            { value: 'full',  label: 'Full body' },
            { value: 'upper', label: 'Upper' },
            { value: 'lower', label: 'Lower' },
            { value: 'split', label: 'Split' },
          ].map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setBodyPart(value)}
              className={`seg-item${bodyPart === value ? ' active' : ''}`}
            >
              {label}
            </button>
          ))}
        </div>
        {bodyPart !== 'full' && (
          <span className="field-hint">
            Requires <code>UpperBody</code> and <code>LowerBody</code> collections.
            {bodyPart === 'split' && ' Runs two passes (2× render time).'}
          </span>
        )}
      </div>

      {/* Output name */}
      <div className="pf-group">
        <span className="eyebrow">Output name (optional)</span>
        <input
          type="text"
          maxLength={40}
          placeholder="sprite_sheet"
          value={outputName}
          onChange={e => setOutputName(e.target.value)}
          className="pf-input"
        />
        <span className="field-hint">Names the output file(s). Defaults to <code>sprite_sheet</code>.</span>
      </div>

      {/* Output folder */}
      <div className="pf-group">
        <span className="eyebrow">Output folder (optional)</span>
        <input
          type="text"
          placeholder="e.g. C:\MyGame\assets\sprites"
          value={outputDir}
          onChange={e => handleOutputDirChange(e.target.value)}
          className="pf-input pf-input-mono"
          style={{ fontSize: '0.72em' }}
        />
        <span className="field-hint">Copies finished sheets here too. Remembered between sessions.</span>
      </div>

      {/* Merge sheets — animation mode only */}
      {isAnimation && (
        <div className="pf-group">
          <label
            style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}
            onClick={() => setMergeSheets(v => !v)}
          >
            <div className={`pf-toggle-track${mergeSheets ? ' on' : ''}`}>
              <div className="pf-toggle-thumb" />
            </div>
            <span style={{ fontSize: '0.85em' }}>Merge all 8 directions into one master sheet</span>
          </label>
          <span className="field-hint" style={{ marginLeft: 46 }}>
            Produces <code>{outputName.trim() || 'sprite_sheet'}_all.png</code> — 8 rows × num_frames columns.
          </span>
        </div>
      )}

      {/* Mesh info */}
      <div style={{ marginBottom: 12, fontSize: '0.72em', color: 'var(--pf-mute)' }}>
        Mesh: <span style={{ color: 'var(--pf-text)' }}>{meshFilename || '(test primitive)'}</span>
      </div>

      {error && (
        <div style={{
          marginBottom: 10,
          borderRadius: 'var(--pf-radius)',
          background: 'rgba(248,113,113,0.08)',
          border: '1px solid rgba(248,113,113,0.3)',
          padding: '8px 12px',
        }}>
          <p style={{ margin: '0 0 3px', fontSize: '0.85em', fontWeight: 600, color: 'var(--pf-err)' }}>
            Render failed to start
          </p>
          <p style={{ margin: 0, fontSize: '0.75em', color: 'rgba(248,113,113,0.8)' }}>{error}</p>
        </div>
      )}

      <button
        onClick={handleRender}
        disabled={isRendering || isPosting || disabled}
        className="btn-primary"
      >
        {isPosting ? 'Connecting…' : isRendering ? 'Rendering…' : isAnimation ? 'Render Animation' : 'Render Sprite Sheet'}
      </button>
    </div>
  )
}
