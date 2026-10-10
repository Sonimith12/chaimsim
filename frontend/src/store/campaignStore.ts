import { create } from 'zustand'
import type { CampaignLevelMeta } from '../types/sim'

const KEY = 'chainsim.campaign.v1'

export interface LevelProgress {
  bestScore: number
  /** Best star rating (0 = never passed). */
  stars: number
  attempts: number
}

interface Persisted {
  progress: Record<number, LevelProgress>
  hintsSeen: string[]
}

function load(): Persisted {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<Persisted>
      return { progress: parsed.progress ?? {}, hintsSeen: parsed.hintsSeen ?? [] }
    }
  } catch {
    /* private mode or corrupt data: start fresh */
  }
  return { progress: {}, hintsSeen: [] }
}

function save(p: Persisted) {
  try {
    localStorage.setItem(KEY, JSON.stringify(p))
  } catch {
    /* progress just won't persist */
  }
}

/** What happened when the latest run was recorded (for the completion screen). */
export interface LastRecord {
  runKey: string
  levelId: number
  previousBest: number | null
  previousStars: number
  isBestScore: boolean
  newlyUnlocked: boolean
}

interface CampaignStore extends Persisted {
  levels: CampaignLevelMeta[]
  lastRecord: LastRecord | null
  setLevels: (levels: CampaignLevelMeta[]) => void
  recordRun: (r: { runKey: string; levelId: number; score: number; stars: number }) => void
  markHint: (id: string) => void
  reset: () => void
}

export const FEATURE_LEVEL = { turbo: 3, forecast: 5, analytics: 7, master: 10 } as const
export type Feature = keyof typeof FEATURE_LEVEL

/** The highest level the player may start (level 1 is always open). */
export function unlockedUpTo(progress: Record<number, LevelProgress>, total: number): number {
  let highest = 0
  for (const [id, p] of Object.entries(progress)) if (p.stars > 0) highest = Math.max(highest, Number(id))
  return Math.min(total, highest + 1)
}

export const totalStars = (progress: Record<number, LevelProgress>) =>
  Object.values(progress).reduce((sum, p) => sum + p.stars, 0)

export const useCampaignStore = create<CampaignStore>((set, get) => ({
  ...load(),
  levels: [],
  lastRecord: null,

  setLevels: (levels) => set({ levels }),

  recordRun: ({ runKey, levelId, score, stars }) => {
    if (get().lastRecord?.runKey === runKey) return
    const { progress, hintsSeen, levels } = get()
    const prev = progress[levelId]
    const total = levels.length || 10
    const before = unlockedUpTo(progress, total)
    const next: LevelProgress = {
      bestScore: Math.max(prev?.bestScore ?? -Infinity, score),
      stars: Math.max(prev?.stars ?? 0, stars),
      attempts: (prev?.attempts ?? 0) + 1,
    }
    const nextProgress = { ...progress, [levelId]: next }
    save({ progress: nextProgress, hintsSeen })
    set({
      progress: nextProgress,
      lastRecord: {
        runKey,
        levelId,
        previousBest: prev ? prev.bestScore : null,
        previousStars: prev?.stars ?? 0,
        isBestScore: !prev || score > prev.bestScore,
        newlyUnlocked: unlockedUpTo(nextProgress, total) > before,
      },
    })
  },

  markHint: (id) => {
    const { hintsSeen, progress } = get()
    if (hintsSeen.includes(id)) return
    const next = [...hintsSeen, id]
    save({ progress, hintsSeen: next })
    set({ hintsSeen: next })
  },

  reset: () => {
    save({ progress: {}, hintsSeen: [] })
    set({ progress: {}, hintsSeen: [], lastRecord: null })
  },
}))

/** Hook: has the player earned this feature by clearing its level? */
export function useFeature(feature: Feature): boolean {
  return useCampaignStore((s) => (s.progress[FEATURE_LEVEL[feature]]?.stars ?? 0) > 0)
}
