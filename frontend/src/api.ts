import type {
  CancellationResponse,
  CheckInResponse,
  EventRecord,
  EventStats,
  EventSummary,
  Registration,
  TicketDetails,
} from './types'

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(
  /\/$/,
  '',
)

export class ApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

/** The API is protected by an organizer key and this request did not carry a valid one. */
export class UnauthorizedError extends ApiError {
  constructor(message: string) {
    super(message)
    this.name = 'UnauthorizedError'
  }
}

const ORGANIZER_KEY_STORAGE = 'organizerKey'

export function getOrganizerKey(): string | null {
  try {
    return localStorage.getItem(ORGANIZER_KEY_STORAGE)
  } catch {
    return null
  }
}

export function setOrganizerKey(key: string): void {
  try {
    localStorage.setItem(ORGANIZER_KEY_STORAGE, key)
  } catch {
    // Storage unavailable (private mode, blocked): the key simply has to be re-entered.
  }
}

export function clearOrganizerKey(): void {
  try {
    localStorage.removeItem(ORGANIZER_KEY_STORAGE)
  } catch {
    // ignore
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const organizerKey = getOrganizerKey()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(organizerKey ? { 'X-Organizer-Key': organizerKey } : {}),
      ...options?.headers,
    },
  })
  if (response.status === 401) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new UnauthorizedError(body?.detail || 'This action requires the organizer key')
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string | Array<{ msg?: string }> }
      | null
    const detail = body?.detail
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).filter(Boolean).join(', ')
      : detail
    throw new ApiError(message || `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const api = {
  createEvent: (data: {
    title: string
    description: string
    starts_at: string
    capacity: number
  }) => request<EventRecord>('/api/events', { method: 'POST', body: JSON.stringify(data) }),
  listEvents: (includePast = false) =>
    request<EventSummary[]>(`/api/events${includePast ? '?include_past=true' : ''}`),
  getEvent: (eventId: string) => request<EventRecord>(`/api/events/${eventId}`),
  rescheduleEvent: (eventId: string, startsAt: string) =>
    request<EventRecord>(`/api/events/${eventId}`, {
      method: 'PATCH',
      body: JSON.stringify({ starts_at: startsAt }),
    }),
  register: (eventId: string, email: string) =>
    request<Registration>(`/api/events/${eventId}/registrations`, {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),
  getRegistration: (eventId: string, registrationId: string) =>
    request<Registration>(`/api/events/${eventId}/registrations/${registrationId}`),
  cancelRegistration: (eventId: string, registrationId: string) =>
    request<CancellationResponse>(
      `/api/events/${eventId}/registrations/${registrationId}/cancel`,
      { method: 'POST' },
    ),
  getTicket: (code: string) => request<TicketDetails>(`/api/tickets/${encodeURIComponent(code)}`),
  checkIn: (code: string) =>
    request<CheckInResponse>('/api/check-ins', {
      method: 'POST',
      body: JSON.stringify({ code }),
    }),
  getStats: (eventId: string) => request<EventStats>(`/api/events/${eventId}/stats`),
}

export function statsStreamUrl(eventId: string): string {
  // EventSource cannot send headers, so the stream takes the key as a query parameter.
  const organizerKey = getOrganizerKey()
  const query = organizerKey ? `?organizer_key=${encodeURIComponent(organizerKey)}` : ''
  return `${API_BASE_URL}/api/events/${eventId}/stats/stream${query}`
}
