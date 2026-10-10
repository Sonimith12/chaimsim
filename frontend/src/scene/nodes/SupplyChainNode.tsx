import { Html } from '@react-three/drei'
import { useFrame, useThree } from '@react-three/fiber'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { BackSide, Color, type Group, type Mesh, type MeshBasicMaterial } from 'three'
import { warnIfCycle } from '../../hooks/useEditor'
import { useEditStore } from '../../store/editStore'
import { useGameStore } from '../../store/gameStore'
import { useSimStore } from '../../store/simStore'
import type { NodeState } from '../../types/sim'
import { NODE_COLORS } from '../colors'
import { DemandPulse } from '../effects/DemandPulse'
import { createAppearance, PLACEHOLDER_SIZE, type NodeHandlers, type Size3 } from './appearance'
import { InventoryCrates } from './InventoryCrates'
import { NodeBody } from './NodeBody'

const SELECTED_LIFT = 0.35
const FLASH_SECONDS = 0.9
const STOCKOUT_FLASH_SECONDS = 0.8
const CRATE_COLOR = '#b7864b'

const BACKLOG_TINT = new Color('#f97316')
const OFFLINE = new Color('#7f1d1d')
const HALO_HOVER = new Color('#e2e8f0')
const HALO_SELECTED = new Color('#38bdf8')
const HALO_STOCKOUT = new Color('#ef4444')
const HALO_FLASH = new Color('#a3e635')

interface Props {
  node: NodeState
  position: [number, number, number]
}

const sameSize = (a: Size3, b: Size3) => a[0] === b[0] && a[1] === b[1] && a[2] === b[2]

export function SupplyChainNode({ node, position: layoutPosition }: Props) {
  // Stable reference: the layout is rebuilt each step and a re-applied position would snap the lift.
  const [px, py, pz] = layoutPosition
  const position = useMemo<[number, number, number]>(() => [px, py, pz], [px, py, pz])

  const selected = useGameStore((s) => s.selectedNodeId === node.id)
  const selectNode = useGameStore((s) => s.selectNode)
  const period = useGameStore((s) => s.currentPeriod)
  const flashAt = useGameStore((s) => (s.policyFlash?.nodeId === node.id ? s.policyFlash.at : 0))
  const stockoutAt = useGameStore((s) => s.stockoutFlashes[node.id] ?? 0)
  const editing = useGameStore((s) => s.currentPhase === 'edit')
  const simScale = useSimStore((s) => s.inventoryScale)
  const draftScale = useEditStore((s) => s.spec?.inventory_scale ?? 20)
  const inventoryScale = editing ? draftScale : simScale
  const connecting = useEditStore((s) => s.connectMode || s.shiftDown)
  const placing = useEditStore((s) => s.placing !== null)
  const isConnectSource = useEditStore((s) => s.connectFrom === node.id)
  const invalid = useEditStore((s) => s.invalidNodes.includes(node.id))
  const controls = useThree((s) => s.controls) as unknown as { enabled: boolean } | null
  const [hovered, setHovered] = useState(false)
  const [size, setSize] = useState<Size3>(PLACEHOLDER_SIZE)
  // The delete button lingers briefly after the pointer leaves so it can be reached.
  const [stickyHover, setStickyHover] = useState(false)
  useEffect(() => {
    if (hovered) {
      setStickyHover(true)
      return
    }
    const t = setTimeout(() => setStickyHover(false), 450)
    return () => clearTimeout(t)
  }, [hovered])

  const group = useRef<Group>(null)
  const haloRef = useRef<Mesh>(null)

  const baseColor = NODE_COLORS[node.type] ?? '#94a3b8'
  const stockout = node.on_hand < 0.5
  const phase = useMemo(
    () => [...node.id].reduce((acc, ch) => acc + ch.charCodeAt(0), 0) % 7,
    [node.id],
  )
  const appearance = useRef(createAppearance(baseColor))

  const onMeasured = useCallback((next: Size3) => setSize((prev) => (sameSize(prev, next) ? prev : next)), [])

  // Backlog tints the placeholder orange; an offline node goes dark red.
  const targetColor = useMemo(() => {
    if (!node.active) return OFFLINE.clone()
    const c = new Color(baseColor)
    return node.backlog > 0.5 ? c.lerp(BACKLOG_TINT, 0.6) : c
  }, [baseColor, node.active, node.backlog])

  useFrame(({ clock }, delta) => {
    const k = 1 - Math.exp(-delta * 10) // frame-rate independent smoothing
    const now = performance.now()

    const g = group.current
    if (g) g.position.y += (position[1] + (selected ? SELECTED_LIFT : 0) - g.position.y) * k

    // --- what the body should look like (read by the placeholder or the model) ---
    const a = appearance.current
    a.tint.lerp(targetColor, k)
    const stockoutAge = stockoutAt ? (now - stockoutAt) / 1000 : Infinity
    if (stockoutAge < STOCKOUT_FLASH_SECONDS) {
      const i = 0.9 * (1 - stockoutAge / STOCKOUT_FLASH_SECONDS)
      a.glow.copy(HALO_STOCKOUT)
      a.glowIntensity = i
      a.modelGlow.copy(HALO_STOCKOUT)
      a.modelGlowIntensity = i
    } else if (hovered || selected) {
      a.glow.copy(a.tint)
      a.glowIntensity = hovered ? 0.3 + 0.15 * Math.sin(clock.elapsedTime * 6) : 0.3
      a.modelGlow.copy(hovered ? HALO_HOVER : HALO_SELECTED)
      a.modelGlowIntensity = hovered ? 0.14 + 0.08 * Math.sin(clock.elapsedTime * 6) : 0.22
    } else {
      a.glowIntensity = 0
      if (!node.active) {
        a.modelGlow.copy(HALO_STOCKOUT)
        a.modelGlowIntensity = 0.45
      } else if (node.backlog > 0.5) {
        a.modelGlow.copy(BACKLOG_TINT)
        a.modelGlowIntensity = 0.28
      } else {
        a.modelGlowIntensity = 0
      }
    }

    // A halo shell behind the body doubles as its outline / glow. Priority:
    // stockout flash > policy-change flash > stockout > selected > hovered.
    const halo = haloRef.current
    if (!halo) return
    const hmat = halo.material as MeshBasicMaterial
    const flashAge = flashAt ? (now - flashAt) / 1000 : Infinity
    let opacity = 0
    let scale = 1.1
    if (stockoutAge < STOCKOUT_FLASH_SECONDS) {
      const t = stockoutAge / STOCKOUT_FLASH_SECONDS
      hmat.color.copy(HALO_STOCKOUT)
      opacity = 1 - t
      scale = 1.12 + 0.3 * t
    } else if (flashAge < FLASH_SECONDS) {
      const t = flashAge / FLASH_SECONDS
      hmat.color.copy(HALO_FLASH)
      opacity = 1 - t
      scale = 1.1 + 0.25 * t
    } else if (invalid || (stockout && !editing)) {
      hmat.color.copy(HALO_STOCKOUT)
      opacity = 0.3 + 0.65 * (0.5 + 0.5 * Math.sin(clock.elapsedTime * 5))
    } else if (selected || isConnectSource) {
      hmat.color.copy(HALO_SELECTED)
      opacity = 0.85
    } else if (hovered) {
      hmat.color.copy(HALO_HOVER)
      opacity = 0.35
      scale = 1.07
    }
    halo.visible = opacity > 0.01
    hmat.opacity = opacity
    halo.scale.setScalar(scale)
  })

  const handlers = useMemo<NodeHandlers>(
    () => ({
      onClick: (e) => {
        e.stopPropagation()
        if (e.delta > 2) return // end of an orbit drag
        const edit = useEditStore.getState()
        if (useGameStore.getState().currentPhase === 'edit') {
          if (edit.connectMode || edit.shiftDown) {
            const from = edit.connectFrom
            if (!from) {
              edit.setConnectFrom(node.id)
            } else {
              edit.setConnectFrom(null)
              if (edit.addEdge(from, node.id)) warnIfCycle()
            }
            return
          }
          if (edit.placing) return
        }
        selectNode(selected ? null : node.id)
      },
      onPointerDown: (e) => {
        const edit = useEditStore.getState()
        if (useGameStore.getState().currentPhase !== 'edit') return
        if (e.button !== 0 || edit.connectMode || edit.shiftDown || edit.placing) return
        e.stopPropagation()
        if (controls) controls.enabled = false
        edit.startDrag(node.id)
      },
      onContextMenu: (e) => {
        if (useGameStore.getState().currentPhase !== 'edit') return
        e.stopPropagation()
        e.nativeEvent.preventDefault()
        useEditStore.getState().removeNode(node.id)
      },
      onDoubleClick: (e) => e.stopPropagation(),
      onPointerOver: (e) => {
        e.stopPropagation()
        setHovered(true)
        document.body.style.cursor =
          useGameStore.getState().currentPhase === 'edit' ? 'grab' : 'pointer'
      },
      onPointerOut: () => {
        setHovered(false)
        document.body.style.cursor = ''
      },
    }),
    [selected, selectNode, node.id, controls],
  )

  const [w, h, d] = size

  return (
    <group ref={group} position={position}>
      <NodeBody
        type={node.type}
        baseColor={baseColor}
        appearance={appearance}
        handlers={handlers}
        phase={phase}
        onMeasured={onMeasured}
      />

      <mesh ref={haloRef} position-y={h / 2} visible={false}>
        <boxGeometry args={[w, h, d]} />
        <meshBasicMaterial
          side={BackSide}
          transparent
          opacity={0}
          depthWrite={false}
          toneMapped={false}
        />
      </mesh>

      {editing && !placing && !connecting && (
        // Drag handle: a ring on the ground. Pressing it (or the building) starts a drag.
        <mesh
          rotation-x={-Math.PI / 2}
          position-y={0.03}
          onPointerDown={handlers.onPointerDown}
          onPointerOver={handlers.onPointerOver}
          onPointerOut={handlers.onPointerOut}
        >
          <ringGeometry args={[Math.max(w, d) * 0.62, Math.max(w, d) * 0.72, 40]} />
          <meshBasicMaterial color="#38bdf8" transparent opacity={0.55} depthWrite={false} />
        </mesh>
      )}

      {editing && (hovered || stickyHover) && (
        <Html position={[w / 2 + 0.3, h + 0.35, 0]} center>
          <button
            className="node-x"
            title="Delete node"
            onClick={() => useEditStore.getState().removeNode(node.id)}
          >
            ×
          </button>
        </Html>
      )}

      <InventoryCrates
        onHand={node.on_hand}
        scale={inventoryScale}
        frontZ={d / 2 + 0.55}
        color={CRATE_COLOR}
      />

      {node.type === 'Retailer' && (
        <DemandPulse
          period={period}
          demand={node.last_demand}
          avgDemand={node.avg_demand}
          shock={node.demand_shock}
        />
      )}

      <Html position={[0, h + 0.9, 0]} center style={{ pointerEvents: 'none' }}>
        <div className={`node-label${selected ? ' selected' : ''}`}>
          <div className="node-label-name">{node.name}</div>
          <div className="node-label-stock">{Math.round(node.on_hand).toLocaleString()} on hand</div>
          {node.backlog > 0.5 && (
            <div className="node-label-backlog">
              {Math.round(node.backlog).toLocaleString()} backlog
            </div>
          )}
        </div>
      </Html>
    </group>
  )
}
