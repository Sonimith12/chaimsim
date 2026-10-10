import { create } from 'zustand'

export type Phase = 'setup' | 'edit' | 'playing' | 'paused' | 'results'
export type ToastKind = 'error' | 'warn' | 'info'

export interface Toast {
  id: number
  text: string
  kind: ToastKind
}
export type Speed = 'slow' | 'normal' | 'fast'
export type Connection = 'closed' | 'connecting' | 'open'

export interface Floater {
  id: number
  nodeId: string
  text: string
  color: string
  born: number
}

export interface Banner {
  id: number
  text: string
}

const FLOATER_MS = 1600
const BANNER_MS = 2400
let nextId = 1

interface GameStore {
  currentPhase: Phase
  currentPeriod: number
  selectedNodeId: string | null
  speed: Speed
  connection: Connection
  error: string | null
  /** Last confirmed policy change, for the node's confirmation flash. */
  policyFlash: { nodeId: string; at: number } | null
  /** Bumped to ask the camera rig to return to the overview. */
  cameraResetToken: number
  /** Floating "+50" / "-200" texts currently rising off nodes. */
  floaters: Floater[]
  /** node id -> performance.now() of its latest stockout flash. */
  stockoutFlashes: Record<string, number>
  /** performance.now() of the latest service-level warning; 0 if none. */
  scoreWarnAt: number
  banner: Banner | null
  historyOpen: boolean
  toasts: Toast[]

  addToast: (text: string, kind?: ToastKind) => void
  addFloater: (nodeId: string, text: string, color: string) => void
  flashStockout: (nodeId: string) => void
  warnScore: () => void
  showBanner: (text: string) => void
  setHistoryOpen: (open: boolean) => void
  setPhase: (phase: Phase) => void
  setCurrentPeriod: (period: number) => void
  selectNode: (id: string | null) => void
  setSpeed: (speed: Speed) => void
  setConnection: (connection: Connection) => void
  setError: (error: string | null) => void
  flashNode: (nodeId: string) => void
  resetCamera: () => void
}

export const useGameStore = create<GameStore>((set) => ({
  currentPhase: 'setup',
  currentPeriod: 0,
  selectedNodeId: null,
  speed: 'normal',
  connection: 'closed',
  error: null,
  policyFlash: null,
  cameraResetToken: 0,
  floaters: [],
  stockoutFlashes: {},
  scoreWarnAt: 0,
  banner: null,
  historyOpen: false,
  toasts: [],

  addToast: (text, kind = 'error') => {
    const id = nextId++
    set((s) => ({ toasts: [...s.toasts.slice(-3), { id, text, kind }] }))
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), 4500)
  },
  addFloater: (nodeId, text, color) => {
    const id = nextId++
    set((s) => ({ floaters: [...s.floaters, { id, nodeId, text, color, born: performance.now() }] }))
    setTimeout(() => set((s) => ({ floaters: s.floaters.filter((f) => f.id !== id) })), FLOATER_MS)
  },
  flashStockout: (nodeId) =>
    set((s) => ({ stockoutFlashes: { ...s.stockoutFlashes, [nodeId]: performance.now() } })),
  warnScore: () => set({ scoreWarnAt: performance.now() }),
  showBanner: (text) => {
    const id = nextId++
    set({ banner: { id, text } })
    setTimeout(() => set((s) => (s.banner?.id === id ? { banner: null } : s)), BANNER_MS)
  },
  setHistoryOpen: (historyOpen) => set({ historyOpen }),

  setPhase: (currentPhase) => set({ currentPhase }),
  setCurrentPeriod: (currentPeriod) => set({ currentPeriod }),
  selectNode: (selectedNodeId) => set({ selectedNodeId }),
  setSpeed: (speed) => set({ speed }),
  setConnection: (connection) => set({ connection }),
  setError: (error) => set({ error }),
  flashNode: (nodeId) => set({ policyFlash: { nodeId, at: performance.now() } }),
  resetCamera: () => set((s) => ({ cameraResetToken: s.cameraResetToken + 1 })),
}))
