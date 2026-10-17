export default function App() {
  return (
    <main className="p-12">
      <h1 className="text-3xl font-semibold">VerifiGST</h1>
      <p className="mt-2">Tailwind and design tokens check.</p>
      <div className="mt-6 max-w-md border border-line bg-surface p-6">
        <p className="font-medium">White working surface on an ivory canvas</p>
        <p className="mt-2 text-forest">Forest green: positive state</p>
        <p className="text-gold">Antique gold: attention</p>
        <p className="text-terracotta">Terracotta: failure</p>
        <button className="mt-4 rounded-md bg-forest px-4 py-2 text-white">
          Primary action
        </button>
      </div>
    </main>
  )
}
