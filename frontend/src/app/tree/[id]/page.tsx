'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'
import type { Tree } from '@/lib/types'

export default function TreeDossierPage({ params }: { params: { id: string } }) {
  const [tree, setTree] = useState<Tree | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.trees.get(params.id).then(setTree).catch(console.error).finally(() => setLoading(false))
  }, [params.id])

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--void)' }}>
      <div className="space-y-3 text-center">
        <div
          className="w-8 h-8 border-2 rounded-full animate-spin mx-auto"
          style={{ borderColor: 'rgba(74,222,128,0.2)', borderTopColor: '#4ade80' }}
        />
        <div className="text-xs animate-pulse" style={{ color: 'rgba(74,222,128,0.4)', fontFamily: 'IBM Plex Mono' }}>Loading tree record...</div>
      </div>
    </div>
  )

  if (!tree) return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--void)' }}>
      <div className="text-sm" style={{ color: 'rgba(240,253,244,0.35)' }}>Tree not found.</div>
    </div>
  )

  const ev = tree.ecosystem_value_usd_yr
  const age = tree.planted_year ? new Date().getFullYear() - tree.planted_year : null

  const healthColor =
    tree.health.toLowerCase() === 'good' ? '#4ade80' :
    tree.health.toLowerCase() === 'fair' ? '#fbbf24' : '#fb923c'

  return (
    <div className="min-h-screen" style={{ background: 'var(--void)', color: '#f0fdf4' }}>
      {/* header */}
      <header
        className="sticky top-0 z-10 px-6 py-3.5 flex items-center gap-4"
        style={{ background: 'rgba(5,13,5,0.92)', borderBottom: '1px solid rgba(255,255,255,0.06)', backdropFilter: 'blur(16px)' }}
      >
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
        <span style={{ color: 'rgba(255,255,255,0.08)' }}>|</span>
        <div className="min-w-0">
          <h1 className="font-bold text-base leading-tight truncate" style={{ fontFamily: 'Syne', color: '#f0fdf4' }}>{tree.species.common}</h1>
          <p className="text-xs italic" style={{ color: 'rgba(240,253,244,0.3)', fontFamily: 'DM Sans' }}>{tree.species.latin}</p>
        </div>
        <span
          className="ml-auto text-xs font-semibold px-2.5 py-1 rounded-full shrink-0"
          style={{
            background: `${healthColor}14`,
            border: `1px solid ${healthColor}33`,
            color: healthColor,
            fontFamily: 'DM Sans',
          }}
        >
          {tree.health}
        </span>
      </header>

      <div className="relative max-w-3xl mx-auto px-6 py-8 space-y-6">

        {/* identity card */}
        <div
          className="rounded-2xl p-6"
          style={{ background: 'rgba(74,222,128,0.04)', border: '1px solid rgba(74,222,128,0.12)' }}
        >
          <div className="flex items-start gap-5 mb-5">
            {/* stylised tree glyph */}
            <div
              className="shrink-0 w-14 h-20 rounded-xl flex flex-col items-center justify-end pb-1 gap-0.5"
              style={{ background: 'rgba(74,222,128,0.06)', border: '1px solid rgba(74,222,128,0.1)' }}
            >
              <div
                className="rounded-full"
                style={{
                  width: Math.min(48, 16 + tree.diameter_in * 1.2),
                  height: Math.min(40, 12 + tree.diameter_in * 0.9),
                  background: 'radial-gradient(ellipse at 40% 35%, #4ade80, #15803d)',
                  opacity: tree.health.toLowerCase() === 'good' ? 1 : 0.55,
                }}
              />
              <div className="w-2 rounded-sm" style={{ height: 10, background: 'rgba(255,255,255,0.15)' }} />
            </div>
            <div>
              <div className="text-2xl font-bold" style={{ fontFamily: 'Syne', color: '#f0fdf4' }}>{tree.diameter_in}" DBH</div>
              <div className="text-sm mt-0.5" style={{ color: 'rgba(240,253,244,0.4)', fontFamily: 'DM Sans' }}>Diameter at breast height</div>
              {age && (
                <div className="text-xs mt-1" style={{ color: 'rgba(240,253,244,0.25)', fontFamily: 'IBM Plex Mono' }}>~{age} years old</div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Field label="Address" value={tree.address} />
            <Field label="Borough" value={tree.borough} />
            <Field label="Health" value={tree.health} />
            <Field label="Status" value={tree.status} />
            <Field label="Census tract" value={tree.census_tract} />
            <Field label="Heat vulnerability" value={`${tree.ej_score.heat_vuln_pct.toFixed(0)}th percentile`} />
          </div>
        </div>

        {/* ecosystem services */}
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <h2 className="font-semibold text-sm" style={{ fontFamily: 'Syne', color: '#f0fdf4' }}>Annual Ecosystem Services</h2>
            <div className="h-px flex-1" style={{ background: 'rgba(255,255,255,0.06)' }} />
          </div>
          <p className="text-xs" style={{ color: 'rgba(240,253,244,0.25)', fontFamily: 'DM Sans' }}>Source: USDA i-Tree Benefits methodology, NYC climate zone</p>

          <div className="grid grid-cols-2 gap-3">
            <ValueCard label="Stormwater intercepted" value={`${ev.stormwater_gal.toLocaleString()} gal/yr`} sub={`$${ev.stormwater_usd.toFixed(2)}/yr`} />
            <ValueCard label="Carbon stored" value={`${ev.co2_lbs.toLocaleString()} lbs/yr`} sub={`$${ev.co2_usd.toFixed(2)}/yr`} />
            <ValueCard label="Cooling energy saved" value={`${ev.cooling_kwh.toFixed(0)} kWh/yr`} sub={`$${ev.cooling_usd.toFixed(2)}/yr`} />
            <ValueCard label="Air quality benefit" value={`$${ev.air_quality_usd.toFixed(2)}/yr`} sub="PM2.5, ozone, NO₂" />
            <ValueCard label="Total annual value" value={`$${ev.total_usd.toFixed(2)}/yr`} sub="Combined ecosystem services" accent />
            <ValueCard label="Lifetime CO₂ (~50yr)" value={`${(ev.co2_lbs * 50).toLocaleString()} lbs`} sub={`~$${((ev.co2_lbs * 50) * 0.021).toFixed(0)} present value`} />
          </div>
        </div>

        <p className="text-[11px] text-center" style={{ color: 'rgba(240,253,244,0.12)', fontFamily: 'IBM Plex Mono' }}>
          Tree ID: {tree.id} · Last inspection: {tree.last_inspection || 'Unknown'} · Synthetic demo data
        </p>
      </div>
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider mb-0.5" style={{ color: 'rgba(240,253,244,0.25)', fontFamily: 'DM Sans' }}>{label}</div>
      <div className="text-sm font-medium" style={{ color: 'rgba(240,253,244,0.75)', fontFamily: 'DM Sans' }}>{value}</div>
    </div>
  )
}

function ValueCard({ label, value, sub, accent }: {
  label: string
  value: string
  sub: string
  accent?: boolean
}) {
  return (
    <div
      className="rounded-xl p-4 transition-all duration-200"
      style={{
        background: accent ? 'rgba(74,222,128,0.07)' : 'rgba(255,255,255,0.025)',
        border: `1px solid ${accent ? 'rgba(74,222,128,0.2)' : 'rgba(255,255,255,0.05)'}`,
      }}
    >
      <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'rgba(240,253,244,0.3)', fontFamily: 'DM Sans' }}>{label}</div>
      <div className="text-lg font-bold" style={{ fontFamily: 'Syne', color: accent ? '#4ade80' : '#f0fdf4' }}>{value}</div>
      <div className="text-[11px] mt-0.5" style={{ color: 'rgba(240,253,244,0.25)', fontFamily: 'DM Sans' }}>{sub}</div>
    </div>
  )
}
