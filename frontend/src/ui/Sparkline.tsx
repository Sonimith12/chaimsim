interface Props {
  values: number[]
  width?: number
  height?: number
}

/** Minimal SVG line chart; scales to the min/max of the values given. */
export function Sparkline({ values, width = 252, height = 38 }: Props) {
  if (values.length < 2) {
    return <div className="sparkline-empty">Step the simulation to see a trend</div>
  }
  const pad = 3
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const x = (i: number) => pad + (i / (values.length - 1)) * (width - pad * 2)
  const y = (v: number) => height - pad - ((v - min) / span) * (height - pad * 2)
  const points = values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  const last = values.length - 1

  return (
    <svg className="sparkline" width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline points={points} fill="none" stroke="#38bdf8" strokeWidth="1.5" strokeLinejoin="round" />
      <circle cx={x(last)} cy={y(values[last])} r="2.5" fill="#38bdf8" />
    </svg>
  )
}
