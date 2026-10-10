import { useEffect, useMemo, useState } from 'react'
import { useCampaignStore } from '../store/campaignStore'
import { useGameStore } from '../store/gameStore'
import { useSimStore } from '../store/simStore'

interface Hint {
  id: string
  text: string
  /** Seen once something makes the hint moot (e.g. the player did what it suggests). */
  satisfied?: boolean
}

/** Contextual tutorial bubbles for the early levels; once dismissed they never return. */
export function HintBubble() {
  const mode = useGameStore((s) => s.mode)
  const phase = useGameStore((s) => s.currentPhase)
  const levelId = useGameStore((s) => s.campaignLevel)
  const selected = useGameStore((s) => s.selectedNodeId)
  const period = useGameStore((s) => s.currentPeriod)
  const level = useCampaignStore((s) => s.levels.find((l) => l.id === levelId))
  const seen = useCampaignStore((s) => s.hintsSeen)
  const markHint = useCampaignStore((s) => s.markHint)
  const nodes = useSimStore((s) => s.networkState.nodes)
  const policyChanges = useSimStore((s) => s.score?.policy_changes ?? 0)
  const pendingEvent = useSimStore((s) => s.pendingEvent)

  // Selecting a node, or changing a policy, answers those hints without a click.
  const [clickedNode, setClickedNode] = useState(false)
  useEffect(() => {
    if (selected) setClickedNode(true)
  }, [selected])
  useEffect(() => {
    if (clickedNode) markHint('click-node')
  }, [clickedNode, markHint])
  useEffect(() => {
    if (policyChanges > 0) markHint('change-policy')
  }, [policyChanges, markHint])

  const hint = useMemo<Hint | null>(() => {
    if (mode !== 'campaign' || !level?.hints || (phase !== 'paused' && phase !== 'playing')) return null
    if (pendingEvent) return null
    const lowStock = nodes.find((n) => n.low_stock && n.policy)
    // Most urgent first.
    if (lowStock && period >= 2) {
      return {
        id: 'low-stock',
        text: `${lowStock.name}'s inventory is getting low — consider increasing its order-up-to level.`,
      }
    }
    if (period >= 5 && policyChanges === 0) {
      return { id: 'change-policy', text: 'Try changing the replenishment policy: select a node and use the policy selector.' }
    }
    if (!clickedNode) return { id: 'click-node', text: 'Click a node to see its details.' }
    return null
  }, [mode, level, phase, nodes, period, policyChanges, clickedNode, pendingEvent])

  const [dismissed, setDismissed] = useState<string | null>(null)
  useEffect(() => setDismissed(null), [hint?.id])

  if (!hint || seen.includes(hint.id) || dismissed === hint.id) return null

  return (
    <div className="hint-bubble" role="status">
      <span className="hint-icon" aria-hidden>
        💡
      </span>
      <span className="hint-text">{hint.text}</span>
      <button
        onClick={() => {
          markHint(hint.id)
          setDismissed(hint.id)
        }}
      >
        Got it
      </button>
    </div>
  )
}
