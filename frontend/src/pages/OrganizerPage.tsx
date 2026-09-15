import { type FormEvent, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api, statsStreamUrl } from '../api'
import { OrganizerKeyPrompt } from '../components/OrganizerKeyPrompt'
import { useOrganizerKeyGate } from '../hooks/useOrganizerKeyGate'
import { errorMessage, formatDateTime } from '../format'
import type { EventRecord, EventStats } from '../types'

export function OrganizerPage() {
  const { eventId = '' } = useParams()
  const [event, setEvent] = useState<EventRecord | null>(null)
  const [stats, setStats] = useState<EventStats | null>(null)
  const [error, setError] = useState('')
  const [live, setLive] = useState(false)
  const [rescheduling, setRescheduling] = useState(false)
  const { needsKey, version: keyVersion, guard, saved } = useOrganizerKeyGate()

  useEffect(() => {
    let active = true
    // The stream only emits changes relative to what it already sent, so a live snapshot must
    // never be replaced by the initial HTTP response if that response happens to resolve later.
    let liveSnapshotApplied = false
    // Each request stands on its own: a failed statistics call must not hide the event
    // details that loaded, and vice versa.
    api
      .getEvent(eventId)
      .then((eventData) => active && setEvent(eventData))
      .catch((caught) => active && setError(errorMessage(caught)))
    api
      .getStats(eventId)
      .then((statsData) => active && !liveSnapshotApplied && setStats(statsData))
      .catch((caught) => active && !guard(caught) && setError(errorMessage(caught)))

    const stream = new EventSource(statsStreamUrl(eventId))
    const update = (message: MessageEvent<string>) => {
      if (active) {
        liveSnapshotApplied = true
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
  }, [eventId, keyVersion, guard])

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
      if (!guard(caught)) setError(errorMessage(caught))
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
      {needsKey && <OrganizerKeyPrompt onSaved={saved} />}
      {stats ? <div className="stat-grid" aria-label="Event statistics">
        <article aria-label={`Capacity: ${stats.capacity}`}><strong>{stats.capacity}</strong><span>Capacity</span></article>
        <article aria-label={`Confirmed: ${stats.confirmed}`}><strong>{stats.confirmed}</strong><span>Confirmed</span></article>
        <article aria-label={`Waiting list: ${stats.waitlisted}`}><strong>{stats.waitlisted}</strong><span>Waiting list</span></article>
        <article aria-label={`Checked in: ${stats.checked_in}`}><strong>{stats.checked_in}</strong><span>Checked in</span></article>
      </div> : !error && !needsKey && <p className="loading" role="status">Loading statistics…</p>}
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
