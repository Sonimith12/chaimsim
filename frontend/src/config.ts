import type { Speed } from './store/gameStore'

/** Real-time milliseconds per simulated period at each speed. */
export const STEP_INTERVAL_MS: Record<Speed, number> = {
  slow: 2000,
  normal: 1000,
  fast: 250,
  turbo: 125, // 8 steps per second (unlocked in the campaign)
}
