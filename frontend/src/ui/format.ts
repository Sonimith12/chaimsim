import type { Grade, Objective } from '../types/sim'

export const money = (n: number) =>
  n.toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })

export const pct = (n: number) => `${(n * 100).toFixed(1)}%`

export const whole = (n: number) => Math.round(n).toLocaleString()

export function formatValue(unit: Objective['unit'], value: number): string {
  switch (unit) {
    case 'currency':
      return money(value)
    case 'percent':
      return pct(value)
    case 'units':
      return `${whole(value)} units`
    case 'count':
      return whole(value)
  }
}

/** "Keep total cost under $28,244" / "Bonus: zero stockouts". */
export function objectiveTitle(o: Objective): string {
  if (o.unit === 'count' && o.target === 0) return o.label
  const target = o.unit === 'percent' ? `${Math.round(o.target * 100)}%+` : formatValue(o.unit, o.target)
  return `${o.label} ${target}`
}

export const GRADE_COLORS: Record<Grade, string> = {
  S: '#fbbf24',
  A: '#4ade80',
  B: '#38bdf8',
  C: '#facc15',
  D: '#fb923c',
  F: '#f87171',
}

export const STATUS_COLORS = { green: '#4ade80', yellow: '#facc15', red: '#f87171' } as const
