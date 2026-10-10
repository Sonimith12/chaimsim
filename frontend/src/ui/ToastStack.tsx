import { useGameStore } from '../store/gameStore'

export function ToastStack() {
  const toasts = useGameStore((s) => s.toasts)
  return (
    <div className="toast-stack" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.kind}`}>
          {t.text}
        </div>
      ))}
    </div>
  )
}
