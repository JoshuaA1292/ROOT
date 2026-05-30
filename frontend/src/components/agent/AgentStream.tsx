'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { AgentEvent } from '@/lib/types'

interface Props {
  permitId: string
  onBriefingReady: (briefingId: string) => void
  onEvent?: (event: AgentEvent) => void
}

const EVENT_LABELS: Record<string, string> = {
  permit_loaded:       'Permit loaded',
  coalition_start:     'Coalition Agent: scanning affected trees...',
  coalition_complete:  'Coalition Agent: impact calculated',
  developer_loaded:    'Developer ledger retrieved',
  precedent_start:     'Precedent Agent: searching similar cases...',
  precedent_complete:  'Precedent Agent: relevant cases found',
  policy_start:        'Policy Agent: checking city targets...',
  policy_complete:     'Policy Agent: contradictions identified',
  briefing_start:      'Briefing Agent: Gemini drafting comment...',
  fallback_llm_start:   'Briefing Agent: fallback draft model running...',
  fallback_llm_ready:   'Fallback draft model armed',
  llm_complete:         'LLM draft complete',
  polish_complete:      'Release Polish Agent: filing approved',
  briefing_complete:   'Draft complete — ready for review',
  warning:             'Notice',
  error:               'Error',
  done:                'Pipeline complete',
}

type Phase = 'idle' | 'triggering' | 'streaming' | 'done' | 'error'

export default function AgentStream({ permitId, onBriefingReady, onEvent }: Props) {
  const [phase, setPhase] = useState<Phase>('idle')
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  useEffect(() => {
    let sse: EventSource | null = null

    async function start() {
      setPhase('triggering')
      setEvents([])
      setErrorMsg(null)

      let briefingId: string
      try {
        const result = await api.briefings.trigger(permitId)
        briefingId = result.briefing_id
      } catch {
        setErrorMsg('Failed to start pipeline. Is the backend running?')
        setPhase('error')
        return
      }

      setPhase('streaming')
      sse = new EventSource(api.stream.url(briefingId))
      const handled = new Set(Object.keys(EVENT_LABELS))

      handled.forEach((name) => {
        sse!.addEventListener(name, (e: MessageEvent) => {
          const data = (() => { try { return JSON.parse(e.data) } catch { return {} } })()
          const evt: AgentEvent = { event: name, data }
          setEvents((prev) => [...prev, evt])
          onEvent?.(evt)
          if (name === 'briefing_complete' && data.briefing_id) onBriefingReady(data.briefing_id)
          if (name === 'done' || name === 'error') {
            setPhase(name === 'error' ? 'error' : 'done')
            sse?.close()
          }
        })
      })

      sse.onerror = () => {
        setErrorMsg('Stream connection lost.')
        setPhase('error')
        sse?.close()
      }
    }

    start()
    return () => sse?.close()
  }, [permitId, onBriefingReady, onEvent])

  const running = phase === 'triggering' || phase === 'streaming'

  return (
    <div className="space-y-3">
      {/* Phase status */}
      <div className="flex items-center gap-2">
        {running && (
          <span className="w-1.5 h-1.5 rounded-full bg-root-leaf shrink-0"
            style={{ boxShadow: '0 0 6px rgba(116,198,157,0.8)', animation: 'pulse 1.2s ease-in-out infinite' }} />
        )}
        {phase === 'done' && (
          <span className="w-4 h-4 shrink-0 flex items-center justify-center rounded-full bg-root-green">
            <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
              <path d="M1 4l2 2 4-4" stroke="white" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </span>
        )}
        {phase === 'error' && (
          <span className="w-4 h-4 shrink-0 flex items-center justify-center rounded-full bg-red-500/20 text-red-400 text-[9px] font-bold">!</span>
        )}
        <span className="text-xs font-semibold text-white/60">
          {phase === 'triggering' && 'Starting pipeline...'}
          {phase === 'streaming'  && 'Agent pipeline running'}
          {phase === 'done'       && 'Pipeline complete'}
          {phase === 'error'      && 'Pipeline error'}
        </span>
        {phase === 'done' && (
          <span className="ml-auto text-[10px] text-root-leaf/50 font-mono">{events.length} steps</span>
        )}
      </div>

      {/* Events log */}
      <div
        className="space-y-0.5 max-h-56 overflow-y-auto rounded-lg p-3"
        style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.05)' }}
      >
        {events.length === 0 && running && (
          <div className="text-xs text-white/25 font-mono animate-pulse">Connecting to agent stream...</div>
        )}
        {events.map((evt, i) => (
          <AgentStep key={i} event={evt} />
        ))}
      </div>

      {errorMsg && (
        <div className="text-red-400 text-xs rounded-lg p-2.5 font-mono" style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
          {errorMsg}
        </div>
      )}
    </div>
  )
}

function AgentStep({ event }: { event: AgentEvent }) {
  const label      = EVENT_LABELS[event.event] || event.event
  const isComplete = event.event.endsWith('_complete') || event.event === 'done'
  const isError    = event.event === 'error'
  const isWarning  = event.event === 'warning'

  return (
    <div className={`flex items-start gap-2 text-[11px] font-mono agent-step-enter py-0.5
      ${isError ? 'text-red-400' : isWarning ? 'text-yellow-400' : isComplete ? 'text-root-leaf' : 'text-white/40'}
    `}>
      <span className="shrink-0 w-3 mt-px">
        {isError ? '✗' : isWarning ? '!' : isComplete ? '✓' : '›'}
      </span>
      <div className="flex-1 min-w-0">
        <span>{label}</span>
        {event.event === 'coalition_complete' && event.data.tree_count != null && (
          <span className="ml-2 text-white/30">
            {String(event.data.tree_count)} trees · ${((event.data.total_ecosystem_usd_yr as number) ?? 0).toLocaleString()}/yr · EJ: {String(event.data.ej_tier)}
          </span>
        )}
        {event.event === 'developer_loaded' && (
          <span className="ml-2 text-white/30">
            {(((event.data.compliance_rate as number) ?? 0) * 100).toFixed(0)}% survival rate
          </span>
        )}
        {event.event === 'precedent_complete' && (
          <span className="ml-2 text-white/30">{event.data.count as number} cases</span>
        )}
        {event.event === 'policy_complete' && (
          <span className="ml-2 text-white/30">{event.data.count as number} references</span>
        )}
      </div>
    </div>
  )
}
