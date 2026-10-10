import { useEffect, useRef, useState } from 'react'
import { useAnimatedNumber } from '../hooks/useAnimatedNumber'
import { useSimStore } from '../store/simStore'
import { STATUS_COLORS } from './format'

/** Cash balance, coloured by how much of the starting cash is left, flashing on income / expense. */
export function CashBadge() {
  const economy = useSimStore((s) => s.economy)
  const cash = economy?.cash ?? 0
  const shown = useAnimatedNumber(cash)

  const prev = useRef(cash)
  const [flash, setFlash] = useState<{ dir: 'up' | 'down'; key: number } | null>(null)
  useEffect(() => {
    const delta = cash - prev.current
    prev.current = cash
    if (Math.abs(delta) >= 1) setFlash((f) => ({ dir: delta > 0 ? 'up' : 'down', key: (f?.key ?? 0) + 1 }))
  }, [cash])

  if (!economy) return null
  const text = `${shown < 0 ? '-' : ''}$${Math.abs(Math.round(shown)).toLocaleString()}`

  return (
    <div className="hud-block hud-cash">
      <span className="hud-label">Cash</span>
      <span
        key={flash?.key ?? 0}
        className={`hud-value hud-cash-value${flash ? ` flash-${flash.dir}` : ''}`}
        style={{ color: STATUS_COLORS[economy.cash_status] }}
        title={`Started with $${Math.round(economy.initial_cash).toLocaleString()}`}
      >
        <span aria-hidden>💰</span> {text}
      </span>
    </div>
  )
}
