import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../api'
import { EventList } from '../components/EventList'
import { errorMessage } from '../format'
import type { EventSummary } from '../types'

export function EventsPage() {
  const [events, setEvents] = useState<EventSummary[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.listEvents().then(setEvents).catch((caught) => setError(errorMessage(caught)))
  }, [])

  return (
    <section className="panel panel--wide" aria-labelledby="events-heading">
      <p className="eyebrow">Participants</p>
      <h1 id="events-heading">Upcoming events</h1>
      <p className="lede">
        Pick an event and register with your email. When an event is full you join the waiting
        list and are moved up automatically as seats free up.
      </p>
      {events ? (
        <EventList
          events={events}
          audience="participant"
          emptyMessage="No upcoming events yet. Organizers can create one from the organizer area."
        />
      ) : !error && <p className="loading" role="status">Loading events…</p>}
      {error && <p className="notice notice--error" role="alert">{error}</p>}
      <p className="status-card__description">
        Organizing an event? <Link className="text-link" to="/organizer">Open the organizer area</Link>.
      </p>
    </section>
  )
}
