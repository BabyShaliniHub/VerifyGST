import { FIELD_KEYS, fieldLabels, type SampleInvoice } from './demoInvoices'

export default function InvoicePreview({ invoice }: { invoice: SampleInvoice }) {
  return (
    <div className="border border-line bg-white p-6">
      <p className="text-lg font-semibold tracking-wide">TAX INVOICE - SYNTHETIC SAMPLE</p>
      <p className="text-base text-ink/70">Not a real invoice. Invented for demonstration.</p>
      <dl className="mt-4 grid grid-cols-[10rem_1fr] gap-x-3 gap-y-2">
        {FIELD_KEYS.map((key) => (
          <div key={key} className="contents">
            <dt className="font-semibold">{fieldLabels[key]}</dt>
            <dd>
              {invoice.visible[key]}
              {invoice.lowConfidence.includes(key) ? ' (unclear in the document)' : ''}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
