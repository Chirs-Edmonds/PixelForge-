import { Suspense, useState, useEffect } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, useGLTF, Center } from '@react-three/drei'

function Model({ url, onLoaded }) {
  const { scene } = useGLTF(url)
  useEffect(() => { onLoaded?.() }, [onLoaded])
  return <primitive object={scene} />
}

function LoadingOverlay() {
  return (
    <div style={{
      position: 'absolute', inset: 0,
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      color: 'var(--pf-mute)', fontSize: '0.8em', gap: 10,
      background: 'var(--pf-panel-2)', zIndex: 1, pointerEvents: 'none',
    }}>
      <div style={{
        width: 8, height: 8, borderRadius: '50%',
        background: 'var(--pf-accent)',
        animation: 'pulse 1.5s ease-in-out infinite',
      }} />
      Loading 3D model…
    </div>
  )
}

export function Viewport3D({ url }) {
  const [loaded, setLoaded] = useState(false)

  // Reset loaded state whenever the URL changes (new mesh uploaded)
  useEffect(() => { setLoaded(false) }, [url])

  return (
    <div style={{
      flex: 1,
      position: 'relative',
      background: 'var(--pf-panel-2)',
      overflow: 'hidden',
      minHeight: 320,
      borderRadius: 8,
    }}>
      {!loaded && <LoadingOverlay />}

      <Canvas
        camera={{ position: [2, 2, 2], fov: 45 }}
        style={{ width: '100%', height: '100%' }}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 10, 5]} intensity={1.2} />
        <directionalLight position={[-5, 5, -5]} intensity={0.4} />

        <Suspense fallback={null}>
          <Center>
            <Model url={url} onLoaded={() => setLoaded(true)} />
          </Center>
        </Suspense>

        <OrbitControls
          makeDefault
          enableDamping
          dampingFactor={0.05}
          minDistance={0.5}
          maxDistance={20}
        />
      </Canvas>
    </div>
  )
}
