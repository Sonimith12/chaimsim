import { useFrame } from '@react-three/fiber'
import { Suspense, useMemo, useRef } from 'react'
import { Color, type Group } from 'three'
import { STEP_INTERVAL_MS } from '../../config'
import { useGameStore } from '../../store/gameStore'
import { useSimStore } from '../../store/simStore'
import type { NodeState, ShipmentState } from '../../types/sim'
import { NODE_COLORS } from '../colors'
import { ErrorBoundary } from '../ErrorBoundary'
import { useModelReady } from '../models/ModelRegistry'
import { TruckModel } from '../nodes/models/TruckModel'
import { EDGE_Y, edgeEndpoints } from './geometry'

const TRUCK_LIFT = 0.28
const WHITE = new Color('#ffffff')

interface TruckProps {
  shipment: ShipmentState
  from: [number, number, number]
  to: [number, number, number]
  color: string
}

function TruckBox({ tint }: { tint: Color }) {
  return (
    <mesh castShadow>
      <boxGeometry args={[0.32, 0.3, 0.5]} />
      <meshStandardMaterial color={tint} emissive={tint} emissiveIntensity={0.35} />
    </mesh>
  )
}

function Truck({ shipment, from, to, color }: TruckProps) {
  const modelReady = useModelReady('truck')
  const group = useRef<Group>(null)
  const { start, end, dir } = useMemo(() => edgeEndpoints(from, to), [from, to])
  const tint = useMemo(() => new Color(color).lerp(WHITE, 0.45), [color])
  const heading = Math.atan2(dir.x, dir.z)
  const span = Math.max(1, shipment.arrive - shipment.depart)

  useFrame(() => {
    const g = group.current
    if (!g) return
    // State arrives once per period; between arrivals, tween from where the
    // truck was after the previous step to where it is after this one.
    const { currentPeriod, speed } = useGameStore.getState()
    const { receivedAt } = useSimStore.getState()
    const tween = Math.min(1, (performance.now() - receivedAt) / STEP_INTERVAL_MS[speed])
    const done = currentPeriod - shipment.depart // periods elapsed after the latest step
    const progress = (done - 1 + tween) / span
    if (progress >= 1) {
      g.visible = false // arrived
      return
    }
    const p = Math.max(0, progress)
    g.visible = true
    g.position.set(
      start.x + (end.x - start.x) * p,
      start.y + TRUCK_LIFT,
      start.z + (end.z - start.z) * p,
    )
  })

  return (
    <group ref={group} rotation-y={heading} visible={false}>
      {modelReady ? (
        <ErrorBoundary fallback={<TruckBox tint={tint} />}>
          <Suspense fallback={<TruckBox tint={tint} />}>
            <group position-y={-(EDGE_Y + TRUCK_LIFT)}>
              <TruckModel />
            </group>
          </Suspense>
        </ErrorBoundary>
      ) : (
        <TruckBox tint={tint} />
      )}
    </group>
  )
}

interface LayerProps {
  shipments: ShipmentState[]
  positions: Map<string, [number, number, number]>
  nodes: NodeState[]
}

/** One small box per in-flight shipment, travelling along its edge. */
export function TruckLayer({ shipments, positions, nodes }: LayerProps) {
  const types = useMemo(() => new Map(nodes.map((n) => [n.id, n.type])), [nodes])
  return (
    <>
      {shipments.map((sh) => {
        const from = positions.get(sh.source)
        const to = positions.get(sh.target)
        const type = types.get(sh.source)
        if (!from || !to || !type) return null
        return <Truck key={sh.id} shipment={sh} from={from} to={to} color={NODE_COLORS[type]} />
      })}
    </>
  )
}
