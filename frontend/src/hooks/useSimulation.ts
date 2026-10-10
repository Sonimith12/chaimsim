import { useGameStore } from '../store/gameStore'
import { useCampaignStore } from '../store/campaignStore'
import { useEditStore } from '../store/editStore'
import { useHistoryStore } from '../store/historyStore'
import { useSimStore } from '../store/simStore'
import type { ServerMessage, ServerState } from '../types/sim'
import { closeSocket, connectSocket, sendCommand, setMessageHandler } from './useWebSocket'

// True while a step command is out and its reply hasn't arrived yet, so the
// auto-play timer can't pile up requests faster than the backend answers.
let stepInFlight = false
// Auto-play was running when an event interrupted it; resume once it's resolved.
let resumeAfterEvent = false

const RED = '#f87171'
const GREEN = '#4ade80'
const COST_COLORS = {
  revenue: GREEN,
  holding: RED,
  backlog: '#fb923c',
  policy: '#c084fc',
  event: '#c084fc',
} as const

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
    } else if (e.type === 'cost') {
      const sign = e.kind === 'revenue' ? '+' : '-'
      game.addFloater(
        e.node_id,
        `${sign}$${Math.round(e.amount).toLocaleString()}`,
        COST_COLORS[e.kind],
      )
    } else if (e.type === 'cash_crisis' && !state.finished) {
      game.showBanner('CASH CRISIS')
    }
  }
}

function applyServerState(state: ServerState) {
  stepInFlight = false
  const advanced = state.period > useSimStore.getState().period
  useSimStore.getState().updateFromServer(state)
  const game = useGameStore.getState()
  game.setCurrentPeriod(state.period)
  game.setError(null)
  if (state.pending_event) {
    // A decision event pauses the run until the player chooses.
    if (game.currentPhase === 'playing') resumeAfterEvent = true
    if (game.currentPhase === 'playing' || game.currentPhase === 'paused') game.setPhase('paused')
  }
  if (state.events.length > 0) showFeedback(state)
  if (advanced) {
    const service = state.objectives.find((o) => o.id === 'service')
    if (service && !service.met) game.warnScore()
  }
  if (state.finished) {
    game.selectNode(null)
    game.setPhase('results')
    if (state.result?.campaign && game.mode === 'campaign') {
      useCampaignStore.getState().recordRun({
        runKey: `${state.scenario_id}:${state.run_id}`,
        levelId: state.result.campaign.level,
        score: state.score.total,
        stars: state.result.campaign.stars,
      })
    }
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
        bankrupt: state.result.bankrupt,
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
    if (msg.event === 'event_resolved' && msg.outcome) {
      const game = useGameStore.getState()
      game.addToast(msg.outcome.message, msg.outcome.cash_delta < 0 ? 'warn' : 'info', 7000)
      if (resumeAfterEvent && !msg.state.finished && !msg.state.pending_event) game.setPhase('playing')
      resumeAfterEvent = false
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

/** Answer the pending decision event. `auto` marks a countdown that ran out. */
export function chooseEvent(uid: number, choiceId: string, auto = false) {
  if (!sendCommand({ type: 'event_action', event_id: uid, choice_id: choiceId, auto })) {
    useGameStore.getState().setError('Not connected to the simulation server.')
  }
}

export function step() {
  if (stepInFlight) return
  const { finished, pendingEvent } = useSimStore.getState()
  if (finished || pendingEvent) return
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
  resumeAfterEvent = false
  if (sendCommand({ type: 'reset' })) {
    useGameStore.getState().setPhase('paused')
  }
}

export function play() {
  const game = useGameStore.getState()
  const sim = useSimStore.getState()
  if (sim.finished || sim.pendingEvent) return
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
  // Return to the right menu for the mode the player was in.
  game.setSetupView(game.mode === 'campaign' ? 'campaign' : 'sandbox')
}
