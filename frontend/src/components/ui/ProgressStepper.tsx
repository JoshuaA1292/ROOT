'use client'

interface Step {
  id: string
  label: string
  sublabel?: string
}

interface Props {
  steps?: Step[]
  completedIds: Set<string>
  activeId: string | null
}

const STEPS: Step[] = [
  { id: 'coalition',  label: 'Coalition',  sublabel: 'Map impact' },
  { id: 'developer', label: 'Ledger',     sublabel: 'Compliance' },
  { id: 'precedent', label: 'Precedents', sublabel: 'Similar cases' },
  { id: 'policy',    label: 'Policy',     sublabel: 'City targets' },
  { id: 'briefing',  label: 'Gemini',     sublabel: 'Draft comment' },
]

export { STEPS }
export type { Step }

export default function ProgressStepper({ steps = STEPS, completedIds, activeId }: Props) {
  return (
    <div className="flex items-start gap-0">
      {steps.map((step, i) => {
        const done    = completedIds.has(step.id)
        const active  = activeId === step.id
        const pending = !done && !active

        return (
          <div key={step.id} className="flex items-center flex-1 last:flex-none">
            {/* Node */}
            <div className="flex flex-col items-center gap-1.5 shrink-0">
              <div
                className={`
                  w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold
                  transition-all duration-300
                  ${done   ? 'bg-root-green shadow-glow-green text-white' : ''}
                  ${active ? 'bg-root-green/30 border-2 border-root-leaf text-root-leaf' : ''}
                  ${pending ? 'border border-white/12 text-white/20' : ''}
                `}
                style={active ? { boxShadow: '0 0 12px rgba(116,198,157,0.35)' } : undefined}
              >
                {done ? (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                ) : active ? (
                  <span className="w-2.5 h-2.5 rounded-full bg-root-leaf animate-pulse" />
                ) : (
                  <span>{i + 1}</span>
                )}
              </div>
              <div className="text-center min-w-0">
                <div
                  className={`text-[11px] font-semibold transition-colors duration-300
                    ${done ? 'text-root-leaf' : active ? 'text-white' : 'text-white/20'}
                  `}
                >
                  {step.label}
                </div>
                {step.sublabel && (
                  <div
                    className={`text-[9px] hidden sm:block mt-0.5 transition-colors
                      ${active ? 'text-white/45' : 'text-white/15'}
                    `}
                  >
                    {step.sublabel}
                  </div>
                )}
              </div>
            </div>

            {/* Connector line */}
            {i < steps.length - 1 && (
              <div className="flex-1 h-px mx-1.5 mt-[-18px] transition-all duration-500 rounded-full"
                style={{ background: completedIds.has(step.id) ? 'rgba(116,198,157,0.5)' : 'rgba(255,255,255,0.08)' }}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
