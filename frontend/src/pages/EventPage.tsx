import { type FormEvent, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { api } from '../api'
import { RegistrationStatus } from '../components/RegistrationStatus'
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
        {registration?.status === 'CANCELLED' && (
          <RegistrationStatus
            registration={registration}
            cancelledFrom={cancelledFrom}
            cancelling={cancelling}
            onCancel={cancelParticipation}
          />
        )}
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
          <p className="status-card__description">
            Already registered? Enter the same email to open your registration, or use the link in
            your email.
          </p>
        </form>}
        {registration && registration.status !== 'CANCELLED' && (
          <RegistrationStatus
            registration={registration}
            cancelledFrom={cancelledFrom}
            cancelling={cancelling}
            onCancel={cancelParticipation}
            manageLink
          />
        )}
      </>}
      {error && <p className="notice notice--error" role="alert">{error}</p>}
    </section>
  )
}
