import { useEffect, useState } from 'react'
import { launch } from '../hooks/useEditor'
import { useEditStore } from '../store/editStore'
import { NumField } from './NumField'

const DEFAULT_SEED = 42

export function RunSettingsModal() {
  const open = useEditStore((s) => s.settingsOpen)
  const defaultPeriods = useEditStore((s) => s.spec?.n_periods ?? 52)
  const setOpen = useEditStore((s) => s.setSettingsOpen)
  const [periods, setPeriods] = useState(defaultPeriods)
  const [seed, setSeed] = useState(DEFAULT_SEED)
  const [busy, setBusy] = useState(false)

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
    await launch({ nPeriods: periods, seed })
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
