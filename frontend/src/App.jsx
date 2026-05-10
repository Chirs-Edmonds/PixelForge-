import { useState, useRef } from 'react'
import { MeshInput } from './components/MeshInput'
import { RenderSettings } from './components/RenderSettings'
import { StatusBar } from './components/StatusBar'
import { RefinementPanel } from './components/RefinementPanel'
import { SpriteSheetOutput } from './components/SpriteSheetOutput'
import { TopBar } from './components/TopBar'
import { Sidebar } from './components/Sidebar'

const DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']

export default function App() {
  const [meshFilename, setMeshFilename]     = useState(null)
  const [renderJobId, setRenderJobId]       = useState(null)
  const [renderDone, setRenderDone]         = useState(false)
  const [isRendering, setIsRendering]       = useState(false)
  const [hasError, setHasError]             = useState(false)
  const [spriteSheetUrl, setSpriteSheetUrl] = useState(null)
  const [refinedUrl, setRefinedUrl]         = useState(null)
  const [animationUrls, setAnimationUrls]   = useState(null)
  const [animConfig, setAnimConfig]         = useState(null)
  const [mergedUrl, setMergedUrl]           = useState(null)
  const [refinedAnimationUrls, setRefinedAnimationUrls] = useState(null)
  const [refinedMergedUrl, setRefinedMergedUrl]         = useState(null)
  const [splitSheets, setSplitSheets]       = useState(null)
  const [activeView, setActiveView]         = useState('forge')

  const animConfigRef = useRef(null)
  const renderDoneRef = useRef(false)

  function handleRenderDone(jobData) {
    if (renderDoneRef.current) return
    renderDoneRef.current = true
    setRenderDone(true)
    setIsRendering(false)
    setHasError(false)

    const config = animConfigRef.current
    const name   = config?.name || 'sprite_sheet'
    const ts     = Date.now()

    const buildAnimUrls = prefix => {
      const urls = {}
      DIRECTIONS.forEach(d => { urls[d] = `/api/output/sheets/${prefix}_${d}.png?t=${ts}` })
      return urls
    }

    if (config?.bodyPart === 'split') {
      const safeBase   = jobData?.output?.replace('sheets/', '').replace(/_legs(\.png)?$/, '') || name
      const showMerged = config.isAnimation && config.mergeSheets
      setSplitSheets([
        {
          label: 'Upper body',
          spriteName: `${safeBase}_upper`,
          animationUrls:  config.isAnimation ? buildAnimUrls(`${safeBase}_upper`) : null,
          spriteSheetUrl: config.isAnimation ? null : `/api/output/${safeBase}_upper.png?t=${ts}`,
          mergedUrl: showMerged ? `/api/output/merged/${safeBase}_upper_all.png?t=${ts}` : null,
        },
        {
          label: 'Lower body',
          spriteName: `${safeBase}_legs`,
          animationUrls:  config.isAnimation ? buildAnimUrls(`${safeBase}_legs`) : null,
          spriteSheetUrl: config.isAnimation ? null : `/api/output/${safeBase}_legs.png?t=${ts}`,
          mergedUrl: showMerged ? `/api/output/merged/${safeBase}_legs_all.png?t=${ts}` : null,
        },
      ])
      setAnimationUrls(null)
      setSpriteSheetUrl(null)
      setMergedUrl(null)
    } else if (config?.isAnimation) {
      const animPrefix = jobData?.output?.replace('sheets/', '') || name
      setSplitSheets(null)
      setAnimationUrls(buildAnimUrls(animPrefix))
      setSpriteSheetUrl(null)
      setMergedUrl(jobData?.merged_url ? `${jobData.merged_url}?t=${ts}` : null)
    } else {
      setSplitSheets(null)
      setSpriteSheetUrl(`/api/output/${name}.png?t=${ts}`)
      setAnimationUrls(null)
      setMergedUrl(null)
    }
  }

  function handleRenderError() {
    renderDoneRef.current = false
    setIsRendering(false)
    setHasError(true)
  }

  function handleSplitRefined(data) {
    const ts = Date.now()
    if (data?.is_split && data?.is_animation) {
      const prefix   = data.output?.replace('sheets/', '') || animConfig?.name || 'sprite_sheet'
      const suffixes = ['_upper', '_legs']
      const hasMasters = [data.has_master_upper, data.has_master_legs]
      setSplitSheets(prev => prev.map((sheet, i) => ({
        ...sheet,
        refinedMergedUrl: hasMasters[i]
          ? `/api/output/refined/${prefix}${suffixes[i]}_all_refined.png?t=${ts}`
          : null,
      })))
    } else {
      setSplitSheets(prev => prev.map((sheet, i) => ({
        ...sheet,
        refinedUrl: `/api/output/${data.output[i]}?t=${ts}`,
      })))
    }
  }

  function handleAnimationRefined(data) {
    const ts = Date.now()
    const prefix = data?.output?.replace('sheets/', '') || animConfig?.name || 'sprite_sheet'
    if (data?.has_master) {
      setRefinedMergedUrl(`/api/output/refined/${prefix}_all_refined.png?t=${ts}`)
    }
  }

  function handleRenderAttempting() {
    renderDoneRef.current = false
    setRenderDone(false)
    setIsRendering(false)
    setHasError(false)
    setSpriteSheetUrl(null)
    setRefinedUrl(null)
    setAnimationUrls(null)
    setMergedUrl(null)
    setRefinedAnimationUrls(null)
    setRefinedMergedUrl(null)
    setSplitSheets(null)
    setRenderJobId(null)
  }

  function handleNewRender(jobId, config) {
    renderDoneRef.current = false
    animConfigRef.current = config
    setAnimConfig(config)
    setRenderDone(false)
    setIsRendering(true)
    setHasError(false)
    setSpriteSheetUrl(null)
    setRefinedUrl(null)
    setAnimationUrls(null)
    setMergedUrl(null)
    setRefinedAnimationUrls(null)
    setRefinedMergedUrl(null)
    setSplitSheets(null)
    setRenderJobId(jobId)
  }

  return (
    <div style={{
      background: 'var(--pf-bg)',
      color: 'var(--pf-text)',
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      fontFamily: "'Geist', system-ui, 'Segoe UI', sans-serif",
      fontSize: 'var(--pf-fs)',
      overflow: 'hidden',
    }}>
      <TopBar
        meshFilename={meshFilename}
        isRendering={isRendering}
        renderDone={renderDone}
        hasError={hasError}
        animConfig={animConfig}
      />

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <Sidebar activeView={activeView} onViewChange={setActiveView} />

        {/* Settings column */}
        <div style={{
          width: 304,
          flexShrink: 0,
          overflowY: 'auto',
          borderRight: '1px solid var(--pf-border)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--pf-gap)',
          padding: 'var(--pf-pad)',
        }}>
          <MeshInput onMeshReady={setMeshFilename} />

          <RenderSettings
            meshFilename={meshFilename}
            onRenderStarted={handleNewRender}
            onRenderAttempting={handleRenderAttempting}
            isRendering={isRendering}
            disabled={false}
          />

          {renderJobId && (
            <StatusBar
              jobId={renderJobId}
              onDone={handleRenderDone}
              onError={handleRenderError}
            />
          )}

          <RefinementPanel
            disabled={!renderDone}
            onRefined={setRefinedUrl}
            onAnimationRefined={handleAnimationRefined}
            onSplitRefined={handleSplitRefined}
            animConfig={animConfig}
          />
        </div>

        {/* Preview pane */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <SpriteSheetOutput
            spriteSheetUrl={spriteSheetUrl}
            refinedUrl={refinedUrl}
            animationUrls={animationUrls}
            refinedAnimationUrls={refinedAnimationUrls}
            frameCount={animConfig?.isAnimation ? (animConfig.frameEnd - animConfig.frameStart + 1) : null}
            spriteSize={animConfig?.spriteSize}
            spriteName={animConfig?.name || 'sprite_sheet'}
            mergedUrl={mergedUrl}
            refinedMergedUrl={refinedMergedUrl}
            splitSheets={splitSheets}
            isRendering={isRendering}
          />
        </div>

        {/* Queue rail stub — shown once a render job exists */}
        {renderJobId && (
          <div style={{
            width: 252,
            flexShrink: 0,
            borderLeft: '1px solid var(--pf-border)',
            background: 'var(--pf-panel)',
            display: 'flex',
            flexDirection: 'column',
          }}>
            <div style={{
              padding: '12px 14px',
              borderBottom: '1px solid var(--pf-border)',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}>
              <span style={{ fontWeight: 600, fontSize: 13 }}>Queue</span>
              <span className="chip">1</span>
            </div>

            <div style={{ padding: 12, flex: 1 }}>
              <div style={{
                padding: '10px 12px',
                borderRadius: 7,
                background: 'var(--pf-panel-2)',
                border: '1px solid var(--pf-border)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <div style={{
                    width: 7,
                    height: 7,
                    borderRadius: '50%',
                    background: renderDone
                      ? 'var(--pf-good)'
                      : hasError
                        ? 'var(--pf-err)'
                        : 'var(--pf-accent)',
                    flexShrink: 0,
                  }} />
                  <span style={{
                    fontSize: 12,
                    fontWeight: 500,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}>
                    {animConfig?.name || 'sprite_sheet'}
                  </span>
                </div>
                <span style={{ fontSize: 11, color: 'var(--pf-mute)', display: 'block' }}>
                  {renderDone ? 'Complete' : hasError ? 'Failed' : 'Rendering…'}
                </span>
                {animConfig && (
                  <span style={{ fontSize: 11, color: 'var(--pf-dim)', display: 'block', marginTop: 2 }}>
                    {animConfig.spriteSize}px
                    {animConfig.isAnimation && ` · ${animConfig.frameEnd - animConfig.frameStart + 1} frames`}
                    {' · 8 dir'}
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
