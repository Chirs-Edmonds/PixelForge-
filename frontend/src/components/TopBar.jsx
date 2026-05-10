export function TopBar({ meshFilename, isRendering, renderDone, hasError, animConfig }) {
  const dotState = hasError ? 'error' : renderDone ? 'done' : isRendering ? 'rendering' : 'idle'

  const dotColor = {
    idle: 'var(--pf-dim)',
    rendering: 'var(--pf-accent)',
    done: 'var(--pf-good)',
    error: 'var(--pf-err)',
  }[dotState]

  const statusLabel = {
    idle: 'Idle',
    rendering: 'Rendering…',
    done: 'Done',
    error: 'Error',
  }[dotState]

  const frameCount = animConfig?.isAnimation
    ? animConfig.frameEnd - animConfig.frameStart + 1
    : null

  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      padding: '0 16px',
      height: 48,
      borderBottom: '1px solid var(--pf-border)',
      background: 'var(--pf-panel)',
      flexShrink: 0,
    }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
        <div style={{
          width: 28,
          height: 28,
          borderRadius: 6,
          background: 'var(--pf-accent)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: "'VT323', monospace",
          fontSize: 17,
          color: '#fff',
          letterSpacing: 1,
          flexShrink: 0,
        }}>
          PF
        </div>
        <span style={{ fontWeight: 600, fontSize: 14, letterSpacing: '-0.01em' }}>PixelForge</span>
        <span className="chip">8-dir generator</span>
      </div>

      <div style={{ flex: 1 }} />

      {/* Stats chip */}
      {frameCount && (
        <span className="chip">{frameCount} fr × 8 dir</span>
      )}
      {animConfig && !animConfig.isAnimation && (
        <span className="chip">8 dir</span>
      )}

      {/* Status indicator */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, paddingLeft: 8, borderLeft: '1px solid var(--pf-border)' }}>
        <div style={{ position: 'relative', width: 8, height: 8, flexShrink: 0 }}>
          <div style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '50%',
            background: dotColor,
          }} />
          {isRendering && (
            <div
              className="pf-ping"
              style={{
                position: 'absolute',
                inset: 0,
                borderRadius: '50%',
                background: dotColor,
                opacity: 0.6,
              }}
            />
          )}
        </div>
        <span style={{ fontSize: '0.75em', color: 'var(--pf-mute)' }}>{statusLabel}</span>
      </div>
    </header>
  )
}
