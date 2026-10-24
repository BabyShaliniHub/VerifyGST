import { useEffect, useRef, useState, type DragEvent } from 'react'
import { Upload } from 'lucide-react'
import { fetchSamples, verifySample, type ApiReport, type ApiSample } from '../../lib/api'
import CheckList, { StatusLabel, statusMeta } from './CheckList'
import { uploadChecks, type CheckResult, type CheckStatus } from './checkTypes'
import { detectFileType } from './fileSignature'
import InvoicePreview from './InvoicePreview'

const MAX_BYTES = 10 * 1024 * 1024
const ALLOWED_TYPES = ['application/pdf', 'image/png', 'image/jpeg']
const ALLOWED_EXT = /\.(pdf|png|jpe?g)$/i
const statusOrder: CheckStatus[] = ['passed', 'failed', 'unknown', 'manual_review', 'not_checked']
const fieldClass = 'rounded-md border border-line bg-surface px-3 py-2'

type UploadedFile = { name: string; size: number; type: string; url: string }
type SamplesState = 'loading' | 'ready' | 'error'
type ResultState =
  | { state: 'idle' }
  | { state: 'loading' }
  | { state: 'error' }
  | { state: 'ready'; report: ApiReport }

function summarize(checks: CheckResult[]): string {
  return statusOrder
    .map((s) => {
      const n = checks.filter((c) => c.status === s).length
      return n > 0 ? `${n} ${statusMeta[s].label.toLowerCase()}` : ''
    })
    .filter(Boolean)
    .join(', ')
}

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function VerifyInvoicePage() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [samples, setSamples] = useState<ApiSample[]>([])
  const [samplesState, setSamplesState] = useState<SamplesState>('loading')
  const [samplesAttempt, setSamplesAttempt] = useState(0)
  const [sampleId, setSampleId] = useState('')
  const [result, setResult] = useState<ResultState>({ state: 'idle' })
  const [resultAttempt, setResultAttempt] = useState(0)
  const [upload, setUpload] = useState<UploadedFile | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    setSamplesState('loading')
    fetchSamples(controller.signal)
      .then((list) => {
        setSamples(list)
        setSamplesState('ready')
      })
      .catch(() => {
        if (!controller.signal.aborted) setSamplesState('error')
      })
    return () => controller.abort()
  }, [samplesAttempt])

  useEffect(() => {
    if (!sampleId) {
      setResult({ state: 'idle' })
      return
    }
    const controller = new AbortController()
    setResult({ state: 'loading' })
    verifySample(sampleId, controller.signal)
      .then((report) => setResult({ state: 'ready', report }))
      .catch(() => {
        if (!controller.signal.aborted) setResult({ state: 'error' })
      })
    return () => controller.abort()
  }, [sampleId, resultAttempt])

  useEffect(() => {
    return () => {
      if (upload) URL.revokeObjectURL(upload.url)
    }
  }, [upload])

  const acceptFile = async (file: File | undefined) => {
    if (!file) return
    if (!ALLOWED_EXT.test(file.name) || !ALLOWED_TYPES.includes(file.type)) {
      setError('Unsupported file. Use a PDF, PNG or JPG file.')
      return
    }
    if (file.size > MAX_BYTES) {
      setError('The file is larger than 10 MB.')
      return
    }
    setError(null)
    const detected = await detectFileType(file)
    if (detected !== file.type) {
      setError('The file content does not match its type. Use a real PDF, PNG or JPG file.')
      return
    }
    setSampleId('')
    setUpload({
      name: file.name,
      size: file.size,
      type: file.type,
      url: URL.createObjectURL(file),
    })
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragActive(false)
    acceptFile(e.dataTransfer.files[0])
  }

  const chooseSample = (id: string) => {
    setSampleId(id)
    setUpload(null)
    setError(null)
  }

  const sample = samples.find((s) => s.id === sampleId)

  return (
    <section>
      <h1 className="text-2xl font-semibold">Verify Invoice</h1>
      <p className="mt-2 max-w-3xl">
        Review the document next to its verification checks. Each check keeps its own result. There
        is no single overall verdict.
      </p>

      <p className="mt-4 max-w-3xl border-l-4 border-gold bg-surface px-4 py-3">
        Demonstration data. The sample invoices are synthetic. Their checks are run by the real
        verification engine on the local server. A file you upload is previewed in your browser
        only. It is not sent anywhere and it is not verified, because uploaded files are not read
        yet.
      </p>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div>
          <h2 className="text-xl font-semibold">Document</h2>

          <div
            onDragOver={(e) => {
              e.preventDefault()
              setDragActive(true)
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            className={`mt-3 flex flex-col items-center gap-2 border-2 border-dashed px-4 py-8 text-center ${
              dragActive ? 'border-forest bg-sunken' : 'border-line bg-surface'
            }`}
          >
            <Upload size={28} aria-hidden="true" />
            <p className="font-semibold">Drag and drop an invoice here</p>
            <p className="text-base text-ink/70">PDF, PNG or JPG, up to 10 MB</p>
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className={`${fieldClass} hover:bg-canvas`}
            >
              Choose a file
            </button>
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              className="sr-only"
              aria-label="Choose an invoice file"
              onChange={(e) => {
                acceptFile(e.target.files?.[0])
                e.target.value = ''
              }}
            />
          </div>
          {error && (
            <p role="alert" className="mt-2 border-l-4 border-terracotta bg-surface px-4 py-2">
              {error}
            </p>
          )}

          <div className="mt-4 flex flex-col gap-1">
            <label htmlFor="sample" className="font-medium">
              Or choose a synthetic sample invoice
            </label>
            <select
              id="sample"
              value={sampleId}
              onChange={(e) => chooseSample(e.target.value)}
              disabled={samplesState !== 'ready'}
              className={fieldClass}
            >
              <option value="">
                {samplesState === 'loading' ? 'Loading samples...' : 'No sample selected'}
              </option>
              {samples.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          {samplesState === 'error' && (
            <div role="alert" className="mt-2 border-l-4 border-terracotta bg-surface px-4 py-3">
              <p>
                The verification service could not be reached, so the sample invoices could not be
                loaded. Start the backend on port 8000 and try again.
              </p>
              <button
                type="button"
                onClick={() => setSamplesAttempt((n) => n + 1)}
                className={`${fieldClass} mt-2 hover:bg-canvas`}
              >
                Try again
              </button>
            </div>
          )}

          <div className="mt-4">
            {sample && <InvoicePreview sample={sample} />}
            {upload && (
              <div className="border border-line bg-surface p-4">
                <p className="font-semibold">{upload.name}</p>
                <p className="text-base text-ink/70">
                  {upload.type} - {formatSize(upload.size)}
                </p>
                {upload.type === 'application/pdf' ? (
                  <object
                    data={upload.url}
                    type="application/pdf"
                    className="mt-3 h-[480px] w-full border border-line"
                    aria-label="PDF preview"
                  >
                    <p>PDF preview is not available in this browser.</p>
                  </object>
                ) : (
                  <img
                    src={upload.url}
                    alt="Preview of the uploaded invoice"
                    className="mt-3 max-h-[480px] w-full border border-line object-contain"
                  />
                )}
              </div>
            )}
            {!sample && !upload && (
              <p className="border border-line bg-surface px-4 py-3">
                Choose a sample invoice or upload a file to see its checks.
              </p>
            )}
          </div>
        </div>

        <div>
          <h2 className="text-xl font-semibold">Checks</h2>
          {!sample && !upload && (
            <p className="mt-3 border border-line bg-surface px-4 py-3">
              Results appear here, one per check.
            </p>
          )}

          {upload && (
            <>
              <p className="mt-1 text-base text-ink/70">{summarize(uploadChecks)}</p>
              <div className="mt-3">
                <CheckList checks={uploadChecks} />
              </div>
              <p className="mt-4">
                Verification of uploaded files arrives once the engine can read documents. Choose a
                sample invoice to see how results are shown.
              </p>
            </>
          )}

          {sample && result.state === 'loading' && <p className="mt-3">Running the checks...</p>}

          {sample && result.state === 'error' && (
            <div role="alert" className="mt-3 border-l-4 border-terracotta bg-surface px-4 py-3">
              <p>
                The checks could not be run because the verification service could not be reached.
              </p>
              <button
                type="button"
                onClick={() => setResultAttempt((n) => n + 1)}
                className={`${fieldClass} mt-2 hover:bg-canvas`}
              >
                Try again
              </button>
            </div>
          )}

          {sample && result.state === 'ready' && (
            <>
              <p className="mt-1 text-base text-ink/70">{summarize(result.report.checks)}</p>
              <div className="mt-3">
                <CheckList checks={result.report.checks} />
              </div>

              <h3 className="mt-6 text-lg font-semibold">Fields: invoice and signed payload</h3>
              <div className="mt-2 overflow-x-auto">
                <table className="w-full border border-line bg-surface text-left">
                  <thead>
                    <tr className="bg-sunken">
                      <th className="px-3 py-2 font-semibold">Field</th>
                      <th className="px-3 py-2 font-semibold">On the invoice</th>
                      <th className="px-3 py-2 font-semibold">Signed payload</th>
                      <th className="px-3 py-2 font-semibold">Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.report.field_comparisons.map((f) => (
                      <tr key={f.field} className="border-t border-line">
                        <th scope="row" className="px-3 py-2 font-semibold">
                          {f.label}
                        </th>
                        <td className="px-3 py-2">{f.visible ?? 'Not found'}</td>
                        <td className="px-3 py-2">{f.signed ?? 'Not available'}</td>
                        <td className="px-3 py-2">
                          <StatusLabel status={f.status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <h3 className="mt-6 text-lg font-semibold">Suggested next actions</h3>
              <ul className="mt-2 list-disc pl-5">
                {result.report.next_actions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </>
          )}

          <p className="mt-6 text-base text-ink/70">
            A valid signature means the signed payload verifies under the relevant key. It does not
            prove that goods or services were delivered. A copied QR code does not certify a
            document, so the signed fields are always compared with the document itself.
          </p>
        </div>
      </div>
    </section>
  )
}
