import { tryStart } from '../hooks/useEditor'
import { backToSetup } from '../hooks/useSimulation'
import { MAX_NODES, useEditStore } from '../store/editStore'

export function EditBanner() {
  const spec = useEditStore((s) => s.spec)
  if (!spec) return null

  return (
    <header className="edit-banner">
      <span className="edit-badge">Edit Mode</span>
      <span className="edit-title">— {spec.name}</span>
      <span className="muted edit-count">
        {spec.nodes.length}/{MAX_NODES} nodes · {spec.edges.length} connections
      </span>
      <div className="hud-spacer" />
      <button onClick={backToSetup}>← Scenarios</button>
      <button className="start-btn" onClick={tryStart}>
        Start Simulation ▶
      </button>
    </header>
  )
}
