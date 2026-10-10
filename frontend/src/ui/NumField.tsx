import { useEffect, useState } from 'react'

interface Props {
  value: number
  onCommit: (value: number) => void
  min?: number
  step?: number | 'any'
  disabled?: boolean
  autoFocus?: boolean
  onEnter?: () => void
}

/**
 * A number input that keeps its own text while typing, so intermediate states
 * ("", "1.", "-") are allowed, and only reports complete valid numbers.
 */
export function NumField({ value, onCommit, min, step = 'any', disabled, autoFocus, onEnter }: Props) {
  const [text, setText] = useState(String(value))

  // Follow external changes (e.g. switching to another node) unless the text already means this value.
  useEffect(() => {
    setText((t) => (Number(t) === value && t.trim() !== '' ? t : String(value)))
  }, [value])

  return (
    <input
      type="number"
      inputMode="decimal"
      value={text}
      min={min}
      step={step}
      disabled={disabled}
      autoFocus={autoFocus}
      onChange={(e) => {
        setText(e.target.value)
        const n = Number(e.target.value)
        if (e.target.value.trim() !== '' && Number.isFinite(n)) onCommit(n)
      }}
      onKeyDown={(e) => {
        if (e.key === 'Enter') onEnter?.()
      }}
    />
  )
}
