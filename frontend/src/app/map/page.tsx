'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import dynamic from 'next/dynamic'
import Link from 'next/link'
import { api } from '@/lib/api'
import type { AgentEvent, Briefing, Developer, GuardianNotification, Permit, TreeSummary, VerificationResult } from '@/lib/types'
import { INVASIVE_SPECIES } from '@/lib/types'

const TreeMap = dynamic(() => import('@/components/map/TreeMap'), {
  ssr: false,
  loading: () => (
    <div className="radar-loader">
      <div className="radar-loader__ring" />
      <p>Building canopy radar</p>
    </div>
  ),
})

type PanelState = 'closed' | 'tree' | 'running' | 'draft'
type MapStyleMode = 'satellite' | 'dark' | 'light'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

const EVENT_LABEL: Record<string, string> = {
  permit_loaded: 'Permit record loaded',
  mcp_active: '⬡ MongoDB MCP toolset registered — Gemini calling Atlas via MCP protocol',
  strategy_complete: '★ Intervention strategy computed',
  coalition_start: 'Scanning nearby canopy',
  coalition_complete: 'Impact zone measured',
  developer_loaded: 'Developer ledger reviewed',
  precedent_start: 'Searching precedent library',
  precedent_complete: 'Relevant cases found',
  policy_start: 'Reading city policy',
  policy_complete: 'Policy issues marked',
  gemini_start: 'Calling Gemini — drafting public comment',
  fallback_llm_start: 'Calling fallback draft model',
  fallback_llm_ready: 'Fallback draft model armed',
  llm_complete: 'LLM draft complete',
  polish_complete: 'Release Polish Agent approved the filing',
  briefing_start: 'Building Day 1 intervention package',
  briefing_complete: 'Protection brief ready',
  done: 'Pipeline complete',
}

const STEP_LABELS = [
  { id: 'coalition', label: 'Assign coalition' },
  { id: 'developer', label: 'Load ledger' },
  { id: 'precedent', label: 'Find precedent' },
  { id: 'policy', label: 'Attach policy' },
  { id: 'briefing', label: 'Write Day 1 package' },
]

const GUARDIAN_TIMELINE = [
  {
    when: 'Day 1',
    title: 'Agent activates',
    body: 'Builds the affected tree coalition, checks developer survival history, retrieves policy and precedent, then drafts the intervention package.',
    state: 'now',
  },
  {
    when: 'Day 90',
    title: 'Permit status check',
    body: 'Checks whether the permit lapsed, construction finished, or removal was confirmed, then updates the tree record.',
    state: 'scheduled',
  },
  {
    when: 'Month 12',
    title: 'Planting promise audit',
    body: 'Queries Parks planting records for promised replacements at the address and escalates missing records to the enforcement queue.',
    state: 'scheduled',
  },
  {
    when: 'Month 36',
    title: 'Survival check',
    body: 'Cross-references inspection records to verify which replacement trees are still alive and updates the developer ledger.',
    state: 'scheduled',
  },
  {
    when: 'Year 5',
    title: 'Case closure',
    body: 'Records final compliance, ecosystem service debt, and the developer survival score attached to future permits.',
    state: 'scheduled',
  },
] as const

const EVENT_TO_STEP: Record<string, string> = {
  coalition_complete: 'coalition',
  developer_loaded: 'developer',
  precedent_complete: 'precedent',
  policy_complete: 'policy',
  polish_complete: 'briefing',
  briefing_complete: 'briefing',
}

function Mark() {
  return (
    <span className="root-mark" aria-hidden>
      <span />
    </span>
  )
}

function CloseIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden>
      <path d="M3 3l9 9M12 3l-9 9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

function ArrowIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden>
      <path d="M2 7.5h10M8.5 4l3.5 3.5L8.5 11" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function CopyIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden>
      <rect x="5" y="4" width="7" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.4" />
      <path d="M3 10V3.8C3 2.8 3.8 2 4.8 2H10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

function SendIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden>
      <path d="M2 7.5L12.5 2.5 9 12.5 6.7 8.4 2 7.5z" stroke="currentColor" strokeWidth="1.45" strokeLinejoin="round" />
      <path d="M6.7 8.4l2.6-2.6" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    </svg>
  )
}

function BellIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none" aria-hidden>
      <path d="M7.5 1.5C5 1.5 3.5 3.5 3.5 6v3l-1 1.5h10L11.5 9V6C11.5 3.5 10 1.5 7.5 1.5z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M6 10.5c0 .83.67 1.5 1.5 1.5S9 11.33 9 10.5" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden>
      <path d="M2.5 6.5l3 3 5-5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function formatProject(value?: string) {
  return (value ?? 'tree work').replace(/_/g, ' ')
}

function daysUntil(date: string) {
  return Math.ceil((new Date(date).getTime() - Date.now()) / 86400000)
}

function pickPermitForTree(tree: TreeSummary, permits: Permit[]) {
  return permits.find(p => p.threatened_tree_ids.includes(tree.id)) ?? null
}

function usePermitData() {
  const [permits, setPermits] = useState<Permit[]>([])
  const [threatenedIds, setThreatenedIds] = useState<Set<string>>(new Set())
  const [threatenedPermits, setThreatenedPermits] = useState<Permit[]>([])

  useEffect(() => {
    api.permits.list().then(data => {
      setPermits(data)
      setThreatenedIds(new Set(data.flatMap(p => p.threatened_tree_ids)))
      setThreatenedPermits(data.filter(p => (p.threatened_tree_ids?.length ?? 0) > 0))
    }).catch(() => {})
  }, [])

  return { permits, threatenedIds, threatenedPermits }
}

export default function MapPage() {
  const { permits, threatenedIds, threatenedPermits } = usePermitData()
  const jumpIndexRef = useRef(0)
  const [selectedTree, setSelectedTree] = useState<TreeSummary | null>(null)
  const [selectedPermit, setSelectedPermit] = useState<Permit | null>(null)
  const [panel, setPanel] = useState<PanelState>('closed')
  const [mapStyle, setMapStyle] = useState<MapStyleMode>('satellite')
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set())
  const [activeStep, setActiveStep] = useState<string | null>(null)
  const [briefing, setBriefing] = useState<Briefing | null>(null)
  const [briefingId, setBriefingId] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitResult, setSubmitResult] = useState<{
    guardian_schedule: { day90: string; month12: string; month36: string; year5: string }
    permit_address: string
    nyc_dob_url: string
    nyc_parks_email: string
    maps_url: string
  } | null>(null)
  const [copied, setCopied] = useState(false)
  const [developer, setDeveloper] = useState<Developer | null>(null)
  const [outcome, setOutcome] = useState<{ acknowledged: boolean; conditions: string[]; notes: string } | null>(null)
  const [trackingOutcome, setTrackingOutcome] = useState(false)
  const [notifications, setNotifications] = useState<GuardianNotification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [inboxOpen, setInboxOpen] = useState(false)
  const [defendedIds, setDefendedIds] = useState<Map<string, number>>(new Map())
  // Email capture modal
  const [emailModal, setEmailModal] = useState<'submit' | null>(null)
  const [emailInput, setEmailInput] = useState('')
  const [pendingEmail, setPendingEmail] = useState<string>('')
  const logRef = useRef<HTMLDivElement>(null)
  const mapFlyToRef = useRef<((lng: number, lat: number) => void) | null>(null)

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [events])

  useEffect(() => {
    if (briefing?.draft_comment) setDraft(briefing.draft_comment)
  }, [briefing])

  // Poll notifications every 5 seconds
  useEffect(() => {
    const poll = () => {
      api.notifications.list().then(data => {
        setNotifications(data.notifications)
        setUnreadCount(data.unread_count)
      }).catch(() => {})
    }
    poll()
    const interval = setInterval(poll, 5000)
    return () => clearInterval(interval)
  }, [])

  // Poll defense map every 15 seconds
  useEffect(() => {
    const pollDefenses = () => {
      api.briefings.defenseMap().then(data => {
        const m = new Map<string, number>()
        data.defenses.forEach(d => m.set(d.tree_id, d.count))
        setDefendedIds(m)
      }).catch(() => {})
    }
    pollDefenses()
    const interval = setInterval(pollDefenses, 15000)
    return () => clearInterval(interval)
  }, [])

  const resetWorkflow = useCallback(() => {
    setEvents([])
    setCompletedSteps(new Set())
    setActiveStep(null)
    setBriefing(null)
    setDraft('')
    setSubmitted(false)
    setSubmitResult(null)
    setCopied(false)
    setBriefingId(null)
    setDeveloper(null)
    setOutcome(null)
    setTrackingOutcome(false)
  }, [])


  const refreshDefenses = useCallback(() => {
    api.briefings.defenseMap().then(data => {
      const m = new Map<string, number>()
      data.defenses.forEach(d => m.set(d.tree_id, d.count))
      setDefendedIds(m)
    }).catch(() => {})
  }, [])

  const handleTreeClick = useCallback((tree: TreeSummary) => {
    const permit = pickPermitForTree(tree, permits)
    setSelectedTree(tree)
    setSelectedPermit(permit)
    setPanel('tree')
    resetWorkflow()
    if (permit?.developer_id) {
      api.developers.get(permit.developer_id).then(setDeveloper).catch(() => {})
    }
  }, [permits, resetWorkflow])

  const jumpToNextThreat = useCallback(async () => {
    const pool = threatenedPermits.length > 0 ? threatenedPermits : permits
    if (pool.length === 0) return

    const permit = pool[jumpIndexRef.current % pool.length]
    jumpIndexRef.current += 1

    if (permit.center?.coordinates) {
      mapFlyToRef.current?.(permit.center.coordinates[0], permit.center.coordinates[1])
    }

    // Auto-open the case panel for the first threatened tree on this permit
    const treeId = permit.threatened_tree_ids?.[0]
    if (treeId) {
      try {
        const full = await api.trees.get(treeId)
        const summary: TreeSummary = {
          id: full.id,
          species: full.species?.common ?? (full.species as unknown as string),
          lng: full.location?.coordinates?.[0] ?? 0,
          lat: full.location?.coordinates?.[1] ?? 0,
          health: full.health,
          ecosystem_total_usd: full.ecosystem_value_usd_yr?.total_usd ?? 0,
          diameter_in: full.diameter_in,
        }
        setSelectedTree(summary)
        setSelectedPermit(permit)
        setPanel('tree')
        resetWorkflow()
        if (permit.developer_id) {
          api.developers.get(permit.developer_id).then(setDeveloper).catch(() => {})
        }
      } catch {
        // fly-to still happened; user can click a tree manually
      }
    }
  }, [threatenedPermits, permits, resetWorkflow])

  const closePanel = useCallback(() => {
    setPanel('closed')
    setSelectedTree(null)
    setSelectedPermit(null)
  }, [])

  const runPipeline = useCallback(async () => {
    if (!selectedPermit) return
    setPanel('running')
    setEvents([])
    setCompletedSteps(new Set())
    setActiveStep('coalition')
    setBriefing(null)
    setDraft('')
    setBriefingId(null)

    let bid: string
    try {
      const result = await api.briefings.trigger(selectedPermit.id)
      bid = result.briefing_id
      setBriefingId(bid)

      // Permit already has a submitted briefing — show the case file but keep
      // the submit button open so this person can add their own defense.
      if (result.status === 'already_submitted' && result.briefing) {
        const b = result.briefing as import('@/lib/types').Briefing
        setBriefing(b)
        if (b.draft_comment) setDraft(b.draft_comment)
        setSubmitted(false)   // leave submit button visible
        setPanel('draft')
        return
      }
    } catch {
      setEvents([{ event: 'error', data: { message: 'Failed to start the pipeline. Check that the backend is running.' } }])
      return
    }

    const es = new EventSource(`${BASE}/stream/briefings/${bid}`)
    es.onmessage = e => {
      try {
        const evt: AgentEvent = JSON.parse(e.data)
        setEvents(prev => [...prev, evt])

        const stepId = EVENT_TO_STEP[evt.event]
        if (stepId) setCompletedSteps(prev => {
          const next = new Set(prev)
          next.add(stepId)
          return next
        })
        if (evt.event.endsWith('_start')) setActiveStep(evt.event.replace('_start', ''))

        if (evt.event === 'briefing_complete') {
          // Poll until draft_comment arrives, then show the panel immediately.
          // Strategy/evidence arrive in a second write — handled by strategy_complete below.
          const poll = async () => {
            for (let i = 0; i < 20; i++) {
              const b = await api.briefings.get(bid)
              if (b?.draft_comment) {
                setBriefing(b)
                if (b.draft_comment) setDraft(b.draft_comment)
                setPanel('draft')
                // Don't close the stream yet — wait for strategy_complete
                return
              }
              await new Promise(r => setTimeout(r, 1000))
            }
          }
          poll()
        }

        // Strategy is saved in a second MongoDB write after the comment.
        // Refetch the briefing so the Case File fills in without page reload.
        if (evt.event === 'strategy_complete') {
          api.briefings.get(bid).then(b => {
            if (b) {
              setBriefing(b)
              if (b.draft_comment) setDraft(b.draft_comment)
            }
          }).catch(() => {})
        }

        if (evt.event === 'error') {
          es.close()
        }

        if (evt.event === 'done') {
          es.close()
          // Final fetch — ensures the complete briefing (with strategy) is in state.
          api.briefings.get(bid).then(b => {
            if (b) {
              setBriefing(b)
              if (b.draft_comment) setDraft(b.draft_comment)
              setPanel('draft')
            }
          }).catch(() => {})
        }
      } catch {}
    }
    es.onerror = () => es.close()
  }, [selectedPermit])

  const threatCount = threatenedIds.size
  const selectedDaysLeft = selectedPermit ? daysUntil(selectedPermit.comment_deadline) : null

  return (
    <main className="radar-shell">
      <TreeMap
        onTreeClick={handleTreeClick}
        highlightedIds={threatCount > 0 ? threatenedIds : undefined}
        defendedIds={defendedIds.size > 0 ? defendedIds : undefined}
        selectedTreeId={selectedTree?.id ?? null}
        mapStyle={mapStyle}
        onFlyToReady={fn => { mapFlyToRef.current = fn }}
      />

      <div className="radar-vignette" aria-hidden />
      <div className="radar-scanline" aria-hidden />

      <header className="radar-header">
        <Link href="/" className="brand-lockup" aria-label="ROOT home">
          <Mark />
          <span>ROOT</span>
        </Link>
        <div className="header-actions">
          <button className="chip-button chip-button--alert" onClick={jumpToNextThreat} disabled={permits.length === 0}>
            <span className="pulse-dot" />
            {threatCount > 0 ? `${threatCount} threatened trees` : permits.length > 0 ? 'Active permits loaded' : 'No permits loaded'}
          </button>
          <button
            className="chip-button"
            onClick={() => setMapStyle(s => s === 'satellite' ? 'dark' : s === 'dark' ? 'light' : 'satellite')}
          >
            View: {mapStyle}
          </button>
          <Link href="/developers" className="chip-link">Ledger</Link>
          <button
            className={`chip-button inbox-bell${unreadCount > 0 ? ' inbox-bell--active' : ''}`}
            onClick={() => {
              setInboxOpen(o => !o)
              if (!inboxOpen && unreadCount > 0) {
                notifications.filter(n => !n.read).forEach(n => api.notifications.markRead(n.id).catch(() => {}))
                setTimeout(() => setUnreadCount(0), 300)
              }
            }}
          >
            <BellIcon />
            {unreadCount > 0 && <span className="inbox-badge">{unreadCount}</span>}
          </button>
        </div>
      </header>

      <section className="mission-panel" aria-label="How to use this map">
        <div className="mission-panel__kicker">Guardian map</div>
        <h1>The tree has an agent now.</h1>
        <p>
          Select an amber canopy to open its guardian case. The agent starts with a public intervention,
          then keeps checking permit status, replacement planting, survival, and developer compliance over time.
        </p>
        <div className="mission-steps">
          <div className={panel === 'closed' ? 'is-current' : ''}>
            <strong>1</strong>
            <span>Assign the guardian</span>
          </div>
          <div className={panel === 'tree' ? 'is-current' : ''}>
            <strong>2</strong>
            <span>Open the case timeline</span>
          </div>
          <div className={panel === 'running' || panel === 'draft' ? 'is-current' : ''}>
            <strong>3</strong>
            <span>Start Day 1 action</span>
          </div>
        </div>
        <button className="primary-action" onClick={jumpToNextThreat} disabled={permits.length === 0}>
          Activate a guardian case
          <ArrowIcon />
        </button>
      </section>

      {panel === 'closed' && (
        <div className="map-callout">
          <span className="callout-pin" />
          <div>
            <strong>{threatCount > 0 ? 'Amber canopies are removal permits' : 'Click a canopy to inspect it'}</strong>
            <p>{threatCount > 0 ? 'Pick one to see the agent assigned to that tree.' : 'The panel will explain what the guardian would track.'}</p>
          </div>
        </div>
      )}

      <aside className={`case-panel ${panel !== 'closed' ? 'is-open' : ''}`} aria-label="Selected tree workflow">
        <PanelHeader panel={panel} onClose={closePanel} />

        {panel === 'tree' && selectedTree && (
          <TreePanel
            tree={selectedTree}
            permit={selectedPermit}
            developer={developer}
            daysLeft={selectedDaysLeft}
            onRun={runPipeline}
            hasThreats={threatCount > 0}
            defenseCount={defendedIds.get(selectedTree.id)}
          />
        )}

        {panel === 'running' && selectedTree && (
          <RunningPanel
            tree={selectedTree}
            events={events}
            completedSteps={completedSteps}
            activeStep={activeStep}
            logRef={logRef}
          />
        )}

        {panel === 'draft' && (
          <DraftPanel
            briefing={briefing}
            selectedTree={selectedTree}
            selectedPermit={selectedPermit}
            daysLeft={selectedDaysLeft}
            draft={draft}
            setDraft={setDraft}
            submitted={submitted}
            submitting={submitting}
            briefingId={briefingId}
            setSubmitting={setSubmitting}
            setSubmitted={setSubmitted}
            setSubmitResult={setSubmitResult}
            submitResult={submitResult}
            copied={copied}
            setCopied={setCopied}
            closePanel={closePanel}
            outcome={outcome}
            setOutcome={setOutcome}
            trackingOutcome={trackingOutcome}
            setTrackingOutcome={setTrackingOutcome}
            onRequestSubmit={() => setEmailModal('submit')}
            pendingEmail={pendingEmail}
            onSubmitWithEmail={async (email: string) => {
              setSubmitting(true)
              try {
                if (briefingId) {
                  const result = await api.briefings.submit(briefingId, email)
                  setSubmitResult(result)
                }
                if (draft) { try { await navigator.clipboard.writeText(draft); setCopied(true) } catch {} }
                refreshDefenses()
              } catch {}
              setSubmitting(false)
              setSubmitted(true)
            }}
          />
        )}
      </aside>

      {inboxOpen && (
        <InboxPanel
          notifications={notifications}
          onClose={() => setInboxOpen(false)}
        />
      )}

      {emailModal && (
        <EmailModal
          value={emailInput}
          onChange={setEmailInput}
          onConfirm={email => {
            setPendingEmail(email)
            setEmailInput('')
            setEmailModal(null)
            setSubmitting(true)
            ;(async () => {
              try {
                if (briefingId) {
                  const result = await api.briefings.submit(briefingId, email)
                  setSubmitResult(result)
                }
                if (draft) { try { await navigator.clipboard.writeText(draft); setCopied(true) } catch {} }
                refreshDefenses()
              } catch {}
              setSubmitting(false)
              setSubmitted(true)
            })()
          }}
          onCancel={() => {
            setEmailModal(null)
            setEmailInput('')
          }}
        />
      )}
    </main>
  )
}

function PanelHeader({ panel, onClose }: { panel: PanelState; onClose: () => void }) {
  const title =
    panel === 'tree' ? 'Guardian case' :
    panel === 'running' ? 'Agent activation' :
    panel === 'draft' ? 'Day 1 intervention' :
    'No tree selected'

  return (
    <div className="case-panel__header">
      <div>
        <span>Current case</span>
        <strong>{title}</strong>
      </div>
      <button className="icon-button" onClick={onClose} aria-label="Close panel">
        <CloseIcon />
      </button>
    </div>
  )
}

function TreePanel({
  tree,
  permit,
  developer,
  daysLeft,
  onRun,
  hasThreats,
  defenseCount,
}: {
  tree: TreeSummary
  permit: Permit | null
  developer: Developer | null
  daysLeft: number | null
  onRun: () => void
  hasThreats: boolean
  defenseCount?: number
}) {
  const invasive = INVASIVE_SPECIES.has(tree.species)
  const survivalRate = developer ? Math.round(developer.compliance_rate * 100) : permit?.developer_compliance_rate !== undefined
    ? Math.round(permit.developer_compliance_rate * 100)
    : null
  const promised = developer?.promised_replacements ?? permit?.promised_replacements ?? 0
  const surviving = developer?.verified_surviving ?? 0
  const missingSurvival = Math.max(0, promised - surviving)
  const ecosystemDebt = Math.round(missingSurvival * Math.max(1200, tree.ecosystem_total_usd * 30))

  return (
    <div className="case-panel__body">
      {defenseCount != null && defenseCount > 0 && (
        <div className="defense-notice">
          <span className="defense-notice__icon">✓</span>
          <div>
            <strong>{defenseCount} defense{defenseCount !== 1 ? 's' : ''} already filed</strong>
            <p>Community advocacy is on record for this tree. Your intervention adds to the accountability pressure — filing again still matters.</p>
          </div>
        </div>
      )}
      <section className="tree-identity">
        <div className={`canopy-token ${permit ? 'is-threat' : invasive ? 'is-invasive' : ''}`}>
          <span />
        </div>
        <div>
          <span className="section-label">{permit ? 'Guardian assigned' : 'Selected canopy'}</span>
          <h2>{tree.species}</h2>
          <p>{permit ? 'This tree now has persistent representation in the civic system.' : 'No active threat is attached to this tree yet.'}</p>
        </div>
      </section>

      <div className="metrics-grid">
        <Metric label="Annual value" value={`$${Math.round(tree.ecosystem_total_usd).toLocaleString()}`} />
        <Metric label="Thirty year value" value={`$${Math.round(tree.ecosystem_total_usd * 30).toLocaleString()}`} />
        <Metric label="Health" value={tree.health} />
        <Metric label="Developer survival" value={survivalRate !== null ? `${survivalRate}%` : 'Unknown'} />
      </div>

      <GuardianTimeline active={!!permit} />

      {permit ? (
        <section className="threat-card">
          <div className="section-label">Active removal permit</div>
          <h3>{permit.address}</h3>
          <p>{formatProject(permit.project_type)} requested by {permit.developer_id}.</p>
          <div className="deadline-strip">
            <span>Comment clock</span>
            <strong>{daysLeft !== null && daysLeft > 0 ? `${daysLeft} days left` : 'Deadline passed'}</strong>
          </div>
          {permit.enforcement_flag && (
            <div className="warning-line">Enhanced review triggered by replacement compliance history.</div>
          )}
        </section>
      ) : (
        <section className="quiet-card">
          <div className="section-label">No removal permit attached</div>
          <p>
            This tree can be inspected, but the action workflow begins on amber canopies.
            {hasThreats ? ' Use the map controls to jump to an active permit.' : ' Permit data is not loaded yet.'}
          </p>
        </section>
      )}

      {developer && <DeveloperCard developer={developer} />}

      {permit && (
        <section className="debt-card">
          <span className="section-label">Ecosystem service debt</span>
          <h3>${ecosystemDebt.toLocaleString()}</h3>
          <p>
            Estimated value of promised canopy services not yet verified as surviving. This becomes part of the next permit review packet.
          </p>
          <p className="debt-methodology">
            <abbr title="Unverified replacement trees × max($1,200 floor, i-Tree annual value × 30-year present value). Methodology: i-Tree Eco v6, USDA Forest Service.">Methodology ⓘ</abbr>
          </p>
        </section>
      )}

      <div className="panel-action-block">
        <p>{permit ? 'Next step: start the Day 1 intervention. The guardian will keep the future checks on schedule.' : 'Next step: choose an amber tree with an active removal permit.'}</p>
        <button className="primary-action primary-action--wide" onClick={onRun} disabled={!permit}>
          Start Day 1 intervention
          <ArrowIcon />
        </button>
      </div>
    </div>
  )
}

function GuardianTimeline({ active }: { active: boolean }) {
  return (
    <section className={`guardian-timeline ${active ? 'is-active' : ''}`}>
      <div className="guardian-timeline__intro">
        <span className="section-label">Guardian lifecycle</span>
        <h3>{active ? 'This case does not end today.' : 'What a guardian tracks'}</h3>
        <p>
          ROOT keeps working after the comment. Scheduled checks turn promises into verified outcomes.
        </p>
      </div>
      <div className="guardian-timeline__rail">
        {GUARDIAN_TIMELINE.map(item => (
          <article key={item.when} className={item.state === 'now' && active ? 'is-now' : ''}>
            <span>{item.when}</span>
            <div>
              <h4>{item.title}</h4>
              <p>{item.body}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

function RunningPanel({
  tree,
  events,
  completedSteps,
  activeStep,
  logRef,
}: {
  tree: TreeSummary
  events: AgentEvent[]
  completedSteps: Set<string>
  activeStep: string | null
  logRef: React.RefObject<HTMLDivElement>
}) {
  const developerEvent = [...events].reverse().find(event => event.event === 'developer_loaded')
  const coalitionEvent = [...events].reverse().find(event => event.event === 'coalition_complete')
  const exposureScore = _exposureScoreFromDeveloper(developerEvent?.data, coalitionEvent?.data)
  const complianceRate = Number(developerEvent?.data?.compliance_rate ?? NaN)
  const atRisk = Number(developerEvent?.data?.at_risk_replacements ?? 0)
  const violations = Number(developerEvent?.data?.violations_count ?? 0)

  return (
    <div className="case-panel__body">
      <section className="pipeline-hero">
        <span className="section-label">Guardian waking up</span>
        <h2>{tree.species}</h2>
        <p>The tree agent is opening the case, assembling evidence, and preparing the first intervention.</p>
      </section>

      <section className={`exposure-drop ${exposureScore !== null ? 'is-locked' : ''}`}>
        <span className="section-label">Developer exposure before draft</span>
        <div className="exposure-drop__score">
          <strong>{exposureScore !== null ? exposureScore : '—'}</strong>
          <span>/100 cumulative exposure</span>
        </div>
        {developerEvent ? (
          <>
            <p>
              {String(developerEvent.data.name ?? 'Developer')} is now attached to a case record:
              {' '}{Number.isFinite(complianceRate) ? _fmtPct(complianceRate) : 'unknown'} survival,
              {' '}{atRisk} replacements below target,
              {' '}{violations} documented violations.
            </p>
            <div className="exposure-drop__stamp">Ledger evidence locked before Gemini writes a word</div>
          </>
        ) : (
          <p>Waiting on the developer ledger. The draft stays secondary until the accountability record is assembled.</p>
        )}
      </section>

      <div className="pipeline-list">
        {STEP_LABELS.map(step => {
          const done = completedSteps.has(step.id)
          const active = activeStep === step.id
          return (
            <div key={step.id} className={done ? 'is-done' : active ? 'is-active' : ''}>
              <span />
              <strong>{step.label}</strong>
            </div>
          )
        })}
      </div>

      <div className="event-console" ref={logRef}>
        {events.length === 0 ? (
          <p>Connecting to guardian stream</p>
        ) : events.map((event, index) => {
          const data = event.data as Record<string, unknown>
          const label = event.event === 'atlas_read'
            ? `MongoDB Atlas ${data.op as string} ${data.collection as string}`
            : event.event === 'error'
            ? `Error: ${data.message as string}`
            : event.event === 'warning'
            ? `⚠ ${data.message as string}`
            : EVENT_LABEL[event.event] ?? event.event
          return <p key={`${event.event}-${index}`} className={event.event === 'error' ? 'is-error' : event.event === 'warning' ? 'is-warning' : ''}>{label}</p>
        })}
      </div>
    </div>
  )
}

function _fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

type SubmitResultShape = {
  guardian_schedule: { day90: string; month12: string; month36: string; year5: string }
  permit_address: string; nyc_dob_url: string; nyc_parks_email: string; maps_url: string
}

function _fmtPct(value: number): string {
  return `${Math.round(value * 100)}%`
}

function _exposureScoreFromDeveloper(data?: Record<string, unknown>, coalition?: Record<string, unknown>): number | null {
  if (!data) return null
  const rate = Number(data.compliance_rate ?? 0)
  const violations = Number(data.violations_count ?? 0)
  const atRisk = Number(data.at_risk_replacements ?? 0)
  const treeCount = Number(coalition?.tree_count ?? 0)
  const ejTier = String(coalition?.ej_tier ?? '')
  return Math.min(100, Math.round(
    (Math.max(0, 0.85 - rate) * 55)
    + Math.min(violations * 8, 24)
    + Math.min(atRisk * 2.5, 18)
    + Math.min(treeCount * 0.9, 14)
    + (ejTier === 'High' ? 8 : 0)
  ))
}

function _tierClass(tier?: string): string {
  if (tier === 'critical') return 'cf-tier--critical'
  if (tier === 'high')     return 'cf-tier--high'
  if (tier === 'elevated') return 'cf-tier--elevated'
  return 'cf-tier--compliant'
}

function _developerTier(rate: number): 'critical' | 'high' | 'elevated' | 'compliant' {
  if (rate < 0.4) return 'critical'
  if (rate < 0.6) return 'high'
  if (rate < 0.85) return 'elevated'
  return 'compliant'
}

function _deriveEvidence(briefing: Briefing | null): Briefing['evidence_board'] | undefined {
  if (briefing?.evidence_board) return briefing.evidence_board
  const coalition = briefing?.coalition_summary
  const developer = briefing?.developer_snapshot
  if (!coalition || !developer) return undefined
  const top = briefing.precedent_refs?.[0]
  const exposure = _exposureScoreFromDeveloper(
    {
      compliance_rate: developer.compliance_rate,
      violations_count: developer.violations_count,
      at_risk_replacements: developer.at_risk_replacements ?? 0,
    },
    {
      tree_count: coalition.tree_count,
      ej_tier: coalition.ej_tier,
    },
  ) ?? 0

  return {
    developer: {
      name: developer.name,
      compliance_rate: developer.compliance_rate,
      city_target: developer.city_target ?? 0.85,
      permits_filed: developer.permits_filed,
      promised_replacements: developer.promised_replacements,
      verified_surviving: developer.verified_surviving,
      violations_count: developer.violations_count,
      linked_entity_count: 0,
      at_risk_replacements: developer.at_risk_replacements ?? 0,
      cumulative_exposure_score: exposure,
    },
    coalition: {
      tree_count: coalition.tree_count,
      canopy_sqft: coalition.canopy_sqft,
      stormwater_gal_yr: coalition.stormwater_gal_yr,
      total_ecosystem_usd_yr: coalition.total_ecosystem_usd_yr,
      ej_tier: coalition.ej_tier,
      heat_vulnerable_residents: coalition.heat_vulnerable_residents,
    },
    top_precedent: top ? {
      title: top.title,
      outcome: top.outcome,
      year: top.year,
      similarity_score: top.similarity_score,
      arguments_used: top.arguments_used,
    } : null,
    policy_count: briefing.policy_refs?.length ?? 0,
    policy_titles: briefing.policy_refs?.slice(0, 4).map(policy => policy.title) ?? [],
  }
}

function _deriveStrategy(briefing: Briefing | null, evidence?: Briefing['evidence_board']): Briefing['intervention_strategy'] | undefined {
  if (briefing?.intervention_strategy) return briefing.intervention_strategy
  if (!evidence) return undefined
  const rate = evidence.developer.compliance_rate
  const tier = _developerTier(rate)
  const exposure = evidence.developer.cumulative_exposure_score ?? 0
  const target = evidence.developer.city_target ?? 0.85
  const gap = Math.round(Math.max(0, target - rate) * 100)
  const reasons: string[] = []

  if (rate < target) {
    reasons.push(`${evidence.developer.name} is ${gap} pts below the city replacement survival target`)
  }
  if (evidence.developer.violations_count > 0) {
    reasons.push(`${evidence.developer.violations_count} documented violation(s) attached to prior permits`)
  }
  if (evidence.coalition.ej_tier === 'High') {
    reasons.push(`High EJ burden: ${evidence.coalition.heat_vulnerable_residents.toLocaleString()} heat-vulnerable residents in the affected tract`)
  }
  if (evidence.coalition.total_ecosystem_usd_yr >= 1000) {
    reasons.push(`Threatened coalition provides $${evidence.coalition.total_ecosystem_usd_yr.toLocaleString()}/yr in ecosystem services`)
  }
  if (evidence.top_precedent?.outcome) {
    reasons.push(`Similar case (${evidence.top_precedent.title}) was ${evidence.top_precedent.outcome.replace(/_/g, ' ')}`)
  }

  const recommended_action =
    tier === 'critical' ? 'ESCALATE — DENY OR REQUIRE MAJOR CONDITIONS' :
    tier === 'high' || evidence.coalition.ej_tier === 'High' ? 'ESCALATE WITH ENFORCEABLE CONDITIONS' :
    tier === 'elevated' ? 'FILE COMMENT WITH STANDARD CONDITIONS' :
    'APPROVE WITH MONITORING'

  return {
    recommended_action,
    confidence: exposure >= 40 ? 'High' : exposure >= 20 ? 'Medium' : 'Low',
    developer_risk_tier: tier,
    cumulative_exposure_score: exposure,
    best_argument: rate < target ? 'developer_compliance_history' : 'replacement_survival_rate',
    best_argument_rationale: rate < target
      ? `${evidence.developer.name} has a ${Math.round(rate * 100)}% verified replacement survival rate, ${gap} points below the city's ${Math.round(target * 100)}% benchmark. This directly challenges whether the replacement promise is credible.`
      : 'Replacement survival should remain attached to the permit record so future approvals inherit the verified outcome.',
    reasons,
    requested_conditions: [
      'Performance bond covering replacement planting and survival verification',
      'Independent arborist inspection and photo-documented survival report at 12, 36, and 60 months',
      'GPS-tagged planting records submitted to NYC Parks ForMS within 30 days of installation',
      'Species diversity requirement: minimum 3 approved native species in replacement plan',
      'Public survival status updates attached to future permit applications by this developer',
    ],
    precedent_signal: evidence.top_precedent ?? undefined,
  }
}

function DraftPanel({
  briefing,
  selectedTree,
  selectedPermit,
  daysLeft,
  draft,
  setDraft,
  submitted,
  submitting,
  briefingId,
  setSubmitting,
  setSubmitted,
  setSubmitResult,
  submitResult,
  copied,
  setCopied,
  closePanel,
  outcome,
  setOutcome,
  trackingOutcome,
  setTrackingOutcome,
  onRequestSubmit,
  pendingEmail: _pendingEmail,
  onSubmitWithEmail: _onSubmitWithEmail,
}: {
  briefing: import('@/lib/types').Briefing | null
  selectedTree: TreeSummary | null
  selectedPermit: Permit | null
  daysLeft: number | null
  draft: string
  setDraft: (value: string) => void
  submitted: boolean
  submitting: boolean
  briefingId: string | null
  setSubmitting: (value: boolean) => void
  setSubmitted: (value: boolean) => void
  setSubmitResult: (value: SubmitResultShape | null) => void
  submitResult: SubmitResultShape | null
  copied: boolean
  setCopied: (v: boolean) => void
  closePanel: () => void
  outcome: { acknowledged: boolean; conditions: string[]; notes: string } | null
  setOutcome: (value: { acknowledged: boolean; conditions: string[]; notes: string } | null) => void
  trackingOutcome: boolean
  setTrackingOutcome: (value: boolean) => void
  onRequestSubmit: () => void
  pendingEmail: string
  onSubmitWithEmail: (email: string) => void
}) {
  const evidence  = _deriveEvidence(briefing)
  const strategy  = _deriveStrategy(briefing, evidence)
  const tierClass = _tierClass(strategy?.developer_risk_tier)
  const gs: Record<string,string> | undefined =
    submitResult?.guardian_schedule ??
    (briefing?.guardian_schedule as Record<string,string> | undefined)

  // Always build the mailto from the live draft textarea so edits are included.
  // Do NOT use submitResult.nyc_parks_email — it was truncated at storage time.
  const parksEmailAddress = 'UrbanForestry@parks.nyc.gov'
  const parksSubject = `Public Comment — Tree Removal Permit: ${selectedPermit?.address ?? ''}`
  const parksEmail = `mailto:${parksEmailAddress}?subject=${encodeURIComponent(parksSubject)}&body=${encodeURIComponent(draft)}`

  const exposureScore = strategy?.cumulative_exposure_score
    ?? evidence?.developer?.cumulative_exposure_score
    ?? null
  const targetPct = evidence?.developer?.city_target !== undefined
    ? Math.round(evidence.developer.city_target * 100)
    : 85

  return (
    <div className="case-panel__body cf">

      {/* ══ 1. DECISION BANNER ══════════════════════════════════════════ */}
      <header className="cf__header">
        <div className="cf__header-kicker">Tree Protection Case File</div>
        <div className="cf__header-address">
          {selectedPermit?.address ?? selectedTree?.species ?? '—'}
        </div>
        <div className="cf__header-pills">
          {daysLeft !== null && (
            <span className={`cf__pill${daysLeft <= 7 ? ' cf__pill--urgent' : ''}`}>
              {daysLeft > 0 ? `${daysLeft}d to deadline` : 'Deadline passed'}
            </span>
          )}
          {submitted && <span className="cf__pill cf__pill--open">● Guardian open</span>}
        </div>
      </header>

      <div className={`cf__verdict ${tierClass}`}>
        <div className="cf__verdict-row">
          <div>
            <div className="cf__verdict-label">Recommended action</div>
            <div className="cf__verdict-action">
              {strategy?.recommended_action ?? <span className="cf__loading">Computing strategy…</span>}
            </div>
          </div>
          {strategy?.confidence && (
            <div className="cf__verdict-badge">{strategy.confidence}</div>
          )}
        </div>
        <div className="cf__verdict-stats">
          {strategy?.developer_risk_tier && <span>Developer risk: <strong>{strategy.developer_risk_tier.toUpperCase()}</strong></span>}
          {exposureScore !== null && <span>Exposure score: <strong>{exposureScore}/100</strong></span>}
          {evidence?.coalition?.tree_count != null && <span><strong>{evidence.coalition.tree_count}</strong> trees threatened</span>}
          <span>{submitted ? 'Guardian: 5-year monitoring scheduled' : 'Guardian: activates on publication'}</span>
        </div>
        {strategy?.reasons && strategy.reasons.length > 0 && (
          <ul className="cf__reasons">
            {strategy.reasons.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        )}
      </div>

      <section className="cf__exposure">
        <div>
          <span className="cf__ev-label">Cumulative developer exposure</span>
          <strong>{exposureScore !== null ? `${exposureScore}/100` : 'Pending'}</strong>
          <p>
            {evidence
              ? `${evidence.developer.name} is now tied to ${evidence.developer.permits_filed} prior permits, ${evidence.developer.promised_replacements} promised replacements, ${evidence.developer.verified_surviving} verified survivors, and ${evidence.developer.violations_count} documented violations.`
              : 'ROOT is assembling the developer ledger before presenting the draft.'}
          </p>
        </div>
        <div className="cf__exposure-stamp">{evidence ? 'Dossier ready' : 'Assembling'}</div>
      </section>

      <section className="cf__consequence">
        <span className="cf__ev-label">If nothing is filed</span>
        <p>Without a formal objection, this permit proceeds to approval with no replacement verification requirement.</p>
      </section>

      {/* ══ 2. AGENT STRATEGY ═══════════════════════════════════════════ */}
      <section className="cf__section">
        <h3 className="cf__section-title">Agent Strategy</h3>
        {strategy ? (
          <div className="cf__strategy">
            <div className="cf__strategy-arg">
              <div className="cf__ev-label">Best argument</div>
              <div className="cf__strategy-arg-name">{strategy.best_argument.replace(/_/g, ' ')}</div>
              <p className="cf__strategy-rationale">{strategy.best_argument_rationale}</p>
            </div>
            {strategy.requested_conditions.length > 0 && (
              <div className="cf__conditions">
                <div className="cf__ev-label">Conditions to demand</div>
                <ol className="cf__conditions-list">
                  {strategy.requested_conditions.map((c, i) => <li key={i}>{c}</li>)}
                </ol>
              </div>
            )}
            {strategy.precedent_signal?.title && (
              <div className="cf__strategy-precedent">
                <div className="cf__ev-label">Supporting precedent</div>
                <div>{strategy.precedent_signal.title} — <strong>{strategy.precedent_signal.outcome?.replace(/_/g, ' ')}</strong> ({strategy.precedent_signal.year}) · {Math.round((strategy.precedent_signal.similarity_score ?? 0) * 100)}% semantic match</div>
              </div>
            )}
          </div>
        ) : (
          <div className="cf__skeleton-block">Agent strategy computing…</div>
        )}
      </section>

      {/* ══ 3. EVIDENCE BOARD ═══════════════════════════════════════════ */}
      <section className="cf__section">
        <h3 className="cf__section-title">Evidence Board</h3>
        {evidence ? (
          <div className="cf__evidence">
            <div className="cf__ev-card">
              <div className="cf__ev-label">Developer record</div>
              <div className="cf__ev-name">{evidence.developer.name}</div>
              <div className="cf__ev-stat">
                <span className={`cf__compliance-pct${evidence.developer.compliance_rate < 0.85 ? ' cf__compliance-pct--bad' : ''}`}>
                  {Math.round(evidence.developer.compliance_rate * 100)}%
                </span>
                <span className="cf__ev-sub">survival vs {targetPct}% city target</span>
              </div>
              <div className="cf__ev-row">
                <span>{evidence.developer.promised_replacements} promised</span>
                <span>{evidence.developer.verified_surviving} surviving</span>
                <span>{evidence.developer.violations_count} violations</span>
              </div>
              {evidence.developer.linked_entity_count > 0 && (
                <div className="cf__ev-flag">⚠ {evidence.developer.linked_entity_count} linked {evidence.developer.linked_entity_count === 1 ? 'entity' : 'entities'}</div>
              )}
            </div>
            <div className="cf__ev-card">
              <div className="cf__ev-label">Coalition at risk</div>
              <div className="cf__ev-stat">
                <span className="cf__ev-big">{evidence.coalition.tree_count}</span>
                <span className="cf__ev-sub">trees threatened</span>
              </div>
              <div className="cf__ev-row"><span>{evidence.coalition.canopy_sqft.toLocaleString()} sq ft canopy</span></div>
              <div className="cf__ev-row"><span className="cf__ev-value">${evidence.coalition.total_ecosystem_usd_yr.toLocaleString()}/yr</span></div>
              <div className="cf__ev-row">
                <span>EJ <strong>{evidence.coalition.ej_tier}</strong> · {evidence.coalition.heat_vulnerable_residents.toLocaleString()} heat-vulnerable</span>
              </div>
            </div>
            {evidence.top_precedent && (
              <div className="cf__ev-card">
                <div className="cf__ev-label">Closest precedent</div>
                <div className="cf__ev-name cf__ev-name--mono">{evidence.top_precedent.title}</div>
                <div className="cf__ev-row">
                  <span className="cf__ev-outcome">{evidence.top_precedent.outcome.replace(/_/g, ' ')}</span>
                  <span>{evidence.top_precedent.year}</span>
                  <span>{Math.round(evidence.top_precedent.similarity_score * 100)}% match</span>
                </div>
              </div>
            )}
            {evidence.policy_titles.length > 0 && (
              <div className="cf__ev-card">
                <div className="cf__ev-label">Policy conflicts ({evidence.policy_count})</div>
                {evidence.policy_titles.map((t, i) => <div key={i} className="cf__ev-policy">{t}</div>)}
              </div>
            )}
          </div>
        ) : (
          <div className="cf__skeleton-grid">
            <div className="cf__skeleton-block" /><div className="cf__skeleton-block" />
            <div className="cf__skeleton-block" /><div className="cf__skeleton-block" />
          </div>
        )}
      </section>

      {/* ══ 4. PUBLIC COMMENT DRAFT ═════════════════════════════════════ */}
      <section className="cf__section">
        <h3 className="cf__section-title">
          ROOT drafts. You authorize.
          <span className="cf__section-note"> Civic filings stay human-reviewed by design.</span>
        </h3>
        <p className="cf__authorization-note">
          ROOT assembled the evidence and drafted the intervention. You review the record, edit the language, and decide what gets published.
        </p>
        <textarea
          id="draft-comment"
          value={draft}
          onChange={e => setDraft(e.target.value)}
          className="cf__comment"
          placeholder="Gemini is writing your intervention package…"
        />
      </section>

      {/* ══ 5. ACTION BUTTONS ═══════════════════════════════════════════ */}
      <section className="cf__section">
        <h3 className="cf__section-title">
          {submitted ? 'Published accountability actions' : 'Publishing actions unlock after authorization'}
        </h3>
        <div className="cf__actions">
          <a
            className={`cf__action-primary${!submitted ? ' cf__action-primary--dim' : ''}`}
            href={submitted ? parksEmail : undefined}
            onClick={!submitted ? e => e.preventDefault() : undefined}
          >
            → File with NYC Parks Urban Forestry
          </a>
          <div className="cf__action-row">
            {submitted && submitResult?.nyc_dob_url && (
              <a className="cf__action" href={submitResult.nyc_dob_url} target="_blank" rel="noopener noreferrer">NYC DOB ↗</a>
            )}
            <a
              className={`cf__action${!submitted ? ' cf__action--dim' : ''}`}
              href={submitted ? 'https://portal.311.nyc.gov/' : undefined}
              target={submitted ? '_blank' : undefined}
              rel="noopener noreferrer"
              onClick={!submitted ? e => e.preventDefault() : undefined}
            >NYC 311 ↗</a>
            <button className="cf__action" onClick={async () => { await navigator.clipboard?.writeText(draft); setCopied(true) }}>
              {copied ? '✓ Copied' : 'Copy'}
            </button>
          </div>
        </div>
        {submitted && gs?.day90 && (
          <div className="cf__guardian-active">● Intervention logged in ROOT's public accountability record — Day 90 check: {_fmtDate(gs.day90)}</div>
        )}
      </section>

      {/* ══ 6. GUARDIAN PLAN ════════════════════════════════════════════ */}
      <section className="cf__section">
        <h3 className="cf__section-title">Closing statement: five-year guardian plan</h3>
        <p className="cf__guardian-statement">
          ROOT will check this permit on Day 90, Month 12, Month 36, and Year 5. The developer's compliance record will update automatically regardless of what happens today.
        </p>
        <div className="cf__guardian">
          {([
            { key: 'day90' as const,   when: 'Day 90',   title: 'Permit status check',   body: 'Verify permit was approved, modified, denied, or expired. Update the tree record.' },
            { key: 'month12' as const, when: 'Month 12', title: 'Planting promise audit', body: 'Cross-reference promised replacements with NYC Parks ForMS records. Flag missing plantings.' },
            { key: 'month36' as const, when: 'Month 36', title: 'Survival check',         body: 'Verify replacement trees via inspection records. Update developer ledger.' },
            { key: 'year5' as const,   when: 'Year 5',   title: 'Case closure',           body: 'Record final compliance and attach to developer permanent permit history.' },
          ]).map(({ key, when, title, body }) => (
            <div key={when} className={`cf__guardian-step${key === 'day90' && submitted ? ' cf__guardian-step--next' : ''}`}>
              <div className="cf__guardian-when">
                <span>{when}</span>
                {gs?.[key] && <span className="cf__guardian-date">{_fmtDate(gs[key]!)}</span>}
              </div>
              <div className="cf__guardian-content">
                <strong>{title}</strong>
                <p>{body}</p>
              </div>
            </div>
          ))}
          <div className="cf__guardian-step cf__guardian-step--enforce">
            <div className="cf__guardian-when"><span>If fail</span></div>
            <div className="cf__guardian-content">
              <strong>Enforcement trigger</strong>
              <p>Developer flagged on future permits · failure record attached · enforcement letter generated.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ══ CTA FOOTER ══════════════════════════════════════════════════ */}
      {submitted ? (
        <div className="cf__submitted-footer">
          <OutcomeBlock
            permitId={selectedPermit?.id ?? ''}
            briefingId={briefingId ?? undefined}
            outcome={outcome}
            setOutcome={setOutcome}
            trackingOutcome={trackingOutcome}
            setTrackingOutcome={setTrackingOutcome}
          />
          <button className="secondary-action secondary-action--wide" onClick={closePanel}>← Back to map</button>
        </div>
      ) : (
        <div className="cf__submit">
          {briefing?.guardian_emails && briefing.guardian_emails.length > 0 && (
            <div className="cf__prior-defenses">
              ✓ {briefing.guardian_emails.length} defender{briefing.guardian_emails.length !== 1 ? 's' : ''} already watching this permit — add your defense below.
            </div>
          )}
          <p className="cf__submit-hint">
            Review the comment above, then publish to ROOT&apos;s accountability record.
            You&apos;ll receive email updates as the guardian checks run.
          </p>
          <button
            className="primary-action primary-action--wide"
            disabled={submitting}
            onClick={() => onRequestSubmit()}
          >
            <SendIcon />
            {submitting ? 'Publishing…' : briefing?.status === 'submitted' ? 'Add your defense' : 'Publish Day 1 intervention'}
          </button>
        </div>
      )}

    </div>
  )
}

function OutcomeBlock({
  permitId,
  briefingId,
  outcome,
  setOutcome,
  trackingOutcome,
  setTrackingOutcome,
}: {
  permitId: string
  briefingId?: string
  outcome: { acknowledged: boolean; conditions: string[]; notes: string } | null
  setOutcome: (value: { acknowledged: boolean; conditions: string[]; notes: string } | null) => void
  trackingOutcome: boolean
  setTrackingOutcome: (value: boolean) => void
}) {
  return (
    <section className="outcome-block">
      <span className="section-label">Close the loop</span>
      <p>When the city responds or a scheduled audit completes, add the result here. ROOT uses it to update the permanent survival score.</p>
      {outcome ? (
        <div className="saved-outcome">Outcome saved to the ledger.</div>
      ) : trackingOutcome ? (
        <OutcomeForm
          permitId={permitId}
          briefingId={briefingId}
          onSaved={setOutcome}
          onCancel={() => setTrackingOutcome(false)}
        />
      ) : (
        <button className="secondary-action secondary-action--wide" onClick={() => setTrackingOutcome(true)}>
          Record outcome
        </button>
      )}
    </section>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-tile">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function _riskTier(rate: number): { tier: string; color: string; bg: string } {
  if (rate < 0.40) return { tier: 'CRITICAL', color: '#b91c1c', bg: '#fef2f2' }
  if (rate < 0.60) return { tier: 'HIGH', color: '#b45309', bg: '#fffbeb' }
  if (rate < 0.85) return { tier: 'ELEVATED', color: '#d97706', bg: '#fffbeb' }
  return { tier: 'COMPLIANT', color: '#15803d', bg: '#f0fdf4' }
}

function DeveloperCard({ developer }: { developer: Developer }) {
  const pct = Math.round(developer.compliance_rate * 100)
  const weak = developer.compliance_rate < 0.85
  const { tier } = _riskTier(developer.compliance_rate)
  const networkCount = developer.linked_entities?.length ?? 0
  const missing = Math.max(0, developer.promised_replacements - developer.verified_surviving)
  const exposure = Math.min(100, Math.round(
    (Math.max(0, 0.85 - developer.compliance_rate) * 55)
    + Math.min(developer.violations.length * 8, 24)
    + Math.min(missing * 1.5, 18)
  ))

  return (
    <section className={`developer-card ${weak ? 'is-weak' : ''}`}>
      <div className="developer-card__head">
        <div>
          <span className="section-label">Developer ledger</span>
          <h3>{developer.name}</h3>
          <p>{developer.permits_filed} prior permits, {developer.violations.length} violations</p>
          {networkCount > 0 && (
            <p className="developer-card__entity">
              +{networkCount} linked {networkCount === 1 ? 'entity' : 'entities'}
            </p>
          )}
        </div>
        <span className={`developer-card__risk${tier === 'COMPLIANT' ? ' is-compliant' : ''}`}>
          {tier}
        </span>
      </div>
      <div className="developer-card__exposure">
        <div>
          <strong>{exposure}</strong>
          <span>/100 exposure</span>
        </div>
        <p>Permanent ledger pressure before any public comment is filed.</p>
      </div>
      <div className="compliance-meter">
        <strong>{pct}%</strong>
        <span style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
      </div>
      <p>{developer.promised_replacements} promised replacements, {developer.verified_surviving} verified surviving.</p>
    </section>
  )
}

function OutcomeForm({
  permitId,
  briefingId,
  onSaved,
  onCancel,
}: {
  permitId: string
  briefingId?: string
  onSaved: (outcome: { acknowledged: boolean; conditions: string[]; notes: string }) => void
  onCancel: () => void
}) {
  const [acknowledged, setAcknowledged] = useState(false)
  const [conditions, setConditions] = useState<string[]>([])
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [verification, setVerification] = useState<VerificationResult | null>(null)

  const options = [
    ['surety_bond', 'Surety bond required'],
    ['independent_audit', 'Independent arborist audit'],
    ['species_diversity', 'Species diversity mandate'],
    ['gps_tracking', 'GPS tagged planting records'],
    ['phased_review', 'Phased review at 1, 3, and 5 years'],
  ] as const

  const verify = async () => {
    setVerifying(true)
    setVerification(null)
    try {
      const result = await api.outcomes.verify(permitId, {
        permit_id: permitId,
        briefing_id: briefingId,
        comment_acknowledged: acknowledged,
        conditions_imposed: conditions,
        notes,
      })
      setVerification(result)
    } catch {}
    setVerifying(false)
  }

  const save = async () => {
    setSaving(true)
    try {
      await api.outcomes.record({
        permit_id: permitId,
        briefing_id: briefingId,
        comment_acknowledged: acknowledged,
        conditions_imposed: conditions,
        notes,
      })
    } catch {}
    setSaving(false)
    onSaved({ acknowledged, conditions, notes })
  }

  return (
    <div className="outcome-form">
      <label>
        <input type="checkbox" checked={acknowledged} onChange={e => { setAcknowledged(e.target.checked); setVerification(null) }} />
        Agency acknowledged the comment
      </label>
      {options.map(([value, label]) => (
        <label key={value}>
          <input
            type="checkbox"
            checked={conditions.includes(value)}
            onChange={e => { setConditions(prev => e.target.checked ? [...prev, value] : prev.filter(item => item !== value)); setVerification(null) }}
          />
          {label}
        </label>
      ))}
      <textarea value={notes} onChange={e => { setNotes(e.target.value); setVerification(null) }} placeholder="Outcome notes" />

      {verification && (
        <div className={`outcome-verification ${verification.verified ? 'is-verified' : 'is-flagged'}`}>
          <div className="outcome-verification__header">
            <span>{verification.verified ? '✓' : '⚠'} Agent verification — {verification.confidence} confidence</span>
          </div>
          <p>{verification.summary}</p>
          {verification.flags.length > 0 && (
            <ul>{verification.flags.map((f, i) => <li key={i}>{f}</li>)}</ul>
          )}
        </div>
      )}

      <div className="outcome-actions">
        <button className="secondary-action" onClick={verify} disabled={verifying || saving}>
          {verifying ? 'Verifying…' : 'Verify with agent'}
        </button>
        <button className="primary-action" onClick={save} disabled={saving}>{saving ? 'Saving' : 'Save outcome'}</button>
        <button className="secondary-action" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  )
}

function InboxPanel({
  notifications,
  onClose,
}: {
  notifications: GuardianNotification[]
  onClose: () => void
}) {
  const [expanded, setExpanded] = useState<string | null>(null)

  const typeIcon: Record<string, string> = {
    guardian_activated: '🛡',
    guardian_day90: '📋',
    guardian_month12: '🌱',
    guardian_month36: '📊',
    guardian_year5: '✓',
  }

  function formatRelativeTime(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'just now'
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  return (
    <div className="inbox-panel">
      <div className="inbox-panel__header">
        <div>
          <span className="inbox-panel__title">Guardian Inbox</span>
          <span className="inbox-panel__sub">Autonomous follow-ups · real emails when SMTP is configured</span>
        </div>
        <button className="icon-button" onClick={onClose} aria-label="Close inbox">
          <CloseIcon />
        </button>
      </div>

      {notifications.length === 0 ? (
        <div className="inbox-empty">
          <p>No guardian notifications yet.</p>
          <p>Submit a Day 1 intervention to activate the guardian — the first email arrives immediately.</p>
        </div>
      ) : (
        <div className="inbox-list">
          {notifications.map(n => (
            <article
              key={n.id}
              className={`inbox-item${!n.read ? ' inbox-item--unread' : ''}${expanded === n.id ? ' inbox-item--expanded' : ''}`}
              onClick={() => setExpanded(e => e === n.id ? null : n.id)}
            >
              <div className="inbox-item__row">
                <span className="inbox-item__icon">{typeIcon[n.type] ?? '📬'}</span>
                <div className="inbox-item__meta">
                  <div className="inbox-item__subject">{n.subject}</div>
                  <div className="inbox-item__from">ROOT Guardian System · {formatRelativeTime(n.created_at)}</div>
                </div>
                {!n.read && <span className="inbox-item__dot" />}
              </div>
              {expanded === n.id && (
                <div className="inbox-item__body">
                  <pre>{n.body}</pre>
                </div>
              )}
            </article>
          ))}
        </div>
      )}

      <div className="inbox-panel__footer">
        <span>SMTP configured → real emails to your inbox</span>
        <span>See .env → NOTIFICATION_EMAIL</span>
      </div>
    </div>
  )
}

function EmailModal({
  value,
  onChange,
  onConfirm,
  onCancel,
}: {
  value: string
  onChange: (v: string) => void
  onConfirm: (email: string) => void
  onCancel: () => void
}) {
  const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)

  return (
    <div className="email-modal-overlay" onClick={onCancel}>
      <div className="email-modal" onClick={e => e.stopPropagation()}>
        <div className="email-modal__header">
          <strong>Publish Day 1 Intervention</strong>
          <button className="icon-button" onClick={onCancel}><CloseIcon /></button>
        </div>
        <p className="email-modal__desc">
          Enter your email. ROOT will send you an activation confirmation and automatically
          notify you when the guardian runs its next check.
        </p>
        <div className="email-modal__field">
          <label htmlFor="email-input">Your email address</label>
          <input
            id="email-input"
            type="email"
            value={value}
            onChange={e => onChange(e.target.value)}
            placeholder="you@example.com"
            autoFocus
            onKeyDown={e => { if (e.key === 'Enter' && isValid) onConfirm(value) }}
          />
        </div>
        <div className="email-modal__actions">
          <button className="primary-action" disabled={!isValid} onClick={() => onConfirm(value)}>
            Publish &amp; activate guardian
          </button>
          <button className="secondary-action" onClick={onCancel}>Cancel</button>
        </div>
      </div>
    </div>
  )
}
