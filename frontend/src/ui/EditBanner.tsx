import { tryStart } from '../hooks/useEditor'
import { backToSetup } from '../hooks/useSimulation'
import { MAX_NODES, remainingBudget, useEditStore } from '../store/editStore'
import { useGameStore } from '../store/gameStore'

export function EditBanner() {
  const spec = useEditStore((s) => s.spec)
  const mode = useGameStore((s) => s.mode)
  if (!spec) return null
  const remaining = remainingBudget(spec)

  return (
    <header className="edit-banner">
      <span className="edit-badge">Edit Mode</span>
      <span className="edit-title">— {spec.name}</span>
      <span className="muted edit-count">
        {spec.nodes.length}/{MAX_NODES} nodes · {spec.edges.length} connections
      </span>
      <span
        className={`budget-chip ${
          remaining < 0
            ? 'bad'
            : remaining < spec.economy.starting_capital * 0.25
              ? 'low'
              : 'ok'
        }`}
        title="Whatever you don't spend building becomes your operating cash"
      >
        Build Budget: ${Math.round(remaining).toLocaleString()} remaining
      </span>
      <div className="hud-spacer" />
      <button onClick={backToSetup}>{mode === 'campaign' ? '← Levels' : '← Scenarios'}</button>
      <button className="start-btn" onClick={tryStart}>
        Start Simulation ▶
      </button>
    </header>
  )
}
