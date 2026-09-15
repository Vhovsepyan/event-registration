import { useState } from 'react'
import { Link } from 'react-router-dom'

import { formatDateTime } from '../format'
import type { EventSummary } from '../types'

type Props = {
  events: EventSummary[]
  audience: 'participant' | 'organizer'
  emptyMessage: string
}

function availability(event: EventSummary): string {
  if (event.seats_left > 0) {
    return `${event.seats_left} of ${event.capacity} seats left`
  }
  return event.waitlisted > 0
    ? `Full · ${event.waitlisted} waiting`
    : 'Full · joining adds you to the waiting list'
}

export function EventList({ events, audience, emptyMessage }: Props) {
  // Captured once per mount: "past" is a label, not something that must tick live.
  const [now] = useState(() => Date.now())
  if (events.length === 0) {
    return <p className="status-card__description">{emptyMessage}</p>
  }
  return (
    <ul className="event-list" aria-label={audience === 'participant' ? 'Upcoming events' : 'Your events'}>
      {events.map((event) => {
        const past = new Date(event.starts_at).getTime() <= now
        return (
          <li key={event.id} className="event-list__item">
            <div>
              <h3>{event.title}</h3>
              <p className="event-time">{formatDateTime(event.starts_at)}</p>
              <p className="event-list__meta">
                {audience === 'participant'
                  ? availability(event)
                  : `${event.confirmed} confirmed · ${event.waitlisted} waiting · capacity ${event.capacity}${past ? ' · past' : ''}`}
              </p>
            </div>
            {audience === 'participant' ? (
              <Link className="button" to={`/events/${event.id}`}>
                {event.seats_left > 0 ? 'Register' : 'Join waiting list'}
              </Link>
            ) : (
              <Link className="button button--secondary" to={`/events/${event.id}/organizer`}>
                Open dashboard
              </Link>
            )}
          </li>
        )
      })}
    </ul>
  )
}
