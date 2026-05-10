import { useState, useEffect } from 'react'

const SIZES = [16, 32, 64, 128, 256]
const LS_OUTPUT_DIR = 'pixelforge_output_dir'

export function RenderSettings({ meshFilename, onRenderStarted, onRenderAttempting, isRendering, disabled }) {
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
  const [blendActions, setBlendActions] = useState([])   // [{name, frame_start, frame_end}]
  const [selectedAction, setSelectedAction] = useState('')
  const [loadingActions, setLoadingActions] = useState(false)

  useEffect(() => {
    const saved = localStorage.getItem(LS_OUTPUT_DIR)
    if (saved) setOutputDir(saved)
  }, [])

  // Fetch action list whenever a .blend file is loaded
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

  async function handleRender() {
    setError(null)

    if (isAnimation && frameEnd <= frameStart) {
      setError('End frame must be greater than start frame.')
      return
    }

    // Immediately clear old job state so stale results never show
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
      // Network errors (backend not running) show as "Failed to fetch"
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
    <div className={`bg-white/5 border border-white/10 rounded-xl p-5 transition-opacity ${disabled ? 'opacity-40 pointer-events-none' : ''}`}>
      <h2 className="text-lg font-semibold text-white mb-4">2. Render Settings</h2>

      {/* Sprite size */}
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
          Renders at {spriteSize}×{spriteSize}px. Use larger sizes for higher detail.
        </p>
      </div>

      {/* Super-sampling */}
      <div className="mb-4">
        <p className="text-xs text-white/50 mb-2 uppercase tracking-wider">Super-sampling</p>
        <div className="flex gap-2">
          {[1, 2, 4].map(n => (
            <button
              key={n}
              onClick={() => setSupersample(n)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                supersample === n
                  ? 'bg-violet-600 border-violet-500 text-white'
                  : 'bg-white/5 border-white/20 text-white/60 hover:border-white/40 hover:text-white'
              }`}
            >
              {n === 1 ? 'Off' : `${n}×`}
            </button>
          ))}
        </div>
        {supersample > 1 && (
          <p className="text-xs text-white/30 mt-2">
            Blender renders at {spriteSize * supersample}px, assembled to {spriteSize}px — better quality for thin geometry.
          </p>
        )}
      </div>

      {/* Action selector — .blend files only */}
      {meshFilename && meshFilename.toLowerCase().endsWith('.blend') && (
        <div className="mb-4">
          <p className="text-xs text-white/50 mb-2 uppercase tracking-wider">Action</p>
          {loadingActions ? (
            <p className="text-xs text-white/30">Reading actions…</p>
          ) : blendActions.length === 0 ? (
            <p className="text-xs text-white/30">No actions found in this .blend file.</p>
          ) : (
            <>
              <select
                value={selectedAction}
                onChange={e => handleActionChange(e.target.value)}
                className="w-full bg-[#1a1a22] border border-white/20 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-violet-500 cursor-pointer"
              >
                {blendActions.map(a => (
                  <option key={a.name} value={a.name}>{a.name}</option>
                ))}
              </select>
              {selectedAction && (() => {
                const a = blendActions.find(x => x.name === selectedAction)
                return a ? (
                  <p className="text-xs text-white/30 mt-1.5">
                    Frames {a.frame_start}–{a.frame_end} ({a.frame_end - a.frame_start + 1} frames)
                  </p>
                ) : null
              })()}
            </>
          )}
        </div>
      )}

      {/* Output mode */}
      <div className="mb-4">
        <p className="text-xs text-white/50 mb-2 uppercase tracking-wider">Output mode</p>
        <div className="flex gap-2 mb-3">
          <button
            onClick={() => setIsAnimation(false)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
              !isAnimation
                ? 'bg-violet-600 border-violet-500 text-white'
                : 'bg-white/5 border-white/20 text-white/60 hover:border-white/40 hover:text-white'
            }`}
          >
            Single Frame
          </button>
          <button
            onClick={() => setIsAnimation(true)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
              isAnimation
                ? 'bg-violet-600 border-violet-500 text-white'
                : 'bg-white/5 border-white/20 text-white/60 hover:border-white/40 hover:text-white'
            }`}
          >
            Animation
          </button>
        </div>

        {isAnimation && (
          <div className="flex gap-4 items-end">
            <div>
              <p className="text-xs text-white/40 mb-1">From frame</p>
              <input
                type="number"
                min={0}
                value={frameStart}
                onChange={e => setFrameStart(Number(e.target.value))}
                className="w-20 bg-white/5 border border-white/20 rounded-lg px-3 py-1.5 text-sm text-white text-center focus:outline-none focus:border-violet-500"
              />
            </div>
            <div>
              <p className="text-xs text-white/40 mb-1">To frame</p>
              <input
                type="number"
                min={1}
                value={frameEnd}
                onChange={e => setFrameEnd(Number(e.target.value))}
                className="w-20 bg-white/5 border border-white/20 rounded-lg px-3 py-1.5 text-sm text-white text-center focus:outline-none focus:border-violet-500"
              />
            </div>
            {frameCount && (
              <p className="text-xs text-white/30 pb-2">{frameCount} frames × 8 directions</p>
            )}
          </div>
        )}
      </div>

      {/* Body part */}
      <div className="mb-4">
        <p className="text-xs text-white/50 mb-2 uppercase tracking-wider">Body part</p>
        <div className="flex gap-2 flex-wrap">
          {[
            { value: 'full',  label: 'Full body' },
            { value: 'upper', label: 'Upper only' },
            { value: 'lower', label: 'Lower only' },
            { value: 'split', label: 'Split (both)' },
          ].map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setBodyPart(value)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                bodyPart === value
                  ? 'bg-violet-600 border-violet-500 text-white'
                  : 'bg-white/5 border-white/20 text-white/60 hover:border-white/40 hover:text-white'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        {bodyPart !== 'full' && (
          <p className="text-xs text-white/30 mt-2">
            Requires <code className="text-white/40">UpperBody</code> and <code className="text-white/40">LowerBody</code> collections in the .blend file.
            {bodyPart === 'split' && ' Runs two passes — takes 2× render time.'}
          </p>
        )}
      </div>

      {/* Output name */}
      <div className="mb-4">
        <p className="text-xs text-white/50 mb-2 uppercase tracking-wider">Output name (optional)</p>
        <input
          type="text"
          maxLength={40}
          placeholder="sprite_sheet"
          value={outputName}
          onChange={e => setOutputName(e.target.value)}
          className="w-full bg-white/5 border border-white/20 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-violet-500 placeholder:text-white/20"
        />
        <p className="text-xs text-white/30 mt-1.5">Names the output file(s). Defaults to <code className="text-white/40">sprite_sheet</code>.</p>
      </div>

      {/* Output folder */}
      <div className="mb-4">
        <p className="text-xs text-white/50 mb-2 uppercase tracking-wider">Output folder (optional)</p>
        <input
          type="text"
          placeholder="e.g. C:\MyGame\assets\sprites"
          value={outputDir}
          onChange={e => handleOutputDirChange(e.target.value)}
          className="w-full bg-white/5 border border-white/20 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-violet-500 placeholder:text-white/20 font-mono"
        />
        <p className="text-xs text-white/30 mt-1.5">Copies finished sheets here too (e.g. your game asset repo). Remembered between sessions.</p>
      </div>

      {/* Merge sheets — animation mode only */}
      {isAnimation && (
        <div className="mb-4">
          <label className="flex items-center gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={mergeSheets}
              onChange={e => setMergeSheets(e.target.checked)}
              className="w-4 h-4 accent-violet-500 cursor-pointer"
            />
            <span className="text-sm text-white/70 group-hover:text-white transition-colors">
              Merge all 8 directions into one master sheet
            </span>
          </label>
          <p className="text-xs text-white/30 mt-1.5 ml-7">
            Produces <code className="text-white/40">{outputName.trim() || 'sprite_sheet'}_all.png</code> — 8 rows (N→NW) × num_frames columns. Ideal for engine import.
          </p>
        </div>
      )}

      <div className="mb-4 text-xs text-white/50">
        Mesh: <span className="text-white/80">{meshFilename || '(test primitive — humanoid capsule)'}</span>
      </div>

      {error && (
        <div className="mb-3 rounded-lg bg-red-500/15 border border-red-500/40 px-4 py-3">
          <p className="text-sm font-semibold text-red-400 mb-0.5">Render failed to start</p>
          <p className="text-xs text-red-300/80">{error}</p>
        </div>
      )}

      <button
        onClick={handleRender}
        disabled={isRendering || isPosting || disabled}
        className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-lg text-sm transition-colors"
      >
        {isPosting ? 'Connecting...' : isRendering ? 'Rendering...' : isAnimation ? 'Render Animation' : 'Render Sprite Sheet'}
      </button>
    </div>
  )
}
