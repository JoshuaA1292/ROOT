import type { Briefing } from '@/lib/types'

type Snapshot = NonNullable<Briefing['developer_snapshot']>

export default function DeveloperLedger({ snapshot }: { snapshot: Snapshot }) {
  const rate = snapshot.compliance_rate
  const cityTarget = snapshot.city_target ?? 0.85
  const delta = snapshot.target_delta ?? rate - cityTarget
  const atRisk = snapshot.at_risk_replacements ?? Math.max(Math.round(snapshot.promised_replacements * cityTarget) - snapshot.verified_surviving, 0)
  const barWidth = `${Math.min(rate * 100, 100)}%`
  const targetLeft = `${cityTarget * 100}%`
  const weak = rate < cityTarget
  const exposure = Math.min(100, Math.round(
    (Math.max(0, cityTarget - rate) * 55)
    + Math.min(snapshot.violations_count * 8, 24)
    + Math.min(atRisk * 2.5, 18)
  ))

  return (
    <div className={`ledger-dossier ${weak ? 'is-weak' : ''}`}>
      <div className="ledger-dossier__header">
        <div>
          <span className="section-label">Developer ledger</span>
          <h3>{snapshot.name}</h3>
        </div>
        <div className="ledger-dossier__score">
          <strong>{exposure}</strong>
          <span>/100 exposure</span>
        </div>
      </div>

      <div className="ledger-dossier__meter">
        <div className="ledger-dossier__meter-top">
          <span>Replacement survival rate</span>
          <strong>
            {(rate * 100).toFixed(0)}%
            <small>{delta >= 0 ? '+' : ''}{(delta * 100).toFixed(0)} pts vs target</small>
          </strong>
        </div>
        <div className="ledger-dossier__bar">
          <div
            className={rate >= cityTarget ? 'is-good' : rate >= 0.6 ? 'is-warning' : 'is-bad'}
            style={{ width: barWidth }}
          />
          <div
            className="ledger-dossier__target"
            style={{ left: targetLeft }}
            title={`City target: ${(cityTarget * 100).toFixed(0)}%`}
          />
        </div>
        <div className="ledger-dossier__scale">
          <span>0%</span>
          <span>City target: {(cityTarget * 100).toFixed(0)}%</span>
          <span>100%</span>
        </div>
      </div>

      <div className="ledger-dossier__stats">
        <div>
          <strong>{snapshot.permits_filed}</strong>
          <span>Prior permits</span>
        </div>
        <div>
          <strong>{snapshot.promised_replacements}</strong>
          <span>Promised</span>
        </div>
        <div>
          <strong>{snapshot.verified_surviving}</strong>
          <span>Verified alive</span>
        </div>
      </div>

      {atRisk > 0 && (
        <div className="ledger-dossier__notice">
          {atRisk} replacement tree{atRisk !== 1 ? 's' : ''} below the city survival target based on prior promises.
        </div>
      )}

      {snapshot.violations_count > 0 && (
        <div className="ledger-dossier__notice is-danger">
          {snapshot.violations_count} documented violation{snapshot.violations_count !== 1 ? 's' : ''} on record
        </div>
      )}
    </div>
  )
}
