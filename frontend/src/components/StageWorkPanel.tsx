import type { StageWork } from '../types'
import { formatDateTime } from '../cron'

const VERDICT: Record<string, string> = { approved: 'approvata', changes_requested: 'modifiche richieste' }
const STATUS: Record<string, string> = { met: 'soddisfatto', unmet: 'non soddisfatto', unknown: 'da verificare' }

export function StageWorkPanel({ work, stageName }: { work: StageWork | null; stageName: string }) {
  if (!work) return null
  const reviewsOf = (artifactId: number) => work.reviews.filter((r) => r.artifactId === artifactId)
  return (
    <section className="card" aria-label="Artefatti, revisioni e evidenze della fase">
      <h2>Artefatti e revisioni · {stageName}</h2>
      {work.artifacts.length === 0 && <div className="muted small">Nessun artefatto prodotto in questa fase.</div>}
      {work.artifacts.map((a) => (
        <div key={a.id} className="work-item">
          <details>
            <summary>
              <strong>{a.name}</strong> <span className="chip">v{a.version}</span>
              <span className="muted small">{formatDateTime(a.createdAt)} · {a.slot}</span>
            </summary>
            <pre>{a.content}</pre>
          </details>
          {reviewsOf(a.id).map((r) => (
            <div key={r.id} className="small">
              Revisione di <span className="mono">{r.reviewer}</span> ({r.taskId}):{' '}
              <span className={r.verdict === 'approved' ? 'ev-met' : 'ev-unmet'}>{VERDICT[r.verdict]}</span>
            </div>
          ))}
          {reviewsOf(a.id).length === 0 && <div className="muted small">Non ancora revisionata.</div>}
        </div>
      ))}
      <div>
        <div className="eyebrow">Pacchetto di evidenze per il gate</div>
        {!work.evidence && <div className="muted small">Il gatekeeper non l'ha ancora preparato.</div>}
        {work.evidence && (
          <>
            <ul className="small">
              {work.evidence.criteria.map((c) => (
                <li key={c.criterion}>
                  {c.criterion}: <span className={`ev-${c.status}`}>{STATUS[c.status]}</span>
                  {c.evidence && <span className="muted"> · {c.evidence}</span>}
                </li>
              ))}
            </ul>
            <div className="muted small">Preparato il {formatDateTime(work.evidence.createdAt)}. È un'informazione per chi approva: la decisione resta umana.</div>
          </>
        )}
      </div>
    </section>
  )
}
