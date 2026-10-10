import { useCampaignStore } from '../store/campaignStore'
import { useEditStore } from '../store/editStore'
import { useGameStore } from '../store/gameStore'
import type { CampaignLevelMeta, NetworkSpec, ServerState } from '../types/sim'
import { beginRun } from './useSimulation'

export async function fetchLevels() {
  try {
    const res = await fetch('/api/campaign')
    if (res.ok) useCampaignStore.getState().setLevels((await res.json()) as CampaignLevelMeta[])
  } catch {
    useGameStore.getState().setError('Cannot reach the backend. Is `uvicorn main:app --port 8000` running?')
  }
}

/** Start a campaign level: straight into play, or into the editor for the build level. */
export async function startCampaignLevel(id: number) {
  const game = useGameStore.getState()
  const level = useCampaignStore.getState().levels.find((l) => l.id === id)
  game.setMode('campaign', id)
  game.setError(null)
  try {
    if (level?.edit_mode) {
      const res = await fetch(`/api/campaign/${id}/spec`)
      if (!res.ok) throw new Error(res.statusText)
      useEditStore.getState().load((await res.json()) as NetworkSpec)
      game.selectNode(null)
      game.setPhase('edit')
      return
    }
    const res = await fetch(`/api/campaign/${id}/start`, { method: 'POST' })
    if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText)
    beginRun((await res.json()) as ServerState)
  } catch (err) {
    game.setMode('sandbox')
    game.setError(
      err instanceof TypeError
        ? 'Cannot reach the backend. Is `uvicorn main:app --port 8000` running?'
        : String(err instanceof Error ? err.message : err),
    )
  }
}
