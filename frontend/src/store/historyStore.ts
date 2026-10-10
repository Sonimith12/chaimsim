import { create } from 'zustand'
import type { Grade, Objective, RunStats } from '../types/sim'

export interface RunRecord {
  id: number
  /** `${scenarioId}:${runId}`; guards against recording the same run twice. */
  runKey: string
  scenarioId: string
  scenarioName: string
  score: number
  grade: Grade
  stars: number
  objectives: Objective[]
  stats: RunStats
  bankrupt: boolean
  finishedAt: number
}

interface HistoryStore {
  runs: RunRecord[]
  add: (record: Omit<RunRecord, 'id' | 'finishedAt'>) => void
}

let nextId = 1

// Session-only on purpose: lost on refresh.
export const useHistoryStore = create<HistoryStore>((set, get) => ({
  runs: [],
  add: (record) => {
    if (get().runs.some((r) => r.runKey === record.runKey)) return
    set((s) => ({ runs: [{ ...record, id: nextId++, finishedAt: Date.now() }, ...s.runs] }))
  },
}))
