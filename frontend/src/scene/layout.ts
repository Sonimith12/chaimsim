import type { NodeState } from '../types/sim'

type LayoutNode = Pick<NodeState, 'id' | 'echelon' | 'slot' | 'echelon_size' | 'x' | 'z'>

const ECHELON_SPACING = 7
const SLOT_SPACING = 6.5

export interface Layout {
  positions: Map<string, [number, number, number]>
  /** Largest half-extent of the network on the ground plane, for camera framing. */
  radius: number
}

/** Lay nodes out left to right by echelon, spreading siblings along z, centred on the origin. */
export function computeLayout(nodes: LayoutNode[]): Layout {
  const positions = new Map<string, [number, number, number]>()
  if (nodes.length === 0) return { positions, radius: 6 }

  const maxEchelon = Math.max(...nodes.map((n) => n.echelon))
  let extent = 4
  for (const n of nodes) {
    // A position chosen in the editor wins over the echelon-based default.
    const x = n.x ?? (n.echelon - maxEchelon / 2) * ECHELON_SPACING
    const z = n.z ?? (n.slot - (n.echelon_size - 1) / 2) * SLOT_SPACING
    positions.set(n.id, [x, 0, z])
    extent = Math.max(extent, Math.abs(x), Math.abs(z))
  }
  return { positions, radius: extent }
}
