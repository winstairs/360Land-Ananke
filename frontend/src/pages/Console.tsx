import { useEffect, useState } from 'react'
import { api, ApiError } from '../api'
import { Avatar, TypeTag } from '../components/Avatar'
import { describeCron, formatDateTime } from '../cron'
import { StageWorkPanel } from '../components/StageWorkPanel'
import type { PersonaDetail, Project, ProjectDetail, RaciColumn, StageWork } from '../types'

const STATUS_LABEL: Record<string, string> = { done: 'completata', active: 'in corso', future: 'da iniziare', continuous: 'continua' }
const RUN_LABEL: Record<string, string> = { queued: 'in coda', running: 'in esecuzione', done: 'completata', failed: 'errore', skipped: 'saltata' }

export function Console() {
  const [projects, setProjects] = useState<Project[]>([])
  const [pid, setPid] = useState('')
  const [detail, setDetail] = useState<ProjectDetail | null>(null)
  const [stage, setStage] = useState('')
  const [raci, setRaci] = useState<RaciColumn[]>([])
  const [personaId, setPersonaId] = useState('')
  const [persona, setPersona] = useState<PersonaDetail | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [tick, setTick] = useState(0)
  const [target, setTarget] = useState('')
  const [work, setWork] = useState<StageWork | null>(null)

  useEffect(() => {
    api.projects().then((ps) => {
      setProjects(ps)
      if (ps.length) setPid(ps[0].id)
    }).catch((e) => setError(String(e)))
    const t = setInterval(() => setTick((x) => x + 1), 15000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    if (!pid) return
    api.project(pid).then((d) => {
      setDetail(d)
      setStage((s) => (s && d.stages.some((x) => x.id === s) ? s : d.currentStage))
      setTarget((t) => t || d.gate?.targets[0]?.id || '')
    }).catch((e) => setError(String(e)))
  }, [pid, tick])

  useEffect(() => {
    if (!pid || !stage) return
    api.raci(pid, stage).then((cols) => {
      setRaci(cols)
      const ids = cols.flatMap((c) => c.people.map((p) => p.id))
      setPersonaId((cur) => (ids.includes(cur) ? cur : cols[0]?.people[0]?.id ?? ''))
    }).catch((e) => setError(String(e)))
  }, [pid, stage, tick])

  useEffect(() => {
    if (!pid || !stage) return
    api.stageWork(pid, stage).then(setWork).catch((e) => setError(String(e)))
  }, [pid, stage, tick])

  useEffect(() => {
    if (!pid || !personaId) return
    api.persona(pid, personaId).then(setPersona).catch((e) => setError(String(e)))
  }, [pid, personaId, tick])

  const changeProject = (id: string) => {
    setPid(id); setStage(''); setPersonaId(''); setPersona(null); setMessage(''); setTarget('')
  }

  const runNow = async (slot: string, taskId: string) => {
    try {
      const r = await api.runTask(pid, slot, taskId)
      setMessage(r.message)
      setTick((x) => x + 1)
    } catch (e) {
      setMessage(e instanceof ApiError ? String(e.detail) : String(e))
    }
  }

  const decide = async (outcome: 'approved' | 'rejected') => {
    if (!persona) return
    try {
      const r = await api.decideGate(pid, { outcome, personaId: persona.id, targetStage: target || undefined })
      setMessage(r.message)
    } catch (e) {
      setMessage(e instanceof ApiError ? String(e.detail) : String(e))
    }
  }

  const project = projects.find((p) => p.id === pid)
  const stageName = detail?.stages.find((s) => s.id === stage)?.name ?? ''
  const selLetter = raci.find((c) => c.people.some((p) => p.id === personaId))

  return (
    <div className="page">
      {error && <div className="alert alert-error" role="alert">{error}</div>}

      <section className="card" aria-label="Macchina a stati del progetto">
        <div className="row-between">
          <div className="field">
            <label htmlFor="project-select" className="eyebrow">Progetto attivo</label>
            <select id="project-select" className="select-lg" value={pid} onChange={(e) => changeProject(e.target.value)}>
              {projects.map((p) => <option key={p.id} value={p.id}>{p.name} · {p.methodologyLabel}</option>)}
            </select>
            {project && (
              <div className="chips">
                <span className="chip">{project.client}</span>
                <span className="chip">Modello {project.methodologyLabel}</span>
                <span className="chip">Fase attuale: {detail?.currentStageName}</span>
                {project.sprint && <span className="chip">Sprint {detail?.sprint}</span>}
              </div>
            )}
          </div>
          <div className="muted small">Seleziona una fase per vederne i responsabili</div>
        </div>
        <div className="stages">
          {detail?.stages.map((s, i) => (
            <div key={s.id} className="stage-wrap">
              <button type="button" className={`stage stage-${s.status}${s.id === stage ? ' stage-selected' : ''}`}
                aria-pressed={s.id === stage} onClick={() => setStage(s.id)}>
                <span className="stage-name">{s.name}</span>
                <span className="stage-status">{STATUS_LABEL[s.status]}{s.timebox ? ` · ${s.timebox}` : ''}</span>
              </button>
              {i < detail.stages.length - 1 && <span className="arrow" aria-hidden="true">→</span>}
            </div>
          ))}
        </div>
        {detail?.methodology === 'scrum' && <p className="muted small">Da Sprint planning a Retrospettiva gli stadi si ripetono a ogni sprint.</p>}
      </section>

      <div className="split">
        <section className="card grow" aria-label="Matrice RACI della fase">
          <div className="row-between">
            <h2>Responsabili · {stageName}</h2>
            <div className="legend"><span className="dot dot-human" />Umano <span className="dot dot-avatar" />Avatar (agenti)</div>
          </div>
          <div className="raci">
            {raci.map((col) => (
              <div key={col.letter} className="raci-col">
                <div className="raci-head"><span className="mono">{col.letter}</span> <span className="muted small">{col.label}</span></div>
                {col.people.length === 0 && <div className="muted small">Nessuno</div>}
                {col.people.map((p) => (
                  <button key={p.id} type="button" className={`badge${p.id === personaId ? ' badge-selected' : ''}`}
                    aria-pressed={p.id === personaId} onClick={() => setPersonaId(p.id)}>
                    <Avatar kind={p.kind} face={p.face} />
                    <span className="badge-text">
                      <strong>{p.name}</strong>
                      <span className="muted small">{p.roles.slice(0, 2).join(', ')}{p.roles.length > 2 ? '…' : ''}</span>
                      <span className="chips"><TypeTag kind={p.kind} />{p.slots.length > 1 && <span className="tag">{p.slots.length} agenti</span>}</span>
                    </span>
                  </button>
                ))}
              </div>
            ))}
          </div>
        </section>

        <section className="card side" aria-label="Dettaglio della persona">
          {persona ? (
            <>
              <div className="persona-head">
                <Avatar kind={persona.kind} face={persona.face} size={64} />
                <div>
                  <h2>{persona.name}</h2>
                  <div className="muted small">{persona.title}{selLetter ? ` · ${selLetter.letter} in ${stageName}` : ''}</div>
                  <div className="chips"><TypeTag kind={persona.kind} />{persona.processRoles.map((r) => <span key={r} className="chip">{r}</span>)}</div>
                </div>
              </div>

              {persona.approvesCurrentGate && detail?.gate && (
                <div className="gate-box">
                  <div className="eyebrow">Gate da decidere · {detail.gate.stageName}</div>
                  <strong>{detail.gate.name}</strong>
                  <ul>{detail.gate.criteria.map((c) => <li key={c}>{c}</li>)}</ul>
                  {detail.gate.targets.length > 1 && (
                    <label className="field">Prossimo stadio
                      <select value={target} onChange={(e) => setTarget(e.target.value)}>
                        {detail.gate.targets.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                      </select>
                    </label>
                  )}
                  <div className="chips">
                    <button type="button" className="btn btn-primary" onClick={() => decide('approved')}>Approva</button>
                    <button type="button" className="btn btn-danger" onClick={() => decide('rejected')}>Respingi</button>
                  </div>
                </div>
              )}

              {persona.slots.length > 0 && (
                <div>
                  <div className="eyebrow">{persona.kind === 'avatar' ? 'Agenti e compiti pianificati' : 'Compiti assegnati'}</div>
                  {persona.slots.map((s) => (
                    <div key={s.slot} className="slot">
                      <div className="row-between">
                        <strong>{s.agentName}</strong>
                        <span className="mono small">{s.model ?? 'persona umana'}</span>
                      </div>
                      <div className="muted small">{s.stageName} · autonomia {s.autonomy}</div>
                      {s.tasks.map((t) => (
                        <div key={t.id} className="task">
                          <div>
                            <div className="task-name">{t.name}</div>
                            <div className="muted small"><span className="mono">{t.cron}</span> · {describeCron(t.cron) ?? 'cron non valido'}</div>
                            <div className="muted small">
                              {!t.enabled ? 'disattivato' : t.activeInCurrentStage ? `prossima: ${formatDateTime(t.nextRun)}` : 'attivo solo nella sua fase'}
                            </div>
                          </div>
                          {persona.kind === 'avatar' && t.action === 'agent' && (
                            <button type="button" className="btn btn-primary" onClick={() => runNow(s.slot, t.id)}>Esegui ora</button>
                          )}
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              )}

              {message && <div className="alert" role="status">{message}</div>}

              <div>
                <div className="eyebrow">{persona.kind === 'avatar' ? 'Attività svolte in modalità agentica' : 'Ultime attività'}</div>
                {persona.runs.length === 0 && <div className="muted small">Nessuna esecuzione ancora.</div>}
                {persona.runs.map((r) => (
                  <div key={r.id} className="log">
                    <span className="mono small muted">{formatDateTime(r.createdAt)}</span>
                    <span>
                      <strong>{r.taskName}</strong> <span className={`run run-${r.status}`}>{RUN_LABEL[r.status]}</span>
                      {r.trigger === 'manual' && <span className="muted small"> · manuale</span>}
                      {r.output && <span className="muted small block">{r.output}</span>}
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : <div className="muted">Seleziona un responsabile.</div>}
        </section>
      </div>

      <StageWorkPanel work={work} stageName={stageName} />
    </div>
  )
}
