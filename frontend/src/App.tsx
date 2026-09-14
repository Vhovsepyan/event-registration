import { Link, Route, Routes } from 'react-router-dom'

import './App.css'

function FoundationPage() {
  return (
    <section className="status-card" aria-labelledby="foundation-heading">
      <p className="eyebrow">Frontend foundation</p>
      <h1 id="foundation-heading">Ready for event registration</h1>
      <p className="status-card__description">
        The React application is configured and ready for the product screens in the next tasks.
      </p>
    </section>
  )
}

function NotFoundPage() {
  return (
    <section className="status-card" aria-labelledby="not-found-heading">
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
          Event Registration
        </Link>
      </header>
      <main className="page-content">
        <Routes>
          <Route path="/" element={<FoundationPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </div>
  )
}
