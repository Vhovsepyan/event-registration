import { Link, Route, Routes } from 'react-router-dom'

import './App.css'
import { CheckInPage } from './pages/CheckInPage'
import { CreateEventPage } from './pages/CreateEventPage'
import { EventPage } from './pages/EventPage'
import { EventsPage } from './pages/EventsPage'
import { OrganizerPage } from './pages/OrganizerPage'
import { TicketPage } from './pages/TicketPage'

function NotFoundPage() {
  return (
    <section className="panel" aria-labelledby="not-found-heading">
      <p className="eyebrow">404</p>
      <h1 id="not-found-heading">Page not found</h1>
      <p className="status-card__description">The requested page does not exist.</p>
      <Link className="text-link" to="/">
        Return home
      </Link>
    </section>
  )
}

export default function App() {
  return (
    <div className="app-shell">
      <header className="site-header">
        <Link className="brand" to="/" aria-label="Event Registration home">
          <span aria-hidden="true">E·R</span> Event Registration
        </Link>
        <nav aria-label="Primary navigation">
          <Link to="/">Events</Link>
          <Link to="/organizer">Organizer</Link>
          <Link to="/check-in">Check in</Link>
        </nav>
      </header>
      <main className="page-content">
        <Routes>
          <Route path="/" element={<EventsPage />} />
          <Route path="/organizer" element={<CreateEventPage />} />
          <Route path="/events/:eventId" element={<EventPage />} />
          <Route path="/events/:eventId/organizer" element={<OrganizerPage />} />
          <Route path="/tickets/:code" element={<TicketPage />} />
          <Route path="/check-in" element={<CheckInPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </div>
  )
}
