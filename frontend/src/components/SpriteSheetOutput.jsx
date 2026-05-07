import { useState, useEffect, useRef } from 'react'

const DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']

// ── Split-body tab wrapper ───────────────────────────────────────────────────
function SplitSheetsOutput({ splitSheets, frameCount, spriteSize }) {
  const [activeTab, setActiveTab] = useState(0)
  const sheet = splitSheets[activeTab]

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">4. Output</h2>
        <span className="text-xs text-white/40">Split body — 2 sheets</span>
      </div>

      {/* Tab buttons */}
      <div className="flex gap-2 mb-4">
        {splitSheets.map((s, i) => (
          <button
            key={s.label}
            onClick={() => setActiveTab(i)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
              activeTab === i
                ? 'bg-violet-600 border-violet-500 text-white'
                : 'bg-white/5 border-white/20 text-white/60 hover:border-white/40 hover:text-white'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Render active sheet — _noChrome suppresses the outer card */}
      <SpriteSheetOutput
        key={sheet.label}
        spriteSheetUrl={sheet.spriteSheetUrl}
        refinedUrl={sheet.refinedUrl}
        animationUrls={sheet.animationUrls}
        refinedAnimationUrls={sheet.refinedAnimationUrls}
        mergedUrl={sheet.mergedUrl}
        refinedMergedUrl={sheet.refinedMergedUrl}
        frameCount={frameCount}
        spriteSize={spriteSize}
        spriteName={sheet.spriteName}
        _noChrome
      />
    </div>
  )
}

// ── Main component ───────────────────────────────────────────────────────────
export function SpriteSheetOutput({
  spriteSheetUrl, refinedUrl,
  animationUrls, refinedAnimationUrls,
  frameCount, spriteSize,
  spriteName = 'sprite_sheet',
  mergedUrl, refinedMergedUrl,
  splitSheets,
  _noChrome = false,
}) {
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

  if (!spriteSheetUrl && !refinedUrl && !animationUrls && !splitSheets) return null

  // ── Split-body mode ──────────────────────────────────────────────────────────
  if (splitSheets) {
    return <SplitSheetsOutput splitSheets={splitSheets} frameCount={frameCount} spriteSize={spriteSize} />
  }

  // ── Animation mode ───────────────────────────────────────────────────────────
  if (animationUrls) {
    const isRefined     = !!refinedAnimationUrls
    const activeUrls    = refinedAnimationUrls || animationUrls
    const selectedUrl   = activeUrls[selectedDir]
    const activeMergedUrl = refinedMergedUrl || mergedUrl

    const inner = (
      <>
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

        {/* Preview + playback controls */}
        <div className="bg-[#1a1a2e] rounded-lg p-4 mb-3 flex gap-6 items-center flex-wrap">
          <div>
            <p className="text-xs text-white/30 mb-2 text-center">
              {isRefined ? 'Refined' : 'Preview'} — {selectedDir}
            </p>
            <div
              style={{
                width: 192,
                height: 192,
                borderRadius: 8,
                backgroundColor: 'rgba(255,255,255,0.03)',
                imageRendering: 'pixelated',
                backgroundImage: `url("${selectedUrl}")`,
                backgroundSize: `${frameCount * 192}px 192px`,
                backgroundPosition: `-${currentFrame * 192}px 0px`,
                backgroundRepeat: 'no-repeat',
              }}
            />
            <p className="text-xs text-white/20 mt-1.5 text-center">
              Frame {currentFrame + 1} / {frameCount}
            </p>
          </div>
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
                type="range" min={1} max={24} value={fps}
                onChange={e => setFps(Number(e.target.value))}
                className="w-28 accent-violet-500"
              />
            </div>
          </div>
        </div>

        {/* Full strip */}
        <div className="bg-[#1a1a2e] rounded-lg p-4 mb-3 overflow-x-auto">
          <p className="text-xs text-white/30 mb-2">
            {isRefined ? 'Refined strip' : 'Full strip'} — {selectedDir} ({frameCount} frames)
          </p>
          <img
            src={selectedUrl}
            alt={`Sprite sheet ${selectedDir}`}
            style={{ imageRendering: 'pixelated', height: '64px', width: 'auto', display: 'block' }}
            className="rounded"
          />
        </div>

        {/* Original strip comparison — only after refinement */}
        {isRefined && (
          <div className="bg-[#1a1a2e] rounded-lg p-4 mb-3 overflow-x-auto">
            <p className="text-xs text-white/30 mb-2">Original — {selectedDir}</p>
            <img
              src={animationUrls[selectedDir]}
              alt={`Original sprite sheet ${selectedDir}`}
              style={{ imageRendering: 'pixelated', height: '64px', width: 'auto', display: 'block' }}
              className="rounded opacity-70"
            />
          </div>
        )}

        {/* Per-direction downloads */}
        <div>
          <p className="text-xs text-white/30 mb-2">Download per direction</p>
          <div className="flex gap-2 flex-wrap">
            {DIRECTIONS.map(dir => (
              <a
                key={dir}
                href={activeUrls[dir]}
                download={`${spriteName}_${dir}${isRefined ? '_refined' : ''}.png`}
                className="text-xs bg-white/5 hover:bg-white/10 border border-white/20 text-white/60 hover:text-white px-3 py-1.5 rounded-lg transition-colors"
              >
                ↓ {dir}
              </a>
            ))}
          </div>
        </div>

        {/* Merged master sheet */}
        {activeMergedUrl && (
          <div className="mt-4 pt-4 border-t border-white/10">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-white/50 uppercase tracking-wider">
                Master sheet{isRefined && refinedMergedUrl ? ' — Refined' : ' — all directions'}
              </p>
              <a
                href={activeMergedUrl}
                download={`${spriteName}_all${isRefined && refinedMergedUrl ? '_refined' : ''}.png`}
                className="text-xs bg-violet-600 hover:bg-violet-500 text-white px-3 py-1.5 rounded-lg transition-colors"
              >
                ↓ Download master sheet
              </a>
            </div>
            <div className="bg-[#1a1a2e] rounded-lg p-4 overflow-x-auto overflow-y-auto max-h-64">
              <p className="text-xs text-white/20 mb-2">8 rows (N → NW) × {frameCount} frames</p>
              <img
                src={activeMergedUrl}
                alt="Master sprite sheet"
                style={{ imageRendering: 'pixelated', height: 'auto', width: `${frameCount * (spriteSize || 64)}px`, minWidth: '100%', display: 'block' }}
                className="rounded"
              />
              <div className="mt-2 flex flex-col gap-0.5">
                {DIRECTIONS.map(d => (
                  <div key={d} className="text-xs text-white/20 leading-none" style={{ height: '8px' }}>{d}</div>
                ))}
              </div>
            </div>
            {/* Before/after comparison — shown only after refinement */}
            {isRefined && refinedMergedUrl && mergedUrl && (
              <div className="mt-3 bg-[#1a1a2e] rounded-lg p-4 overflow-x-auto overflow-y-auto max-h-64">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-white/20">Original master sheet</p>
                  <a
                    href={mergedUrl}
                    download={`${spriteName}_all_original.png`}
                    className="text-xs text-white/30 hover:text-white/60 transition-colors"
                  >
                    ↓ original
                  </a>
                </div>
                <img
                  src={mergedUrl}
                  alt="Original master sprite sheet"
                  style={{ imageRendering: 'pixelated', height: 'auto', width: `${frameCount * (spriteSize || 64)}px`, minWidth: '100%', display: 'block', opacity: 0.7 }}
                  className="rounded"
                />
              </div>
            )}
          </div>
        )}
      </>
    )

    if (_noChrome) return <div>{inner}</div>

    return (
      <div className="bg-white/5 border border-white/10 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-white">4. Output</h2>
            {isRefined && (
              <span className="text-xs bg-violet-600/30 border border-violet-500/40 text-violet-300 px-2 py-0.5 rounded-full">
                Refined
              </span>
            )}
          </div>
          <span className="text-xs text-white/40">{frameCount} frames × 8 directions</span>
        </div>
        {inner}
      </div>
    )
  }

  // ── Single-frame mode ────────────────────────────────────────────────────────
  const activeUrl = refinedUrl || spriteSheetUrl
  const label     = refinedUrl ? 'Refined' : 'Sprite Sheet'

  const singleInner = (
    <>
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
            download={`${spriteName}_original.png`}
            className="mt-2 inline-block text-xs text-white/40 hover:text-white/70 transition-colors"
          >
            Download original
          </a>
        </div>
      )}
    </>
  )

  if (_noChrome) return <div>{singleInner}</div>

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">4. Output</h2>
        <a
          href={activeUrl}
          download={refinedUrl ? `${spriteName}_refined.png` : `${spriteName}.png`}
          className="text-xs bg-violet-600 hover:bg-violet-500 text-white px-3 py-1.5 rounded-lg transition-colors"
        >
          Download PNG
        </a>
      </div>
      {singleInner}
    </div>
  )
}
