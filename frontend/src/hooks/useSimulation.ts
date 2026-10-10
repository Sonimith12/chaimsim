import { useGameStore } from '../store/gameStore'
import { useEditStore } from '../store/editStore'
import { useHistoryStore } from '../store/historyStore'
import { useSimStore } from '../store/simStore'
import type { ServerMessage, ServerState } from '../types/sim'
import { closeSocket, connectSocket, sendCommand, setMessageHandler } from './useWebSocket'

// True while a step command is out and its reply hasn't arrived yet, so the
// auto-play timer can't pile up requests faster than the backend answers.
let stepInFlight = false

const RED = '#f87171'
const GREEN = '#4ade80'

/** Turn the backend's one-off events from a step into on-screen feedback. */
function showFeedback(state: ServerState) {
  const game = useGameStore.getState()
  for (const e of state.events) {
    if (e.type === 'stockout') {
      game.addFloater(e.node_id, `${e.points}`, RED)
      game.flashStockout(e.node_id)
    } else if (e.type === 'policy_bonus') {
      game.addFloater(e.node_id, `+${e.points}`, GREEN)
    } else if (e.type === 'milestone' && !state.finished) {
      game.showBanner(`Quarter ${e.quarter} Complete`)
    }
  }
  const service = state.objectives.find((o) => o.id === 'service')
  if (service && !service.met) game.warnScore()
}

function applyServerState(state: ServerState) {
  stepInFlight = false
  const advanced = state.period > useSimStore.getState().period
  useSimStore.getState().updateFromServer(state)
  const game = useGameStore.getState()
  game.setCurrentPeriod(state.period)
  game.setError(null)
  if (advanced) showFeedback(state)
  if (state.finished) {
    game.selectNode(null)
    game.setPhase('results')
    if (state.result) {
      useHistoryStore.getState().add({
        runKey: `${state.scenario_id}:${state.run_id}`,
        scenarioId: state.scenario_id ?? 'unknown',
        scenarioName: state.scenario_name,
        score: state.score.total,
        grade: state.result.grade,
        stars: state.result.stars,
        objectives: state.objectives,
        stats: state.result.stats,
      })
    }
  }
}
setMessageHandler((msg: ServerMessage) => {
  if (msg.type === 'state') {
    applyServerState(msg.state)
    if (msg.event === 'policy_changed' && msg.node_id) {
      useGameStore.getState().flashNode(msg.node_id)
    }
  } else {
    stepInFlight = false
    useGameStore.getState().setError(msg.message)
  }
})

/** Enter play mode with a freshly loaded run (from the editor or a preset). */
export function beginRun(state: ServerState) {
  applyServerState(state)
  const game = useGameStore.getState()
  game.selectNode(null)
  game.setPhase('paused')
  connectSocket()
}

export async function loadScenario(name: string) {
  const game = useGameStore.getState()
  try {
    const res = await fetch('/api/scenario/load', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    })
    if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText)
    applyServerState(await res.json())
    game.selectNode(null)
    game.setPhase('paused')
    connectSocket()
  } catch (err) {
    game.setError(
      err instanceof TypeError
        ? 'Cannot reach the backend. Is `uvicorn main:app --port 8000` running?'
        : String(err instanceof Error ? err.message : err),
    )
  }
}

export function step() {
  if (stepInFlight) return
  const { finished } = useSimStore.getState()
  if (finished) return
  stepInFlight = sendCommand({ type: 'step' })
  if (!stepInFlight) useGameStore.getState().setError('Not connected to the simulation server.')
}

/** Ask the backend to swap a node's policy; it applies from the next period step. */
export function changePolicy(nodeId: string, policyType: string, params: Record<string, number>) {
  const sent = sendCommand({
    type: 'policy_change',
    node_id: nodeId,
    policy_type: policyType,
    params,
  })
  if (!sent) useGameStore.getState().setError('Not connected to the simulation server.')
  return sent
}

export function resetRun() {
  stepInFlight = false
  if (sendCommand({ type: 'reset' })) {
    useGameStore.getState().setPhase('paused')
  }
}

export function play() {
  const game = useGameStore.getState()
  if (useSimStore.getState().finished) return
  game.setPhase('playing')
}

export function pause() {
  useGameStore.getState().setPhase('paused')
}

export function backToSetup() {
  closeSocket()
  stepInFlight = false
  useSimStore.getState().reset()
  useEditStore.getState().clear()
  const game = useGameStore.getState()
  game.selectNode(null)
  game.setCurrentPeriod(0)
  game.setPhase('setup')
}
