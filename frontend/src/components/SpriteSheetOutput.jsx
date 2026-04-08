import { useState, useEffect, useRef } from 'react'

const DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']

export function SpriteSheetOutput({ spriteSheetUrl, refinedUrl, animationUrls, frameCount }) {
  const [selectedDir, setSelectedDir] = useState('S')
  const [currentFrame, setCurrentFrame] = useState(0)
  const [isPlaying, setIsPlaying] = useState(true)
  const [fps, setFps] = useState(8)
  const intervalRef = useRef(null)

  // Playback loop
  useEffect(() => {
    clearInterval(intervalRef.current)
    if (!animationUrls || !isPlaying || !frameCount) return
    intervalRef.current = setInterval(() => {
      setCurrentFrame(f => (f + 1) % frameCount)
    }, 1000 / fps)
    return () => clearInterval(intervalRef.current)
  }, [animationUrls, isPlaying, fps, frameCount])

  // Reset when new animation arrives
  useEffect(() => {
    if (animationUrls) {
      setSelectedDir('S')
      setCurrentFrame(0)
      setIsPlaying(true)
    }
  }, [animationUrls])

  // Reset frame on direction change
  useEffect(() => {
    setCurrentFrame(0)
  }, [selectedDir])

  if (!spriteSheetUrl && !refinedUrl && !animationUrls) return null

  // ── Animation mode ──────────────────────────────────────────────────────────
  if (animationUrls) {
    const selectedUrl = animationUrls[selectedDir]

    return (
      <div className="bg-white/5 border border-white/10 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">4. Output</h2>
          <span className="text-xs text-white/40">{frameCount} frames × 8 directions</span>
        </div>

        {/* Direction selector */}
        <div className="flex gap-1.5 mb-4 flex-wrap">
          {DIRECTIONS.map(dir => (
            <button
              key={dir}
              onClick={() => setSelectedDir(dir)}
              className={`px-3 py-1 rounded-lg text-sm font-medium border transition-colors ${
                selectedDir === dir
                  ? 'bg-violet-600 border-violet-500 text-white'
                  : 'bg-white/5 border-white/20 text-white/60 hover:border-white/40 hover:text-white'
              }`}
            >
              {dir}
            </button>
          ))}
        </div>

        {/* Preview + controls */}
        <div className="bg-[#1a1a2e] rounded-lg p-4 mb-3 flex gap-6 items-center flex-wrap">
          {/* Animated preview — clips to one frame at a time.
              Each frame in the sheet is square (spriteSize × spriteSize),
              so at 192px display height each frame is also 192px wide. */}
          <div>
            <p className="text-xs text-white/30 mb-2 text-center">Preview — {selectedDir}</p>
            <div style={{ width: 192, height: 192, overflow: 'hidden', position: 'relative', borderRadius: 8, background: 'rgba(255,255,255,0.03)' }}>
              <img
                src={selectedUrl}
                alt={`Direction ${selectedDir}`}
                style={{
                  imageRendering: 'pixelated',
                  height: '192px',
                  width: 'auto',
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  transform: `translateX(-${currentFrame * 192}px)`,
                }}
              />
            </div>
            <p className="text-xs text-white/20 mt-1.5 text-center">
              Frame {currentFrame + 1} / {frameCount}
            </p>
          </div>

          {/* Playback controls */}
          <div className="flex flex-col gap-3">
            <button
              onClick={() => setIsPlaying(p => !p)}
              className="px-4 py-2 rounded-lg text-sm font-medium border border-white/20 bg-white/5 text-white/70 hover:text-white hover:border-white/40 transition-colors"
            >
              {isPlaying ? '⏸ Pause' : '▶ Play'}
            </button>
            <div>
              <p className="text-xs text-white/40 mb-1">Speed: {fps} fps</p>
              <input
                type="range"
                min={1}
                max={24}
                value={fps}
                onChange={e => setFps(Number(e.target.value))}
                className="w-28 accent-violet-500"
              />
            </div>
          </div>
        </div>

        {/* Full strip for selected direction */}
        <div className="bg-[#1a1a2e] rounded-lg p-4 mb-3 overflow-x-auto">
          <p className="text-xs text-white/30 mb-2">Full strip — {selectedDir} ({frameCount} frames)</p>
          <img
            src={selectedUrl}
            alt={`Sprite sheet ${selectedDir}`}
            style={{ imageRendering: 'pixelated', height: '64px', width: 'auto', display: 'block' }}
            className="rounded"
          />
        </div>

        {/* Download one per direction */}
        <div>
          <p className="text-xs text-white/30 mb-2">Download</p>
          <div className="flex gap-2 flex-wrap">
            {DIRECTIONS.map(dir => (
              <a
                key={dir}
                href={animationUrls[dir]}
                download={`sprite_sheet_${dir}.png`}
                className="text-xs bg-white/5 hover:bg-white/10 border border-white/20 text-white/60 hover:text-white px-3 py-1.5 rounded-lg transition-colors"
              >
                ↓ {dir}
              </a>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // ── Single-frame mode ────────────────────────────────────────────────────────
  const activeUrl = refinedUrl || spriteSheetUrl
  const label     = refinedUrl ? 'Refined' : 'Sprite Sheet'

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">4. Output</h2>
        <a
          href={activeUrl}
          download={refinedUrl ? 'sprite_sheet_refined.png' : 'sprite_sheet.png'}
          className="text-xs bg-violet-600 hover:bg-violet-500 text-white px-3 py-1.5 rounded-lg transition-colors"
        >
          Download PNG
        </a>
      </div>

      <div className="bg-[#1a1a2e] rounded-lg p-4 mb-3 overflow-x-auto">
        <div style={{ width: 'max-content', minWidth: '100%' }}>
          <img
            src={activeUrl}
            alt="Sprite sheet"
            style={{ imageRendering: 'pixelated', height: '192px', width: 'auto', display: 'block' }}
            className="rounded"
          />
          <div className="flex mt-2">
            {DIRECTIONS.map(dir => (
              <div key={dir} className="flex-1 text-center text-xs text-white/30">{dir}</div>
            ))}
          </div>
        </div>
      </div>

      <p className="text-xs text-white/40 text-center">
        {label} — 8 directions, left to right: {DIRECTIONS.join(', ')}
      </p>

      {refinedUrl && spriteSheetUrl && (
        <div className="mt-4 pt-4 border-t border-white/10">
          <p className="text-xs text-white/40 mb-2">Original (pre-refinement):</p>
          <div className="bg-[#1a1a2e] rounded-lg p-4 overflow-x-auto">
            <img
              src={spriteSheetUrl}
              alt="Original sprite sheet"
              style={{ imageRendering: 'pixelated', height: '192px', width: 'auto', display: 'block' }}
              className="rounded opacity-70"
            />
          </div>
          <a
            href={spriteSheetUrl}
            download="sprite_sheet_original.png"
            className="mt-2 inline-block text-xs text-white/40 hover:text-white/70 transition-colors"
          >
            Download original
          </a>
        </div>
      )}
    </div>
  )
}
