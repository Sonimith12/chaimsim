import { Html, Line } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import { useMemo, useRef, useState } from 'react'
import { Quaternion, Vector3 } from 'three'
import { edgeKey, remainingBudget, useEditStore } from '../../store/editStore'
import { useGameStore } from '../../store/gameStore'
import type { EdgeState } from '../../types/sim'
import { NumField } from '../../ui/NumField'
import { edgeEndpoints } from './geometry'

interface Props {
  edge: EdgeState
  from: [number, number, number]
  to: [number, number, number]
}

const INVALID = '#ef4444'

/** Inline lead-time editor shown at an edge's midpoint (edit mode). */
function LeadTimeEditor({ edge, onDone }: { edge: EdgeState; onDone: () => void }) {
  const updateEdge = useEditStore((s) => s.updateEdge)
  const [value, setValue] = useState(edge.lead_time)
  const spec = useEditStore((s) => s.spec)
  const isFree = !!spec?.free_edges.some(([s, t]) => s === edge.source && t === edge.target)
  const perUnit = spec?.economy.build_cost_per_lead_time ?? 0
  // Budget left if this edge ended up at the typed lead time (original edges cost nothing).
  const cost = isFree ? 0 : perUnit * value
  const spare = spec ? remainingBudget(spec) + (isFree ? 0 : perUnit * edge.lead_time) - cost : 0
  const valid = value >= 1 && spare >= 0
  const commit = () => {
    if (valid) updateEdge(edge.source, edge.target, { lead_time: value })
    onDone()
  }
  return (
    <div className="edge-editor">
      <span>Lead time</span>
      <NumField value={value} min={1} onCommit={setValue} onEnter={commit} autoFocus />
      {!isFree && (
        <span className={spare < 0 ? 'neg' : 'muted'}>
          ${Math.round(cost).toLocaleString()}
        </span>
      )}
      <button onClick={commit} disabled={!valid}>
        OK
      </button>
    </div>
  )
}

export function TransportEdge({ edge, from, to }: Props) {
  const lineRef = useRef<{ material: { dashOffset: number } } | null>(null)
  const editing = useGameStore((s) => s.currentPhase === 'edit')
  const key = edgeKey(edge.source, edge.target)
  const invalid = useEditStore((s) => s.invalidEdges.includes(key))
  const isEditingThis = useEditStore(
    (s) => s.editingEdge?.source === edge.source && s.editingEdge.target === edge.target,
  )

  const { points, mid, arrowPos, arrowQuat, center, length } = useMemo(() => {
    const { start, end, dir } = edgeEndpoints(from, to)
    const quat = new Quaternion().setFromUnitVectors(new Vector3(0, 1, 0), dir)
    return {
      points: [start, end] as [Vector3, Vector3],
      mid: start.clone().lerp(end, 0.5).add(new Vector3(0, 0.7, 0)),
      arrowPos: end.clone().addScaledVector(dir, -0.25),
      arrowQuat: quat,
      center: start.clone().lerp(end, 0.5),
      length: start.distanceTo(end),
    }
  }, [from, to])

  const flowing = edge.in_transit > 0.5
  // Dashes march toward the destination; faster when more material is in transit.
  const speed = editing ? 0.5 : flowing ? 1.2 + Math.min(edge.in_transit / 200, 2) : 0.25

  useFrame((_, delta) => {
    const mat = lineRef.current?.material
    if (mat) mat.dashOffset -= delta * speed
  })

  const color = invalid ? INVALID : editing ? '#7dd3fc' : flowing ? '#38bdf8' : '#475569'

  return (
    <group>
      <Line
        // drei exposes the underlying Line2 through the ref
        ref={lineRef as never}
        points={points}
        color={color}
        lineWidth={invalid ? 3.5 : flowing || editing ? 3 : 1.5}
        dashed
        dashSize={0.35}
        gapSize={0.25}
      />
      <mesh position={arrowPos} quaternion={arrowQuat}>
        <coneGeometry args={[0.18, 0.4, 12]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.6} />
      </mesh>

      {editing && (
        // A fat invisible tube so a thin line can be right-clicked to delete it.
        <mesh
          position={center}
          quaternion={arrowQuat}
          onContextMenu={(e) => {
            e.stopPropagation()
            e.nativeEvent.preventDefault()
            useEditStore.getState().removeEdge(edge.source, edge.target)
          }}
        >
          <cylinderGeometry args={[0.3, 0.3, length, 8]} />
          <meshBasicMaterial transparent opacity={0} depthWrite={false} />
        </mesh>
      )}

      <Html position={mid} center style={{ pointerEvents: editing ? 'auto' : 'none' }}>
        {editing ? (
          isEditingThis ? (
            <LeadTimeEditor
              edge={edge}
              onDone={() => useEditStore.getState().setEditingEdge(null)}
            />
          ) : (
            <div className={`edge-label edge-label-edit${invalid ? ' invalid' : ''}`}>
              <button
                className="edge-chip"
                title="Edit lead time"
                onClick={() =>
                  useEditStore.getState().setEditingEdge({ source: edge.source, target: edge.target })
                }
              >
                LT {edge.lead_time} ✎
              </button>
              <button
                className="edge-x"
                title="Delete connection"
                onClick={() => useEditStore.getState().removeEdge(edge.source, edge.target)}
              >
                ×
              </button>
            </div>
          )
        ) : (
          <div className="edge-label">
            LT {edge.lead_time}
            {flowing && <span> · {Math.round(edge.in_transit).toLocaleString()} in transit</span>}
          </div>
        )}
      </Html>
    </group>
  )
}
