import { create } from 'zustand'
import type {
  EdgeState,
  Metrics,
  NodeState,
  PeriodSnapshot,
  Objective,
  RunResult,
  ScoreState,
  ServerState,
  ShipmentState,
} from '../types/sim'

const EMPTY_METRICS: Metrics = { totalCost: 0, fillRate: 1, serviceLevel: 1, waste: 0 }

// The sim store only mirrors what the backend sends; it never computes anything.
interface SimStore {
  loaded: boolean
  period: number
  inventoryScale: number
  runId: number
  score: ScoreState | null
  objectives: Objective[]
  result: RunResult | null
  scenarioId: string | null
  scenarioName: string
  description: string
  nPeriods: number
  finished: boolean
  networkState: { nodes: NodeState[]; edges: EdgeState[] }
  metrics: Metrics
  history: PeriodSnapshot[]
  shipments: ShipmentState[]
  /** performance.now() when the latest state arrived; drives animation tweening. */
  receivedAt: number

  updateFromServer: (data: ServerState) => void
  reset: () => void
}

const initial = {
  loaded: false,
  period: 0,
  inventoryScale: 1,
  runId: 0,
  score: null,
  objectives: [],
  result: null,
  scenarioId: null,
  scenarioName: '',
  description: '',
  nPeriods: 0,
  finished: false,
  networkState: { nodes: [], edges: [] },
  metrics: EMPTY_METRICS,
  history: [],
  shipments: [],
  receivedAt: 0,
}

export const useSimStore = create<SimStore>((set) => ({
  ...initial,

  updateFromServer: (data) =>
    set((s) => {
      const metrics: Metrics = {
        totalCost: data.metrics.total_cost ?? 0,
        fillRate: data.metrics.fill_rate ?? 0,
        serviceLevel: data.metrics.service_level ?? 0,
        waste: data.metrics.waste ?? 0,
      }
      // Period 0 means a fresh run: drop any earlier history. Otherwise keep one
      // snapshot per period (a policy change re-sends the same period).
      const history =
        data.period === 0
          ? []
          : [
              ...s.history.filter((h) => h.period !== data.period),
              { period: data.period, nodes: data.nodes, metrics },
            ]
      return {
        loaded: true,
        period: data.period,
        inventoryScale: data.inventory_scale,
        runId: data.run_id,
        score: data.score,
        objectives: data.objectives,
        result: data.result,
        scenarioId: data.scenario_id,
        scenarioName: data.scenario_name,
        description: data.description,
        nPeriods: data.n_periods,
        finished: data.finished,
        networkState: { nodes: data.nodes, edges: data.edges },
        metrics,
        history,
        shipments: data.shipments,
        // A policy change re-sends the same period; don't restart the tweens for it.
        receivedAt: data.period === s.period ? s.receivedAt : performance.now(),
      }
    }),

  reset: () => set(initial),
}))
