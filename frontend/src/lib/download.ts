export function toCsv(rows: string[][]): string {
  return (
    rows
      .map((row) =>
        row
          .map((cell) => {
            // Prefix cells that a spreadsheet could treat as a formula.
            const safe = /^[=+\-@\t\r]/.test(cell) ? `'${cell}` : cell
            return `"${safe.replace(/"/g, '""')}"`
          })
          .join(','),
      )
      .join('\r\n') + '\r\n'
  )
}

export function downloadText(filename: string, text: string, mime: string): void {
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
