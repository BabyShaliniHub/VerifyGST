export type DetectedType = 'application/pdf' | 'image/png' | 'image/jpeg' | null

function startsWith(bytes: Uint8Array, signature: number[]): boolean {
  return signature.every((value, i) => bytes[i] === value)
}

// Reads the first bytes of a file and reports its real type, or null if unrecognised.
export async function detectFileType(file: File): Promise<DetectedType> {
  const bytes = new Uint8Array(await file.slice(0, 1024).arrayBuffer())
  if (startsWith(bytes, [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])) return 'image/png'
  if (startsWith(bytes, [0xff, 0xd8, 0xff])) return 'image/jpeg'
  if (String.fromCharCode(...bytes).includes('%PDF-')) return 'application/pdf'
  return null
}
