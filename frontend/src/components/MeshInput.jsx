import { useState, useRef, useEffect } from 'react'
import { useJobStatus } from '../hooks/useJobStatus'

export function MeshInput({ onMeshReady }) {
  const [tab, setTab] = useState('upload')
  const [uploading, setUploading] = useState(false)
  const [uploadedFile, setUploadedFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)

  // Tripo3D fields
  const [prompt, setPrompt] = useState('')
  const [tripoJobId, setTripoJobId] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [tripoError, setTripoError] = useState(null)
  const tripoStatus = useJobStatus(tripoJobId)

  const fileInputRef = useRef(null)

  // Handle Tripo3D job completion and error — must be in effect, not render body
  useEffect(() => {
    if (!tripoStatus) return
    if (tripoStatus.status === 'done' && tripoStatus.output) {
      setGenerating(false)
      onMeshReady(tripoStatus.output)
    } else if (tripoStatus.status === 'error') {
      setGenerating(false)
    }
  }, [tripoStatus?.status, tripoStatus?.output]) // eslint-disable-line react-hooks/exhaustive-deps

  async function handleFileUpload(file) {
    if (!file || !file.name.endsWith('.glb')) {
      alert('Please upload a .glb file.')
      return
    }
    setUploading(true)
    const form = new FormData()
    form.append('file', file)
    try {
      const res = await fetch('/api/upload-mesh', { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      setUploadedFile(data.filename)
      onMeshReady(data.filename)
    } catch (e) {
      alert(`Upload error: ${e.message}`)
    } finally {
      setUploading(false)
    }
  }

  async function handleGenerateMesh() {
    if (!prompt.trim()) return
    setTripoError(null)
    setGenerating(true)
    try {
      const res = await fetch('/api/generate-mesh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt.trim(), outfile: 'generated.glb' }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Request failed')
      setTripoJobId(data.job_id)
    } catch (e) {
      setTripoError(e.message)
      setGenerating(false)
    }
  }

  const tripoProgressMsg = tripoStatus?.progress_msg || 'Waiting...'
  const tripoFailed = tripoStatus?.status === 'error'

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-5">
      <h2 className="text-lg font-semibold text-white mb-4">1. Mesh Input</h2>

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        {['upload', 'generate'].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              tab === t
                ? 'bg-violet-600 text-white'
                : 'text-white/50 hover:text-white hover:bg-white/10'
            }`}
          >
            {t === 'upload' ? 'Upload .glb' : 'Generate (Tripo3D)'}
          </button>
        ))}
      </div>

      {tab === 'upload' && (
        <div>
          <div
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={e => {
              e.preventDefault()
              setDragOver(false)
              handleFileUpload(e.dataTransfer.files[0])
            }}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              dragOver
                ? 'border-violet-400 bg-violet-400/10'
                : 'border-white/20 hover:border-white/40'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".glb"
              className="hidden"
              onChange={e => handleFileUpload(e.target.files[0])}
            />
            {uploading ? (
              <p className="text-white/60">Uploading...</p>
            ) : uploadedFile ? (
              <p className="text-green-400 font-medium">{uploadedFile} ✓</p>
            ) : (
              <>
                <p className="text-white/60 text-sm">Drag & drop a .glb file here</p>
                <p className="text-white/30 text-xs mt-1">or click to browse</p>
              </>
            )}
          </div>
          <button
            onClick={() => { setUploadedFile(null); onMeshReady(null) }}
            className="mt-3 text-xs text-white/30 hover:text-white/60 transition-colors"
          >
            Use test primitive instead
          </button>
        </div>
      )}

      {tab === 'generate' && (
        <div className="space-y-3">
          <input
            type="text"
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            placeholder="e.g. a fantasy sword, a sci-fi robot..."
            disabled={generating}
            className="w-full bg-white/5 border border-white/20 rounded-lg px-4 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-violet-500 disabled:opacity-50"
          />
          <button
            onClick={handleGenerateMesh}
            disabled={generating || !prompt.trim()}
            className="w-full bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium py-2.5 rounded-lg text-sm transition-colors"
          >
            {generating ? 'Generating...' : 'Generate Mesh'}
          </button>
          {generating && (
            <p className="text-xs text-white/50 text-center">{tripoProgressMsg}</p>
          )}
          {tripoFailed && (
            <p className="text-xs text-red-400">{tripoStatus.error || 'Generation failed.'}</p>
          )}
          {tripoError && (
            <p className="text-xs text-red-400">{tripoError}</p>
          )}
        </div>
      )}
    </div>
  )
}
