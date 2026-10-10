import { useMemo } from 'react'
import type { ThreeEvent } from '@react-three/fiber'
import { CanvasTexture, RepeatWrapping, SRGBColorSpace } from 'three'

interface Props {
  onClick?: (e: ThreeEvent<MouseEvent>) => void
  onDoubleClick?: () => void
  onPointerMove?: (e: ThreeEvent<PointerEvent>) => void
  /** Draw the snap grid (edit mode). */
  showGrid?: boolean
}

const TILE_PX = 256
const TILES = 24 // across the 120-unit plane: 5 world units per slab

/** Procedural concrete: speckle noise plus faint slab joints. No asset needed. */
function makeConcreteTexture(): CanvasTexture {
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = TILE_PX
  const ctx = canvas.getContext('2d')!
  ctx.fillStyle = '#1a2130'
  ctx.fillRect(0, 0, TILE_PX, TILE_PX)

  // Deterministic speckle so the texture doesn't change between reloads.
  let seed = 7
  const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646
  for (let i = 0; i < 5200; i++) {
    const v = Math.floor(18 + rand() * 40)
    ctx.fillStyle = `rgba(${v + 10}, ${v + 14}, ${v + 26}, ${0.1 + rand() * 0.22})`
    const s = 1 + rand() * 2
    ctx.fillRect(rand() * TILE_PX, rand() * TILE_PX, s, s)
  }
  ctx.strokeStyle = 'rgba(8, 12, 20, 0.85)'
  ctx.lineWidth = 3
  ctx.strokeRect(0, 0, TILE_PX, TILE_PX)

  const tex = new CanvasTexture(canvas)
  tex.wrapS = tex.wrapT = RepeatWrapping
  tex.repeat.set(TILES, TILES)
  tex.colorSpace = SRGBColorSpace
  tex.anisotropy = 8
  return tex
}

export function Ground({ onClick, onDoubleClick, onPointerMove, showGrid = false }: Props) {
  const texture = useMemo(makeConcreteTexture, [])
  return (
    <group>
      <mesh
        rotation-x={-Math.PI / 2}
        position-y={-0.01}
        receiveShadow
        onClick={(e) => {
          if (e.delta <= 2) onClick?.(e) // ignore the end of an orbit drag
        }}
        onDoubleClick={(e) => {
          if (e.delta <= 2) onDoubleClick?.()
        }}
        onPointerMove={onPointerMove}
      >
        <planeGeometry args={[120, 120]} />
        <meshStandardMaterial map={texture} roughness={0.85} metalness={0.15} />
      </mesh>
      {showGrid && (
        // 60 cells of 2 units: matches the editor's snap size.
        <gridHelper
          args={[120, 60, '#38bdf8', '#2b5a86']}
          position-y={0.015}
          material-transparent
          material-opacity={0.4}
          material-depthWrite={false}
        />
      )}
    </group>
  )
}
