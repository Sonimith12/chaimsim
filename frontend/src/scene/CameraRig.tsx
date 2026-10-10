import { useFrame, useThree } from '@react-three/fiber'
import { useEffect, useRef } from 'react'
import { Vector3 } from 'three'
import { useGameStore } from '../store/gameStore'

const DURATION_MS = 500
const FOCUS_ZOOM = 0.75 // fraction of the current distance to move in on first focus
const MIN_FOCUS_DISTANCE = 11
const PULLBACK = 1.35 // results camera: this much farther out than the overview
const PULLBACK_MS = 1600
export const OVERVIEW_TARGET: [number, number, number] = [0, 0.5, 0]

interface OrbitLike {
  target: Vector3
  update: () => void
}

interface Anim {
  start: number
  fromTarget: Vector3
  toTarget: Vector3
  fromPos: Vector3
  toPos: Vector3
  durationMs?: number
}

interface Props {
  positions: Map<string, [number, number, number]>
  overviewPosition: [number, number, number]
}

/** Smoothly flies the camera to the selected node, or back to the overview on request. */
export function CameraRig({ positions, overviewPosition }: Props) {
  const camera = useThree((s) => s.camera)
  const controls = useThree((s) => s.controls) as unknown as OrbitLike | null
  const selectedId = useGameStore((s) => s.selectedNodeId)
  const resetToken = useGameStore((s) => s.cameraResetToken)
  const phase = useGameStore((s) => s.currentPhase)

  const anim = useRef<Anim | null>(null)
  const focused = useRef(false)
  // Positions are recomputed every step; keep them out of the effect deps.
  const positionsRef = useRef(positions)
  positionsRef.current = positions

  useEffect(() => {
    if (!controls) return
    if (!selectedId) {
      focused.current = false
      return
    }
    // Selecting while editing opens the config panel; the camera stays put so dragging is predictable.
    if (useGameStore.getState().currentPhase === 'edit') return
    const p = positionsRef.current.get(selectedId)
    if (!p) return
    const toTarget = new Vector3(p[0], 0.9, p[2])
    const offset = camera.position.clone().sub(controls.target)
    const dist = offset.length()
    // Zoom in on the first focus; hopping between nodes keeps the current zoom.
    const newDist = focused.current ? dist : Math.max(MIN_FOCUS_DISTANCE, dist * FOCUS_ZOOM)
    focused.current = true
    anim.current = {
      start: performance.now(),
      fromTarget: controls.target.clone(),
      toTarget,
      fromPos: camera.position.clone(),
      toPos: toTarget.clone().addScaledVector(offset.normalize(), newDist),
    }
  }, [selectedId, controls, camera])

  const firstReset = useRef(true)
  useEffect(() => {
    if (firstReset.current) {
      firstReset.current = false
      return
    }
    if (!controls) return
    focused.current = false
    anim.current = {
      start: performance.now(),
      fromTarget: controls.target.clone(),
      toTarget: new Vector3(...OVERVIEW_TARGET),
      fromPos: camera.position.clone(),
      toPos: new Vector3(...overviewPosition),
    }
  }, [resetToken]) // eslint-disable-line react-hooks/exhaustive-deps

  // Leaving edit mode: glide out to frame the (possibly rearranged) network.
  const prevPhase = useRef(phase)
  useEffect(() => {
    const wasEditing = prevPhase.current === 'edit'
    const wasSetup = prevPhase.current === 'setup'
    prevPhase.current = phase
    if (!controls) return
    if (wasSetup && phase !== 'setup') {
      // The canvas lives behind the scenario picker, so frame the new network
      // instantly (it's hidden until now) rather than gliding from wherever it was.
      anim.current = null
      focused.current = false
      controls.target.set(...OVERVIEW_TARGET)
      camera.position.set(...overviewPosition)
      controls.update()
      return
    }
    if (!wasEditing || phase === 'edit') return
    focused.current = false
    anim.current = {
      start: performance.now(),
      fromTarget: controls.target.clone(),
      toTarget: new Vector3(...OVERVIEW_TARGET),
      fromPos: camera.position.clone(),
      toPos: new Vector3(...overviewPosition),
      durationMs: 1200,
    }
  }, [phase]) // eslint-disable-line react-hooks/exhaustive-deps

  // When the run ends, pull back to show the whole chain behind the results.
  useEffect(() => {
    if (phase !== 'results' || !controls) return
    focused.current = false
    anim.current = {
      start: performance.now(),
      fromTarget: controls.target.clone(),
      toTarget: new Vector3(...OVERVIEW_TARGET),
      fromPos: camera.position.clone(),
      toPos: new Vector3(...overviewPosition).multiplyScalar(PULLBACK),
      durationMs: PULLBACK_MS,
    }
  }, [phase]) // eslint-disable-line react-hooks/exhaustive-deps

  useFrame(() => {
    const a = anim.current
    if (!a || !controls) return
    const t = Math.min(1, (performance.now() - a.start) / (a.durationMs ?? DURATION_MS))
    const e = t * t * (3 - 2 * t) // smoothstep
    controls.target.lerpVectors(a.fromTarget, a.toTarget, e)
    camera.position.lerpVectors(a.fromPos, a.toPos, e)
    controls.update()
    if (t >= 1) anim.current = null
  })

  return null
}
