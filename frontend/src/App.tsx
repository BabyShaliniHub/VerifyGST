import { Route, Routes } from 'react-router-dom'
import AppShell from './app/AppShell'
import PlaceholderPage from './components/PlaceholderPage'
import OverviewPage from './features/overview/OverviewPage'

const placeholders = [
  {
    path: 'verify',
    title: 'Verify Invoice',
    description: 'Upload an invoice and review signature, field and issuer checks.',
  },
  {
    path: 'network',
    title: 'Network Explorer',
    description: 'Interactive graph of companies and transactions.',
  },
  {
    path: 'investigations',
    title: 'Investigations',
    description: 'Cases, related records, evidence completeness and review status.',
  },
  {
    path: 'evidence',
    title: 'Evidence and Reports',
    description: 'Traceable evidence records and exportable case reports.',
  },
  {
    path: 'settings',
    title: 'Settings',
    description: 'Integration status and safe configuration guidance.',
  },
]

function NotFound() {
  return (
    <section>
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <p className="mt-2 max-w-2xl">This address does not match any section of VerifiGST.</p>
    </section>
  )
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<OverviewPage />} />
        {placeholders.map((p) => (
          <Route
            key={p.path}
            path={p.path}
            element={<PlaceholderPage title={p.title} description={p.description} />}
          />
        ))}
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
