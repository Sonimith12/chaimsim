import { useEditStore, blankSpec } from '../store/editStore'
import { useGameStore } from '../store/gameStore'
import type { NetworkSpec, ServerState, ValidationIssue } from '../types/sim'
import { beginRun } from './useSimulation'

const OFFLINE =
  'Cannot reach the backend. Is `uvicorn main:app --port 8000` running?'

async function postJson(url: string, body: unknown) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return { ok: res.ok, status: res.status, body: await res.json().catch(() => null) }
}

function reportIssues(issues: ValidationIssue[]) {
  const game = useGameStore.getState()
  useEditStore.getState().markInvalid(issues)
  // One toast per distinct message, capped so a broken network doesn't bury the screen.
  for (const message of [...new Set(issues.map((i) => i.message))].slice(0, 4)) {
    game.addToast(message, 'error')
  }
}

/** Load a preset into edit mode (not play). */
export async function openPresetForEdit(id: string) {
  const game = useGameStore.getState()
  try {
    const res = await fetch(`/api/scenario/${id}/spec`)
    if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText)
    const spec = (await res.json()) as NetworkSpec
    useEditStore.getState().load(spec)
    game.selectNode(null)
    game.setError(null)
    game.setPhase('edit')
  } catch (err) {
    game.setError(err instanceof TypeError ? OFFLINE : String(err instanceof Error ? err.message : err))
  }
}

export function openBlank() {
  const game = useGameStore.getState()
  useEditStore.getState().load(blankSpec())
  game.selectNode(null)
  game.setError(null)
  game.setPhase('edit')
}

/** Ask the backend whether the edited network can run; opens the run-settings modal if so. */
export async function tryStart() {
  const { spec } = useEditStore.getState()
  if (!spec) return
  try {
    const { body } = await postJson('/api/network/validate', spec)
    if (body?.valid) {
      useEditStore.getState().clearInvalid()
      useEditStore.getState().setSettingsOpen(true)
    } else {
      reportIssues(body?.errors ?? [])
    }
  } catch {
    useGameStore.getState().addToast(OFFLINE)
  }
}

/** Build and load the edited network with the chosen run settings, then enter play mode. */
export async function launch(settings: { nPeriods: number; seed: number }) {
  const edit = useEditStore.getState()
  if (!edit.spec) return
  const spec: NetworkSpec = { ...edit.spec, n_periods: settings.nPeriods, seed: settings.seed }
  try {
    const { ok, body } = await postJson('/api/scenario/from_spec', spec)
    if (ok) {
      edit.setSettingsOpen(false)
      edit.clear()
      beginRun(body as ServerState)
      return
    }
    edit.setSettingsOpen(false)
    const issues = body?.detail?.errors as ValidationIssue[] | undefined
    if (issues) reportIssues(issues)
    else useGameStore.getState().addToast(String(body?.detail ?? 'Could not start the simulation'))
  } catch {
    useGameStore.getState().addToast(OFFLINE)
  }
}

/** Validate after adding an edge so a cycle is flagged straight away (the edge is kept). */
export async function warnIfCycle() {
  const { spec } = useEditStore.getState()
  if (!spec) return
  try {
    const { body } = await postJson('/api/network/validate', spec)
    const cycle = (body?.errors as ValidationIssue[] | undefined)?.find((e) => e.code === 'cycle')
    if (cycle) {
      useEditStore.getState().markInvalid([cycle])
      useGameStore.getState().addToast('Warning: this connection creates a cycle', 'warn')
    }
  } catch {
    /* validation is repeated on launch, so a failure here is harmless */
  }
}
