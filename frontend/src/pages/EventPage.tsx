import { type FormEvent, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../api'
import { errorMessage, formatDateTime } from '../format'
import type { EventRecord, Registration } from '../types'

export function EventPage() {
  const { eventId = '' } = useParams()
  const [event, setEvent] = useState<EventRecord | null>(null)
  const [registration, setRegistration] = useState<Registration | null>(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [cancelledFrom, setCancelledFrom] = useState<'CONFIRMED' | 'WAITLISTED' | null>(null)

  useEffect(() => {
    api.getEvent(eventId).then(setEvent).catch((caught) => setError(errorMessage(caught)))
  }, [eventId])

  async function submit(submitEvent: FormEvent<HTMLFormElement>) {
    submitEvent.preventDefault()
    const form = new FormData(submitEvent.currentTarget)
    setSubmitting(true)
    setError('')
    try {
      setRegistration(await api.register(eventId, String(form.get('email'))))
      setCancelledFrom(null)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setSubmitting(false)
    }
  }

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

  if (!event && !error) return <p className="loading" role="status">Loading event…</p>

  return (
    <section className="panel panel--wide" aria-labelledby="event-heading">
      {event && <>
        <p className="eyebrow">Registration open</p>
        <h1 id="event-heading">{event.title}</h1>
        <p className="event-time">{formatDateTime(event.starts_at)}</p>
        {event.description && <p className="lede">{event.description}</p>}
        {registration?.status === 'CANCELLED' && <div className="result-card result-card--warning" role="status">
          <p className="eyebrow">Cancelled</p>
          <h2>Your participation is cancelled</h2>
          {cancelledFrom === 'CONFIRMED' && <p>Your previous ticket is no longer active.</p>}
          {cancelledFrom === 'WAITLISTED' && <p>You are no longer on the waiting list.</p>}
          {!cancelledFrom && <p>You are no longer participating in this event.</p>}
        </div>}
        {(!registration || registration.status === 'CANCELLED') && <form className="form-grid compact-form" onSubmit={submit}>
          <label>
            Email address
            <input
              name="email"
              type="email"
              required
              autoComplete="email"
              defaultValue={registration?.email ?? ''}
            />
          </label>
          <button className="button" disabled={submitting}>
            {submitting ? 'Registering…' : registration ? 'Register again' : 'Register'}
          </button>
        </form>}
        {registration?.status === 'CONFIRMED' && <div className="result-card result-card--success" role="status">
          <p className="eyebrow">Confirmed</p>
          <h2>Your place is secured</h2>
          {registration.ticket && <>
            <p>Your ticket code</p>
            <strong className="ticket-code">{registration.ticket.code}</strong>
            <Link className="text-link" to={`/tickets/${registration.ticket.code}`}>View ticket</Link>
          </>}
          <button className="button button--danger" disabled={cancelling} onClick={cancelParticipation}>
            {cancelling ? 'Cancelling…' : 'Cancel participation'}
          </button>
        </div>}
        {registration?.status === 'WAITLISTED' && <div className="result-card" role="status">
          <p className="eyebrow">Waiting list</p>
          <h2>You’re on the waiting list</h2>
          <p>We’ll email you if a place becomes available.</p>
          <button className="button button--danger" disabled={cancelling} onClick={cancelParticipation}>
            {cancelling ? 'Cancelling…' : 'Cancel participation'}
          </button>
        </div>}
      </>}
      {error && <p className="notice notice--error" role="alert">{error}</p>}
    </section>
  )
}
