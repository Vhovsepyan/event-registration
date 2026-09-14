import { type FormEvent, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api, statsStreamUrl } from '../api'
import { errorMessage, formatDateTime } from '../format'
import type { EventRecord, EventStats } from '../types'

export function OrganizerPage() {
  const { eventId = '' } = useParams()
  const [event, setEvent] = useState<EventRecord | null>(null)
  const [stats, setStats] = useState<EventStats | null>(null)
  const [error, setError] = useState('')
  const [live, setLive] = useState(false)
  const [rescheduling, setRescheduling] = useState(false)

  useEffect(() => {
    let active = true
    Promise.all([api.getEvent(eventId), api.getStats(eventId)])
      .then(([eventData, statsData]) => {
        if (active) {
          setEvent(eventData)
          setStats(statsData)
        }
      })
      .catch((caught) => active && setError(errorMessage(caught)))

    const stream = new EventSource(statsStreamUrl(eventId))
    const update = (message: MessageEvent<string>) => {
      if (active) {
        setStats(JSON.parse(message.data) as EventStats)
        setLive(true)
      }
    }
    stream.addEventListener('stats', update as EventListener)
    stream.onerror = () => active && setLive(false)
    return () => {
      active = false
      stream.close()
    }
  }, [eventId])

  async function reschedule(submitEvent: FormEvent<HTMLFormElement>) {
    submitEvent.preventDefault()
    const formElement = submitEvent.currentTarget
    const form = new FormData(formElement)
    setRescheduling(true)
    setError('')
    try {
      setEvent(
        await api.rescheduleEvent(
          eventId,
          new Date(String(form.get('starts_at'))).toISOString(),
        ),
      )
      formElement.reset()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setRescheduling(false)
    }
  }

  return (
    <section className="panel panel--wide dashboard" aria-labelledby="dashboard-heading">
      <div className="dashboard__heading">
        <div>
          <p className="eyebrow">Organizer dashboard</p>
          <h1 id="dashboard-heading">{event?.title ?? 'Event overview'}</h1>
          {event && <p className="event-time">{formatDateTime(event.starts_at)}</p>}
        </div>
        <span className={`live-indicator ${live ? 'live-indicator--connected' : ''}`}>
          <span aria-hidden="true" /> {live ? 'Live' : 'Connecting'}
        </span>
      </div>
      {stats ? <div className="stat-grid" aria-label="Event statistics">
        <article aria-label={`Capacity: ${stats.capacity}`}><strong>{stats.capacity}</strong><span>Capacity</span></article>
        <article aria-label={`Confirmed: ${stats.confirmed}`}><strong>{stats.confirmed}</strong><span>Confirmed</span></article>
        <article aria-label={`Waiting list: ${stats.waitlisted}`}><strong>{stats.waitlisted}</strong><span>Waiting list</span></article>
        <article aria-label={`Checked in: ${stats.checked_in}`}><strong>{stats.checked_in}</strong><span>Checked in</span></article>
      </div> : !error && <p className="loading" role="status">Loading statistics…</p>}
      <div className="dashboard__links">
        <Link className="button button--secondary" to={`/events/${eventId}`}>Participant page</Link>
        <Link className="button button--secondary" to="/check-in">Open check-in</Link>
      </div>
      <form className="form-grid reschedule-form" onSubmit={reschedule}>
        <h2>Reschedule event</h2>
        <label>
          New date and time
          <input name="starts_at" type="datetime-local" required />
        </label>
        <button className="button" disabled={rescheduling}>
          {rescheduling ? 'Updating…' : 'Update schedule'}
        </button>
      </form>
      {error && <p className="notice notice--error" role="alert">{error}</p>}
    </section>
  )
}
