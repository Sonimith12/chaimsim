import { useFrame } from '@react-three/fiber'
import { useEffect, useRef } from 'react'
import type { Group, MeshStandardMaterial } from 'three'
import { useFittedModel } from '../../models/useFittedModel'
import type { Appearance, NodeHandlers, Size3 } from '../appearance'

export interface BuildingProps {
  appearance: React.RefObject<Appearance>
  handlers: NodeHandlers
  /** Desynchronises the idle motion between nodes. */
  phase: number
  onMeasured: (size: Size3) => void
  position?: [number, number, number]
  rotation?: [number, number, number]
  scale?: number
}

interface Props extends BuildingProps {
  path: string
  /** Target footprint in world units (see MODEL_FIT). */
  footprint: number
}

const hasEmissive = (m: unknown): m is MeshStandardMaterial =>
  typeof m === 'object' && m !== null && 'emissive' in m && 'emissiveIntensity' in m

/** Shared implementation behind FactoryModel / WarehouseModel / StoreModel. */
export function BuildingModel({
  path,
  footprint,
  appearance,
  handlers,
  phase,
  onMeasured,
  position = [0, 0, 0],
  rotation = [0, 0, 0],
  scale = 1,
}: Props) {
  const fitted = useFittedModel(path, footprint * scale)
  const idle = useRef<Group>(null)

  useEffect(() => {
    onMeasured(fitted.size)
  }, [fitted, onMeasured])

  useFrame(({ clock }) => {
    const a = appearance.current
    for (const m of fitted.materials) {
      if (!hasEmissive(m)) continue
      m.emissive.copy(a.modelGlow)
      m.emissiveIntensity = a.modelGlowIntensity
    }
    // Very slow bob and sway; enough to feel alive, not enough to distract.
    const g = idle.current
    if (g) {
      const t = clock.elapsedTime
      g.position.y = Math.sin(t * 0.7 + phase) * 0.025
      g.rotation.y = Math.sin(t * 0.25 + phase) * 0.035
    }
  })

  return (
    <group position={position} rotation={rotation} {...handlers}>
      <group ref={idle}>
        <primitive object={fitted.root} scale={fitted.scale} position={fitted.offset} />
      </group>
    </group>
  )
}
