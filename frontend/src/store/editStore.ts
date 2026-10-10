import { create } from 'zustand'
import { computeLayout } from '../scene/layout'
import type {
  EdgeSpec,
  EditableNodeType,
  NetworkSpec,
  NodeSpec,
  ValidationIssue,
} from '../types/sim'
import { useGameStore } from './gameStore'

export const MAX_NODES = 10
export const GRID = 2

export const snap = (v: number) => Math.max(-50, Math.min(50, Math.round(v / GRID) * GRID))

const PREFIX: Record<EditableNodeType, string> = {
  Supplier: 'Supplier',
  DistributionCenter: 'DC',
  Retailer: 'Retailer',
}

const toast = (text: string, kind: 'error' | 'warn' | 'info' = 'error') =>
  useGameStore.getState().addToast(text, kind)

function newNode(type: EditableNodeType, id: string, x: number, z: number): NodeSpec {
  const base: NodeSpec = {
    id,
    name: id,
    type,
    x,
    z,
    echelon: 0,
    slot: 0,
    echelon_size: 1,
    initial_inventory: 200,
    holding_cost: 0.5,
    backlog_cost: 0,
    capacity: null,
    shelf_life: null,
    external_lead_time: 1,
    forecast: null,
    demand: null,
    policy: { type: 'order_up_to', params: { S: 300 } },
  }
  if (type === 'Supplier') {
    return { ...base, initial_inventory: 10000, holding_cost: 0, policy: null }
  }
  if (type === 'Retailer') {
    return {
      ...base,
      initial_inventory: 100,
      holding_cost: 1,
      backlog_cost: 8,
      policy: { type: 'order_up_to', params: { S: 200 } },
      demand: {
        type: 'stationary',
        mean: 40,
        std: 0,
        distribution: 'poisson',
        base: 40,
        amplitude: 10,
        period_length: 13,
        trend_per_period: 0.5,
        noise_std: 0,
      },
    }
  }
  return base
}

/** Money spent on nodes/edges that didn't come with the preset (mirrors the backend's rule). */
export function infrastructureCost(spec: NetworkSpec): number {
  const e = spec.economy
  const freeNodes = new Set(spec.free_nodes)
  const freeEdges = new Set(spec.free_edges.map(([s, t]) => `${s}->${t}`))
  let total = 0
  for (const n of spec.nodes) {
    if (freeNodes.has(n.id)) continue
    total +=
      n.type === 'DistributionCenter'
        ? e.build_cost_dc
        : n.type === 'Retailer'
          ? e.build_cost_retailer
          : e.build_cost_supplier
  }
  for (const edge of spec.edges) {
    if (!freeEdges.has(`${edge.source}->${edge.target}`)) {
      total += e.build_cost_per_lead_time * edge.lead_time
    }
  }
  return total
}

export const remainingBudget = (spec: NetworkSpec) =>
  spec.economy.starting_capital - infrastructureCost(spec)

export function nodeBuildCost(spec: NetworkSpec, type: EditableNodeType): number {
  const e = spec.economy
  return type === 'DistributionCenter'
    ? e.build_cost_dc
    : type === 'Retailer'
      ? e.build_cost_retailer
      : e.build_cost_supplier
}

const money = (n: number) => `$${Math.round(n).toLocaleString()}`

export function blankSpec(): NetworkSpec {
  return {
    scenario_id: null,
    name: 'Custom Network',
    description: 'A network built from scratch.',
    nodes: [],
    edges: [],
    disruptions: [],
    n_periods: 52,
    seed: 42,
    inventory_scale: 20,
    economy: {
      starting_capital: 30000,
      revenue_per_unit: 10,
      ordering_cost: 20,
      transport_cost_per_lead_time: 10,
      holding_multiplier: 1,
      backlog_multiplier: 1,
      policy_change_cost: 500,
      overdraft_limit: 5000,
      bankruptcy_periods: 5,
      build_cost_supplier: 5000,
      build_cost_dc: 3000,
      build_cost_retailer: 2000,
      build_cost_per_lead_time: 500,
    },
    free_nodes: [],
    free_edges: [],
    events_enabled: true,
  }
}

interface EditStore {
  spec: NetworkSpec | null
  /** Node type waiting to be placed on the next ground click. */
  placing: EditableNodeType | null
  connectMode: boolean
  shiftDown: boolean
  connectFrom: string | null
  dragId: string | null
  editingEdge: { source: string; target: string } | null
  invalidNodes: string[]
  invalidEdges: string[]
  settingsOpen: boolean

  load: (spec: NetworkSpec) => void
  clear: () => void
  setPlacing: (type: EditableNodeType | null) => void
  setConnectMode: (on: boolean) => void
  setShift: (down: boolean) => void
  setConnectFrom: (id: string | null) => void
  startDrag: (id: string) => void
  endDrag: () => void
  setEditingEdge: (edge: { source: string; target: string } | null) => void
  setSettingsOpen: (open: boolean) => void
  markInvalid: (issues: ValidationIssue[]) => void
  clearInvalid: () => void

  addNodeAt: (type: EditableNodeType, x: number, z: number) => void
  moveNode: (id: string, x: number, z: number) => void
  removeNode: (id: string) => void
  updateNode: (id: string, patch: Partial<NodeSpec>) => void
  addEdge: (source: string, target: string) => EdgeSpec | null
  removeEdge: (source: string, target: string) => void
  updateEdge: (source: string, target: string, patch: Partial<EdgeSpec>) => void
}

const edgeKey = (s: string, t: string) => `${s}->${t}`
export { edgeKey }

export const useEditStore = create<EditStore>((set, get) => ({
  spec: null,
  placing: null,
  connectMode: false,
  shiftDown: false,
  connectFrom: null,
  dragId: null,
  editingEdge: null,
  invalidNodes: [],
  invalidEdges: [],
  settingsOpen: false,

  load: (spec) => {
    // Presets arrive without positions; seed them from the echelon layout so what
    // the player drags around starts where the play view would have put it.
    const layout = computeLayout(spec.nodes)
    const nodes = spec.nodes.map((n) => {
      const p = layout.positions.get(n.id)
      return { ...n, x: n.x ?? snap(p?.[0] ?? 0), z: n.z ?? snap(p?.[2] ?? 0) }
    })
    set({
      spec: { ...spec, nodes },
      placing: null,
      connectMode: false,
      connectFrom: null,
      dragId: null,
      editingEdge: null,
      invalidNodes: [],
      invalidEdges: [],
      settingsOpen: false,
    })
  },
  clear: () =>
    set({
      spec: null,
      placing: null,
      connectMode: false,
      connectFrom: null,
      dragId: null,
      editingEdge: null,
      invalidNodes: [],
      invalidEdges: [],
      settingsOpen: false,
    }),

  setPlacing: (placing) => set({ placing, connectMode: placing ? false : get().connectMode, connectFrom: null }),
  setConnectMode: (connectMode) =>
    set({ connectMode, placing: connectMode ? null : get().placing, connectFrom: null }),
  setShift: (shiftDown) => set({ shiftDown }),
  setConnectFrom: (connectFrom) => set({ connectFrom }),
  startDrag: (dragId) => set({ dragId }),
  endDrag: () => set({ dragId: null }),
  setEditingEdge: (editingEdge) => set({ editingEdge }),
  setSettingsOpen: (settingsOpen) => set({ settingsOpen }),
  markInvalid: (issues) =>
    set({
      invalidNodes: [...new Set(issues.flatMap((i) => i.node_ids))],
      invalidEdges: [...new Set(issues.flatMap((i) => i.edges.map(([s, t]) => edgeKey(s, t))))],
    }),
  clearInvalid: () => set({ invalidNodes: [], invalidEdges: [] }),

  addNodeAt: (type, x, z) => {
    const { spec } = get()
    if (!spec) return
    if (spec.nodes.length >= MAX_NODES) {
      toast(`A network can have at most ${MAX_NODES} nodes`)
      return
    }
    const cost = nodeBuildCost(spec, type)
    if (cost > remainingBudget(spec)) {
      toast(`Not enough build budget: a ${PREFIX[type]} costs ${money(cost)}, you have ${money(remainingBudget(spec))}`)
      return
    }
    const taken = new Set(spec.nodes.map((n) => n.id))
    let n = spec.nodes.filter((node) => node.type === type).length + 1
    while (taken.has(`${PREFIX[type]}_${n}`)) n++
    const node = newNode(type, `${PREFIX[type]}_${n}`, x, z)
    set({
      spec: { ...spec, nodes: [...spec.nodes, node] },
      placing: null,
      invalidNodes: [],
      invalidEdges: [],
    })
    useGameStore.getState().selectNode(node.id)
  },

  moveNode: (id, x, z) => {
    const { spec } = get()
    if (!spec) return
    const node = spec.nodes.find((n) => n.id === id)
    if (!node || (node.x === x && node.z === z)) return
    set({ spec: { ...spec, nodes: spec.nodes.map((n) => (n.id === id ? { ...n, x, z } : n)) } })
  },

  removeNode: (id) => {
    const { spec } = get()
    if (!spec) return
    const node = spec.nodes.find((n) => n.id === id)
    if (!node) return
    if (spec.locked_nodes?.includes(id)) {
      toast(`${node.name} is part of the contract and can't be removed`)
      return
    }
    const isSupply = node.type === 'Supplier' || node.type === 'Manufacturer'
    const sameKind = spec.nodes.filter((n) =>
      isSupply ? n.type === 'Supplier' || n.type === 'Manufacturer' : n.type === node.type,
    )
    if ((isSupply || node.type === 'Retailer') && sameKind.length <= 1) {
      toast(
        `Can't delete ${node.name}: the network needs at least one ${isSupply ? 'supplier' : 'retailer'}`,
      )
      return
    }
    set({
      spec: {
        ...spec,
        nodes: spec.nodes.filter((n) => n.id !== id),
        edges: spec.edges.filter((e) => e.source !== id && e.target !== id),
      },
      invalidNodes: [],
      invalidEdges: [],
      connectFrom: get().connectFrom === id ? null : get().connectFrom,
      editingEdge: null,
    })
    const game = useGameStore.getState()
    if (game.selectedNodeId === id) game.selectNode(null)
  },

  updateNode: (id, patch) => {
    const { spec } = get()
    if (!spec) return
    set({ spec: { ...spec, nodes: spec.nodes.map((n) => (n.id === id ? { ...n, ...patch } : n)) } })
  },

  addEdge: (source, target) => {
    const { spec } = get()
    if (!spec) return null
    const name = (id: string) => spec.nodes.find((n) => n.id === id)?.name ?? id
    if (source === target) {
      toast(`${name(source)} can't connect to itself`)
      return null
    }
    if (spec.edges.some((e) => e.source === source && e.target === target)) {
      toast(`${name(source)} → ${name(target)} already exists`)
      return null
    }
    const cost = spec.economy.build_cost_per_lead_time * 2
    if (cost > remainingBudget(spec)) {
      toast(`Not enough build budget: a connection costs ${money(cost)}, you have ${money(remainingBudget(spec))}`)
      return null
    }
    const edge: EdgeSpec = {
      source,
      target,
      lead_time: 2,
      capacity: null,
      cost_per_unit: 0,
      mode: 'truck',
    }
    set({
      spec: { ...spec, edges: [...spec.edges, edge] },
      editingEdge: { source, target },
      invalidNodes: [],
      invalidEdges: [],
    })
    return edge
  },

  removeEdge: (source, target) => {
    const { spec, editingEdge } = get()
    if (!spec) return
    set({
      spec: {
        ...spec,
        edges: spec.edges.filter((e) => !(e.source === source && e.target === target)),
      },
      editingEdge:
        editingEdge?.source === source && editingEdge.target === target ? null : editingEdge,
      invalidNodes: [],
      invalidEdges: [],
    })
  },

  updateEdge: (source, target, patch) => {
    const { spec } = get()
    if (!spec) return
    // A longer route costs more to build; refuse a change that overspends.
    if (patch.lead_time !== undefined) {
      const next = {
        ...spec,
        edges: spec.edges.map((e) =>
          e.source === source && e.target === target ? { ...e, ...patch } : e,
        ),
      }
      if (remainingBudget(next) < 0) {
        toast(`Not enough build budget for a lead time of ${patch.lead_time}`)
        return
      }
    }
    set({
      spec: {
        ...spec,
        edges: spec.edges.map((e) =>
          e.source === source && e.target === target ? { ...e, ...patch } : e,
        ),
      },
    })
  },
}))
