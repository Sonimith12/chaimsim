import { OrbitControls } from '@react-three/drei'
import { Canvas, type ThreeEvent } from '@react-three/fiber'
import { useMemo } from 'react'
import { Plane, Vector3 } from 'three'
import { snap, useEditStore } from '../store/editStore'
import { useGameStore } from '../store/gameStore'
import { useSimStore } from '../store/simStore'
import { CameraRig, OVERVIEW_TARGET } from './CameraRig'
import { TransportEdge } from './edges/TransportEdge'
import { TruckLayer } from './edges/Trucks'
import { draftEdgeState, draftNodeState } from './editAdapter'
import { EditInteractions } from './EditInteractions'
import { FloatingTexts } from './effects/FloatingTexts'
import { Atmosphere } from './environment/Atmosphere'
import { Ground } from './environment/Ground'
import { Lighting } from './environment/Lighting'
import { computeLayout } from './layout'
import { SupplyChainNode } from './nodes/SupplyChainNode'

/** Camera pulled back along a ~40 degree elevation, far enough to fit the whole network. */
function framedCameraPosition(radius: number): [number, number, number] {
  const d = radius * 2.3 + 10
  return [0, d * 0.7, d * 0.75]
}

// Dragged nodes follow the cursor on a plane at roughly box mid-height, so grabbing
// the top of a box doesn't make it jump away from the pointer.
const DRAG_PLANE = new Plane(new Vector3(0, 1, 0), -0.7)
const dragPoint = new Vector3()

export function SupplyChainWorld() {
  const editing = useGameStore((s) => s.currentPhase === 'edit')
  const idle = useGameStore((s) => s.currentPhase === 'setup')
  const selectNode = useGameStore((s) => s.selectNode)
  const resetCamera = useGameStore((s) => s.resetCamera)

  const simNodes = useSimStore((s) => s.networkState.nodes)
  const simEdges = useSimStore((s) => s.networkState.edges)
  const shipments = useSimStore((s) => s.shipments)
  const spec = useEditStore((s) => s.spec)

  const nodes = useMemo(
    () => (editing && spec ? spec.nodes.map(draftNodeState) : simNodes),
    [editing, spec, simNodes],
  )
  const edges = useMemo(
    () => (editing && spec ? spec.edges.map(draftEdgeState) : simEdges),
    [editing, spec, simEdges],
  )

  const layout = useMemo(() => computeLayout(nodes), [nodes])
  // The Canvas persists across edit -> play, so this only seeds the initial camera.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const initialCamera = useMemo(() => framedCameraPosition(layout.radius), [])
  const overview = useMemo(() => framedCameraPosition(layout.radius), [layout.radius])

  const onGroundClick = (e: ThreeEvent<MouseEvent>) => {
    const edit = useEditStore.getState()
    if (useGameStore.getState().currentPhase === 'edit' && edit.placing) {
      edit.addNodeAt(edit.placing, snap(e.point.x), snap(e.point.z))
      return
    }
    edit.setConnectFrom(null)
    selectNode(null)
  }

  const onGroundMove = (e: ThreeEvent<PointerEvent>) => {
    const edit = useEditStore.getState()
    if (!edit.dragId) return
    if (e.ray.intersectPlane(DRAG_PLANE, dragPoint)) {
      edit.moveNode(edit.dragId, snap(dragPoint.x), snap(dragPoint.z))
    }
  }

  return (
    <Canvas
      frameloop={idle ? 'never' : 'always'}
      shadows
      camera={{ fov: 45, near: 0.1, far: 400, position: initialCamera }}
      onPointerMissed={() => {
        useEditStore.getState().setConnectFrom(null)
        selectNode(null)
      }}
    >
      <color attach="background" args={['#06090f']} />
      <fog attach="fog" args={['#06090f', 38, 100]} />
      <Lighting edit={editing} />
      <Atmosphere />
      <Ground
        onClick={onGroundClick}
        onDoubleClick={editing ? undefined : resetCamera}
        onPointerMove={onGroundMove}
        showGrid={editing}
      />
      <CameraRig positions={layout.positions} overviewPosition={overview} />
      <OrbitControls
        makeDefault
        target={OVERVIEW_TARGET}
        maxPolarAngle={Math.PI / 2.1}
        minDistance={5}
        maxDistance={90}
      />
      {editing && <EditInteractions />}

      {edges.map((edge) => {
        const from = layout.positions.get(edge.source)
        const to = layout.positions.get(edge.target)
        if (!from || !to) return null
        return (
          <TransportEdge key={`${edge.source}->${edge.target}`} edge={edge} from={from} to={to} />
        )
      })}

      <FloatingTexts positions={layout.positions} />
      <TruckLayer shipments={shipments} positions={layout.positions} nodes={nodes} />

      {nodes.map((node) => {
        const position = layout.positions.get(node.id)
        return position ? <SupplyChainNode key={node.id} node={node} position={position} /> : null
      })}
    </Canvas>
  )
}
