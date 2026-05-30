import type { CoalitionSummary } from '@/lib/types'

const EJ_BADGE = {
  High:   'bg-red-500/15 border-red-500/25 text-red-400',
  Medium: 'bg-yellow-500/15 border-yellow-500/25 text-yellow-400',
  Low:    'bg-green-500/15 border-green-500/25 text-green-400',
}

export default function CoalitionSummaryCard({ data }: { data: CoalitionSummary }) {
  return (
    <div
      className="rounded-xl p-5 space-y-4"
      style={{ background: 'rgba(45,106,79,0.09)', border: '1px solid rgba(116,198,157,0.18)' }}
    >
      <div className="flex items-center justify-between">
        <h3 className="font-display font-semibold text-white">Coalition Impact</h3>
        <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${EJ_BADGE[data.ej_tier]}`}>
          EJ {data.ej_tier} Risk
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Metric value={data.tree_count.toString()}                          label="Trees threatened"       accent />
        <Metric value={`${data.canopy_sqft.toLocaleString()} sq ft`}       label="Canopy lost" />
        <Metric value={`${data.stormwater_gal_yr.toLocaleString()} gal`}   label="Stormwater / yr" />
        <Metric value={`${data.co2_lbs_lifetime.toLocaleString()} lbs`}    label="CO₂ (lifetime)" />
        <Metric value={`$${data.cooling_usd_yr.toLocaleString()}`}         label="Cooling value / yr" />
        <Metric value={`$${data.total_ecosystem_usd_yr.toLocaleString()}`} label="Total value / yr"       accent />
      </div>

      {data.ej_tier === 'High' && data.heat_vulnerable_residents > 0 && (
        <div
          className="text-sm text-red-300/80 rounded-lg p-3 leading-5"
          style={{ background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.12)' }}
        >
          ~{data.heat_vulnerable_residents} residents in a heat-vulnerable census tract lose meaningful shade cover.
        </div>
      )}
    </div>
  )
}

function Metric({ value, label, accent }: { value: string; label: string; accent?: boolean }) {
  return (
    <div
      className="rounded-lg p-3"
      style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
    >
      <div className={`font-display text-xl font-bold ${accent ? 'text-root-leaf' : 'text-white'}`}>{value}</div>
      <div className="text-[10px] text-white/40 mt-0.5 uppercase tracking-wide">{label}</div>
    </div>
  )
}
