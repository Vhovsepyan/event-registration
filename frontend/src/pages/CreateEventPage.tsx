import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../api'
import { errorMessage } from '../format'

export function CreateEventPage() {
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setSubmitting(true)
    setError('')
    try {
      const created = await api.createEvent({
        title: String(form.get('title')),
        description: String(form.get('description')),
        starts_at: new Date(String(form.get('starts_at'))).toISOString(),
        capacity: Number(form.get('capacity')),
      })
      navigate(`/events/${created.id}/organizer`)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="panel panel--wide" aria-labelledby="create-heading">
      <p className="eyebrow">Organizer</p>
      <h1 id="create-heading">Create an event</h1>
      <p className="lede">Set the details, then share the participant link from your dashboard.</p>
      <form className="form-grid" onSubmit={submit}>
        <label>
          Event title
          <input name="title" required maxLength={200} autoComplete="off" />
        </label>
        <label>
          Description
          <textarea name="description" rows={4} maxLength={10000} />
        </label>
        <div className="form-row">
          <label>
            Date and time
            <input name="starts_at" type="datetime-local" required />
          </label>
          <label>
            Capacity
            <input name="capacity" type="number" min="1" required />
          </label>
        </div>
        {error && <p className="notice notice--error" role="alert">{error}</p>}
        <button className="button" disabled={submitting}>{submitting ? 'Creating…' : 'Create event'}</button>
      </form>
    </section>
  )
}
