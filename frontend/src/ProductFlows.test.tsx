import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import type { EventRecord, EventStats } from './types'

const EVENT: EventRecord = {
  id: 'event-1',
  title: 'Autumn Gathering',
  description: 'A small community event.',
  starts_at: '2030-10-12T14:00:00Z',
  capacity: 20,
  created_at: '2030-01-01T00:00:00Z',
  updated_at: '2030-01-01T00:00:00Z',
}

const STATS: EventStats = {
  event_id: EVENT.id,
  capacity: 20,
  confirmed: 7,
  waitlisted: 2,
  checked_in: 3,
}

function response(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  })
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('product flows', () => {
  it('renders a confirmed registration and its ticket', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response(EVENT))
      .mockResolvedValueOnce(response({
        id: 'registration-1',
        event_id: EVENT.id,
        email: 'guest@example.com',
        status: 'CONFIRMED',
        waitlist_order: null,
        created_at: '2030-01-01T00:00:00Z',
        confirmed_at: '2030-01-01T00:00:00Z',
        cancelled_at: null,
        ticket: {
          id: 'ticket-1',
          registration_id: 'registration-1',
          code: 'ABCD-EFGH-IJKL',
          created_at: '2030-01-01T00:00:00Z',
          checked_in_at: null,
          invalidated_at: null,
        },
      }))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    renderAt('/events/event-1')
    await screen.findByRole('heading', { name: EVENT.title })
    await user.type(screen.getByLabelText('Email address'), 'guest@example.com')
    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(await screen.findByRole('heading', { name: 'Your place is secured' })).toBeVisible()
    expect(screen.getByText('ABCD-EFGH-IJKL')).toBeVisible()
    expect(screen.getByRole('link', { name: 'View ticket' })).toHaveAttribute(
      'href',
      '/tickets/ABCD-EFGH-IJKL',
    )
  })

  it.each([
    ['SUCCESS', 'Check-in successful'],
    ['ALREADY_CHECKED_IN', 'Already checked in'],
    ['INVALID_TICKET', 'Invalid ticket'],
  ] as const)('renders the %s check-in result', async (result, heading) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ result, checked_in_at: null })))
    const user = userEvent.setup()

    renderAt('/check-in')
    await user.type(screen.getByLabelText('Ticket code'), 'ABCD-EFGH-IJKL')
    await user.click(screen.getByRole('button', { name: 'Check in' }))

    expect(await screen.findByRole('heading', { name: heading })).toBeVisible()
  })

  it('renders initial statistics and applies a live SSE snapshot', async () => {
    let statsListener: ((event: MessageEvent<string>) => void) | undefined
    class MockEventSource {
      onerror: (() => void) | null = null
      addEventListener(type: string, listener: EventListener) {
        if (type === 'stats') statsListener = listener as (event: MessageEvent<string>) => void
      }
      close() {}
    }
    vi.stubGlobal('EventSource', MockEventSource)
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) =>
        Promise.resolve(response(url.endsWith('/stats') ? STATS : EVENT)),
      ),
    )

    renderAt('/events/event-1/organizer')
    const stats = await screen.findByLabelText('Event statistics')
    expect(within(stats).getByText('7')).toBeVisible()
    expect(within(stats).getByText('3')).toBeVisible()

    act(() => {
      statsListener?.(
        new MessageEvent('stats', { data: JSON.stringify({ ...STATS, checked_in: 4 }) }),
      )
    })

    await waitFor(() => expect(within(stats).getByText('4')).toBeVisible())
    expect(screen.getByText('Live')).toBeVisible()
  })
})
