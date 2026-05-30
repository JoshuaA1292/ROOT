'use client'

import Link from 'next/link'

function Mark() {
  return (
    <span className="root-mark" aria-hidden>
      <span />
    </span>
  )
}

const SOURCES = [
  {
    id: 'nyc_street_tree_census_2015',
    name: 'NYC 2015 Street Tree Census',
    publisher: 'NYC Parks & Recreation',
    license: 'NYC Open Data — Public Domain',
    url: 'https://data.cityofnewyork.us/Environment/2015-Street-Tree-Census-Tree-Data/uvpi-gqnh',
    apiUrl: 'https://data.cityofnewyork.us/resource/uvpi-gqnh.json',
    recordCount: '683,788 trees',
    usedFor: 'Tree location (GPS), species, diameter at breast height (DBH), health status',
    verify: 'https://data.cityofnewyork.us/Environment/2015-Street-Tree-Census-Tree-Data/uvpi-gqnh',
    note: 'Conducted by 2,000+ volunteers coordinated by NYC Parks. This is the authoritative record of every street tree in New York City by address and GPS coordinate.',
  },
  {
    id: 'usda_itree',
    name: 'USDA i-Tree Eco — Ecosystem Valuation',
    publisher: 'USDA Forest Service',
    license: 'Public domain / USDA open access',
    url: 'https://www.itreetools.org/tools/itree-eco',
    apiUrl: null,
    recordCount: 'Methodology reference',
    usedFor: 'Annual ecosystem service valuations: stormwater (gal/yr), CO₂ (lbs/yr), cooling energy (kWh/yr), air quality ($/yr)',
    verify: 'https://www.itreetools.org/tools/itree-eco',
    note: 'ROOT applies per-inch-DBH annual benefit coefficients for NYC\'s climate zone. Stormwater: $0.14/gal (NYC DEP). CO₂: $0.045/lb ($100/ton, EPA 2023). Electricity: $0.22/kWh (ConEd 2024). Air quality: $3.20/in-DBH-yr.',
  },
  {
    id: 'epa_ejscreen',
    name: 'EPA EJScreen — Environmental Justice Screening',
    publisher: 'U.S. Environmental Protection Agency',
    license: 'U.S. Government Work — Public Domain',
    url: 'https://www.epa.gov/ejscreen',
    apiUrl: 'https://ejscreen.epa.gov/mapper/ejscreenRESTbroker.aspx',
    recordCount: 'Census-tract level, all U.S.',
    usedFor: 'Heat vulnerability percentile scores by census tract. Flags permits in environmental justice communities.',
    verify: 'https://www.epa.gov/ejscreen/download-ejscreen-data',
    note: 'The heat vulnerability index (HVEI) in EJScreen is especially relevant to tree canopy loss, which amplifies urban heat island effects in low-income and minority communities.',
  },
  {
    id: 'nyc_dob',
    name: 'NYC DOB Job Application Filings',
    publisher: 'NYC Department of Buildings',
    license: 'NYC Open Data — Public Domain',
    url: 'https://data.cityofnewyork.us/Housing-Development/DOB-Job-Application-Filings/ic3t-wcy2',
    apiUrl: 'https://data.cityofnewyork.us/resource/ic3t-wcy2.json',
    recordCount: '3M+ filings (live feed)',
    usedFor: 'New building (NB) and major alteration (A2) permits that trigger tree removal review.',
    verify: 'https://data.cityofnewyork.us/Housing-Development/DOB-Job-Application-Filings/ic3t-wcy2',
    note: 'ROOT cross-references DOB job filings with NYC Parks tree work permits to identify cases where construction projects threaten street trees in their pit buffer zone.',
  },
  {
    id: 'nyc_parks_tree_work',
    name: 'NYC Parks — Tree Work Orders (ForMS)',
    publisher: 'NYC Parks & Recreation',
    license: 'NYC Open Data — Public Domain',
    url: 'https://data.cityofnewyork.us/Recreation/Forestry-Tree-Work-Requests/5rq2-4hqu',
    apiUrl: 'https://data.cityofnewyork.us/resource/5rq2-4hqu.json',
    recordCount: 'Active and historical work orders',
    usedFor: 'Follow-up planting verification at 12 months and 36 months. Checks whether promised replacement trees were planted and survived.',
    verify: 'https://data.cityofnewyork.us/Recreation/Forestry-Tree-Work-Requests/5rq2-4hqu',
    note: 'The Forestry Management System (ForMS) is the authoritative Parks database for tree work. The public extract is used by ROOT\'s survival check agents to verify planting outcomes.',
  },
  {
    id: 'nyc_admin_code',
    name: 'NYC Administrative Code § 18-107',
    publisher: 'NYC Council',
    license: 'Public law',
    url: 'https://codelibrary.amlegal.com/codes/newyorkcity/latest/NYCadmin/0-0-0-30551',
    apiUrl: null,
    recordCount: 'Statute',
    usedFor: 'Legal citation in public comments. Governs street tree protections and replacement requirements for construction projects.',
    verify: 'https://codelibrary.amlegal.com/codes/newyorkcity/latest/NYCadmin/0-0-0-30551',
    note: 'Requires developers to obtain a permit and provide replacement trees for any street tree removed. ROOT cites this in every generated public comment to ground the intervention in existing NYC law.',
  },
  {
    id: 'onenyc_2050',
    name: 'OneNYC 2050 — 30% Urban Tree Canopy Target',
    publisher: "NYC Mayor's Office of Long-Term Planning",
    license: 'Public policy document',
    url: 'https://onenyc.cityofnewyork.us/',
    apiUrl: null,
    recordCount: 'Policy commitment',
    usedFor: 'Benchmark cited in ROOT\'s impact calculations. NYC committed to 30% canopy cover by 2035; developer replacement compliance is a key instrument.',
    verify: 'https://onenyc.cityofnewyork.us/initiatives/a-livable-climate/',
    note: 'As of 2020, NYC canopy cover was approximately 22%. Every permitted tree removal that results in no replacement moves the city further from its own stated target. ROOT makes that gap visible.',
  },
]

export default function SourcesPage() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--paper)', color: 'var(--ink)' }}>

      {/* Nav */}
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 28px', borderBottom: '2px solid var(--ink)',
        background: 'var(--chalk)',
      }}>
        <Link href="/" className="brand-lockup" style={{ color: 'var(--ink)' }}>
          <Mark />
          <span style={{ fontFamily: 'var(--font-heavy)', fontSize: 20, color: 'var(--ink)' }}>ROOT</span>
        </Link>
        <div className="header-actions">
          <Link href="/map" className="chip-link">Map</Link>
          <Link href="/developers" className="chip-link">Ledger</Link>
        </div>
      </nav>

      <main style={{ maxWidth: 820, margin: '0 auto', padding: '48px 28px 80px' }}>

        {/* Header */}
        <div style={{ marginBottom: 48, borderBottom: '2px solid var(--ink)', paddingBottom: 32 }}>
          <span className="mission-panel__kicker" style={{ marginBottom: 12 }}>Data provenance</span>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(36px, 5vw, 60px)', fontWeight: 900, lineHeight: 0.92, margin: '0 0 20px' }}>
            Every number<br />is verifiable.
          </h1>
          <p style={{ fontSize: 15, lineHeight: 1.7, color: 'var(--ink-soft)', maxWidth: 560 }}>
            ROOT is built entirely on publicly available government datasets and peer-reviewed USDA methodology.
            Every tree location, valuation figure, permit record, and compliance rate can be independently verified
            through the sources below. We link directly to the original records.
          </p>
        </div>

        {/* Sources */}
        <div style={{ display: 'grid', gap: 2 }}>
          {SOURCES.map((src, i) => (
            <div key={src.id} style={{
              padding: '24px',
              border: '2px solid var(--ink)',
              background: i % 2 === 0 ? 'var(--chalk)' : 'var(--paper)',
              marginBottom: 0,
            }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', marginBottom: 14 }}>
                <div>
                  <span style={{ display: 'block', fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--permit-dark)', marginBottom: 6 }}>
                    {src.publisher}
                  </span>
                  <h2 style={{ margin: 0, fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700, lineHeight: 1.1 }}>
                    {src.name}
                  </h2>
                </div>
                <a
                  href={src.verify}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="secondary-action"
                  style={{ fontSize: 11, padding: '8px 14px', minHeight: 36, flexShrink: 0 }}
                >
                  Verify ↗
                </a>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10, marginBottom: 16 }}>
                <div style={{ padding: '10px', border: '1px solid var(--line)', background: 'rgba(255,247,223,0.5)' }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', marginBottom: 4, color: 'var(--violet-brown)' }}>Records</div>
                  <div style={{ fontFamily: 'var(--font-display)', fontSize: 17 }}>{src.recordCount}</div>
                </div>
                <div style={{ padding: '10px', border: '1px solid var(--line)', background: 'rgba(255,247,223,0.5)' }}>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', marginBottom: 4, color: 'var(--violet-brown)' }}>License</div>
                  <div style={{ fontFamily: 'var(--font-display)', fontSize: 17 }}>{src.license}</div>
                </div>
              </div>

              <div style={{ marginBottom: 10 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: 'var(--violet-brown)', letterSpacing: '0.06em' }}>Used for: </span>
                <span style={{ fontSize: 13 }}>{src.usedFor}</span>
              </div>

              <p style={{ margin: '0 0 14px', fontSize: 13, lineHeight: 1.6, color: 'var(--ink-soft)' }}>
                {src.note}
              </p>

              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <a
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--canopy-deep)', textDecoration: 'underline' }}
                >
                  {src.url.replace('https://', '')}
                </a>
                {src.apiUrl && (
                  <a
                    href={src.apiUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--violet-brown)', textDecoration: 'underline' }}
                  >
                    API →
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Methodology note */}
        <div style={{ marginTop: 32, padding: '20px 24px', border: '2px solid var(--ink)', background: 'var(--night)', color: 'var(--chalk)' }}>
          <span style={{ display: 'block', fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'rgba(255,247,223,0.55)', marginBottom: 10 }}>
            Methodology note
          </span>
          <p style={{ margin: 0, fontSize: 13, lineHeight: 1.7, color: 'rgba(255,247,223,0.8)' }}>
            Developer compliance rates are calculated from NYC Parks ForMS planting inspection records matched by permit number and address.
            Survival figures reflect GPS-tagged plantings only — unverified or undocumented replacements are not counted.
            Phase 1 compliance records for Brooklyn developers were manually structured from publicly available DOB filings and Parks inspection data.
            The ROOT pipeline automates enrichment and verification as new records arrive.
            All ecosystem valuations use the updated USDA i-Tree per-inch-DBH methodology with 2024 NYC utility and regulatory pricing.
          </p>
        </div>

        {/* Footer nav */}
        <div style={{ marginTop: 40, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <Link href="/developers" className="primary-action" style={{ fontSize: 12 }}>View compliance ledger</Link>
          <Link href="/map" className="secondary-action" style={{ fontSize: 12 }}>Open guardian map</Link>
        </div>
      </main>
    </div>
  )
}
