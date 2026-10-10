import { Suspense } from 'react'
import { ErrorBoundary } from '../ErrorBoundary'
import { MODEL_FIT, MODEL_PATHS, useModelReady } from '../models/ModelRegistry'
import { useFittedModel } from '../models/useFittedModel'

const COLS = 4
const ROWS = 4
export const MAX_CRATES = COLS * ROWS
const STEP = 0.46
const SLOT = 0.38

function CrateModel() {
  const fitted = useFittedModel(MODEL_PATHS.crate, MODEL_FIT.crate)
  return <primitive object={fitted.root} scale={fitted.scale} position={fitted.offset} />
}

function CrateBox({ color }: { color: string }) {
  const s = MODEL_FIT.crate
  return (
    <mesh position-y={s / 2} castShadow receiveShadow>
      <boxGeometry args={[s, s, s]} />
      <meshStandardMaterial color={color} roughness={0.8} />
    </mesh>
  )
}

interface Props {
  /** Units of inventory on hand. */
  onHand: number
  /** Units each crate represents (from the scenario). */
  scale: number
  /** How far in front (+z) of the building centre the grid starts. */
  frontZ: number
  color: string
}

/** Inventory as a 4x4 grid of crates in front of the building; empty slots = nothing in stock. */
export function InventoryCrates({ onHand, scale, frontZ, color }: Props) {
  const crateReady = useModelReady('crate')
  const count = onHand < 0.5 ? 0 : Math.min(MAX_CRATES, Math.max(1, Math.round(onHand / scale)))

  const slots = []
  for (let i = 0; i < MAX_CRATES; i++) {
    const col = i % COLS
    const row = Math.floor(i / COLS)
    const x = (col - (COLS - 1) / 2) * STEP
    const z = frontZ + row * STEP
    const filled = i < count
    slots.push(
      <group key={i} position={[x, 0, z]}>
        {filled ? (
          crateReady ? (
            <ErrorBoundary fallback={<CrateBox color={color} />}>
              <Suspense fallback={<CrateBox color={color} />}>
                <CrateModel />
              </Suspense>
            </ErrorBoundary>
          ) : (
            <CrateBox color={color} />
          )
        ) : (
          // An empty pallet slot, so a stockout reads as bare ground rather than nothing.
          <mesh rotation-x={-Math.PI / 2} position-y={0.02}>
            <planeGeometry args={[SLOT, SLOT]} />
            <meshBasicMaterial color="#334155" transparent opacity={0.45} />
          </mesh>
        )}
      </group>,
    )
  }
  return <>{slots}</>
}
