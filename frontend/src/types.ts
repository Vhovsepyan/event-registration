export type EventRecord = {
  id: string
  title: string
  description: string
  starts_at: string
  capacity: number
  created_at: string
  updated_at: string
}

export type Ticket = {
  id: string
  registration_id: string
  code: string
  created_at: string
  checked_in_at: string | null
  invalidated_at: string | null
}

export type Registration = {
  id: string
  event_id: string
  email: string
  status: 'CONFIRMED' | 'WAITLISTED' | 'CANCELLED'
  waitlist_order: number | null
  created_at: string
  confirmed_at: string | null
  cancelled_at: string | null
  ticket: Ticket | null
}

export type TicketDetails = Ticket & {
  event: EventRecord
  registration_status: Registration['status']
}

export type CheckInResponse = {
  result: 'SUCCESS' | 'ALREADY_CHECKED_IN' | 'INVALID_TICKET'
  checked_in_at: string | null
}

export type EventStats = {
  event_id: string
  capacity: number
  confirmed: number
  waitlisted: number
  checked_in: number
}
