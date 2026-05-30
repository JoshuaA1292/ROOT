'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import DeckGL from '@deck.gl/react'
import { ScatterplotLayer, TextLayer } from '@deck.gl/layers'
import type { MapViewState } from '@deck.gl/core'
import MapGL, { type MapRef } from 'react-map-gl/maplibre'
import type { TreeSummary } from '@/lib/types'
import { INVASIVE_SPECIES } from '@/lib/types'
import { api } from '@/lib/api'

const LIGHT_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'
const DARK_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'

const SATELLITE_STYLE = {
  version: 8 as const,
  sources: {
    esri: {
      type: 'raster' as const,
      tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
      tileSize: 256,
      minzoom: 0,
      maxzoom: 19,
      attribution: 'Esri',
    },
    labels: {
      type: 'raster' as const,
      tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}'],
      tileSize: 256,
    },
  },
  layers: [
    { id: 'satellite', type: 'raster' as const, source: 'esri' },
    { id: 'labels', type: 'raster' as const, source: 'labels', paint: { 'raster-opacity': 0.58 } },
  ],
}

type RGBA = [number, number, number, number]

const INITIAL_VIEW: MapViewState = {
  longitude: -73.97,
  latitude: 40.685,
  zoom: 16.1,
  pitch: 42,
  bearing: -18,
}

export interface TreeMapProps {
  onTreeClick: (tree: TreeSummary) => void
  highlightedIds?: Set<string>
  defendedIds?: Map<string, number>
  selectedTreeId?: string | null
  mapStyle?: 'light' | 'dark' | 'satellite'
  onFlyToReady?: (flyTo: (lng: number, lat: number) => void) => void
}

function canopyRadius(dbh: number | undefined): number {
  const diameter = dbh ?? 10
  return Math.max(3.2, diameter * 0.23)
}

function viewToBbox(view: MapViewState, pad = 0.02): string {
  const lng = view.longitude ?? INITIAL_VIEW.longitude
  const lat = view.latitude ?? INITIAL_VIEW.latitude
  return `${lng - pad},${lat - pad * 0.75},${lng + pad},${lat + pad * 0.75}`
}

function colorForTree(tree: TreeSummary, threatened: boolean, selected: boolean): RGBA {
  if (selected) return [255, 255, 235, 245]
  if (threatened) return [255, 91, 58, 238]
  if (INVASIVE_SPECIES.has(tree.species)) return [216, 188, 126, 210]
  if (tree.health.toLowerCase() === 'good') return [43, 214, 132, 218]
  if (tree.health.toLowerCase() === 'fair') return [173, 215, 105, 205]
  return [238, 178, 86, 205]
}

function haloForTree(tree: TreeSummary, threatened: boolean, selected: boolean): RGBA {
  if (selected) return [255, 255, 235, 54]
  if (threatened) return [255, 91, 58, 58]
  if (tree.health.toLowerCase() === 'good') return [43, 214, 132, 28]
  if (tree.health.toLowerCase() === 'fair') return [173, 215, 105, 25]
  return [238, 178, 86, 24]
}

function seedTrees(centerLng: number, centerLat: number, count = 1250): TreeSummary[] {
  const trees: TreeSummary[] = []
  const species = [
    ['London Plane', false],
    ['Pin Oak', false],
    ['Honeylocust', false],
    ['Callery Pear', true],
    ['Norway Maple', true],
    ['Ginkgo', false],
    ['Silver Linden', false],
    ['Red Maple', false],
    ['Sweetgum', false],
    ['Tree of Heaven', true],
  ] as const

  for (let row = 0; row < 24 && trees.length < count; row++) {
    for (let col = 0; col < 24 && trees.length < count; col++) {
      const baseLng = centerLng - 0.027 + col * 0.00225
      const baseLat = centerLat - 0.016 + row * 0.00136
      for (let i = 0; i < 3 && trees.length < count; i++) {
        const n = Math.abs(Math.sin((row * 71 + col * 37 + i * 19) * 12.9898) * 43758.5453) % 1
        if (n > 0.86) continue
        const item = species[Math.floor(n * species.length)]
        const health = n < 0.58 ? 'Good' : n < 0.8 ? 'Fair' : 'Poor'
        const dbh = Math.round(6 + n * 24)
        trees.push({
          id: `demo-${row}-${col}-${i}`,
          species: item[0],
          lng: baseLng + (i - 1) * 0.00038 + (n - 0.5) * 0.00024,
          lat: baseLat + (n - 0.5) * 0.00055,
          health,
          ecosystem_total_usd: Math.round(dbh * 9 + n * 80),
          diameter_in: dbh,
        })
      }
    }
  }

  return trees
}

const DEMO_TREES = seedTrees(INITIAL_VIEW.longitude, INITIAL_VIEW.latitude)
const DEMO_THREATS = new Set(DEMO_TREES.filter((_, index) => index % 18 === 0).map(tree => tree.id))

export default function TreeMap({
  onTreeClick,
  highlightedIds,
  defendedIds,
  selectedTreeId,
  mapStyle = 'satellite',
  onFlyToReady,
}: TreeMapProps) {
  const [trees, setTrees] = useState<TreeSummary[]>([])
  const [usingDemo, setUsingDemo] = useState(false)
  const [hovered, setHovered] = useState<TreeSummary | null>(null)
  const [hoveredPx, setHoveredPx] = useState<{ x: number; y: number } | null>(null)
  const [viewState, setViewState] = useState<MapViewState>(INITIAL_VIEW)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastBboxRef = useRef('')
  const hasDataRef = useRef(false)
  const mapRef = useRef<MapRef | null>(null)

  const fetchTrees = useCallback((view: MapViewState) => {
    const bbox = viewToBbox(view)
    if (bbox === lastBboxRef.current) return
    lastBboxRef.current = bbox

    api.trees.list(bbox).then(data => {
      if (data && data.length > 0) {
        setTrees(data)
        setUsingDemo(false)
        hasDataRef.current = true
      } else if (!hasDataRef.current) {
        setTrees(DEMO_TREES)
        setUsingDemo(true)
      }
    }).catch(() => {
      if (!hasDataRef.current) {
        setTrees(DEMO_TREES)
        setUsingDemo(true)
      }
    })
  }, [])

  useEffect(() => {
    fetchTrees(INITIAL_VIEW)
  }, [fetchTrees])

  useEffect(() => {
    if (!onFlyToReady) return
    onFlyToReady((lng, lat) => {
      mapRef.current?.flyTo({
        center: [lng, lat],
        zoom: 18,
        pitch: 50,
        bearing: -28,
        duration: 1450,
        essential: true,
      })
      lastBboxRef.current = ''
      const next = { ...INITIAL_VIEW, longitude: lng, latitude: lat, zoom: 18, pitch: 50, bearing: -28 }
      setTimeout(() => {
        setViewState(next)
        fetchTrees(next)
      }, 850)
    })
  }, [onFlyToReady, fetchTrees])

  useEffect(() => {
    if (!selectedTreeId) return
    const tree = trees.find(item => item.id === selectedTreeId)
    if (!tree) return
    mapRef.current?.flyTo({
      center: [tree.lng, tree.lat],
      zoom: 18.4,
      pitch: 54,
      bearing: -32,
      duration: 1100,
      essential: true,
    })
    setViewState(view => ({ ...view, longitude: tree.lng, latitude: tree.lat, zoom: 18.4, pitch: 54, bearing: -32 }))
  }, [selectedTreeId, trees])

  const threatIds = useMemo(() => highlightedIds ?? (usingDemo ? DEMO_THREATS : new Set<string>()), [highlightedIds, usingDemo])
  const defenseMap = useMemo<Map<string, number>>(() => defendedIds ?? new Map<string, number>(), [defendedIds])

  const layers = useMemo(() => {
    const selectedTrees = selectedTreeId ? trees.filter(tree => tree.id === selectedTreeId) : []
    const threatenedTrees = trees.filter(tree => threatIds.has(tree.id))
    const defendedTrees = trees.filter(tree => defenseMap.has(tree.id))

    const haloLayer = new ScatterplotLayer<TreeSummary>({
      id: 'tree-halo',
      data: trees,
      getPosition: tree => [tree.lng, tree.lat],
      getRadius: tree => canopyRadius(tree.diameter_in) * (threatIds.has(tree.id) ? 5.4 : 3.1),
      getFillColor: tree => haloForTree(tree, threatIds.has(tree.id), tree.id === selectedTreeId),
      radiusUnits: 'meters',
      radiusMinPixels: 7,
      radiusMaxPixels: 150,
      pickable: false,
      updateTriggers: {
        getRadius: [threatIds, selectedTreeId],
        getFillColor: [threatIds, selectedTreeId],
      },
    })

    const canopyLayer = new ScatterplotLayer<TreeSummary>({
      id: 'tree-canopy',
      data: trees,
      getPosition: tree => [tree.lng, tree.lat],
      getRadius: tree => canopyRadius(tree.diameter_in),
      getFillColor: tree => colorForTree(tree, threatIds.has(tree.id), tree.id === selectedTreeId),
      getLineColor: tree => threatIds.has(tree.id) ? [255, 246, 214, 230] : [10, 23, 17, 160],
      getLineWidth: tree => threatIds.has(tree.id) ? 2.2 : 0.8,
      radiusUnits: 'meters',
      radiusMinPixels: 4,
      radiusMaxPixels: 90,
      lineWidthUnits: 'pixels',
      stroked: true,
      filled: true,
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 235, 130],
      updateTriggers: {
        getFillColor: [threatIds, selectedTreeId],
        getLineColor: [threatIds],
        getLineWidth: [threatIds],
      },
      onHover: ({ object, x, y }) => {
        setHovered(object ?? null)
        setHoveredPx(object ? { x, y } : null)
      },
      onClick: ({ object }) => {
        if (object) onTreeClick(object)
      },
    })

    const threatRingLayer = new ScatterplotLayer<TreeSummary>({
      id: 'threat-radar-rings',
      data: threatenedTrees,
      getPosition: tree => [tree.lng, tree.lat],
      getRadius: tree => canopyRadius(tree.diameter_in) * 2.7,
      getFillColor: [0, 0, 0, 0],
      getLineColor: [255, 91, 58, 225],
      getLineWidth: 2.4,
      radiusUnits: 'meters',
      radiusMinPixels: 12,
      radiusMaxPixels: 130,
      lineWidthUnits: 'pixels',
      stroked: true,
      filled: false,
      pickable: false,
      updateTriggers: { data: [threatIds] },
    })

    const selectedRingLayer = new ScatterplotLayer<TreeSummary>({
      id: 'selected-crosshair',
      data: selectedTrees,
      getPosition: tree => [tree.lng, tree.lat],
      getRadius: tree => canopyRadius(tree.diameter_in) * 4.6,
      getFillColor: [0, 0, 0, 0],
      getLineColor: [255, 255, 235, 250],
      getLineWidth: 3,
      radiusUnits: 'meters',
      radiusMinPixels: 28,
      radiusMaxPixels: 180,
      lineWidthUnits: 'pixels',
      stroked: true,
      filled: false,
      pickable: false,
    })

    const labelLayer = new TextLayer<TreeSummary>({
      id: 'threat-labels',
      data: threatenedTrees.slice(0, 40),
      getPosition: tree => [tree.lng, tree.lat],
      getText: () => 'PERMIT',
      getSize: 10,
      getColor: [255, 247, 220, 230],
      getAngle: -12,
      getTextAnchor: 'middle',
      getAlignmentBaseline: 'bottom',
      getPixelOffset: [0, -16],
      fontFamily: 'monospace',
      pickable: false,
    })

    // Defense shield layer — green ring for defended trees
    const defenseRingLayer = new ScatterplotLayer<TreeSummary>({
      id: 'defense-rings',
      data: defendedTrees,
      getPosition: tree => [tree.lng, tree.lat],
      getRadius: tree => canopyRadius(tree.diameter_in) * 3.6,
      getFillColor: [0, 0, 0, 0],
      getLineColor: [34, 197, 94, 220],
      getLineWidth: 2.8,
      radiusUnits: 'meters',
      radiusMinPixels: 14,
      radiusMaxPixels: 120,
      lineWidthUnits: 'pixels',
      stroked: true,
      filled: false,
      pickable: false,
      updateTriggers: { data: [defenseMap] },
    })

    const defenseCountLayer = new TextLayer<TreeSummary>({
      id: 'defense-count',
      data: defendedTrees,
      getPosition: tree => [tree.lng, tree.lat],
      getText: tree => `✓ ${defenseMap.get(tree.id) ?? 1}`,
      getSize: 11,
      getColor: [34, 197, 94, 240],
      getTextAnchor: 'middle',
      getAlignmentBaseline: 'bottom',
      getPixelOffset: [0, -18],
      fontFamily: 'monospace',
      fontWeight: 700,
      pickable: false,
      updateTriggers: { getText: [defenseMap] },
    })

    return [haloLayer, canopyLayer, threatRingLayer, defenseRingLayer, defenseCountLayer, selectedRingLayer, labelLayer]
  }, [trees, threatIds, defenseMap, selectedTreeId, onTreeClick])

  const onViewStateChange = useCallback(({ viewState: nextViewState }: { viewState: MapViewState }) => {
    setViewState(nextViewState)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => fetchTrees(nextViewState), 420)
  }, [fetchTrees])

  const mapStyleObj =
    mapStyle === 'satellite' ? SATELLITE_STYLE :
    mapStyle === 'dark' ? DARK_STYLE :
    LIGHT_STYLE

  return (
    <div className={`tree-map tree-map--${mapStyle}`}>
      <DeckGL
        viewState={viewState}
        controller={{ dragPan: true, scrollZoom: true, touchZoom: true, doubleClickZoom: true }}
        onViewStateChange={onViewStateChange as never}
        layers={layers}
        getCursor={({ isDragging, isHovering }) => isDragging ? 'grabbing' : isHovering ? 'pointer' : 'grab'}
        style={{ position: 'absolute', top: '0', left: '0', right: '0', bottom: '0' }}
      >
        <MapGL ref={mapRef} mapStyle={mapStyleObj as string} attributionControl={false} reuseMaps />
      </DeckGL>

      <div className="map-grid-overlay" aria-hidden />
      <div className="map-compass" aria-hidden>
        <span>N</span>
      </div>

      {hovered && hoveredPx && (
        <div className="tree-tooltip" style={{ left: hoveredPx.x + 16, top: hoveredPx.y - 10 }}>
          <TooltipCard tree={hovered} threatened={threatIds.has(hovered.id)} defenseCount={defenseMap.get(hovered.id)} />
        </div>
      )}

      <div className="map-legend">
        <span>Canopy key</span>
        <LegendItem color="#ff5b3a" label="Removal permit" />
        <LegendItem color="#22c55e" label="Defense filed" />
        <LegendItem color="#2bd684" label="Healthy" />
        <LegendItem color="#add769" label="Fair" />
        <LegendItem color="#d8bc7e" label="Invasive" />
        <strong>{trees.length.toLocaleString()} trees{usingDemo ? ' demo' : ''}</strong>
      </div>
    </div>
  )
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <p>
      <i style={{ background: color }} />
      {label}
    </p>
  )
}

function TooltipCard({ tree, threatened, defenseCount }: { tree: TreeSummary; threatened: boolean; defenseCount?: number }) {
  const invasive = INVASIVE_SPECIES.has(tree.species)
  const status = threatened ? 'Removal permit' : invasive ? 'Invasive species' : `${tree.health} health`

  return (
    <div>
      <span>{status}</span>
      <strong>{tree.species}</strong>
      <p>{tree.diameter_in ? `${tree.diameter_in} inch DBH` : 'Diameter unavailable'} · ${Math.round(tree.ecosystem_total_usd).toLocaleString()} per year</p>
      {defenseCount != null && <p style={{ color: '#22c55e', fontWeight: 700 }}>✓ {defenseCount} defense{defenseCount !== 1 ? 's' : ''} filed</p>}
      <em>{threatened ? 'Click to generate a public comment.' : 'Click to inspect this tree.'}</em>
    </div>
  )
}
