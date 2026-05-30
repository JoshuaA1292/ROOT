'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'
import type { Developer, Permit, DeveloperRiskIntelligence, EntityNetwork } from '@/lib/types'

const CITY_TARGET = 0.85

function riskTier(rate: number): 'critical' | 'high' | 'elevated' | 'compliant' {
  if (rate < 0.4) return 'critical'
  if (rate < 0.6) return 'high'
  if (rate < CITY_TARGET) return 'elevated'
  return 'compliant'
}

function exposureScore(dev: Developer, treeExposure = 0): number {
  const missing = Math.max(0, dev.promised_replacements - dev.verified_surviving)
  return Math.min(100, Math.round(
    (Math.max(0, CITY_TARGET - dev.compliance_rate) * 55)
    + Math.min(dev.violations.length * 8, 24)
    + Math.min(missing * 1.5, 18)
    + Math.min(treeExposure * 0.9, 14)
  ))
}

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return 'No active deadline'
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function DeveloperPage({ params }: { params: { id: string } }) {
  const [dev, setDev] = useState<Developer | null>(null)
  const [permits, setPermits] = useState<Permit[]>([])
  const [intel, setIntel] = useState<DeveloperRiskIntelligence | null>(null)
  const [network, setNetwork] = useState<EntityNetwork | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.developers.get(params.id),
      api.permits.list(),
      api.developers.getRiskIntelligence(params.id).catch(() => null),
      api.developers.getNetwork(params.id).catch(() => null),
    ]).then(([d, ps, ri, net]) => {
      setDev(d)
      setPermits(ps.filter(p => p.developer_id === params.id))
      setIntel(ri)
      setNetwork(net)
      setLoading(false)
    }).catch(() => {
      setError('Developer not found.')
      setLoading(false)
    })
  }, [params.id])

  if (loading) {
    return (
      <main className="ledger-page">
        <div className="ledger-loading">Loading developer ledger</div>
      </main>
    )
  }

  if (error || !dev) {
    return (
      <main className="ledger-page">
        <div className="ledger-empty">
          <strong>{error || 'Developer not found'}</strong>
          <Link href="/map">Back to ROOT map</Link>
        </div>
      </main>
    )
  }

  const pct = Math.round(dev.compliance_rate * 100)
  const targetPct = Math.round(CITY_TARGET * 100)
  const gap = pct - targetPct
  const missingTrees = Math.max(0, dev.promised_replacements - dev.verified_surviving)
  const activeTrees = intel?.active_exposure.trees_at_risk ?? permits.reduce((sum, permit) => sum + (permit.threatened_tree_ids?.length ?? 0), 0)
  const score = exposureScore(dev, activeTrees)
  const tier = intel?.risk_profile?.risk_tier ?? riskTier(dev.compliance_rate)

  return (
    <main className="ledger-page">
      <header className="ledger-nav">
        <Link href="/map" className="brand-lockup" aria-label="ROOT map">
          <span className="root-mark"><span /></span>
          <span>ROOT</span>
        </Link>
        <div className="header-actions">
          <Link href="/developers" className="chip-link">All developers</Link>
          <Link href="/map" className="chip-link">Map</Link>
        </div>
      </header>

      <section className={`ledger-hero ledger-tier--${tier}`}>
        <div>
          <span className="section-label">Developer accountability ledger</span>
          <h1>{dev.name}</h1>
          {dev.linked_entities.length > 0 && (
            <p>Also operates as: {dev.linked_entities.join(' / ')}</p>
          )}
        </div>
        <div className="ledger-hero__score">
          <strong>{score}</strong>
          <span>/100 cumulative exposure</span>
        </div>
      </section>

      <section className="ledger-grid">
        <article className="ledger-card ledger-card--primary">
          <div className="ledger-card__label">Replacement survival record</div>
          <div className="ledger-survival">
            <strong>{pct}%</strong>
            <span>{gap >= 0 ? '+' : ''}{gap} pts vs {targetPct}% city target</span>
          </div>
          <div className="ledger-bar">
            <div style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
            <span style={{ left: `${targetPct}%` }} />
          </div>
          <div className="ledger-scale">
            <span>0%</span>
            <span>City target: {targetPct}%</span>
            <span>100%</span>
          </div>
        </article>

        <article className="ledger-card ledger-card--dark">
          <div className="ledger-card__label">Current risk tier</div>
          <strong className="ledger-risk">{tier}</strong>
          <p>
            {missingTrees} promised replacement trees are unaccounted for across the ledger.
            Future permits inherit this record automatically.
          </p>
        </article>

        {[
          { value: dev.permits_filed, label: 'Permits filed' },
          { value: dev.promised_replacements, label: 'Trees promised' },
          { value: dev.verified_surviving, label: 'Verified alive' },
          { value: missingTrees, label: 'Unaccounted trees' },
        ].map(item => (
          <article key={item.label} className="ledger-stat">
            <strong>{item.value}</strong>
            <span>{item.label}</span>
          </article>
        ))}
      </section>

      {intel && (
        <section className="ledger-section">
          <div className="ledger-section__head">
            <span className="section-label">MongoDB Atlas intelligence</span>
            <strong>$lookup + $facet + $switch</strong>
          </div>
          <div className="ledger-grid ledger-grid--compact">
            <article className="ledger-stat">
              <strong>{intel.active_exposure.open_permit_count}</strong>
              <span>Open permits</span>
            </article>
            <article className="ledger-stat">
              <strong>{intel.active_exposure.trees_at_risk}</strong>
              <span>Trees at risk</span>
            </article>
            <article className="ledger-stat">
              <strong>{fmtDate(intel.active_exposure.earliest_deadline)}</strong>
              <span>Earliest deadline</span>
            </article>
          </div>

          {intel.compliance_by_year.length > 0 && (
            <div className="ledger-timeline">
              <div className="ledger-card__label">Survival by inspection cohort</div>
              {intel.compliance_by_year.map(row => {
                const rowPct = Math.round(row.survival_rate * 100)
                return (
                  <div key={row._id} className="ledger-timeline__row">
                    <span>{row._id}</span>
                    <div><span style={{ width: `${Math.min(100, Math.max(0, rowPct))}%` }} /></div>
                    <strong>{rowPct}%</strong>
                    <em>{row.surviving}/{row.promised}</em>
                  </div>
                )
              })}
            </div>
          )}
        </section>
      )}

      {network && network.entities?.length > 0 && (
        <section className="ledger-section ledger-section--warning">
          <span className="section-label">Entity network detected</span>
          <h2>True network rate: {Math.round(network.network_compliance_rate * 100)}%</h2>
          <p>
            {network.total_permits_filed} permits / {network.total_promised - network.total_surviving} trees unaccounted /
            {' '}{network.combined_violations} violations across related entities.
          </p>
          <div className="ledger-entities">
            {network.all_entity_names.map(name => <span key={name}>{name}</span>)}
          </div>
        </section>
      )}

      {dev.violations.length > 0 && (
        <section className="ledger-section">
          <span className="section-label">Documented violations</span>
          <div className="ledger-violations">
            {dev.violations.map((violation, index) => (
              <div key={`${violation.permit_id}-${index}`}>
                <strong>{violation.type.replace(/_/g, ' ')}</strong>
                <span>{violation.count} trees / {violation.year} / {violation.permit_id}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {permits.length > 0 && (
        <section className="ledger-section">
          <span className="section-label">Active permits attached to this ledger</span>
          <div className="ledger-permits">
            {permits.map(permit => {
              const daysLeft = Math.ceil((new Date(permit.comment_deadline).getTime() - Date.now()) / 86400000)
              return (
                <Link key={permit.id} href={`/permit/${permit.id}`}>
                  <strong>{permit.address}</strong>
                  <span>{permit.project_type.replace(/_/g, ' ')} / {permit.threatened_tree_ids.length} trees / {daysLeft > 0 ? `${daysLeft}d left` : 'expired'}</span>
                </Link>
              )
            })}
          </div>
        </section>
      )}
    </main>
  )
}
