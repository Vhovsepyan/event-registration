import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'

afterEach(cleanup)

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

describe('application routing', () => {
  it('renders the participant event list at the root route', () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('[]', { status: 200 })))
    renderAt('/')

    expect(screen.getByRole('heading', { name: 'Upcoming events' })).toBeVisible()
  })

  it('renders event creation in the organizer area', () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('[]', { status: 200 })))
    renderAt('/organizer')

    expect(screen.getByRole('heading', { name: 'Create an event' })).toBeVisible()
  })

  it('renders a not-found page for unknown routes', () => {
    renderAt('/missing')

    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Return home' })).toHaveAttribute('href', '/')
  })
})
