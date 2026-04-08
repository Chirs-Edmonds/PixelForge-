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
  const [animConfig, setAnimConfig]         = useState(null)

  // Use a ref to track animConfig inside callbacks without stale closure issues
  const animConfigRef = useRef(null)
  const renderDoneRef = useRef(false)

  function handleRenderDone() {
    if (renderDoneRef.current) return
    renderDoneRef.current = true
    setRenderDone(true)
    setIsRendering(false)

    const config = animConfigRef.current
    if (config?.isAnimation) {
      const ts = Date.now()
      const urls = {}
      DIRECTIONS.forEach(d => {
        urls[d] = `/api/output/sheets/sprite_sheet_${d}.png?t=${ts}`
      })
      setAnimationUrls(urls)
      setSpriteSheetUrl(null)
    } else {
      setSpriteSheetUrl(`/api/output/sprite_sheet.png?t=${Date.now()}`)
      setAnimationUrls(null)
    }
  }

  function handleRenderError() {
    renderDoneRef.current = false
    setIsRendering(false)
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
          disabled={!renderDone || !!animConfig?.isAnimation}
          onRefined={setRefinedUrl}
        />

        <SpriteSheetOutput
          spriteSheetUrl={spriteSheetUrl}
          refinedUrl={refinedUrl}
          animationUrls={animationUrls}
          frameCount={animConfig?.isAnimation ? (animConfig.frameEnd - animConfig.frameStart + 1) : null}
        />
      </main>
    </div>
  )
}
