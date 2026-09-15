import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../api'
import { RegistrationStatus } from '../components/RegistrationStatus'
import { errorMessage, formatDateTime } from '../format'
import type { EventRecord, Registration } from '../types'

export function RegistrationPage() {
  const { eventId = '', registrationId = '' } = useParams()
  const [event, setEvent] = useState<EventRecord | null>(null)
  const [registration, setRegistration] = useState<Registration | null>(null)
  const [error, setError] = useState('')
  const [cancelling, setCancelling] = useState(false)
  const [cancelledFrom, setCancelledFrom] = useState<'CONFIRMED' | 'WAITLISTED' | null>(null)

  useEffect(() => {
    api.getEvent(eventId).then(setEvent).catch((caught) => setError(errorMessage(caught)))
    api
      .getRegistration(eventId, registrationId)
      .then(setRegistration)
      .catch((caught) => setError(errorMessage(caught)))
  }, [eventId, registrationId])

  async function cancelParticipation() {
    if (!registration || registration.status === 'CANCELLED' || cancelling) return
    if (!window.confirm('Cancel your participation in this event?')) return

    const previousStatus = registration.status
    setCancelling(true)
    setError('')
    try {
      const result = await api.cancelRegistration(eventId, registration.id)
      setRegistration(result.registration)
      setCancelledFrom(previousStatus)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setCancelling(false)
    }
  }

  if (!registration && !error) return <p className="loading" role="status">Loading registration…</p>

  return (
    <section className="panel panel--wide" aria-labelledby="registration-heading">
      <p className="eyebrow">Your registration</p>
      <h1 id="registration-heading">{event?.title ?? 'Registration'}</h1>
      {event && <p className="event-time">{formatDateTime(event.starts_at)}</p>}
      {registration && <p className="status-card__description">Registered as {registration.email}</p>}
      {registration && (
        <RegistrationStatus
          registration={registration}
          cancelledFrom={cancelledFrom}
          cancelling={cancelling}
          onCancel={cancelParticipation}
        />
      )}
      {registration?.status === 'CANCELLED' && (
        <p className="status-card__description">
          Changed your mind? <Link className="text-link" to={`/events/${eventId}`}>Register again</Link>.
        </p>
      )}
      {error && <p className="notice notice--error" role="alert">{error}</p>}
    </section>
  )
}
