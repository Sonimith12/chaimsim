import { useEffect, useState } from 'react'
import { launch } from '../hooks/useEditor'
import { infrastructureCost, useEditStore } from '../store/editStore'
import { NumField } from './NumField'

const DEFAULT_SEED = 42

export function RunSettingsModal() {
  const open = useEditStore((s) => s.settingsOpen)
  const defaultPeriods = useEditStore((s) => s.spec?.n_periods ?? 52)
  const spec = useEditStore((s) => s.spec)
  const setOpen = useEditStore((s) => s.setSettingsOpen)
  const [periods, setPeriods] = useState(defaultPeriods)
  const [seed, setSeed] = useState(DEFAULT_SEED)
  const [busy, setBusy] = useState(false)
  const [events, setEvents] = useState(true)

  useEffect(() => {
    if (open) {
      setPeriods(defaultPeriods)
      setSeed(DEFAULT_SEED)
      setBusy(false)
    }
  }, [open, defaultPeriods])

  if (!open) return null

  const valid = Number.isInteger(periods) && periods >= 1 && periods <= 520 && Number.isInteger(seed)
  const go = async () => {
    setBusy(true)
    await launch({ nPeriods: periods, seed, events })
    setBusy(false)
  }

  return (
    <div className="modal-backdrop" onClick={() => setOpen(false)}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Run settings</h2>
        <label className="field">
          <span>Number of periods</span>
          <NumField value={periods} min={1} step={1} onCommit={setPeriods} onEnter={() => valid && go()} autoFocus />
        </label>
        <label className="field">
          <span>Random seed</span>
          <NumField value={seed} step={1} onCommit={setSeed} onEnter={() => valid && go()} />
        </label>
        <label className="check-row events-toggle">
          <input type="checkbox" checked={events} onChange={(e) => setEvents(e.target.checked)} />
          <span>Random decision events (pause the run for a choice)</span>
        </label>
        {spec && (
          <div className="muted modal-note">
            Starting cash: $
            {Math.round(spec.economy.starting_capital - infrastructureCost(spec)).toLocaleString()}
            {infrastructureCost(spec) > 0 &&
              ` (after $${Math.round(infrastructureCost(spec)).toLocaleString()} of construction)`}
          </div>
        )}
        {!valid && <div className="field-problem">Periods: a whole number from 1 to 520. Seed: a whole number.</div>}
        <div className="modal-actions">
          <button onClick={() => setOpen(false)}>Cancel</button>
          <button className="start-btn" disabled={!valid || busy} onClick={go}>
            Go
          </button>
        </div>
      </div>
    </div>
  )
}
