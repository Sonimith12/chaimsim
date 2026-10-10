import { useThree } from '@react-three/fiber'
import { useEffect } from 'react'
import { useEditStore } from '../store/editStore'

/** Camera-side behaviour of edit mode: pause orbiting while dragging, release on pointer-up, cursors. */
export function EditInteractions() {
  const controls = useThree((s) => s.controls) as unknown as { enabled: boolean } | null
  const dom = useThree((s) => s.gl.domElement)
  const dragId = useEditStore((s) => s.dragId)
  const placing = useEditStore((s) => s.placing)
  const connecting = useEditStore((s) => s.connectMode || s.shiftDown)

  useEffect(() => {
    if (controls) controls.enabled = dragId === null
    if (dragId === null) return
    const release = () => useEditStore.getState().endDrag()
    window.addEventListener('pointerup', release)
    window.addEventListener('pointercancel', release)
    return () => {
      window.removeEventListener('pointerup', release)
      window.removeEventListener('pointercancel', release)
      if (controls) controls.enabled = true
    }
  }, [dragId, controls])

  useEffect(() => {
    dom.style.cursor = dragId ? 'grabbing' : placing || connecting ? 'crosshair' : ''
    return () => {
      dom.style.cursor = ''
    }
  }, [dom, dragId, placing, connecting])

  return null
}
