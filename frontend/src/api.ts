import type {
  CheckInResponse,
  EventRecord,
  EventStats,
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

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
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
  getTicket: (code: string) => request<TicketDetails>(`/api/tickets/${encodeURIComponent(code)}`),
  checkIn: (code: string) =>
    request<CheckInResponse>('/api/check-ins', {
      method: 'POST',
      body: JSON.stringify({ code }),
    }),
  getStats: (eventId: string) => request<EventStats>(`/api/events/${eventId}/stats`),
}

export function statsStreamUrl(eventId: string): string {
  return `${API_BASE_URL}/api/events/${eventId}/stats/stream`
}
