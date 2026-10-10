import { useFrame } from '@react-three/fiber'
import { useEffect, useRef } from 'react'
import type { Mesh, MeshStandardMaterial } from 'three'
import type { Appearance, NodeHandlers, Size3 } from './appearance'
import { PLACEHOLDER_SIZE } from './appearance'

interface Props {
  appearance: React.RefObject<Appearance>
  handlers: NodeHandlers
  onMeasured: (size: Size3) => void
  baseColor: string
}

/** The original coloured box; used whenever a model file is missing or still loading. */
export function PlaceholderBody({ appearance, handlers, onMeasured, baseColor }: Props) {
  const mesh = useRef<Mesh>(null)
  const [w, h, d] = PLACEHOLDER_SIZE

  useEffect(() => {
    onMeasured(PLACEHOLDER_SIZE)
  }, [onMeasured])

  useFrame(() => {
    const mat = mesh.current?.material as MeshStandardMaterial | undefined
    if (!mat) return
    const a = appearance.current
    mat.color.copy(a.tint)
    mat.emissive.copy(a.glow)
    mat.emissiveIntensity = a.glowIntensity
  })

  return (
    <group {...handlers}>
      <mesh ref={mesh} position-y={h / 2} castShadow receiveShadow>
        <boxGeometry args={[w, h, d]} />
        <meshStandardMaterial color={baseColor} emissive={baseColor} emissiveIntensity={0} />
      </mesh>
    </group>
  )
}
