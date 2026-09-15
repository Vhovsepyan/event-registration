import { type FormEvent, useState } from 'react'

import { clearOrganizerKey, getOrganizerKey, setOrganizerKey } from '../api'

type Props = {
  onSaved: () => void
}

export function OrganizerKeyPrompt({ onSaved }: Props) {
  const rejected = getOrganizerKey() !== null
  const [key, setKey] = useState('')

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = key.trim()
    if (!trimmed) return
    setOrganizerKey(trimmed)
    setKey('')
    onSaved()
  }

  return (
    <form className="form-grid compact-form" onSubmit={submit} aria-labelledby="organizer-key-heading">
      <h2 id="organizer-key-heading">Organizer key required</h2>
      <p className="status-card__description">
        {rejected
          ? 'The stored organizer key was rejected. Enter the current key to continue.'
          : 'This area is protected. Enter the organizer key to continue; it is remembered in this browser.'}
      </p>
      <label>
        Organizer key
        <input
          name="organizer_key"
          type="password"
          autoComplete="off"
          required
          value={key}
          onChange={(event) => setKey(event.target.value)}
        />
      </label>
      <div className="dashboard__links">
        <button className="button">Unlock</button>
        {rejected && (
          <button
            type="button"
            className="button button--secondary"
            onClick={() => {
              clearOrganizerKey()
              setKey('')
            }}
          >
            Forget stored key
          </button>
        )}
      </div>
    </form>
  )
}
