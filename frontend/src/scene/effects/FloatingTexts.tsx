import { Html } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import type { Group } from 'three'
import { useGameStore, type Floater } from '../../store/gameStore'

const LIFETIME_MS = 1600
const START_Y = 3.4
const RISE = 2.2

function FloatingText({ floater, position }: { floater: Floater; position: [number, number, number] }) {
  const group = useRef<Group>(null)
  const label = useRef<HTMLDivElement>(null)
  // Spread simultaneous texts on one node so they don't overlap exactly.
  const jitter = ((floater.id % 3) - 1) * 0.7

  useFrame(() => {
    const age = Math.min(1, (performance.now() - floater.born) / LIFETIME_MS)
    if (group.current) group.current.position.y = START_Y + RISE * (1 - (1 - age) * (1 - age))
    if (label.current) label.current.style.opacity = String(Math.max(0, 1 - age * age * age))
  })

  return (
    <group ref={group} position={[position[0] + jitter, START_Y, position[2]]}>
      <Html center style={{ pointerEvents: 'none' }}>
        <div ref={label} className="floater" style={{ color: floater.color }}>
          {floater.text}
        </div>
      </Html>
    </group>
  )
}

/** "-200" / "+50" score feedback rising off the node it relates to. */
export function FloatingTexts({ positions }: { positions: Map<string, [number, number, number]> }) {
  const floaters = useGameStore((s) => s.floaters)
  return (
    <>
      {floaters.map((f) => {
        const position = positions.get(f.nodeId)
        return position ? <FloatingText key={f.id} floater={f} position={position} /> : null
      })}
    </>
  )
}
