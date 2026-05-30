'use client'

export default function BriefingSkeleton() {
  return (
    <div
      className="rounded-xl p-5 space-y-5 animate-pulse"
      style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
    >
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="h-4 w-48 rounded-md" style={{ background: 'rgba(255,255,255,0.08)' }} />
        <div className="h-5 w-20 rounded-full" style={{ background: 'rgba(116,198,157,0.12)' }} />
      </div>

      {/* Shimmer paragraphs */}
      {[
        [1, 5/6, 1, 4/5],
        [1, 3/4, 1],
        [5/6, 1, 2/3],
      ].map((widths, gi) => (
        <div key={gi} className="space-y-2">
          {widths.map((w, i) => (
            <div
              key={i}
              className="h-2.5 rounded"
              style={{ width: `${(w as number) * 100}%`, background: 'rgba(255,255,255,0.06)' }}
            />
          ))}
        </div>
      ))}

      {/* Live indicator */}
      <div className="flex items-center gap-2.5 pt-1">
        <div className="w-2 h-2 rounded-full bg-root-leaf/50 animate-ping shrink-0" />
        <div className="text-xs text-root-leaf/45 font-mono">Gemini is drafting your public comment...</div>
      </div>
    </div>
  )
}
