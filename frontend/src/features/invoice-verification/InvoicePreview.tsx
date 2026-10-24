import type { ApiSample } from '../../lib/api'

export default function InvoicePreview({ sample }: { sample: ApiSample }) {
  return (
    <div className="border border-line bg-white p-6">
      <p className="text-lg font-semibold tracking-wide">TAX INVOICE - SYNTHETIC SAMPLE</p>
      <p className="text-base text-ink/70">Not a real invoice. Invented for demonstration.</p>
      <dl className="mt-4 grid grid-cols-[10rem_1fr] gap-x-3 gap-y-2">
        {sample.visible.map((f) => (
          <div key={f.field} className="contents">
            <dt className="font-semibold">{f.label}</dt>
            <dd>
              {f.value ?? 'Not found on the document'}
              {f.unclear ? ' (unclear in the document)' : ''}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
