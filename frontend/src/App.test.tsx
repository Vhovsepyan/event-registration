import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'

import App from './App'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

describe('application routing', () => {
  it('renders the frontend foundation at the root route', () => {
    renderAt('/')

    expect(screen.getByRole('heading', { name: 'Ready for event registration' })).toBeVisible()
  })

  it('renders a not-found page for unknown routes', () => {
    renderAt('/missing')

    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Return home' })).toHaveAttribute('href', '/')
  })
})
