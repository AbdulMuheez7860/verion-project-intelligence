export function formatScore(value: number | null | undefined): string | undefined {
  if (value == null) return undefined
  return String(Math.round(value))
}
