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
  avg_demand: number
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
  id: 'cost' | 'service' | 'fill' | 'bonus'
  label: string
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
}

export type Grade = 'S' | 'A' | 'B' | 'C' | 'D' | 'F'

export interface RunStats {
  total_cost: number
  fill_rate: number
  service_level: number
  waste: number
  stockouts: number
  policy_changes: number
}

export interface RunResult {
  grade: Grade
  stars: number
  objectives_met: number
  objectives_total: number
  stats: RunStats
}

export type GameEvent =
  | { type: 'stockout'; node_id: string; points: number }
  | { type: 'policy_bonus'; node_id: string; points: number }
  | { type: 'milestone'; quarter: number }

export interface ServerState {
  /** Units of on-hand inventory each displayed crate stands for. */
  inventory_scale: number
  run_id: number
  events: GameEvent[]
  score: ScoreState
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
  | {
      type: 'policy_change'
      node_id: string
      policy_type: string
      params: Record<string, number>
    }

export type ServerMessage =
  | { type: 'state'; state: ServerState; event?: 'policy_changed' | null; node_id?: string | null }
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
}

export interface ValidationIssue {
  code: string
  message: string
  node_ids: string[]
  edges: [string, string][]
}
