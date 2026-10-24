const DAYS: Record<string, string> = { '0': 'domenica', '1': 'lunedì', '2': 'martedì', '3': 'mercoledì', '4': 'giovedì', '5': 'venerdì', '6': 'sabato' }
const pad = (s: string) => (s.length < 2 ? '0' + s : s)

/** Traduzione in parole delle espressioni cron più comuni; null se l'espressione non ha 5 campi validi. */
export function describeCron(expr: string): string | null {
  const f = expr.trim().split(/\s+/)
  if (f.length !== 5 || !f.every((x) => /^[\d*/,-]+$/.test(x))) return null
  const [m, h, dom, mon, dw] = f
  if (dom !== '*' || mon !== '*') return 'pianificazione personalizzata'
  let days: string | null = null
  if (dw === '1-5') days = 'feriali'
  else if (dw === '*') days = 'tutti i giorni'
  else if (/^\d(,\d)+$/.test(dw)) {
    const list = dw.split(',').map((d) => DAYS[d])
    if (list.every(Boolean)) days = list.slice(0, -1).join(', ') + ' e ' + list[list.length - 1]
  } else days = DAYS[dw] ?? null
  if (!days) return 'pianificazione personalizzata'
  if (/^\d+$/.test(m) && /^\d+$/.test(h)) return `${days} alle ${pad(h)}:${pad(m)}`
  if (/^\*\/\d+$/.test(m) && h === '*') return `ogni ${m.slice(2)} minuti, ${days}`
  if (/^\*\/\d+$/.test(m) && /^\d+-\d+$/.test(h)) return `ogni ${m.slice(2)} minuti, ore ${h.replace('-', '–')}, ${days}`
  if (m === '0' && /^\*\/\d+$/.test(h)) return `ogni ${h.slice(2)} ore, ${days}`
  return 'pianificazione personalizzata'
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('it-IT', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}
