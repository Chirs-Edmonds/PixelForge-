import { useState, useRef, useEffect } from 'react'
import { useJobStatus } from '../hooks/useJobStatus'

export function MeshInput({ onMeshReady }) {
  const [tab, setTab] = useState('upload')
  const [uploading, setUploading] = useState(false)
  const [uploadedFile, setUploadedFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)

  const [prompt, setPrompt] = useState('')
  const [tripoJobId, setTripoJobId] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [tripoError, setTripoError] = useState(null)
  const tripoStatus = useJobStatus(tripoJobId)

  const fileInputRef = useRef(null)

  useEffect(() => {
    if (!tripoStatus) return
    if (tripoStatus.status === 'done' && tripoStatus.output) {
      setGenerating(false)
      onMeshReady(tripoStatus.output)
    } else if (tripoStatus.status === 'error') {
      setGenerating(false)
    }
  }, [tripoStatus?.status, tripoStatus?.output]) // eslint-disable-line react-hooks/exhaustive-deps

  const ALLOWED_EXTENSIONS = ['.glb', '.gltf', '.blend', '.fbx', '.obj']

  async function handleFileUpload(file) {
    if (!file || !ALLOWED_EXTENSIONS.some(ext => file.name.toLowerCase().endsWith(ext))) {
      alert('Supported formats: .glb, .gltf, .blend, .fbx, .obj')
      return
    }
    setUploading(true)
    const form = new FormData()
    form.append('file', file)
    try {
      const res = await fetch('/api/upload-mesh', { method: 'POST', body: form })
      if (!res.ok) {
        let detail = 'Upload failed'
        try { detail = (await res.json()).detail || detail } catch { /* empty body */ }
        throw new Error(detail)
      }
      const data = await res.json()
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
      if (!res.ok) {
        let detail = 'Request failed'
        try { detail = (await res.json()).detail || detail } catch { /* empty body */ }
        throw new Error(detail)
      }
      const data = await res.json()
      setTripoJobId(data.job_id)
    } catch (e) {
      setTripoError(e.message)
      setGenerating(false)
    }
  }

  const tripoProgressMsg = tripoStatus?.progress_msg || 'Waiting...'
  const tripoFailed = tripoStatus?.status === 'error'

  return (
    <div className="panel">
      <span className="eyebrow">Mesh Input</span>

      {/* Tab switcher */}
      <div className="seg seg-full" style={{ marginBottom: 12 }}>
        {[
          { id: 'upload',   label: 'Upload Mesh' },
          { id: 'generate', label: 'Generate (Tripo3D)' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`seg-item${tab === t.id ? ' active' : ''}`}
          >
            {t.label}
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
            style={{
              border: `1px dashed ${dragOver ? 'var(--pf-accent)' : 'var(--pf-border)'}`,
              background: dragOver ? 'var(--pf-accent-dim)' : 'var(--pf-panel-2)',
              borderRadius: 'var(--pf-radius)',
              padding: '20px 12px',
              textAlign: 'center',
              cursor: 'pointer',
              transition: 'border-color 0.15s, background 0.15s',
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".glb,.gltf,.blend,.fbx,.obj"
              style={{ display: 'none' }}
              onChange={e => handleFileUpload(e.target.files[0])}
            />
            {uploading ? (
              <p style={{ margin: 0, color: 'var(--pf-mute)', fontSize: '0.85em' }}>Uploading…</p>
            ) : uploadedFile ? (
              <p style={{ margin: 0, color: 'var(--pf-good)', fontWeight: 500, fontSize: '0.85em' }}>
                {uploadedFile} ✓
              </p>
            ) : (
              <>
                <p style={{ margin: '0 0 4px', color: 'var(--pf-mute)', fontSize: '0.85em' }}>
                  Drag & drop a mesh file here
                </p>
                <p style={{ margin: 0, color: 'var(--pf-dim)', fontSize: '0.72em' }}>
                  .glb · .gltf · .blend · .fbx · .obj — or click to browse
                </p>
              </>
            )}
          </div>
          <button
            onClick={() => { setUploadedFile(null); onMeshReady(null) }}
            style={{
              marginTop: 8,
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.72em',
              color: 'var(--pf-dim)',
              padding: 0,
              transition: 'color 0.15s',
            }}
          >
            Use test primitive instead
          </button>
        </div>
      )}

      {tab === 'generate' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <input
            type="text"
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleGenerateMesh()}
            placeholder="e.g. a fantasy sword, a sci-fi robot…"
            disabled={generating}
            className="pf-input"
          />
          <button
            onClick={handleGenerateMesh}
            disabled={generating || !prompt.trim()}
            className="btn-primary"
          >
            {generating ? 'Generating…' : 'Generate Mesh'}
          </button>
          {generating && (
            <p style={{ margin: 0, fontSize: '0.72em', color: 'var(--pf-mute)', textAlign: 'center' }}>
              {tripoProgressMsg}
            </p>
          )}
          {tripoFailed && (
            <p style={{ margin: 0, fontSize: '0.72em', color: 'var(--pf-err)' }}>
              {tripoStatus.error || 'Generation failed.'}
            </p>
          )}
          {tripoError && (
            <p style={{ margin: 0, fontSize: '0.72em', color: 'var(--pf-err)' }}>{tripoError}</p>
          )}
        </div>
      )}
    </div>
  )
}
