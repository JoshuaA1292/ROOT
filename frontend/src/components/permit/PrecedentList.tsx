import type { PrecedentRef } from '@/lib/types'

const OUTCOME_STYLE: Record<string, string> = {
  permit_modified: 'bg-yellow-500/20 text-yellow-400',
  denied: 'bg-green-500/20 text-green-400',
  approved: 'bg-red-500/20 text-red-400',
}

const OUTCOME_LABEL: Record<string, string> = {
  permit_modified: 'Modified',
  denied: 'Denied',
  approved: 'Approved',
}

export default function PrecedentList({ precedents }: { precedents: PrecedentRef[] }) {
  if (!precedents.length) return null

  return (
    <div className="space-y-3">
      <h3 className="font-semibold text-white">Relevant Precedents</h3>
      {precedents.map((p) => (
        <div key={p.id} className="bg-root-bark/40 border border-white/10 rounded-lg p-4 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <span className="text-sm text-white font-medium leading-snug">{p.title}</span>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded shrink-0 ${OUTCOME_STYLE[p.outcome] || 'bg-white/10 text-white/60'}`}>
              {OUTCOME_LABEL[p.outcome] || p.outcome}
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-white/40">
            <span>{p.year}</span>
            <span>Match: {(p.similarity_score * 100).toFixed(0)}%</span>
          </div>
          {p.arguments_used.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {p.arguments_used.map((arg) => (
                <span key={arg} className="text-xs bg-root-green/20 text-root-leaf px-2 py-0.5 rounded">
                  {arg.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
