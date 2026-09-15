import { Link } from 'react-router-dom'

import type { Registration } from '../types'

type Props = {
  registration: Registration
  cancelledFrom: 'CONFIRMED' | 'WAITLISTED' | null
  cancelling: boolean
  onCancel: () => void
  /** Shown on the event page right after registering; the self-service page is that link. */
  manageLink?: boolean
}

export function RegistrationStatus({
  registration,
  cancelledFrom,
  cancelling,
  onCancel,
  manageLink = false,
}: Props) {
  const manageUrl = `/events/${registration.event_id}/registrations/${registration.id}`
  const manage = manageLink && (
    <p className="status-card__description">
      Bookmark <Link className="text-link" to={manageUrl}>your registration page</Link> to view
      or cancel later. The same link is in your email.
    </p>
  )

  if (registration.status === 'CANCELLED') {
    return (
      <div className="result-card result-card--warning" role="status">
        <p className="eyebrow">Cancelled</p>
        <h2>Your participation is cancelled</h2>
        {cancelledFrom === 'CONFIRMED' && <p>Your previous ticket is no longer active.</p>}
        {cancelledFrom === 'WAITLISTED' && <p>You are no longer on the waiting list.</p>}
        {!cancelledFrom && <p>You are no longer participating in this event.</p>}
      </div>
    )
  }

  if (registration.status === 'CONFIRMED') {
    return (
      <div className="result-card result-card--success" role="status">
        <p className="eyebrow">Confirmed</p>
        <h2>Your place is secured</h2>
        {registration.ticket && <>
          <p>Your ticket code</p>
          <strong className="ticket-code">{registration.ticket.code}</strong>
          <Link className="text-link" to={`/tickets/${registration.ticket.code}`}>View ticket</Link>
        </>}
        <button className="button button--danger" disabled={cancelling} onClick={onCancel}>
          {cancelling ? 'Cancelling…' : 'Cancel participation'}
        </button>
        {manage}
      </div>
    )
  }

  return (
    <div className="result-card" role="status">
      <p className="eyebrow">Waiting list</p>
      <h2>You’re on the waiting list</h2>
      <p>We’ll email you if a place becomes available.</p>
      <button className="button button--danger" disabled={cancelling} onClick={onCancel}>
        {cancelling ? 'Cancelling…' : 'Cancel participation'}
      </button>
      {manage}
    </div>
  )
}
