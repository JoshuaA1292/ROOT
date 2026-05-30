'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'
import type { Developer } from '@/lib/types'

const CITY_TARGET = 0.85

function exposureScore(dev: Developer): number {
  const missing = Math.max(0, dev.promised_replacements - dev.verified_surviving)
  return Math.min(100, Math.round(
    (Math.max(0, CITY_TARGET - dev.compliance_rate) * 55)
    + Math.min(dev.violations.length * 8, 24)
    + Math.min(missing * 1.5, 18)
  ))
}

function riskTier(rate: number): string {
  if (rate < 0.4) return 'critical'
  if (rate < 0.6) return 'high'
  if (rate < CITY_TARGET) return 'elevated'
  return 'compliant'
}

export default function DevelopersPage() {
  const [devs, setDevs] = useState<Developer[]>([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.developers.list()
      .then(data => { setDevs(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const filtered = devs.filter(dev =>
    dev.name.toLowerCase().includes(query.toLowerCase()) ||
    dev.linked_entities?.some(entity => entity.toLowerCase().includes(query.toLowerCase()))
  )

  const criticalCount = devs.filter(dev => dev.compliance_rate < 0.6).length
  const unaccounted = devs.reduce((sum, dev) => sum + Math.max(0, dev.promised_replacements - dev.verified_surviving), 0)
  const promised = devs.reduce((sum, dev) => sum + dev.promised_replacements, 0)

  return (
    <main className="ledger-page">
      <header className="ledger-nav">
        <Link href="/map" className="brand-lockup" aria-label="ROOT map">
          <span className="root-mark"><span /></span>
          <span>ROOT</span>
        </Link>
        <div className="header-actions">
          <Link href="/map" className="chip-link">Map</Link>
          <Link href="/sources" className="chip-link">Sources</Link>
        </div>
      </header>

      <section className="ledger-hero ledger-tier--high">
        <div>
          <span className="section-label">Accountability ledger</span>
          <h1>Developer exposure directory</h1>
          <p>
            Every developer with a tree-removal history is sorted by verified replacement survival.
            This is the paper trail future permits inherit.
          </p>
        </div>
        <div className="ledger-hero__score">
          <strong>{criticalCount}</strong>
          <span>critical ledgers</span>
        </div>
      </section>

      <section className="ledger-grid ledger-grid--compact">
        <article className="ledger-stat">
          <strong>{devs.length}</strong>
          <span>Developers tracked</span>
        </article>
        <article className="ledger-stat">
          <strong>{promised}</strong>
          <span>Promised replacements</span>
        </article>
        <article className="ledger-stat">
          <strong>{unaccounted}</strong>
          <span>Unaccounted trees</span>
        </article>
      </section>

      <section className="ledger-section">
        <div className="ledger-section__head">
          <span className="section-label">Search the ledger</span>
          <strong>85% city survival target</strong>
        </div>
        <input
          type="text"
          value={query}
          onChange={event => setQuery(event.target.value)}
          className="ledger-search"
          placeholder="Search developer or linked entity"
        />
      </section>

      <section className="ledger-section">
        <div className="ledger-section__head">
          <span className="section-label">Developer records</span>
          <strong>{filtered.length} shown</strong>
        </div>

        {loading ? (
          <div className="ledger-loading-inline">Loading ledger records</div>
        ) : filtered.length === 0 ? (
          <div className="ledger-loading-inline">No developers found</div>
        ) : (
          <div className="ledger-directory">
            {filtered.map(dev => {
              const pct = Math.round(dev.compliance_rate * 100)
              const score = exposureScore(dev)
              const tier = riskTier(dev.compliance_rate)
              const missing = Math.max(0, dev.promised_replacements - dev.verified_surviving)

              return (
                <Link key={dev.id} href={`/developer/${dev.id}`} className={`ledger-directory__row ledger-tier-row--${tier}`}>
                  <div className="ledger-directory__identity">
                    <span>{tier}</span>
                    <strong>{dev.name}</strong>
                    <p>
                      {dev.permits_filed} permit{dev.permits_filed !== 1 ? 's' : ''} /
                      {' '}{dev.violations.length} violation{dev.violations.length !== 1 ? 's' : ''} /
                      {' '}{dev.linked_entities.length} linked entit{dev.linked_entities.length === 1 ? 'y' : 'ies'}
                    </p>
                  </div>
                  <div className="ledger-directory__meter">
                    <div>
                      <span style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
                      <em style={{ left: `${Math.round(CITY_TARGET * 100)}%` }} />
                    </div>
                    <strong>{pct}% survival</strong>
                  </div>
                  <div className="ledger-directory__number">
                    <strong>{score}</strong>
                    <span>exposure</span>
                  </div>
                  <div className="ledger-directory__number">
                    <strong>{missing}</strong>
                    <span>unaccounted</span>
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </section>

      <section className="ledger-section ledger-section--warning">
        <span className="section-label">Method</span>
        <h2>Survival figures count verified records only.</h2>
        <p>
          Compliance records are built from DOB filings, Parks ForMS planting records, and ROOT reconciliation.
          Unverified replacements do not improve the score.
        </p>
      </section>
    </main>
  )
}
