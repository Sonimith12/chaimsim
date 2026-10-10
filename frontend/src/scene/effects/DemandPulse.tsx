import { useFrame, useThree } from '@react-three/fiber'
import { useEffect, useRef } from 'react'
import type { Mesh, MeshBasicMaterial } from 'three'
import { STEP_INTERVAL_MS } from '../../config'
import { useGameStore } from '../../store/gameStore'

const RING_COUNT = 3
const RING_DELAY = 0.2 // fraction of the pulse each successive ring trails the previous

const NORMAL = '#22c55e'
const ELEVATED = '#bbf7d0'
const SHOCK = '#ef4444'

interface Pulse {
  start: number
  radius: number
  intensity: number
  rings: number
  duration: number
}

interface Props {
  period: number
  demand: number
  avgDemand: number
  /** Multiplier of an active demand shock, or null. */
  shock: number | null
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

/** Ripple rings on the ground around a retailer, fired once per period. */
export function DemandPulse({ period, demand, avgDemand, shock }: Props) {
  const clock = useThree((s) => s.clock)
  const pulse = useRef<Pulse | null>(null)
  const rings = useRef<(Mesh | null)[]>([])

  useEffect(() => {
    if (period === 0 || demand <= 0) {
      pulse.current = null
      return
    }
    const ratio = avgDemand > 0 ? demand / avgDemand : 1
    const boost = clamp(1 + (ratio - 1) * 0.8, 0.8, 1.6)
    const shocked = shock !== null && shock > 1
    const elevated = ratio > 1.2

    let radius = (1.8 + 0.18 * Math.sqrt(demand)) * boost
    let intensity = clamp(0.35 + 0.4 * ratio, 0.35, 1)
    if (shocked) {
      radius = Math.max(radius * 1.8, 6)
      intensity = 1
    }

    const color = shocked ? SHOCK : elevated ? ELEVATED : NORMAL
    rings.current.forEach((mesh) => {
      if (mesh) (mesh.material as MeshBasicMaterial).color.set(color)
    })

    const interval = STEP_INTERVAL_MS[useGameStore.getState().speed]
    pulse.current = {
      start: clock.elapsedTime,
      radius,
      intensity,
      rings: shocked ? RING_COUNT : 2,
      duration: clamp((interval * 0.9) / 1000, 0.5, 1.6),
    }
  }, [period]) // eslint-disable-line react-hooks/exhaustive-deps

  useFrame(({ clock: c }) => {
    const p = pulse.current
    rings.current.forEach((mesh, i) => {
      if (!mesh) return
      if (!p || i >= p.rings) {
        mesh.visible = false
        return
      }
      const t = (c.elapsedTime - p.start) / p.duration - i * RING_DELAY
      if (t < 0 || t > 1) {
        mesh.visible = false
        return
      }
      const eased = 1 - (1 - t) * (1 - t)
      const scale = p.radius * (0.3 + 0.7 * eased)
      mesh.visible = true
      mesh.scale.set(scale, scale, 1)
      ;(mesh.material as MeshBasicMaterial).opacity =
        p.intensity * Math.pow(1 - t, 1.5) * (1 - i * 0.2)
    })
  })

  return (
    <group position-y={0.03} rotation-x={-Math.PI / 2}>
      {Array.from({ length: RING_COUNT }, (_, i) => (
        <mesh
          key={i}
          ref={(m) => {
            rings.current[i] = m
          }}
          visible={false}
        >
          <ringGeometry args={[0.86, 1, 64]} />
          <meshBasicMaterial
            color={NORMAL}
            transparent
            opacity={0}
            depthWrite={false}
            toneMapped={false}
          />
        </mesh>
      ))}
    </group>
  )
}
