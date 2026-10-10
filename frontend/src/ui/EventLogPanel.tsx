import { useGameStore } from '../store/gameStore'
import { useSimStore } from '../store/simStore'

const money = (n: number) => `${n < 0 ? '-' : n > 0 ? '+' : ''}$${Math.abs(Math.round(n)).toLocaleString()}`

export function EventLogPanel() {
  const open = useGameStore((s) => s.eventLogOpen)
  const setOpen = useGameStore((s) => s.setEventLogOpen)
  const log = useSimStore((s) => s.eventLog)

  return (
    <aside className={`history${open ? ' open' : ''}`} aria-hidden={!open}>
      <div className="inspector-head">
        <h2>Event log</h2>
        <button className="icon-btn" onClick={() => setOpen(false)} aria-label="Close event log">
          ×
        </button>
      </div>
      {log.length === 0 ? (
        <p className="muted">No events yet. Surprises will land as the run goes on.</p>
      ) : (
        <ul className="event-log">
          {[...log].reverse().map((e) => (
            <li key={e.uid}>
              <div className="event-log-head">
                <span>
                  {e.icon} {e.title}
                </span>
                <span className="muted">Period {e.period}</span>
              </div>
              <div className="event-log-choice">
                {e.auto ? 'Time ran out → ' : 'You chose: '}
                <strong>{e.choice}</strong>
              </div>
              <div className="muted">{e.outcome}</div>
              <div className={e.cash_delta < 0 ? 'neg' : e.cash_delta > 0 ? 'pos' : 'muted'}>
                {e.cash_delta === 0 ? 'No immediate cash impact' : `${money(e.cash_delta)} cash`}
              </div>
            </li>
          ))}
        </ul>
      )}
    </aside>
  )
}
