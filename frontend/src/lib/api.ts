const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
  return res.json()
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PATCH ${path} failed: ${res.status}`)
  return res.json()
}

export const api = {
  trees: {
    list: (bbox: string) => get<import('./types').TreeSummary[]>(`/trees?bbox=${bbox}`),
    get: (id: string) => get<import('./types').Tree>(`/trees/${id}`),
  },
  permits: {
    list: (status?: string) => get<import('./types').Permit[]>(`/permits${status ? `?status=${status}` : ''}`),
    get: (id: string) => get<import('./types').Permit>(`/permits/${id}`),
    getCoalition: (id: string) => get<import('./types').CoalitionSummary>(`/permits/${id}/coalition`),
  },
  developers: {
    list: () => get<import('./types').Developer[]>(`/developers`),
    get: (id: string) => get<import('./types').Developer>(`/developers/${id}`),
    getLedger: (id: string) => get<import('./types').Developer>(`/developers/${id}/ledger`),
    getRiskIntelligence: (id: string) => get<import('./types').DeveloperRiskIntelligence>(`/developers/${id}/risk-intelligence`),
    getNetwork: (id: string) => get<import('./types').EntityNetwork>(`/developers/${id}/network`),
  },
  briefings: {
    trigger: (permitId: string) =>
      post<{ briefing_id: string; status: string; briefing?: import('./types').Briefing }>(`/briefings`, { permit_id: permitId }),
    get: (id: string) => get<import('./types').Briefing>(`/briefings/${id}`),
    patch: (id: string, body: { draft_comment?: string; status?: string; reviewed_by_email?: string }) =>
      patch<import('./types').Briefing>(`/briefings/${id}`, body),
    submit: (id: string, email?: string) => post<{
      status: string
      briefing_id: string
      defense_count: number
      notification_id: string
      email_sent: boolean
      email_error: string
      guardian_schedule: { day90: string; month12: string; month36: string; year5: string; next_check: string }
      permit_address: string
      nyc_dob_url: string
      nyc_parks_email: string
      maps_url: string
    }>(`/briefings/${id}/submit`, email ? { email } : {}),
    defenseMap: () => get<{ defenses: import('./types').DefenseMarker[] }>('/briefings/defense-map'),
  },
  stream: {
    url: (briefingId: string) => `${BASE}/stream/briefings/${briefingId}`,
  },
  config: {
    runtime: () => get<Record<string, unknown>>('/config/runtime'),
  },
  outcomes: {
    record: (body: {
      permit_id: string
      briefing_id?: string
      comment_acknowledged: boolean
      conditions_imposed: string[]
      replacements_required?: number
      notes: string
      reported_by?: string
    }) => post<{ status: string; permit_id: string; conditions: string[] }>('/outcomes', body),
    get: (permitId: string) => get<{ permit_id: string; conditions_imposed: string[]; recorded_at: string }>(`/outcomes/${permitId}`),
    verify: (permitId: string, body: {
      permit_id: string
      briefing_id?: string
      comment_acknowledged: boolean
      conditions_imposed: string[]
      notes: string
    }) => post<import('./types').VerificationResult>(`/outcomes/${permitId}/verify`, body),
  },
  admin: {
    clearDemoData: () => {
      return fetch(`${BASE}/admin/clear-demo-data`, { method: 'DELETE' }).then(r => r.json())
    },
  },
  notifications: {
    list: () => get<{ notifications: import('./types').GuardianNotification[]; unread_count: number }>('/notifications'),
    markRead: (id: string) => post<{ status: string }>(`/notifications/${id}/read`, {}),
  },
}
