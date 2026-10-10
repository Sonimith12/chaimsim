import { Vector3 } from 'three'

const NODE_RADIUS = 1.6 // keep edges clear of the node boxes
export const EDGE_Y = 0.5

export interface EdgeEndpoints {
  start: Vector3
  end: Vector3
  dir: Vector3
}

/** The visible span of an edge: node centre to node centre, trimmed to the box faces. */
export function edgeEndpoints(
  from: [number, number, number],
  to: [number, number, number],
): EdgeEndpoints {
  const a = new Vector3(from[0], EDGE_Y, from[2])
  const b = new Vector3(to[0], EDGE_Y, to[2])
  const dir = b.clone().sub(a).normalize()
  return {
    start: a.clone().addScaledVector(dir, NODE_RADIUS),
    end: b.clone().addScaledVector(dir, -NODE_RADIUS),
    dir,
  }
}
