import { useEffect } from 'react'
import { nodeBuildCost, useEditStore } from '../store/editStore'
import type { EditableNodeType } from '../types/sim'

const ADD_BUTTONS: { type: EditableNodeType; label: string }[] = [
  { type: 'Supplier', label: '+ Supplier' },
  { type: 'DistributionCenter', label: '+ DC' },
  { type: 'Retailer', label: '+ Retailer' },
]

const isTyping = (t: EventTarget | null) =>
  t instanceof HTMLElement && ['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName)

export function EditToolbar() {
  const placing = useEditStore((s) => s.placing)
  const connectMode = useEditStore((s) => s.connectMode)
  const shiftDown = useEditStore((s) => s.shiftDown)
  const connectFrom = useEditStore((s) => s.connectFrom)
  const sourceName = useEditStore((s) => s.spec?.nodes.find((n) => n.id === connectFrom)?.name)
  const spec = useEditStore((s) => s.spec)
  const setPlacing = useEditStore((s) => s.setPlacing)
  const setConnectMode = useEditStore((s) => s.setConnectMode)

  // Holding Shift also connects; Escape cancels whatever tool is active.
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (isTyping(e.target)) return
      if (e.key === 'Shift') useEditStore.getState().setShift(true)
      if (e.key === 'Escape') {
        const s = useEditStore.getState()
        s.setPlacing(null)
        s.setConnectMode(false)
        s.setConnectFrom(null)
        s.setEditingEdge(null)
      }
    }
    const up = (e: KeyboardEvent) => {
      if (e.key === 'Shift') useEditStore.getState().setShift(false)
    }
    const blur = () => useEditStore.getState().setShift(false)
    window.addEventListener('keydown', down)
    window.addEventListener('keyup', up)
    window.addEventListener('blur', blur)
    return () => {
      window.removeEventListener('keydown', down)
      window.removeEventListener('keyup', up)
      window.removeEventListener('blur', blur)
    }
  }, [])

  const connecting = connectMode || shiftDown
  let hint = 'Drag nodes to move · right-click to delete'
  if (placing) hint = 'Click the ground to place it (Esc cancels)'
  else if (connecting) hint = connectFrom ? `Click the target for ${sourceName ?? 'the source'}` : 'Click the source node'

  return (
    <div className="edit-toolbar">
      {ADD_BUTTONS.map((b) => (
        <button
          key={b.type}
          className={placing === b.type ? 'active' : ''}
          onClick={() => setPlacing(placing === b.type ? null : b.type)}
        >
          {b.label}
          {spec && <span className="price">${nodeBuildCost(spec, b.type).toLocaleString()}</span>}
        </button>
      ))}
      <button className={connecting ? 'active' : ''} onClick={() => setConnectMode(!connectMode)}>
        ⤳ Connect
      </button>
      <div className="edit-hint">{hint}</div>
      <div className="edit-hint">
        Connections cost ${(spec?.economy.build_cost_per_lead_time ?? 0).toLocaleString()} per unit of lead time
      </div>
      <div className="edit-hint">Hold Shift to connect quickly</div>
    </div>
  )
}
