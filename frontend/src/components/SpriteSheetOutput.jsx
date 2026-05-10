import { useState, useEffect, useRef } from 'react'

const DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']

// Direction compass layout: 3×3 grid, centre is null
const WHEEL = [
  ['NW', 'N',  'NE'],
  ['W',  null, 'E' ],
  ['SW', 'S',  'SE'],
]

function DirWheel({ selectedDir, onSelect }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 34px)', gap: 3 }}>
      {WHEEL.flat().map((dir, i) =>
        dir === null ? (
          <div key={i} />
        ) : (
          <button
            key={dir}
            onClick={() => onSelect(dir)}
            style={{
              width: 34, height: 34,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              border: '1px solid',
              borderColor: selectedDir === dir ? 'var(--pf-accent)' : 'var(--pf-border)',
              background: selectedDir === dir ? 'var(--pf-accent-dim)' : 'var(--pf-panel-2)',
              color: selectedDir === dir ? 'var(--pf-accent)' : 'var(--pf-mute)',
              borderRadius: 6,
              cursor: 'pointer',
              fontSize: '0.65em',
              fontWeight: 700,
              letterSpacing: '0.04em',
              transition: 'all 0.15s',
            }}
          >
            {dir}
          </button>
        )
      )}
    </div>
  )
}

function EmptyState() {
  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      color: 'var(--pf-dim)', padding: 32, textAlign: 'center',
    }}>
      <div style={{
        width: 48, height: 48, borderRadius: 12,
        border: '1px dashed var(--pf-border)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: 14, fontSize: 22,
      }}>
        ⬡
      </div>
      <p style={{ margin: '0 0 6px', fontSize: '0.85em', color: 'var(--pf-mute)' }}>
        No output yet
      </p>
      <p style={{ margin: 0, fontSize: '0.72em', color: 'var(--pf-dim)' }}>
        Configure a mesh and click Render
      </p>
    </div>
  )
}

// ── Split-body wrapper ───────────────────────────────────────────────────────
function SplitSheetsOutput({ splitSheets, frameCount, spriteSize }) {
  const [activeTab, setActiveTab] = useState(0)
  const sheet = splitSheets[activeTab]

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Split tab selector */}
      <div className="pf-tabs">
        {splitSheets.map((s, i) => (
          <button
            key={s.label}
            onClick={() => setActiveTab(i)}
            className={`pf-tab${activeTab === i ? ' active' : ''}`}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto' }}>
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
  isRendering = false,
  _noChrome = false,
}) {
  const [selectedDir, setSelectedDir] = useState('S')
  const [currentFrame, setCurrentFrame] = useState(0)
  const [isPlaying, setIsPlaying] = useState(true)
  const [fps, setFps] = useState(8)
  // Start on 'live' for animation, '8dir' for single-frame
  const [activeTab, setActiveTab] = useState(() => animationUrls ? 'live' : '8dir')
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

  // Reset on new animation
  useEffect(() => {
    if (animationUrls) {
      setSelectedDir('S')
      setCurrentFrame(0)
      setIsPlaying(true)
      setActiveTab('live')
    }
  }, [animationUrls])

  // Reset frame on direction change
  useEffect(() => {
    setCurrentFrame(0)
  }, [selectedDir])

  // ── Empty / split-body ────────────────────────────────────────────────────
  if (!spriteSheetUrl && !refinedUrl && !animationUrls && !splitSheets) {
    if (isRendering) {
      return (
        <div style={{
          flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--pf-mute)', fontSize: '0.85em', gap: 10,
        }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: 'var(--pf-accent)',
            animation: 'pulse 1.5s ease-in-out infinite',
            flexShrink: 0,
          }} />
          Rendering…
        </div>
      )
    }
    return <EmptyState />
  }

  if (splitSheets) {
    return <SplitSheetsOutput splitSheets={splitSheets} frameCount={frameCount} spriteSize={spriteSize} />
  }

  // ── Derived values ────────────────────────────────────────────────────────
  const isStripRefined  = !!refinedAnimationUrls
  const isMasterRefined = !!refinedMergedUrl
  const isRefined       = isStripRefined || isMasterRefined || !!refinedUrl
  const activeUrls      = refinedAnimationUrls || animationUrls
  const selectedUrl     = activeUrls?.[selectedDir]
  const activeMergedUrl = refinedMergedUrl || mergedUrl
  const dirIndex        = DIRECTIONS.indexOf(selectedDir)
  const useMasterPreview = isMasterRefined && !isStripRefined

  const activeSingleUrl = refinedUrl || spriteSheetUrl

  // ── Tab definitions ───────────────────────────────────────────────────────
  const hasMaster  = !!activeMergedUrl
  const hasCompare = isRefined && (spriteSheetUrl || animationUrls)
  const isAnimMode = !!animationUrls

  const tabs = [
    ...(isAnimMode ? [{ id: 'live',  label: 'Live Preview' }] : []),
    { id: '8dir',   label: '8-Dir' },
    ...(hasMaster ? [{ id: 'master', label: 'Master Sheet' }] : []),
    ...(hasCompare ? [{ id: 'compare', label: 'Compare' }] : []),
  ]

  // Keep activeTab valid when content changes
  const validTab = tabs.find(t => t.id === activeTab) ? activeTab : tabs[0]?.id

  // ── Shared preview box size ───────────────────────────────────────────────
  const previewPx = 192

  // ── Inner content ─────────────────────────────────────────────────────────

  const liveTab = (
    <div style={{ padding: 'var(--pf-pad)', display: 'flex', gap: 24, flexWrap: 'wrap' }}>
      {/* Left: direction wheel + preview */}
      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
        <div>
          <span className="eyebrow">Direction</span>
          <DirWheel selectedDir={selectedDir} onSelect={setSelectedDir} />
        </div>

        <div>
          <span className="eyebrow" style={{ textAlign: 'center', display: 'block' }}>
            {useMasterPreview || isStripRefined ? 'Refined' : 'Preview'} — {selectedDir}
          </span>
          <div
            className="pixel-art"
            style={{
              width: previewPx, height: previewPx,
              borderRadius: 8,
              background: 'var(--pf-panel-2)',
              backgroundImage: useMasterPreview
                ? `url("${refinedMergedUrl}")`
                : `url("${selectedUrl}")`,
              backgroundSize: useMasterPreview
                ? `${frameCount * previewPx}px ${8 * previewPx}px`
                : `${frameCount * previewPx}px ${previewPx}px`,
              backgroundPosition: useMasterPreview
                ? `-${currentFrame * previewPx}px -${dirIndex * previewPx}px`
                : `-${currentFrame * previewPx}px 0px`,
              backgroundRepeat: 'no-repeat',
            }}
          />
          <p style={{ margin: '6px 0 0', fontSize: '0.72em', color: 'var(--pf-dim)', textAlign: 'center' }}>
            Frame {currentFrame + 1} / {frameCount}
          </p>
        </div>
      </div>

      {/* Right: playback controls */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, justifyContent: 'center' }}>
        <button
          onClick={() => setIsPlaying(p => !p)}
          style={{
            padding: '6px 16px',
            borderRadius: 'var(--pf-radius)',
            border: '1px solid var(--pf-border)',
            background: 'var(--pf-panel-2)',
            color: 'var(--pf-text)',
            cursor: 'pointer',
            fontSize: '0.85em',
            fontFamily: 'inherit',
            transition: 'border-color 0.15s',
          }}
        >
          {isPlaying ? '⏸ Pause' : '▶ Play'}
        </button>
        <div>
          <span style={{ fontSize: '0.72em', color: 'var(--pf-mute)', display: 'block', marginBottom: 4 }}>
            Speed: {fps} fps
          </span>
          <input
            type="range" min={1} max={24} value={fps}
            onChange={e => setFps(Number(e.target.value))}
            style={{ width: 120, accentColor: 'var(--pf-accent)' }}
          />
        </div>
      </div>

      {/* Strip preview */}
      <div style={{ width: '100%' }}>
        <span className="eyebrow">
          {useMasterPreview || isStripRefined ? 'Refined strip' : 'Strip'} — {selectedDir} ({frameCount} frames)
        </span>
        <div style={{
          background: 'var(--pf-panel-2)',
          borderRadius: 'var(--pf-radius)',
          border: '1px solid var(--pf-border)',
          padding: 10, overflowX: 'auto',
        }}>
          {useMasterPreview ? (
            <div
              className="pixel-art"
              style={{
                height: 64, width: `${frameCount * 64}px`,
                backgroundImage: `url("${refinedMergedUrl}")`,
                backgroundSize: `${frameCount * 64}px ${8 * 64}px`,
                backgroundPosition: `0px -${dirIndex * 64}px`,
                backgroundRepeat: 'no-repeat',
                borderRadius: 4,
              }}
            />
          ) : (
            <img
              src={selectedUrl}
              alt={`Strip ${selectedDir}`}
              className="pixel-art"
              style={{ height: 64, width: 'auto', display: 'block', borderRadius: 4 }}
            />
          )}
        </div>
      </div>
    </div>
  )

  const eightDirTab = (
    <div style={{ padding: 'var(--pf-pad)' }}>
      {isAnimMode ? (
        <>
          {/* Grid of all 8 directions */}
          <span className="eyebrow">All directions — frame 1</span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
            {DIRECTIONS.map(dir => {
              const url = activeUrls?.[dir]
              return (
                <div key={dir} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <div
                    className="pixel-art"
                    style={{
                      width: 80, height: 80,
                      background: 'var(--pf-panel-2)',
                      border: `1px solid ${dir === selectedDir ? 'var(--pf-accent)' : 'var(--pf-border)'}`,
                      borderRadius: 6, overflow: 'hidden',
                      backgroundImage: url ? `url("${url}")` : 'none',
                      backgroundSize: `${frameCount * 80}px 80px`,
                      backgroundPosition: '0px 0px',
                      backgroundRepeat: 'no-repeat',
                      cursor: 'pointer',
                    }}
                    onClick={() => { setSelectedDir(dir); setActiveTab('live') }}
                  />
                  <span style={{ fontSize: '0.65em', color: 'var(--pf-mute)' }}>{dir}</span>
                </div>
              )
            })}
          </div>

          {/* Per-direction downloads */}
          <span className="eyebrow">Download per direction</span>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {DIRECTIONS.map(dir => (
              <a
                key={dir}
                href={activeUrls?.[dir]}
                download={`${spriteName}_${dir}${isStripRefined ? '_refined' : ''}.png`}
                style={{
                  fontSize: '0.75em',
                  background: 'var(--pf-panel-2)',
                  border: '1px solid var(--pf-border)',
                  color: 'var(--pf-mute)',
                  padding: '4px 10px',
                  borderRadius: 'var(--pf-radius)',
                  textDecoration: 'none',
                  transition: 'color 0.15s, border-color 0.15s',
                }}
              >
                ↓ {dir}
              </a>
            ))}
          </div>
        </>
      ) : (
        <>
          {/* Single-frame: show the 8-direction strip */}
          <span className="eyebrow">8-direction strip</span>
          <div style={{
            background: 'var(--pf-panel-2)',
            borderRadius: 'var(--pf-radius)',
            border: '1px solid var(--pf-border)',
            padding: 12, overflowX: 'auto', marginBottom: 10,
          }}>
            <div style={{ width: 'max-content', minWidth: '100%' }}>
              <img
                src={activeSingleUrl}
                alt="Sprite sheet"
                className="pixel-art"
                style={{ height: 192, width: 'auto', display: 'block', borderRadius: 4 }}
              />
              <div style={{ display: 'flex', marginTop: 6 }}>
                {DIRECTIONS.map(dir => (
                  <div key={dir} style={{ flex: 1, textAlign: 'center', fontSize: '0.65em', color: 'var(--pf-dim)' }}>
                    {dir}
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <a
              href={activeSingleUrl}
              download={refinedUrl ? `${spriteName}_refined.png` : `${spriteName}.png`}
              style={{
                display: 'inline-flex', alignItems: 'center',
                background: 'var(--pf-accent)', color: '#fff',
                padding: '6px 14px', borderRadius: 'var(--pf-radius)',
                fontSize: '0.8em', textDecoration: 'none', fontWeight: 600,
              }}
            >
              ↓ Download PNG
            </a>
          </div>
        </>
      )}
    </div>
  )

  const masterTab = (
    <div style={{ padding: 'var(--pf-pad)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <span className="eyebrow" style={{ marginBottom: 0 }}>
          Master sheet{isMasterRefined ? ' — Refined' : ''}
        </span>
        <a
          href={activeMergedUrl}
          download={`${spriteName}_all${isMasterRefined ? '_refined' : ''}.png`}
          style={{
            background: 'var(--pf-accent)', color: '#fff',
            padding: '5px 12px', borderRadius: 'var(--pf-radius)',
            fontSize: '0.75em', textDecoration: 'none', fontWeight: 600,
          }}
        >
          ↓ Download master sheet
        </a>
      </div>
      <div style={{
        background: 'var(--pf-panel-2)',
        border: '1px solid var(--pf-border)',
        borderRadius: 'var(--pf-radius)',
        padding: 10, overflowX: 'auto', overflowY: 'auto', maxHeight: 320,
      }}>
        <span className="field-hint" style={{ marginBottom: 6 }}>
          8 rows (N → NW) × {frameCount || 1} frames
        </span>
        <img
          src={activeMergedUrl}
          alt="Master sprite sheet"
          className="pixel-art"
          style={{
            height: 'auto',
            width: `${(frameCount || 1) * (spriteSize || 64)}px`,
            minWidth: '100%',
            display: 'block',
            borderRadius: 4,
          }}
        />
      </div>
    </div>
  )

  const compareTab = (
    <div style={{ padding: 'var(--pf-pad)' }}>
      {isAnimMode ? (
        <>
          {/* Compare strips for current direction */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <span className="eyebrow" style={{ marginBottom: 0 }}>Direction</span>
            <DirWheel selectedDir={selectedDir} onSelect={setSelectedDir} />
          </div>

          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: 200 }}>
              <span className="eyebrow">Refined — {selectedDir}</span>
              <div style={{
                background: 'var(--pf-panel-2)',
                border: '1px solid var(--pf-border)',
                borderRadius: 'var(--pf-radius)',
                padding: 8, overflowX: 'auto',
              }}>
                {useMasterPreview ? (
                  <div
                    className="pixel-art"
                    style={{
                      height: 64, width: `${frameCount * 64}px`,
                      backgroundImage: `url("${refinedMergedUrl}")`,
                      backgroundSize: `${frameCount * 64}px ${8 * 64}px`,
                      backgroundPosition: `0px -${dirIndex * 64}px`,
                      backgroundRepeat: 'no-repeat',
                      borderRadius: 4,
                    }}
                  />
                ) : (
                  <img
                    src={activeUrls?.[selectedDir]}
                    alt={`Refined ${selectedDir}`}
                    className="pixel-art"
                    style={{ height: 64, width: 'auto', display: 'block', borderRadius: 4 }}
                  />
                )}
              </div>
            </div>
            <div style={{ flex: 1, minWidth: 200 }}>
              <span className="eyebrow">Original — {selectedDir}</span>
              <div style={{
                background: 'var(--pf-panel-2)',
                border: '1px solid var(--pf-border)',
                borderRadius: 'var(--pf-radius)',
                padding: 8, overflowX: 'auto',
              }}>
                <img
                  src={animationUrls?.[selectedDir]}
                  alt={`Original ${selectedDir}`}
                  className="pixel-art"
                  style={{ height: 64, width: 'auto', display: 'block', borderRadius: 4, opacity: 0.75 }}
                />
              </div>
            </div>
          </div>

          {/* Master sheet comparison */}
          {isMasterRefined && mergedUrl && (
            <div style={{ marginTop: 16 }}>
              <span className="eyebrow">Master sheet comparison</span>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <span className="field-hint" style={{ marginBottom: 6 }}>Refined</span>
                  <div style={{
                    background: 'var(--pf-panel-2)', border: '1px solid var(--pf-border)',
                    borderRadius: 'var(--pf-radius)', padding: 8, overflowX: 'auto', maxHeight: 200,
                  }}>
                    <img src={refinedMergedUrl} alt="Refined master" className="pixel-art"
                      style={{ height: 'auto', width: `${frameCount * (spriteSize || 64)}px`, minWidth: '100%', display: 'block' }} />
                  </div>
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <span className="field-hint" style={{ marginBottom: 6 }}>Original</span>
                  <div style={{
                    background: 'var(--pf-panel-2)', border: '1px solid var(--pf-border)',
                    borderRadius: 'var(--pf-radius)', padding: 8, overflowX: 'auto', maxHeight: 200,
                  }}>
                    <img src={mergedUrl} alt="Original master" className="pixel-art"
                      style={{ height: 'auto', width: `${frameCount * (spriteSize || 64)}px`, minWidth: '100%', display: 'block', opacity: 0.7 }} />
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <>
          {/* Single-frame compare */}
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: 200 }}>
              <span className="eyebrow">Refined</span>
              <div style={{
                background: 'var(--pf-panel-2)', border: '1px solid var(--pf-border)',
                borderRadius: 'var(--pf-radius)', padding: 10, overflowX: 'auto',
              }}>
                <img src={refinedUrl} alt="Refined"
                  className="pixel-art"
                  style={{ height: 192, width: 'auto', display: 'block', borderRadius: 4 }} />
              </div>
            </div>
            <div style={{ flex: 1, minWidth: 200 }}>
              <span className="eyebrow">Original</span>
              <div style={{
                background: 'var(--pf-panel-2)', border: '1px solid var(--pf-border)',
                borderRadius: 'var(--pf-radius)', padding: 10, overflowX: 'auto',
              }}>
                <img src={spriteSheetUrl} alt="Original"
                  className="pixel-art"
                  style={{ height: 192, width: 'auto', display: 'block', borderRadius: 4, opacity: 0.75 }} />
              </div>
              <a
                href={spriteSheetUrl}
                download={`${spriteName}_original.png`}
                style={{ display: 'inline-block', marginTop: 6, fontSize: '0.72em', color: 'var(--pf-mute)', textDecoration: 'none' }}
              >
                ↓ original
              </a>
            </div>
          </div>
        </>
      )}
    </div>
  )

  const tabContent = {
    live:    liveTab,
    '8dir':  eightDirTab,
    master:  masterTab,
    compare: compareTab,
  }

  const inner = (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Tab bar */}
      <div className="pf-tabs" style={{ position: 'relative' }}>
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`pf-tab${validTab === t.id ? ' active' : ''}`}
          >
            {t.label}
          </button>
        ))}
        {isRefined && (
          <span className="chip" style={{
            position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
            background: 'var(--pf-accent-dim)', borderColor: 'rgba(139,92,246,0.3)',
            color: 'var(--pf-accent)',
          }}>
            Refined
          </span>
        )}
      </div>

      {/* Tab content */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {validTab ? tabContent[validTab] : null}
      </div>
    </div>
  )

  if (_noChrome) return inner

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {inner}
    </div>
  )
}
