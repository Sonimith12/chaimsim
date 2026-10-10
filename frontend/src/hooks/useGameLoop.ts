import { useEffect } from 'react'
import { STEP_INTERVAL_MS } from '../config'
import { useGameStore } from '../store/gameStore'
import { step } from './useSimulation'

/** Drives auto-play: while playing, request a step on a timer set by the speed. */
export function useGameLoop() {
  const phase = useGameStore((s) => s.currentPhase)
  const speed = useGameStore((s) => s.speed)

  useEffect(() => {
    if (phase !== 'playing') return
    const timer = setInterval(step, STEP_INTERVAL_MS[speed])
    return () => clearInterval(timer)
  }, [phase, speed])
}
