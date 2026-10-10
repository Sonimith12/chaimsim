import type { EdgeSpec, EdgeState, NodeSpec, NodeState } from '../types/sim'

/** Present an editor node as a sim node so the scene renders both through the same components. */
export function draftNodeState(n: NodeSpec): NodeState {
  return {
    id: n.id,
    name: n.name || n.id,
    type: n.type,
    x: n.x,
    z: n.z,
    echelon: n.echelon,
    slot: n.slot,
    echelon_size: n.echelon_size,
    on_hand: n.initial_inventory,
    backlog: 0,
    pipeline: 0,
    last_order: 0,
    last_demand: 0,
    last_fulfilled: 0,
    avg_demand: 0,
    demand_shock: null,
    fill_rate: null,
    service_level: null,
    active: true,
    policy: n.policy ? { type: n.policy.type, params: n.policy.params } : null,
  }
}

export function draftEdgeState(e: EdgeSpec): EdgeState {
  return {
    source: e.source,
    target: e.target,
    lead_time: e.lead_time,
    in_transit: 0,
    mode: e.mode,
  }
}
