import { type FormEvent, useState } from 'react'

import { api } from '../api'
import { OrganizerKeyPrompt } from '../components/OrganizerKeyPrompt'
import { useOrganizerKeyGate } from '../hooks/useOrganizerKeyGate'
import { errorMessage } from '../format'
import type { CheckInResponse } from '../types'

const RESULT_COPY: Record<CheckInResponse['result'], { heading: string; body: string; tone: string }> = {
  SUCCESS: {
    heading: 'Check-in successful',
    body: 'This ticket is now checked in.',
    tone: 'result-card--success',
  },
  ALREADY_CHECKED_IN: {
    heading: 'Already checked in',
    body: 'This ticket was used previously.',
    tone: 'result-card--warning',
  },
  INVALID_TICKET: {
    heading: 'Invalid ticket',
    body: 'Check the code and try again.',
    tone: 'result-card--error',
  },
}

export function CheckInPage() {
  const [result, setResult] = useState<CheckInResponse | null>(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const gate = useOrganizerKeyGate()

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setSubmitting(true)
    setResult(null)
    setError('')
    try {
      setResult(await api.checkIn(String(form.get('code'))))
    } catch (caught) {
      if (!gate.guard(caught)) setError(errorMessage(caught))
    } finally {
      setSubmitting(false)
    }
  }

  const copy = result ? RESULT_COPY[result.result] : null
  return (
    <section className="panel" aria-labelledby="check-in-heading">
      <p className="eyebrow">Event staff</p>
      <h1 id="check-in-heading">Check in a guest</h1>
      <p className="lede">Enter the ticket code exactly as shown on the attendee’s ticket.</p>
      {gate.needsKey && <OrganizerKeyPrompt onSaved={gate.saved} />}
      <form className="form-grid compact-form" onSubmit={submit}>
        <label>
          Ticket code
          <input className="code-input" name="code" required autoComplete="off" />
        </label>
        <button className="button" disabled={submitting}>{submitting ? 'Checking…' : 'Check in'}</button>
      </form>
      {copy && <div className={`result-card ${copy.tone}`} role="status">
        <h2>{copy.heading}</h2>
        <p>{copy.body}</p>
      </div>}
      {error && <p className="notice notice--error" role="alert">{error}</p>}
    </section>
  )
}
