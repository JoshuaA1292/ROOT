import type { PolicyRef } from '@/lib/types'

export default function PolicyReferenceList({ policies }: { policies: PolicyRef[] }) {
  if (policies.length === 0) return null

  return (
    <div className="bg-root-bark/60 border border-white/10 rounded-lg p-5 space-y-3">
      <h3 className="font-semibold text-white">Policy Contradictions</h3>
      <div className="space-y-3">
        {policies.map((policy) => (
          <div key={policy.id} className="border-l-2 border-root-leaf/50 pl-3">
            <div className="text-sm font-medium text-white/90">{policy.title}</div>
            <div className="mt-0.5 text-xs text-root-leaf/80">{policy.section}</div>
            <p className="mt-2 text-xs leading-5 text-white/55">{policy.text_excerpt}</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {policy.matched_tags.slice(0, 4).map((tag) => (
                <span key={tag} className="rounded bg-white/10 px-2 py-0.5 text-[10px] text-white/40">
                  {tag.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
