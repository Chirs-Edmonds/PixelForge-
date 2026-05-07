import { useState, useRef } from 'react'
import { MeshInput } from './components/MeshInput'
import { RenderSettings } from './components/RenderSettings'
import { StatusBar } from './components/StatusBar'
import { RefinementPanel } from './components/RefinementPanel'
import { SpriteSheetOutput } from './components/SpriteSheetOutput'

const DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']

export default function App() {
  const [meshFilename, setMeshFilename]     = useState(null)
  const [renderJobId, setRenderJobId]       = useState(null)
  const [renderDone, setRenderDone]         = useState(false)
  const [isRendering, setIsRendering]       = useState(false)
  const [spriteSheetUrl, setSpriteSheetUrl] = useState(null)
  const [refinedUrl, setRefinedUrl]         = useState(null)
  const [animationUrls, setAnimationUrls]   = useState(null)
  const [animConfig, setAnimConfig]                   = useState(null)
  const [mergedUrl, setMergedUrl]                     = useState(null)
  const [refinedAnimationUrls, setRefinedAnimationUrls] = useState(null)
  const [refinedMergedUrl, setRefinedMergedUrl]         = useState(null)
  const [splitSheets, setSplitSheets]                 = useState(null) // split-body mode only

  // Use a ref to track animConfig inside callbacks without stale closure issues
  const animConfigRef = useRef(null)
  const renderDoneRef = useRef(false)

  function handleRenderDone(jobData) {
    if (renderDoneRef.current) return
    renderDoneRef.current = true
    setRenderDone(true)
    setIsRendering(false)

    const config = animConfigRef.current
    const name   = config?.name || 'sprite_sheet'
    const ts     = Date.now()

    const buildAnimUrls = prefix => {
      const urls = {}
      DIRECTIONS.forEach(d => { urls[d] = `/api/output/sheets/${prefix}_${d}.png?t=${ts}` })
      return urls
    }

    if (config?.bodyPart === 'split') {
      // Two passes were rendered — build separate URL sets for upper and lower.
      // jobData.output = "sheets/{safe_name}_legs" for split renders; strip both parts
      // to recover the sanitized base name the server actually wrote files under.
      const safeBase   = jobData?.output?.replace('sheets/', '').replace(/_legs(\.png)?$/, '') || name
      const showMerged = config.isAnimation && config.mergeSheets
      setSplitSheets([
        {
          label: 'Upper body',
          spriteName: `${safeBase}_upper`,
          animationUrls:  config.isAnimation ? buildAnimUrls(`${safeBase}_upper`) : null,
          spriteSheetUrl: config.isAnimation ? null : `/api/output/${safeBase}_upper.png?t=${ts}`,
          mergedUrl: showMerged ? `/api/output/sheets/${safeBase}_upper_all.png?t=${ts}` : null,
        },
        {
          label: 'Lower body',
          spriteName: `${safeBase}_legs`,
          animationUrls:  config.isAnimation ? buildAnimUrls(`${safeBase}_legs`) : null,
          spriteSheetUrl: config.isAnimation ? null : `/api/output/${safeBase}_legs.png?t=${ts}`,
          mergedUrl: showMerged ? `/api/output/sheets/${safeBase}_legs_all.png?t=${ts}` : null,
        },
      ])
      setAnimationUrls(null)
      setSpriteSheetUrl(null)
      setMergedUrl(null)
    } else if (config?.isAnimation) {
      // Use the server-returned prefix (safe_name) so URLs match the sanitized filenames on disk
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
  }

  function handleSplitRefined(data) {
    const ts = Date.now()

    if (data?.is_split && data?.is_animation) {
      // Split animation: refine both pass-sets; each tab gets its own refined strips + merged sheet
      const prefix   = data.output?.replace('sheets/', '') || animConfig?.name || 'sprite_sheet'
      const suffixes = ['_upper', '_legs']
      const hasMasters = [data.has_master_upper, data.has_master_legs]
      setSplitSheets(prev => prev.map((sheet, i) => {
        const suf = suffixes[i]
        const refinedDirUrls = {}
        DIRECTIONS.forEach(d => {
          refinedDirUrls[d] = `/api/output/sheets/${prefix}${suf}_${d}_refined.png?t=${ts}`
        })
        return {
          ...sheet,
          refinedAnimationUrls: refinedDirUrls,
          refinedMergedUrl: hasMasters[i]
            ? `/api/output/sheets/${prefix}${suf}_all_refined.png?t=${ts}`
            : null,
        }
      }))
    } else {
      // Single-frame split: data.output = ["{name}_upper_refined.png", "{name}_legs_refined.png"]
      setSplitSheets(prev => prev.map((sheet, i) => ({
        ...sheet,
        refinedUrl: `/api/output/${data.output[i]}?t=${ts}`,
      })))
    }
  }

  function handleAnimationRefined(data) {
    const ts = Date.now()
    // Use server-returned prefix so names match sanitized filenames on disk
    const prefix = data?.output?.replace('sheets/', '') || animConfig?.name || 'sprite_sheet'
    const urls = {}
    DIRECTIONS.forEach(d => {
      urls[d] = `/api/output/sheets/${prefix}_${d}_refined.png?t=${ts}`
    })
    setRefinedAnimationUrls(urls)
    if (data?.has_master) {
      setRefinedMergedUrl(`/api/output/sheets/${prefix}_all_refined.png?t=${ts}`)
    }
  }

  function handleRenderAttempting() {
    // Called the instant the Render button is clicked, before the POST resolves.
    // Clears all old job state so stale status from a previous run never lingers.
    renderDoneRef.current = false
    setRenderDone(false)
    setIsRendering(false)
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
    <div className="min-h-screen bg-[#0f0f13] text-white">
      {/* Header */}
      <header className="border-b border-white/10 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <div className="w-7 h-7 bg-violet-600 rounded-md flex items-center justify-center text-xs font-bold">PF</div>
          <h1 className="text-lg font-semibold tracking-tight">PixelForge</h1>
          <span className="text-xs text-white/30 bg-white/5 px-2 py-0.5 rounded">8-dir sprite sheet generator</span>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-3xl mx-auto px-6 py-8 space-y-4">
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
        />
      </main>
    </div>
  )
}
