'use client'

import Link from 'next/link'

function Mark() {
  return (
    <span className="root-mark" aria-hidden>
      <span />
    </span>
  )
}

function ArrowIcon() {
  return (
    <svg width="17" height="17" viewBox="0 0 17 17" fill="none" aria-hidden>
      <path d="M2.5 8.5h11M9.5 4.5l4 4-4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function MiniRadar() {
  const points = [
    [18, 28, 'good'], [34, 22, 'fair'], [53, 31, 'threat'], [76, 24, 'good'],
    [22, 55, 'threat'], [44, 52, 'good'], [64, 60, 'invasive'], [83, 53, 'fair'],
    [16, 78, 'good'], [38, 79, 'threat'], [58, 76, 'good'], [79, 80, 'good'],
  ] as const

  return (
    <div className="home-radar" aria-hidden>
      <div className="home-radar__map">
        {points.map(([x, y, type], index) => (
          <span key={index} className={`home-radar__point is-${type}`} style={{ left: `${x}%`, top: `${y}%` }} />
        ))}
      </div>
      <div className="home-radar__caption">
        <strong>Guardian agents live here</strong>
        <span>Amber canopies have active cases and scheduled follow-ups.</span>
      </div>
    </div>
  )
}

export default function LandingPage() {
  return (
    <main className="home-shell">
      <div className="home-texture" aria-hidden />

      <nav className="home-nav">
        <Link href="/" className="brand-lockup" aria-label="ROOT home">
          <Mark />
          <span>ROOT</span>
        </Link>
        <div className="header-actions">
          <Link href="/developers" className="chip-link">Ledger</Link>
          <Link href="/map" className="chip-link">Map</Link>
          <Link href="/sources" className="chip-link">Sources</Link>
        </div>
      </nav>

      <section className="home-hero">
        <div className="home-copy">
          <span className="mission-panel__kicker">Persistent civic agents for urban trees</span>
          <h1>Every threatened street tree gets a guardian.</h1>
          <p>
            ROOT assigns a persistent agent to each tree touched by a removal permit. The agent wakes up,
            builds the intervention package, tracks replacement promises for five years, and updates the
            developer survival score forever.
          </p>
          <div className="home-actions">
            <Link href="/map" className="primary-action">
              Open guardian map
              <ArrowIcon />
            </Link>
            <Link href="/developers" className="secondary-action">Review ledger</Link>
          </div>
        </div>

        <MiniRadar />
      </section>

      <section className="home-proof">
        <article>
          <span>01</span>
          <h2>Agent activates</h2>
          <p>A permit wakes the tree agent. It forms the affected coalition and opens the case record.</p>
        </article>
        <article>
          <span>02</span>
          <h2>Promises are tracked</h2>
          <p>The agent watches permit status, planting records, inspections, and missed deadlines.</p>
        </article>
        <article>
          <span>03</span>
          <h2>Ledger is permanent</h2>
          <p>Survival outcomes attach to the developer profile and every future permit they file.</p>
        </article>
      </section>
    </main>
  )
}
