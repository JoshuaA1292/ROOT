'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'
import type { Permit, Briefing, AgentEvent } from '@/lib/types'
import AgentStream from '@/components/agent/AgentStream'
import CoalitionSummaryCard from '@/components/permit/CoalitionSummary'
import DeveloperLedger from '@/components/permit/DeveloperLedger'
import PrecedentList from '@/components/permit/PrecedentList'
import PolicyReferenceList from '@/components/permit/PolicyReferenceList'
import BriefingEditor from '@/components/permit/BriefingEditor'
import ProgressStepper from '@/components/ui/ProgressStepper'
import BriefingSkeleton from '@/components/ui/BriefingSkeleton'

const EVENT_TO_STEP: Record<string, string> = {
  coalition_complete: 'coalition',
  developer_loaded: 'developer',
  precedent_complete: 'precedent',
  policy_complete: 'policy',
  polish_complete: 'briefing',
  briefing_complete: 'briefing',
}

const ACTIVE_STEP: Record<string, string> = {
  coalition_start: 'coalition',
  precedent_start: 'precedent',
  policy_start: 'policy',
  briefing_start: 'briefing',
}

export default function PermitDetailPage({ params }: { params: { id: string } }) {
  const [permit, setPermit] = useState<Permit | null>(null)
  const [briefing, setBriefing] = useState<Briefing | null>(null)
  const [briefingId, setBriefingId] = useState<string | null>(null)
  const [started, setStarted] = useState(false)
  const [loading, setLoading] = useState(true)
  const [agentEvents, setAgentEvents] = useState<AgentEvent[]>([])
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set())
  const [activeStep, setActiveStep] = useState<string | null>(null)
  const [pipelineDone, setPipelineDone] = useState(false)

  useEffect(() => {
    api.permits.get(params.id).then(setPermit).catch(console.error).finally(() => setLoading(false))
  }, [params.id])

  useEffect(() => {
    const lastEvent = agentEvents[agentEvents.length - 1]
    if (!lastEvent) return
    const stepId = EVENT_TO_STEP[lastEvent.event]
    if (stepId) {
      setCompletedSteps((prev) => { const s = new Set(prev); s.add(stepId); return s })
      setActiveStep(null)
    }
    const activeId = ACTIVE_STEP[lastEvent.event]
    if (activeId) setActiveStep(activeId)
    if (lastEvent.event === 'done') setPipelineDone(true)
  }, [agentEvents])

  const handleBriefingReady = useCallback(async (id: string) => {
    setBriefingId(id)
    for (let i = 0; i < 20; i++) {
      const b = await api.briefings.get(id)
      setBriefing(b)
      if (b.draft_comment) break
      await new Promise((r) => setTimeout(r, 1500))
    }
  }, [])

  if (loading) return <LoadingScreen />
  if (!permit) return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--void)' }}>
      <div className="text-sm" style={{ color: 'rgba(240,253,244,0.35)' }}>Permit not found.</div>
    </div>
  )

  const deadline = new Date(permit.comment_deadline)
  const daysLeft = Math.ceil((deadline.getTime() - Date.now()) / 86400000)
  const isUrgent = daysLeft > 0 && daysLeft <= 7

  return (
    <div className="min-h-screen" style={{ background: 'var(--void)' }}>
      {/* header */}
      <header
        className="sticky top-0 z-50 px-6 py-3.5 flex items-center justify-between"
        style={{ background: 'rgba(5,13,5,0.92)', borderBottom: '1px solid rgba(255,255,255,0.06)', backdropFilter: 'blur(16px)' }}
      >
        <div className="flex items-center gap-3 min-w-0">
          <Link
            href="/map"
            className="flex items-center gap-1.5 text-sm transition-colors shrink-0"
            style={{ color: 'rgba(240,253,244,0.35)', fontFamily: 'DM Sans' }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 1L3 7l6 6"/>
            </svg>
            Map
          </Link>
          <span style={{ color: 'rgba(255,255,255,0.1)' }}>|</span>
          <div className="min-w-0">
            <div className="text-sm font-semibold truncate" style={{ color: '#f0fdf4', fontFamily: 'DM Sans' }}>{permit.address}</div>
            <div className="text-[11px] capitalize" style={{ color: 'rgba(240,253,244,0.3)', fontFamily: 'DM Sans' }}>{permit.project_type.replace(/_/g, ' ')}</div>
          </div>
        </div>

        <div className="flex items-center gap-4 shrink-0">
          <div className="text-right">
            <div
              className="text-sm font-bold"
              style={{
                fontFamily: 'IBM Plex Mono, monospace',
                color: isUrgent ? '#f87171' : daysLeft <= 0 ? 'rgba(240,253,244,0.2)' : '#fbbf24',
              }}
            >
              {daysLeft > 0 ? `${daysLeft}d` : 'Expired'}
            </div>
            <div className="text-[10px]" style={{ color: 'rgba(240,253,244,0.25)', fontFamily: 'IBM Plex Mono' }}>{permit.comment_deadline}</div>
          </div>
          <div
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full"
            style={{
              background: 'rgba(74,222,128,0.06)',
              border: '1px solid rgba(74,222,128,0.15)',
              color: '#86efac',
              fontFamily: 'DM Sans',
            }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <circle cx="7" cy="7" r="6" stroke="#4ade80" strokeWidth="1.2" strokeOpacity=".5"/>
              <path d="M7 2.5C5 2.5 4 4.2 4 5.8c0 1.3.7 2.4 1.7 3.1L7 11l1.3-2.1C9.3 8.2 10 7.1 10 5.8 10 4.2 9 2.5 7 2.5z" fill="#4ade80" fillOpacity=".9"/>
            </svg>
            ROOT
          </div>
        </div>
      </header>

      {/* main */}
      <div className="relative max-w-6xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-2 gap-8">

        {/* left column */}
        <div className="space-y-5">

          {/* permit details card */}
          <div
            className="rounded-2xl p-5 space-y-1"
            style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.06)' }}
          >
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-sm" style={{ color: '#f0fdf4', fontFamily: 'Syne' }}>Permit Details</h2>
              <span className="text-[10px] uppercase tracking-widest" style={{ color: 'rgba(240,253,244,0.2)', fontFamily: 'IBM Plex Mono' }}>#{permit.id.slice(-8)}</span>
            </div>
            {[
              { label: 'Filed', val: permit.filed_date },
              { label: 'Developer', val: permit.developer_id },
              { label: 'Stated reason', val: permit.stated_reason },
              { label: 'Replacements promised', val: `${permit.promised_replacements} trees` },
              { label: 'Impact radius', val: `${permit.removal_radius_m} meters` },
            ].map(({ label, val }) => (
              <div key={label} className="flex gap-3 py-2" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <span className="shrink-0 w-36 text-[11px]" style={{ color: 'rgba(240,253,244,0.3)', fontFamily: 'DM Sans' }}>{label}</span>
                <span className="text-sm" style={{ color: 'rgba(240,253,244,0.75)', fontFamily: 'DM Sans' }}>{val}</span>
              </div>
            ))}

            {daysLeft > 0 && (
              <div className="pt-3">
                <div className="flex justify-between text-[11px] mb-2" style={{ fontFamily: 'DM Sans' }}>
                  <span style={{ color: 'rgba(240,253,244,0.3)' }}>Comment deadline</span>
                  <span style={{ color: isUrgent ? '#f87171' : '#fbbf24', fontWeight: 600 }}>
                    {daysLeft} day{daysLeft !== 1 ? 's' : ''} remaining
                  </span>
                </div>
                <div className="h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(100, (daysLeft / 30) * 100)}%`,
                      background: isUrgent ? '#f87171' : '#fbbf24',
                    }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* pipeline trigger */}
          {!started ? (
            <button
              onClick={() => setStarted(true)}
              className="w-full py-3.5 rounded-xl text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2"
              style={{
                background: 'rgba(74,222,128,0.1)',
                border: '1px solid rgba(74,222,128,0.3)',
                color: '#4ade80',
                fontFamily: 'DM Sans',
              }}
            >
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                <circle cx="7.5" cy="7.5" r="6" stroke="currentColor" strokeWidth="1.3"/>
                <path d="M6 5l4 2.5-4 2.5V5z" fill="currentColor"/>
              </svg>
              Run Agent Pipeline
            </button>
          ) : (
            <div
              className="rounded-2xl p-5 space-y-5"
              style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.06)' }}
            >
              <ProgressStepper
                completedIds={completedSteps}
                activeId={pipelineDone ? null : activeStep}
              />
              <AgentStream
                permitId={permit.id}
                onBriefingReady={handleBriefingReady}
                onEvent={(evt) => setAgentEvents((prev) => [...prev, evt])}
              />
            </div>
          )}

          {briefing?.coalition_summary && <CoalitionSummaryCard data={briefing.coalition_summary} />}
          {briefing?.developer_snapshot && <DeveloperLedger snapshot={briefing.developer_snapshot} />}
          {briefing?.precedent_refs && briefing.precedent_refs.length > 0 && (
            <PrecedentList precedents={briefing.precedent_refs} />
          )}
          {briefing?.policy_refs && briefing.policy_refs.length > 0 && (
            <PolicyReferenceList policies={briefing.policy_refs} />
          )}
        </div>

        {/* right column — briefing editor */}
        <div className="space-y-5">
          {briefing?.draft_comment ? (
            <BriefingEditor briefing={briefing} onUpdate={setBriefing} />
          ) : started && !pipelineDone ? (
            <BriefingSkeleton />
          ) : (
            <div
              className="rounded-2xl p-10 text-center space-y-3"
              style={{ background: 'rgba(255,255,255,0.015)', border: '1px dashed rgba(255,255,255,0.08)' }}
            >
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center mx-auto"
                style={{ background: 'rgba(255,255,255,0.04)' }}
              >
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ color: 'rgba(240,253,244,0.2)' }}>
                  <path d="M4 4h12v12H4zM4 8h12M8 8v8" strokeLinecap="round"/>
                </svg>
              </div>
              <div className="text-sm" style={{ color: 'rgba(240,253,244,0.3)', fontFamily: 'DM Sans' }}>
                {started
                  ? 'Generating public comment draft...'
                  : 'Click "Run Agent Pipeline" to generate a public comment draft.'}
              </div>
              {!started && (
                <div className="text-xs" style={{ color: 'rgba(240,253,244,0.15)', fontFamily: 'IBM Plex Mono' }}>
                  Coalition · Developer Ledger · Precedents · Gemini Briefing
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <footer
        className="relative text-center text-[11px] py-6 mt-4"
        style={{ borderTop: '1px solid rgba(255,255,255,0.04)', color: 'rgba(240,253,244,0.12)', fontFamily: 'IBM Plex Mono' }}
      >
        Synthetic demo data · ROOT is research assistance only · You are the voice
      </footer>
    </div>
  )
}

function LoadingScreen() {
  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--void)' }}>
      <div className="space-y-3 text-center">
        <div
          className="w-8 h-8 border-2 rounded-full animate-spin mx-auto"
          style={{ borderColor: 'rgba(74,222,128,0.2)', borderTopColor: '#4ade80' }}
        />
        <div className="text-xs animate-pulse" style={{ color: 'rgba(74,222,128,0.4)', fontFamily: 'IBM Plex Mono' }}>
          Loading permit...
        </div>
      </div>
    </div>
  )
}
