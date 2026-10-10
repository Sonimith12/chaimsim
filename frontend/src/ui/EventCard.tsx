import { useEffect, useRef, useState } from 'react'
import { chooseEvent } from '../hooks/useSimulation'
import { useSimStore } from '../store/simStore'
import type { EventRisk } from '../types/sim'

const RISK_LABEL: Record<EventRisk, string> = {
  safe: 'Safe',
  risky: 'Risky',
  danger: 'Dangerous',
}

/**
 * Modal for a decision event. The run is already paused server-side; this blocks
 * the rest of the UI until a choice is made, and an optional countdown applies
 * the worst option if the player dithers.
 */
export function EventCard() {
  const event = useSimStore((s) => s.pendingEvent)
  const [remaining, setRemaining] = useState<number | null>(null)
  const answered = useRef(false)

  useEffect(() => {
    answered.current = false
    if (!event || event.timer === null) {
      setRemaining(null)
      return
    }
    const end = performance.now() + event.timer * 1000
    setRemaining(event.timer)
    const tick = setInterval(() => {
      const left = Math.max(0, (end - performance.now()) / 1000)
      setRemaining(left)
      if (left <= 0 && !answered.current) {
        answered.current = true
        chooseEvent(event.uid, event.default_choice, true)
      }
    }, 100)
    return () => clearInterval(tick)
  }, [event?.uid]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!event) return null

  const pick = (choiceId: string) => {
    if (answered.current) return
    answered.current = true
    chooseEvent(event.uid, choiceId, false)
  }

  const fraction = event.timer && remaining !== null ? remaining / event.timer : 1
  const worst = event.choices.find((c) => c.id === event.default_choice)

  return (
    <div className="event-dim" role="dialog" aria-modal="true" aria-label={event.title}>
      <div className={`event-card ${event.category}`}>
        <div className="event-head">
          <span className="event-icon" aria-hidden>
            {event.icon}
          </span>
          <div>
            <div className="event-kicker">
              Period {event.period} · {event.category}
            </div>
            <h2>{event.title}</h2>
          </div>
        </div>
        <p className="event-desc">{event.description}</p>

        {event.timer !== null && remaining !== null && (
          <div className="event-timer">
            <div className="event-timer-bar">
              <div
                className={fraction < 0.34 ? 'low' : ''}
                style={{ width: `${Math.max(0, fraction) * 100}%` }}
              />
            </div>
            <span>
              {Math.ceil(remaining)}s — otherwise “{worst?.label}” is chosen
            </span>
          </div>
        )}

        <div className="event-choices">
          {event.choices.map((c, i) => (
            <button key={c.id} className={`event-choice ${c.risk}`} onClick={() => pick(c.id)}>
              <span className="event-choice-top">
                <span className="event-choice-label">
                  {i + 1}. {c.label}
                </span>
                <span className={`risk-pill ${c.risk}`}>{RISK_LABEL[c.risk]}</span>
              </span>
              <span className="event-choice-desc">{c.description}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
