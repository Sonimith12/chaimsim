// Mirrors the JSON produced by backend/sim_bridge.py (snake_case is kept on purpose).

export type NodeType = 'Supplier' | 'Manufacturer' | 'DistributionCenter' | 'Retailer'

export interface PolicyInfo {
  type: 'order_up_to' | 's_S' | 'r_q' | 'base_stock' | 'custom'
  params: Record<string, number>
}

export interface NodeState {
  id: string
  name: string
  type: NodeType
  /** Position chosen in the editor; null for untouched presets (laid out by echelon). */
  x: number | null
  z: number | null
  echelon: number
  slot: number
  echelon_size: number
  on_hand: number
  backlog: number
  pipeline: number
  last_order: number
  last_demand: number
  last_fulfilled: number
  financials: NodeFinancials | null
  avg_demand: number
  /** Below one period of typical demand on hand. */
  low_stock: boolean
  /** Expected demand for the next few periods. */
  forecast: number[] | null
  /** Running KPIs for this node; null before the first period. */
  fill_rate: number | null
  service_level: number | null
  /** Multiplier of a demand shock active this period, else null. */
  demand_shock: number | null
  active: boolean
  policy: PolicyInfo | null
}

export interface EdgeState {
  source: string
  target: string
  lead_time: number
  in_transit: number
  mode: string
}

/** One order's worth of goods currently travelling along an edge. */
export interface ShipmentState {
  id: number
  source: string
  target: string
  qty: number
  /** Period it left the source. */
  depart: number
  /** Period it is delivered. */
  arrive: number
}

export interface ServerMetrics {
  total_cost: number | null
  fill_rate: number | null
  service_level: number | null
  waste: number | null
}

export type ObjectiveStatus = 'ok' | 'borderline' | 'failing'

export interface Objective {
  id: string
  label: string
  /** Campaign objectives carry their full sentence in `label`. */
  title_only?: boolean
  tier?: 'required' | 'goal' | 'bonus'
  unit: 'currency' | 'percent' | 'count' | 'units'
  comparison: 'at_most' | 'at_least'
  target: number
  actual: number
  met: boolean
  status: ObjectiveStatus
  bonus: boolean
}

export interface ScoreState {
  base: number
  service_bonus: number
  fill_bonus: number
  policy_bonus: number
  cost_penalty: number
  waste_penalty: number
  stockout_penalty: number
  total: number
  max: number
  status: 'green' | 'yellow' | 'red'
  /** 0.5 while in a cash crisis. */
  multiplier: number
  stockouts: number
  policy_changes: number
}

export type Grade = 'S' | 'A' | 'B' | 'C' | 'D' | 'F'

export interface CostBreakdown {
  holding: number
  backlog: number
  transport: number
  ordering: number
  policy: number
  events: number
  infrastructure: number
  total: number
}

export interface RunStats {
  total_cost: number
  fill_rate: number
  service_level: number
  waste: number
  stockouts: number
  policy_changes: number
  revenue: number
  costs: CostBreakdown
  cash: number
  net_profit: number
  margin: number
}

export interface FlowBuckets {
  revenue: number
  holding: number
  backlog: number
  transport: number
  ordering: number
  policy: number
  events: number
  net: number
}

export interface NodeFinancials {
  period: FlowBuckets
  cumulative: FlowBuckets
}

export interface EconomyState {
  cash: number
  starting_capital: number
  /** Cash at the start of the run, after build costs. */
  initial_cash: number
  cash_status: 'green' | 'yellow' | 'red'
  crisis: boolean
  crisis_periods: number
  zero_streak: number
  bankrupt: boolean
  bankrupt_reason: 'overdraft' | 'insolvent' | null
  bankruptcy_periods: number
  overdraft_limit: number
  policy_change_cost: number
  revenue: number
  costs: CostBreakdown
  net_profit: number
  margin: number
  last_period: FlowBuckets
}

export interface RunResult {
  grade: Grade
  stars: number
  objectives_met: number
  objectives_total: number
  bankrupt: boolean
  bankrupt_reason: 'overdraft' | 'insolvent' | null
  periods_completed: number
  stats: RunStats
  campaign?: CampaignResult
}

export interface CampaignResult {
  level: number
  passed: boolean
  /** 0 = failed; 1 = required met; 2 = + all goals; 3 = + bonus. */
  stars: number
  required_met: number
  required_total: number
  goals_met: number
  goals_total: number
  bonus_met: number
  bonus_total: number
}

export interface CampaignLevelMeta {
  id: number
  act: number
  act_name: string
  name: string
  blurb: string
  description: string
  difficulty: number
  n_periods: number
  objectives: { label: string; tier: 'required' | 'goal' | 'bonus' }[]
  special_rules: string[]
  completion: string
  edit_mode: boolean
  hints: boolean
}

export type GameEvent =
  | { type: 'stockout'; node_id: string; points: number }
  | { type: 'policy_bonus'; node_id: string; points: number }
  | { type: 'milestone'; quarter: number }
  | {
      type: 'cost'
      kind: 'revenue' | 'holding' | 'backlog' | 'policy' | 'event'
      node_id: string
      amount: number
    }
  | { type: 'cash_crisis' }
  | { type: 'bankrupt'; reason: 'overdraft' | 'insolvent' }

export type EventRisk = 'safe' | 'risky' | 'danger'

export interface EventChoice {
  id: string
  label: string
  /** Cost / consequence preview shown on the button. */
  description: string
  risk: EventRisk
  cost: number
}

export interface PendingEvent {
  uid: number
  event_id: string
  category: 'disruption' | 'demand' | 'financial' | 'operations'
  icon: string
  title: string
  description: string
  /** Seconds to decide; null for no time limit. */
  timer: number | null
  period: number
  /** The worst option, applied automatically when the timer runs out. */
  default_choice: string
  choices: EventChoice[]
}

export interface EventLogEntry {
  uid: number
  period: number
  event_id: string
  title: string
  icon: string
  category: string
  choice_id: string
  choice: string
  outcome: string
  cash_delta: number
  auto: boolean
}

export interface EventOutcome {
  message: string
  cash_delta: number
  title: string
  choice: string
  auto: boolean
}

export interface ServerState {
  level: { id: number; name: string; n_periods: number } | null
  pending_event: PendingEvent | null
  event_log: EventLogEntry[]
  /** Units of on-hand inventory each displayed crate stands for. */
  inventory_scale: number
  run_id: number
  events: GameEvent[]
  score: ScoreState
  economy: EconomyState
  objectives: Objective[]
  result: RunResult | null
  scenario_id: string | null
  scenario_name: string
  description: string
  period: number
  n_periods: number
  finished: boolean
  nodes: NodeState[]
  edges: EdgeState[]
  shipments: ShipmentState[]
  metrics: ServerMetrics
}

export interface Metrics {
  totalCost: number
  fillRate: number
  serviceLevel: number
  waste: number
}

export interface PeriodSnapshot {
  period: number
  nodes: NodeState[]
  metrics: Metrics
}

export interface ScenarioInfo {
  id: string
  name: string
  description: string
  n_periods: number
}

export type ClientCommand =
  | { type: 'step' }
  | { type: 'reset' }
  | { type: 'event_action'; event_id: number; choice_id: string; auto: boolean }
  | {
      type: 'policy_change'
      node_id: string
      policy_type: string
      params: Record<string, number>
    }

export type ServerMessage =
  | {
      type: 'state'
      state: ServerState
      event?: 'policy_changed' | 'event_resolved' | null
      node_id?: string | null
      outcome?: EventOutcome | null
    }
  | { type: 'error'; message: string }

// --- Editable network spec (mirrors backend/network_spec.py) ---------------------

export type EditableNodeType = 'Supplier' | 'DistributionCenter' | 'Retailer'

export interface DemandSpec {
  type: 'stationary' | 'seasonal' | 'trend'
  mean: number
  std: number
  distribution: 'poisson' | 'normal'
  base: number
  amplitude: number
  period_length: number
  trend_per_period: number
  noise_std: number
}

export interface PolicySpec {
  type: 'order_up_to' | 's_S' | 'r_q' | 'base_stock'
  params: Record<string, number>
}

export interface NodeSpec {
  id: string
  name: string
  type: NodeType
  x: number | null
  z: number | null
  echelon: number
  slot: number
  echelon_size: number
  forecast: number | null
  initial_inventory: number
  holding_cost: number
  backlog_cost: number
  capacity: number | null
  shelf_life: number | null
  external_lead_time: number
  demand: DemandSpec | null
  policy: PolicySpec | null
}

export interface EdgeSpec {
  source: string
  target: string
  lead_time: number
  capacity: number | null
  cost_per_unit: number
  mode: string
}

export interface DisruptionSpec {
  type: 'node_outage' | 'capacity_reduction' | 'lead_time_shock' | 'demand_shock'
  target_id: string
  start: number
  duration: number
  value: number
}

export interface NetworkSpec {
  scenario_id: string | null
  name: string
  description: string
  nodes: NodeSpec[]
  edges: EdgeSpec[]
  disruptions: DisruptionSpec[]
  n_periods: number
  seed: number | null
  inventory_scale: number
  events_enabled: boolean
  economy: EconomySpecData
  free_nodes: string[]
  free_edges: [string, string][]
  campaign_level?: number | null
  locked_nodes?: string[]
}

export interface EconomySpecData {
  starting_capital: number
  revenue_per_unit: number
  ordering_cost: number
  transport_cost_per_lead_time: number
  holding_multiplier: number
  backlog_multiplier: number
  policy_change_cost: number
  overdraft_limit: number
  bankruptcy_periods: number
  build_cost_supplier: number
  build_cost_dc: number
  build_cost_retailer: number
  build_cost_per_lead_time: number
}

export interface ValidationIssue {
  code: string
  message: string
  node_ids: string[]
  edges: [string, string][]
}
