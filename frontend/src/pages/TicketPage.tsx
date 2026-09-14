import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { api } from '../api'
import { errorMessage, formatDateTime } from '../format'
import type { TicketDetails } from '../types'

export function TicketPage() {
  const { code = '' } = useParams()
  const [ticket, setTicket] = useState<TicketDetails | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getTicket(code).then(setTicket).catch((caught) => setError(errorMessage(caught)))
  }, [code])

  return (
    <section className="panel ticket" aria-labelledby="ticket-heading">
      <p className="eyebrow">Admission ticket</p>
      {ticket ? <>
        <h1 id="ticket-heading">{ticket.event.title}</h1>
        <p className="event-time">{formatDateTime(ticket.event.starts_at)}</p>
        <div className="ticket__code">
          <span>Ticket code</span>
          <strong className="ticket-code">{ticket.code}</strong>
        </div>
        <p className="status-line">
          Status: <strong>{ticket.invalidated_at ? 'Invalid' : ticket.checked_in_at ? 'Checked in' : 'Ready'}</strong>
        </p>
      </> : !error && <p className="loading" role="status">Loading ticket…</p>}
      {error && <p className="notice notice--error" role="alert">{error}</p>}
    </section>
  )
}
