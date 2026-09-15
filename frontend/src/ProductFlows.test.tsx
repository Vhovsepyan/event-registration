import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import type { EventRecord, EventStats, EventSummary, Registration } from './types'

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

const CONFIRMED_REGISTRATION: Registration = {
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
}

const WAITLISTED_REGISTRATION: Registration = {
  ...CONFIRMED_REGISTRATION,
  id: 'registration-2',
  email: 'waiting@example.com',
  status: 'WAITLISTED',
  waitlist_order: 1,
  confirmed_at: null,
  ticket: null,
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
      .mockResolvedValueOnce(response(CONFIRMED_REGISTRATION))
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

  it('confirms cancellation, prevents repeat requests, and removes the active ticket', async () => {
    let finishCancellation: ((value: Response) => void) | undefined
    const cancellation = new Promise<Response>((resolve) => {
      finishCancellation = resolve
    })
    const cancelled = {
      ...CONFIRMED_REGISTRATION,
      status: 'CANCELLED' as const,
      cancelled_at: '2030-01-02T00:00:00Z',
      ticket: { ...CONFIRMED_REGISTRATION.ticket!, invalidated_at: '2030-01-02T00:00:00Z' },
    }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response(EVENT))
      .mockResolvedValueOnce(response(CONFIRMED_REGISTRATION))
      .mockReturnValueOnce(cancellation)
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()

    renderAt('/events/event-1')
    await screen.findByRole('heading', { name: EVENT.title })
    await user.type(screen.getByLabelText('Email address'), CONFIRMED_REGISTRATION.email)
    await user.click(screen.getByRole('button', { name: 'Register' }))
    const cancelButton = await screen.findByRole('button', { name: 'Cancel participation' })
    await user.click(cancelButton)

    expect(window.confirm).toHaveBeenCalledWith('Cancel your participation in this event?')
    expect(screen.getByRole('button', { name: 'Cancelling…' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Cancelling…' }))
    expect(fetchMock).toHaveBeenCalledTimes(3)
    finishCancellation?.(response({ registration: cancelled, promoted_registration: null }))

    expect(await screen.findByRole('heading', { name: 'Your participation is cancelled' })).toBeVisible()
    expect(screen.getByText('Your previous ticket is no longer active.')).toBeVisible()
    expect(screen.queryByText(CONFIRMED_REGISTRATION.ticket!.code)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'View ticket' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Register again' })).toBeVisible()
    expect(screen.getByLabelText('Email address')).toHaveValue(CONFIRMED_REGISTRATION.email)
    expect(fetchMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/api/events/event-1/registrations/registration-1/cancel'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('shows that a cancelled waitlisted participant is no longer waiting', async () => {
    const cancelled = {
      ...WAITLISTED_REGISTRATION,
      status: 'CANCELLED' as const,
      cancelled_at: '2030-01-02T00:00:00Z',
    }
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(response(EVENT))
        .mockResolvedValueOnce(response(WAITLISTED_REGISTRATION))
        .mockResolvedValueOnce(response({ registration: cancelled, promoted_registration: null })),
    )
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()

    renderAt('/events/event-1')
    await screen.findByRole('heading', { name: EVENT.title })
    await user.type(screen.getByLabelText('Email address'), WAITLISTED_REGISTRATION.email)
    await user.click(screen.getByRole('button', { name: 'Register' }))
    await user.click(await screen.findByRole('button', { name: 'Cancel participation' }))

    expect(await screen.findByText('You are no longer on the waiting list.')).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'You’re on the waiting list' })).not.toBeInTheDocument()
  })

  it('keeps active state and displays the API error when cancellation fails', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response(EVENT))
      .mockResolvedValueOnce(response(CONFIRMED_REGISTRATION))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'Cancellation unavailable' }), {
          status: 503,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()

    renderAt('/events/event-1')
    await screen.findByRole('heading', { name: EVENT.title })
    await user.type(screen.getByLabelText('Email address'), CONFIRMED_REGISTRATION.email)
    await user.click(screen.getByRole('button', { name: 'Register' }))
    await user.click(await screen.findByRole('button', { name: 'Cancel participation' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Cancellation unavailable')
    expect(screen.getByRole('heading', { name: 'Your place is secured' })).toBeVisible()
    expect(screen.getByText(CONFIRMED_REGISTRATION.ticket!.code)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Cancel participation' })).toBeEnabled()
  })

  it('does not send a cancellation request when confirmation is declined', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(response(EVENT))
      .mockResolvedValueOnce(response(WAITLISTED_REGISTRATION))
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const user = userEvent.setup()

    renderAt('/events/event-1')
    await screen.findByRole('heading', { name: EVENT.title })
    await user.type(screen.getByLabelText('Email address'), WAITLISTED_REGISTRATION.email)
    await user.click(screen.getByRole('button', { name: 'Register' }))
    await user.click(await screen.findByRole('button', { name: 'Cancel participation' }))

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(screen.getByRole('heading', { name: 'You’re on the waiting list' })).toBeVisible()
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

  it('does not let a late initial HTTP snapshot replace a newer SSE snapshot', async () => {
    let statsListener: ((event: MessageEvent<string>) => void) | undefined
    class MockEventSource {
      onerror: (() => void) | null = null
      addEventListener(type: string, listener: EventListener) {
        if (type === 'stats') statsListener = listener as (event: MessageEvent<string>) => void
      }
      close() {}
    }
    vi.stubGlobal('EventSource', MockEventSource)
    let resolveStats: (value: Response) => void = () => {}
    const delayedStats = new Promise<Response>((resolve) => {
      resolveStats = resolve
    })
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) =>
        url.endsWith('/stats') ? delayedStats : Promise.resolve(response(EVENT)),
      ),
    )

    renderAt('/events/event-1/organizer')
    await waitFor(() => expect(statsListener).toBeDefined())
    act(() => {
      statsListener?.(
        new MessageEvent('stats', { data: JSON.stringify({ ...STATS, checked_in: 4 }) }),
      )
    })
    const stats = await screen.findByLabelText('Event statistics')
    expect(within(stats).getByLabelText('Checked in: 4')).toBeVisible()

    // The stale HTTP snapshot (checked_in: 3) arrives only now, after the live value.
    await act(async () => {
      resolveStats(response(STATS))
    })

    expect(await screen.findByRole('heading', { name: EVENT.title })).toBeVisible()
    expect(within(stats).getByLabelText('Checked in: 4')).toBeVisible()
    expect(within(stats).queryByLabelText('Checked in: 3')).toBeNull()
  })

  it('lists upcoming events for participants with availability and registration links', async () => {
    const full: EventSummary = { ...EVENT, id: 'event-2', title: 'Sold out', confirmed: 20, waitlisted: 3, seats_left: 0 }
    const open: EventSummary = { ...EVENT, confirmed: 7, waitlisted: 0, seats_left: 13 }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response([open, full])))

    renderAt('/')

    const list = await screen.findByRole('list', { name: 'Upcoming events' })
    expect(within(list).getByText('13 of 20 seats left')).toBeVisible()
    expect(within(list).getByText('Full · 3 waiting')).toBeVisible()
    expect(within(list).getByRole('link', { name: 'Register' })).toHaveAttribute('href', '/events/event-1')
    expect(within(list).getByRole('link', { name: 'Join waiting list' })).toHaveAttribute('href', '/events/event-2')
  })

  it('shows an empty state when nothing is scheduled', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response([])))

    renderAt('/')

    expect(await screen.findByText(/No upcoming events yet/)).toBeVisible()
  })

  it('lists every event with counts and dashboard links in the organizer area', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response([{ ...EVENT, confirmed: 7, waitlisted: 2, seats_left: 13 }]))
    vi.stubGlobal('fetch', fetchMock)

    renderAt('/organizer')

    const list = await screen.findByRole('list', { name: 'Your events' })
    expect(within(list).getByText('7 confirmed · 2 waiting · capacity 20')).toBeVisible()
    expect(within(list).getByRole('link', { name: 'Open dashboard' })).toHaveAttribute('href', '/events/event-1/organizer')
    expect(String(fetchMock.mock.calls[0][0])).toContain('/api/events?include_past=true')
    expect(screen.getByRole('heading', { name: 'Create an event' })).toBeVisible()
  })

  it('lets a returning participant cancel from the self-service page', async () => {
    const cancelled = {
      ...CONFIRMED_REGISTRATION,
      status: 'CANCELLED' as const,
      cancelled_at: '2030-01-02T00:00:00Z',
      ticket: { ...CONFIRMED_REGISTRATION.ticket!, invalidated_at: '2030-01-02T00:00:00Z' },
    }
    const fetchMock = vi.fn((url: string) => {
      if (url.endsWith('/cancel')) return Promise.resolve(response({ registration: cancelled, promoted_registration: null }))
      if (url.endsWith('/registrations/registration-1')) return Promise.resolve(response(CONFIRMED_REGISTRATION))
      return Promise.resolve(response(EVENT))
    })
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()

    renderAt('/events/event-1/registrations/registration-1')

    expect(await screen.findByRole('heading', { name: EVENT.title })).toBeVisible()
    expect(screen.getByText('Registered as guest@example.com')).toBeVisible()
    expect(screen.getByText('ABCD-EFGH-IJKL')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Cancel participation' }))

    expect(await screen.findByRole('heading', { name: 'Your participation is cancelled' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Register again' })).toHaveAttribute('href', '/events/event-1')
    expect(fetchMock).toHaveBeenLastCalledWith(
      expect.stringContaining('/api/events/event-1/registrations/registration-1/cancel'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('shows a waitlisted registration and reports an unknown one', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) =>
        Promise.resolve(
          url.endsWith('/registrations/registration-2')
            ? response(WAITLISTED_REGISTRATION)
            : url.endsWith('/registrations/missing')
              ? new Response(JSON.stringify({ detail: "Registration 'missing' was not found" }), { status: 404 })
              : response(EVENT),
        ),
      ),
    )

    renderAt('/events/event-1/registrations/registration-2')
    expect(await screen.findByRole('heading', { name: 'You’re on the waiting list' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Cancel participation' })).toBeEnabled()
    cleanup()

    renderAt('/events/event-1/registrations/missing')
    expect(await screen.findByRole('alert')).toHaveTextContent("Registration 'missing' was not found")
  })

  it('links a fresh registration to its self-service page', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(response(EVENT)).mockResolvedValueOnce(response(CONFIRMED_REGISTRATION)),
    )
    const user = userEvent.setup()

    renderAt('/events/event-1')
    await screen.findByRole('heading', { name: EVENT.title })
    expect(screen.getByText(/Already registered\?/)).toBeVisible()
    await user.type(screen.getByLabelText('Email address'), 'guest@example.com')
    await user.click(screen.getByRole('button', { name: 'Register' }))

    expect(await screen.findByRole('link', { name: 'your registration page' })).toHaveAttribute(
      'href',
      '/events/event-1/registrations/registration-1',
    )
  })

  it.each([
    ['statistics', '/stats', EVENT.title, 'Event statistics'],
    ['event details', '/events/event-1', 'Checked in: 3', 'Event overview'],
  ] as const)(
    'still renders the other response when the %s request fails',
    async (_label, failingSuffix, visibleLabel, hiddenOrGeneric) => {
      class MockEventSource {
        onerror: (() => void) | null = null
        addEventListener() {}
        close() {}
      }
      vi.stubGlobal('EventSource', MockEventSource)
      vi.stubGlobal(
        'fetch',
        vi.fn((url: string) =>
          Promise.resolve(
            url.endsWith(failingSuffix)
              ? new Response(JSON.stringify({ detail: 'Service unavailable' }), { status: 503 })
              : response(url.endsWith('/stats') ? STATS : EVENT),
          ),
        ),
      )

      renderAt('/events/event-1/organizer')

      expect(await screen.findByRole('alert')).toHaveTextContent('Service unavailable')
      if (failingSuffix === '/stats') {
        expect(screen.getByRole('heading', { name: visibleLabel })).toBeVisible()
        expect(screen.queryByLabelText(hiddenOrGeneric)).toBeNull()
      } else {
        expect(screen.getByLabelText(visibleLabel)).toBeVisible()
        expect(screen.getByRole('heading', { name: hiddenOrGeneric })).toBeVisible()
      }
    },
  )
})
