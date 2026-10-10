import { useEffect, useRef, useState } from 'react'

/** Eases a displayed number toward `target` each animation frame (a rolling counter). */
export function useAnimatedNumber(target: number): number {
  const [value, setValue] = useState(target)
  const current = useRef(target)

  useEffect(() => {
    let raf = 0
    let last = performance.now()
    const tick = (now: number) => {
      const dt = Math.min(0.1, (now - last) / 1000)
      last = now
      const diff = target - current.current
      if (Math.abs(diff) < 0.5) {
        current.current = target
        setValue(target)
        return
      }
      current.current += diff * (1 - Math.exp(-dt * 7))
      setValue(current.current)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target])

  return value
}
