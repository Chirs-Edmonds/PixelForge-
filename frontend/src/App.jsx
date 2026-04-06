import { useState, useRef } from 'react'
import { MeshInput } from './components/MeshInput'
import { RenderSettings } from './components/RenderSettings'
import { StatusBar } from './components/StatusBar'
import { RefinementPanel } from './components/RefinementPanel'
import { SpriteSheetOutput } from './components/SpriteSheetOutput'

export default function App() {
  const [meshFilename, setMeshFilename]     = useState(null)
  const [renderJobId, setRenderJobId]       = useState(null)
  const [renderDone, setRenderDone]         = useState(false)
  const [isRendering, setIsRendering]       = useState(false)
  const [spriteSheetUrl, setSpriteSheetUrl] = useState(null)
  const [refinedUrl, setRefinedUrl]         = useState(null)

  // Prevent onDone from firing on re-renders after already triggered
  const renderDoneRef = useRef(false)

  function handleRenderDone() {
    if (renderDoneRef.current) return
    renderDoneRef.current = true
    setRenderDone(true)
    setIsRendering(false)
    setSpriteSheetUrl(`/api/output/sprite_sheet.png?t=${Date.now()}`)
  }

  function handleRenderError() {
    renderDoneRef.current = false
    setIsRendering(false)
  }

  function handleNewRender(jobId) {
    renderDoneRef.current = false
    setRenderDone(false)
    setIsRendering(true)
    setSpriteSheetUrl(null)
    setRefinedUrl(null)
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
        />

        <SpriteSheetOutput
          spriteSheetUrl={spriteSheetUrl}
          refinedUrl={refinedUrl}
        />
      </main>
    </div>
  )
}
