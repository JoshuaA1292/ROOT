export interface TreeSummary {
  id: string
  species: string
  lng: number
  lat: number
  health: string
  ecosystem_total_usd: number
  diameter_in?: number
}

export const INVASIVE_SPECIES = new Set([
  'Norway Maple', 'Callery Pear', 'Tree of Heaven', 'White Mulberry',
  'Siberian Elm', 'Amur Cork Tree', 'Princess Tree', 'White Poplar',
  'Black Locust', 'Common Privet', 'European Buckthorn',
])

export interface EcosystemValue {
  stormwater_gal: number
  stormwater_usd: number
  co2_lbs: number
  co2_usd: number
  cooling_kwh: number
  cooling_usd: number
  air_quality_usd: number
  total_usd: number
}

export interface Tree {
  id: string
  nyc_tree_id: number
  species: { common: string; latin: string }
  diameter_in: number
  health: string
  status: string
  location: { type: string; coordinates: [number, number] }
  address: string
  borough: string
  census_tract: string
  ecosystem_value_usd_yr: EcosystemValue
  ej_score: { heat_vuln_pct: number; tract_score: number }
  planted_year?: number
  last_inspection?: string
}

export interface Permit {
  id: string
  developer_id: string
  filed_date: string
  address: string
  project_type: string
  removal_radius_m: number
  center: { type: string; coordinates: [number, number] }
  stated_reason: string
  promised_replacements: number
  comment_deadline: string
  status: string
  threatened_tree_ids: string[]
  enforcement_flag?: boolean
  developer_compliance_rate?: number
}

export interface DeveloperViolation {
  permit_id: string
  type: string
  count: number
  year: number
}

export interface Developer {
  id: string
  name: string
  permits_filed: number
  promised_replacements: number
  verified_surviving: number
  compliance_rate: number
  violations: DeveloperViolation[]
  linked_entities: string[]
  last_audit?: string
}

export interface CoalitionSummary {
  tree_count: number
  canopy_sqft: number
  stormwater_gal_yr: number
  co2_lbs_lifetime: number
  cooling_usd_yr: number
  total_ecosystem_usd_yr: number
  ej_tier: 'High' | 'Medium' | 'Low'
  heat_vulnerable_residents: number
  tree_ids: string[]
}

export interface PrecedentRef {
  id: string
  title: string
  outcome: string
  year: number
  similarity_score: number
  arguments_used: string[]
}

export interface PolicyRef {
  id: string
  title: string
  section: string
  text_excerpt: string
  matched_tags: string[]
}

export interface Briefing {
  id: string
  permit_id: string
  created_at: string
  coalition_summary?: CoalitionSummary
  developer_snapshot?: {
    developer_id: string
    name: string
    compliance_rate: number
    city_target?: number
    target_delta?: number
    permits_filed: number
    promised_replacements: number
    verified_surviving: number
    violations_count: number
    at_risk_replacements?: number
  }
  precedent_refs: PrecedentRef[]
  policy_refs: PolicyRef[]
  draft_comment: string
  citations: string[]
  status: 'draft' | 'edited' | 'reviewed' | 'exported' | 'submitted'
  reviewed_by_email?: string
  guardian_schedule?: Record<string, string>
  intervention_strategy?: {
    recommended_action: string
    confidence: 'High' | 'Medium' | 'Low'
    developer_risk_tier: 'critical' | 'high' | 'elevated' | 'compliant'
    cumulative_exposure_score?: number
    best_argument: string
    best_argument_rationale: string
    reasons: string[]
    requested_conditions: string[]
    precedent_signal?: {
      title: string; outcome: string; year: number
      similarity_score: number; arguments_used: string[]
    }
  }
  evidence_board?: {
    developer: {
      name: string; compliance_rate: number; city_target: number
      permits_filed: number; promised_replacements: number
      verified_surviving: number; violations_count: number; linked_entity_count: number
      at_risk_replacements?: number; cumulative_exposure_score?: number
    }
    coalition: {
      tree_count: number; canopy_sqft: number; stormwater_gal_yr: number
      total_ecosystem_usd_yr: number; ej_tier: string; heat_vulnerable_residents: number
    }
    top_precedent?: {
      title: string; outcome: string; year: number
      similarity_score: number; arguments_used: string[]
    } | null
    policy_count: number
    policy_titles: string[]
  }
}

export interface ComplianceByYear {
  _id: number
  promised: number
  planted: number
  surviving: number
  survival_rate: number
}

export interface ViolationBreakdown {
  _id: string
  trees_affected: number
  permit_count: number
}

export interface RiskProfile {
  developer_id: string
  name: string
  compliance_rate: number
  linked_entities: string[]
  network_entity_count: number
  risk_tier: 'critical' | 'high' | 'elevated' | 'compliant'
  accountability_gap_pct: number
}

export interface DeveloperRiskIntelligence {
  compliance_by_year: ComplianceByYear[]
  active_exposure: {
    open_permit_count: number
    trees_at_risk: number
    earliest_deadline: string | null
  }
  violation_breakdown: ViolationBreakdown[]
  risk_profile: RiskProfile
}

export interface EntityNetwork {
  entities: { id: string; name: string; compliance_rate: number }[]
  total_permits_filed: number
  total_promised: number
  total_surviving: number
  combined_violations: number
  network_compliance_rate: number
  all_entity_names: string[]
}

export interface AgentEvent {
  event: string
  data: Record<string, unknown>
}

export interface DefenseMarker {
  tree_id: string
  count: number
}

export interface VerificationResult {
  verified: boolean
  confidence: 'high' | 'medium' | 'low'
  flags: string[]
  summary: string
}

export interface GuardianNotification {
  id: string
  type: string
  briefing_id: string
  permit_id: string
  address: string
  subject: string
  body: string
  tags: string[]
  step?: string
  guardian_schedule?: Record<string, string>
  created_at: string
  read: boolean
}
