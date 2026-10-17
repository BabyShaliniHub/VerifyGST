import { Route, Routes } from 'react-router-dom'
import AppShell from './app/AppShell'
import PlaceholderPage from './components/PlaceholderPage'

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
        <Route
          index
          element={
            <PlaceholderPage
              title="Overview"
              description="Operational summary of invoices, verification results and investigations."
            />
          }
        />
        <Route
          path="verify"
          element={
            <PlaceholderPage
              title="Verify Invoice"
              description="Upload an invoice and review signature, field and issuer checks."
            />
          }
        />
        <Route
          path="network"
          element={
            <PlaceholderPage
              title="Network Explorer"
              description="Interactive graph of companies and transactions."
            />
          }
        />
        <Route
          path="investigations"
          element={
            <PlaceholderPage
              title="Investigations"
              description="Cases, related records, evidence completeness and review status."
            />
          }
        />
        <Route
          path="evidence"
          element={
            <PlaceholderPage
              title="Evidence and Reports"
              description="Traceable evidence records and exportable case reports."
            />
          }
        />
        <Route
          path="settings"
          element={
            <PlaceholderPage
              title="Settings"
              description="Integration status and safe configuration guidance."
            />
          }
        />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
