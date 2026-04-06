const DIRECTIONS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']

export function SpriteSheetOutput({ spriteSheetUrl, refinedUrl }) {
  if (!spriteSheetUrl && !refinedUrl) return null

  const activeUrl = refinedUrl || spriteSheetUrl
  const label     = refinedUrl ? 'Refined' : 'Sprite Sheet'

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">4. Output</h2>
        <a
          href={activeUrl}
          download={refinedUrl ? 'sprite_sheet_refined.png' : 'sprite_sheet.png'}
          className="text-xs bg-violet-600 hover:bg-violet-500 text-white px-3 py-1.5 rounded-lg transition-colors"
        >
          Download PNG
        </a>
      </div>

      {/* Sprite sheet preview */}
      <div className="bg-[#1a1a2e] rounded-lg p-4 mb-3 overflow-x-auto">
        <div style={{ width: 'max-content', minWidth: '100%' }}>
          <img
            src={activeUrl}
            alt="Sprite sheet"
            style={{ imageRendering: 'pixelated', height: '192px', width: 'auto', display: 'block' }}
            className="rounded"
          />
          {/* Direction labels — equal columns matching image width */}
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

      {/* Show both if refined exists */}
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
            download="sprite_sheet_original.png"
            className="mt-2 inline-block text-xs text-white/40 hover:text-white/70 transition-colors"
          >
            Download original
          </a>
        </div>
      )}
    </div>
  )
}
