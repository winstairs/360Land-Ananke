import { useEffect, useMemo, useState } from 'react'
import { api, ApiError } from '../api'
import { Avatar, TypeTag } from '../components/Avatar'
import { ConnectorDialog } from '../components/ConnectorDialog'
import { MODE_LABELS, SPECS } from '../connectorSpecs'
import { describeCron } from '../cron'
import { LlmCatalogEditor } from './LlmCatalogEditor'
import type { AgentPreset, Bindings, ConfigPersona, Connector, LlmCatalog, ModelBundle, PlatformConfig, SlotAssignment, TopologyAgent } from '../types'

type Tab = 'slots' | 'roles' | 'personas' | 'tools' | 'ai'
const FACES = [
  { skin: '#F1C7A5', hair: '#8A4B2A', shirt: '#0F766E', longHair: true },
  { skin: '#C68863', hair: '#2E2E2E', shirt: '#2F45C9', longHair: false },
  { skin: '#E2B58F', hair: '#B07A35', shirt: '#7A5C9E', longHair: true },
  { skin: '#B97A55', hair: '#1F1A17', shirt: '#3F5E3A', longHair: false },
]
const MODES = [{ id: 'human', label: 'Solo persone' }, { id: 'hybrid', label: 'Persone con agenti' }, { id: 'agent', label: 'Solo agenti' }] as const
const CATEGORY_LABELS: Record<Connector['category'], string> = { 'work-tracking': 'Gestione del lavoro', 'knowledge-base': 'Documentazione',
  'file-storage': 'Archivio file', 'code-hosting': 'Codice', communication: 'Comunicazione' }
const BINDINGS: [keyof Omit<Bindings, 'artifactStorage'>, string, boolean][] = [
  ['workTracking', 'Gestione del lavoro', true], ['knowledgeBase', 'Documentazione', true],
  ['fileStorage', 'Archivio file', false], ['codeHosting', 'Codice', false]]

export function Config() {
  const [m, setM] = useState<'waterfall' | 'scrum'>('waterfall')
  const [model, setModel] = useState<ModelBundle | null>(null)
  const [config, setConfig] = useState<PlatformConfig | null>(null)
  const [version, setVersion] = useState(0)
  const [dirty, setDirty] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const [message, setMessage] = useState('')
  const [tab, setTab] = useState<Tab>('slots')
  const [open, setOpen] = useState('')
  // Connettore in modifica nel popup: indice null per uno nuovo
  const [editing, setEditing] = useState<{ index: number | null; connector: Connector } | null>(null)
  // Modelli attivi del catalogo LLM salvato: sono le scelte possibili per i preset
  const [llm, setLlm] = useState<LlmCatalog | null>(null)

  useEffect(() => {
    if (tab === 'ai') api.llmCatalog().then((r) => setLlm(r.catalog)).catch(() => undefined)
  }, [tab])

  useEffect(() => {
    setConfig(null); setDirty(false); setMessage('')
    Promise.all([api.model(m), api.config(m)]).then(([mod, c]) => {
      setModel(mod); setConfig(c.config); setVersion(c.version)
    }).catch((e) => setMessage(String(e)))
  }, [m])

  // Validazione lato server a ogni modifica (le regole di governance vivono nel backend)
  useEffect(() => {
    if (!config || !dirty) return
    const t = setTimeout(() => api.validateConfig(m, config).then((r) => setErrors(r.errors)).catch(() => undefined), 400)
    return () => clearTimeout(t)
  }, [config, dirty, m])

  const update = (fn: (c: PlatformConfig) => void) => {
    setConfig((c) => {
      if (!c) return c
      const next = structuredClone(c)
      fn(next)
      return next
    })
    setDirty(true); setMessage('')
  }

  const save = async () => {
    if (!config) return
    try {
      const r = await api.saveConfig(m, config)
      setVersion(r.version); setDirty(false); setErrors([]); setMessage(r.message)
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) {
        const d = e.detail as { errors?: string[] }
        setErrors(d.errors ?? []); setMessage('Salvataggio bloccato: correggi gli errori elencati.')
      } else setMessage(String(e))
    }
  }

  const groups = useMemo(() => {
    if (!model) return []
    const stageName = Object.fromEntries(model.process.stages.map((s) => [s.id, s.name]))
    return [
      { id: 'supervisor', name: model.topology.supervisor.name, agents: model.topology.supervisor.agents },
      ...model.topology.orchestrators.map((o) => ({ id: o.stage, name: stageName[o.stage] ?? o.name, agents: o.agents })),
    ]
  }, [model])

  if (!config || !model) return <div className="page"><div className="card">{message || 'Caricamento…'}</div></div>

  const personas = Object.fromEntries(config.personas.map((p) => [p.id, p]))
  const humans = config.personas.filter((p) => p.kind === 'human')
  const avatars = config.personas.filter((p) => p.kind === 'avatar')
  const roleName = Object.fromEntries(model.process.roles.map((r) => [r.id, r.name]))
  const slotOf = (id: string) => config.slotAssignments.find((s) => s.slot === id)
  const usage = (pid: string) => config.slotAssignments.filter((s) => s.persona === pid).length
    + config.roleAssignments.filter((r) => r.personas?.includes(pid)).length
  const llmPresets = config.agentPresets.filter((p) => p.kind === 'llm-agent')

  const setSlot = (id: string, fn: (s: SlotAssignment) => void) => update((c) => {
    const s = c.slotAssignments.find((x) => x.slot === id)
    if (s) fn(s)
  })

  const addPersona = (kind: 'human' | 'avatar') => update((c) => {
    const n = c.personas.length + 1
    const p: ConfigPersona = {
      id: `${kind === 'human' ? 'persona' : 'avatar'}-${n}`, kind, name: kind === 'human' ? '[NOME PERSONA]' : `Nuovo avatar ${n}`,
      title: kind === 'human' ? 'Persona umana' : 'Avatar personalizzato', face: FACES[n % FACES.length], email: '',
    }
    c.personas.push(p)
  })

  const setPreset = (id: string, fn: (p: AgentPreset) => void) => update((c) => {
    const p = c.agentPresets.find((x) => x.id === id)
    if (p) fn(p)
  })
  const modelOptions = (llm?.providers ?? []).filter((p) => p.enabled ?? true).flatMap((p) => p.models
    .filter((m) => m.enabled ?? true)
    .map((m) => ({ id: `${p.id}/${m.alias}`, label: `${p.name} · ${m.alias} (${m.family})` })))

  const newConnector = () => {
    let n = config.connectors.length + 1
    while (config.connectors.some((x) => x.id === `connector-${n}`)) n++
    setEditing({ index: null, connector: { id: `connector-${n}`, name: 'Nuovo connettore', system: 'jira', category: 'work-tracking', transport: 'mcp-remote', endpoint: '' } })
  }

  const applyConnector = (x: Connector) => {
    const index = editing?.index ?? null
    update((c) => {
      if (index === null) c.connectors.push(x)
      else c.connectors[index] = x
    })
    setEditing(null)
  }

  // Artefatti raggruppati per la fase che li produce (outputs del processo)
  const artifactName = Object.fromEntries(model.process.artifacts.map((a) => [a.id, a.name]))
  const placed = new Set<string>()
  const artifactGroups = [...model.process.stages].sort((a, b) => a.order - b.order).map((s) => {
    const ids = (s.outputs ?? []).filter((id) => artifactName[id] && !placed.has(id))
    ids.forEach((id) => placed.add(id))
    return { id: s.id, name: s.name, ids }
  }).filter((g) => g.ids.length > 0)
  const others = model.process.artifacts.map((a) => a.id).filter((id) => !placed.has(id))
  if (others.length) artifactGroups.push({ id: 'others', name: 'Altri artefatti', ids: others })

  // Le persone umane prima degli avatar; l'indice originale serve per gli aggiornamenti
  const personaCards = config.personas.map((p, i) => ({ p, i })).sort((a, b) => (a.p.kind === b.p.kind ? 0 : a.p.kind === 'human' ? -1 : 1))

  const renderSlot = (a: TopologyAgent) => {
    const s = slotOf(a.id)
    if (!s) return null
    const p = personas[s.persona]
    const isOpen = open === a.id
    return (
      <div key={a.id} className="cfg-row">
        <div className="cfg-main">
          <button type="button" className="link-btn" aria-expanded={isOpen} onClick={() => setOpen(isOpen ? '' : a.id)}>
            <strong>{a.name}</strong>
            <span className="muted small">supporta {roleName[a.supportsRole]} · {a.scheduledTasks?.length ?? 0} compiti</span>
          </button>
          <div className="cfg-controls">
            {p && <Avatar kind={p.kind} face={p.face} size={32} />}
            <label className="sr-only" htmlFor={`persona-${a.id}`}>Persona per {a.name}</label>
            <select id={`persona-${a.id}`} value={s.persona} onChange={(e) => setSlot(a.id, (x) => { x.persona = e.target.value })}>
              <optgroup label="Avatar">{avatars.map((x) => <option key={x.id} value={x.id}>{x.name} · {x.title}</option>)}</optgroup>
              <optgroup label="Umani">{humans.map((x) => <option key={x.id} value={x.id}>{x.name} · {x.title}</option>)}</optgroup>
            </select>
            {p?.kind === 'avatar' && (
              <>
                <label className="sr-only" htmlFor={`preset-${a.id}`}>Preset per {a.name}</label>
                <select id={`preset-${a.id}`} value={s.preset ?? ''} onChange={(e) => setSlot(a.id, (x) => { x.preset = e.target.value })}>
                  <option value="">— preset —</option>
                  {llmPresets.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
                </select>
              </>
            )}
          </div>
        </div>
        {isOpen && (
          <div className="cfg-detail">
            {p?.kind === 'avatar' && (
              <>
                <label className="field">Istruzioni dell'agente
                  <textarea rows={3} value={s.instructions ?? ''} onChange={(e) => setSlot(a.id, (x) => { x.instructions = e.target.value })} />
                </label>
                <label className="field">Autonomia
                  <select value={s.autonomy ?? 'supervised'} onChange={(e) => setSlot(a.id, (x) => { x.autonomy = e.target.value as SlotAssignment['autonomy'] })}>
                    <option value="advisory">Solo proposte</option>
                    <option value="supervised">Con revisione</option>
                    <option value="autonomous">Autonomo</option>
                  </select>
                </label>
              </>
            )}
            <div className="eyebrow">Compiti standard</div>
            {a.scheduledTasks?.map((t) => {
              const ov = s.taskOverrides?.[t.id] ?? {}
              const cron = ov.cron ?? t.cron
              const enabled = ov.enabled ?? true
              const desc = describeCron(cron)
              return (
                <div key={t.id} className="task">
                  <label className="check">
                    <input type="checkbox" checked={enabled}
                      onChange={() => setSlot(a.id, (x) => { x.taskOverrides = { ...x.taskOverrides, [t.id]: { ...ov, enabled: !enabled } } })} />
                    {t.name}
                  </label>
                  <span className="cron-edit">
                    <input aria-label={`Cron di ${t.name}`} className={`mono${desc ? '' : ' invalid'}`} value={cron}
                      onChange={(e) => setSlot(a.id, (x) => { x.taskOverrides = { ...x.taskOverrides, [t.id]: { ...ov, cron: e.target.value } } })} />
                    <span className={desc ? 'ok small' : 'err small'}>{enabled ? (desc ?? 'non valido') : 'disattivato'}</span>
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="page">
      <section className="card row-between">
        <div className="field">
          <label htmlFor="cfg-method" className="eyebrow">Metodologia da configurare</label>
          <select id="cfg-method" className="select-lg" value={m} onChange={(e) => setM(e.target.value as 'waterfall' | 'scrum')}>
            <option value="waterfall">Waterfall</option>
            <option value="scrum">Agile · Scrum</option>
          </select>
          <div className="muted small">Versione salvata: {version === 0 ? 'default dai file del repository' : version}{dirty ? ' · modifiche non salvate' : ''}</div>
        </div>
        <div className="chips">
          <span className={errors.length ? 'status status-err' : 'status status-ok'}>{errors.length ? `${errors.length} da correggere` : 'Configurazione valida'}</span>
          <button type="button" className="btn btn-primary" onClick={save} disabled={!dirty}>Salva configurazione</button>
        </div>
        {message && <div className="alert full" role="status">{message}</div>}
        {errors.length > 0 && <ul className="errors full">{errors.map((e) => <li key={e}>{e}</li>)}</ul>}
      </section>

      <div role="tablist" className="tabs" aria-label="Aree di configurazione">
        {([['slots', 'Responsabili e agenti'], ['roles', 'Ruoli del processo'], ['personas', 'Persone e avatar'], ['tools', 'Connettori'], ['ai', 'Modelli AI']] as const).map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} className={tab === id ? 'tab tab-on' : 'tab'} onClick={() => setTab(id)}>{label}</button>
        ))}
      </div>

      {tab === 'slots' && groups.map((g) => (
        <section key={g.id} className="card">
          <h2>{g.name}</h2>
          {g.agents.map(renderSlot)}
        </section>
      ))}

      {tab === 'roles' && (
        <section className="card">
          <h2>Ruoli del processo</h2>
          <p className="muted small">I ruoli che approvano un gate o sono Accountable devono avere almeno una persona umana.</p>
          {config.roleAssignments.map((r) => (
            <div key={r.role} className="cfg-row">
              <div className="cfg-main">
                <strong>{roleName[r.role]}</strong>
                <div className="cfg-controls">
                  <select aria-label={`Modalità di ${roleName[r.role]}`} value={r.mode}
                    onChange={(e) => update((c) => { c.roleAssignments.find((x) => x.role === r.role)!.mode = e.target.value as typeof r.mode })}>
                    {MODES.map((x) => <option key={x.id} value={x.id}>{x.label}</option>)}
                  </select>
                </div>
              </div>
              <div className="chips">
                {humans.map((h) => (
                  <label key={h.id} className="check">
                    <input type="checkbox" checked={r.personas?.includes(h.id) ?? false} onChange={() => update((c) => {
                      const x = c.roleAssignments.find((y) => y.role === r.role)!
                      const cur = x.personas ?? []
                      x.personas = cur.includes(h.id) ? cur.filter((i) => i !== h.id) : [...cur, h.id]
                    })} />
                    {h.name}
                  </label>
                ))}
              </div>
            </div>
          ))}
        </section>
      )}

      {tab === 'personas' && (
        <section className="card">
          <div className="row-between">
            <h2>Persone e avatar</h2>
            <div className="chips">
              <button type="button" className="btn" onClick={() => addPersona('human')}>Nuova persona umana</button>
              <button type="button" className="btn" onClick={() => addPersona('avatar')}>Nuovo avatar</button>
            </div>
          </div>
          <div className="grid">
            {personaCards.map(({ p, i }) => (
              <div key={p.id} className={`persona-card persona-card-${p.kind}`}>
                <div className="persona-head">
                  <Avatar kind={p.kind} face={p.face} size={48} />
                  <div><TypeTag kind={p.kind} /> <span className="muted small">usato in {usage(p.id)} assegnazioni</span></div>
                </div>
                <label className="field">Nome sul badge
                  <input value={p.name} onChange={(e) => update((c) => { c.personas[i].name = e.target.value })} />
                </label>
                <label className="field">Titolo
                  <input value={p.title} onChange={(e) => update((c) => { c.personas[i].title = e.target.value })} />
                </label>
                <label className="field">{p.kind === 'human' ? 'Email' : "Email dell'utente tecnico"}
                  <input type="email" value={p.email ?? ''} placeholder={p.kind === 'human' ? 'nome@azienda.it' : 'agente@azienda.it'}
                    onChange={(e) => update((c) => { c.personas[i].email = e.target.value })} />
                </label>
              </div>
            ))}
          </div>
        </section>
      )}

      {tab === 'ai' && (
        <>
          <LlmCatalogEditor onSaved={setLlm} />
          <section className="card">
            <h2>Preset degli agenti</h2>
            <p className="muted small">
              Valgono per questa metodologia e si salvano con «Salva configurazione». Le scelte sono i modelli attivi
              dell'ultima versione salvata dei modelli; il modello di riserva si usa se il principale non risponde.
            </p>
            {config.agentPresets.filter((p) => p.kind === 'llm-agent').map((p) => {
              const known = (v?: string) => !v || modelOptions.some((o) => o.id === v)
              return (
                <div key={p.id} className="cfg-row">
                  <div className="cfg-main">
                    <div>
                      <strong>{p.name}</strong>
                      <div className="muted small">{p.runtime} · usato da {config.slotAssignments.filter((s) => s.preset === p.id).length} slot</div>
                    </div>
                  </div>
                  <div className="connector-fields">
                    <label className="field">Modello
                      <select value={p.model ?? ''} onChange={(e) => setPreset(p.id, (x) => { x.model = e.target.value })}>
                        {!known(p.model) && <option value={p.model}>{p.model} (non disponibile)</option>}
                        {modelOptions.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
                      </select>
                    </label>
                    <label className="field">Modello di riserva
                      <select value={p.fallbackModel ?? ''} onChange={(e) => setPreset(p.id, (x) => {
                        if (e.target.value) x.fallbackModel = e.target.value
                        else delete x.fallbackModel
                      })}>
                        <option value="">— nessuno —</option>
                        {!known(p.fallbackModel) && <option value={p.fallbackModel}>{p.fallbackModel} (non disponibile)</option>}
                        {modelOptions.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
                      </select>
                    </label>
                    <label className="field">Temperatura
                      <input type="number" min={0} max={2} step={0.1} value={p.temperature ?? 0.2}
                        onChange={(e) => setPreset(p.id, (x) => { x.temperature = Number(e.target.value) })} />
                    </label>
                  </div>
                </div>
              )
            })}
          </section>
        </>
      )}

      {tab === 'tools' && (
        <>
          <section className="card">
            <h2>Strumenti per fase</h2>
            <p className="muted small">Quale connettore usiamo per ogni funzione e dove salviamo gli artefatti prodotti in ogni fase.</p>
            <div className="binding-table">
              {BINDINGS.map(([k, label, required]) => (
                <label key={k} className="field">{label}
                  <select value={config.bindings[k] ?? ''} onChange={(e) => update((c) => {
                    if (e.target.value) c.bindings[k] = e.target.value
                    else if (!required) delete c.bindings[k]
                  })}>
                    {!required && <option value="">— nessuno —</option>}
                    {required && !config.bindings[k] && <option value="">— scegli —</option>}
                    {config.connectors.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
                  </select>
                </label>
              ))}
            </div>
            {artifactGroups.map((g) => (
              <div key={g.id} className="stage-tools">
                <div className="eyebrow">{g.name}</div>
                <div className="binding-table">
                  {g.ids.map((a) => (
                    <label key={a} className="field">{artifactName[a]}
                      <select value={config.bindings.artifactStorage?.[a] ?? ''} onChange={(e) => update((c) => {
                        const st = { ...(c.bindings.artifactStorage ?? {}) }
                        if (e.target.value) st[a] = e.target.value
                        else delete st[a]
                        c.bindings.artifactStorage = st
                      })}>
                        <option value="">— nessuno —</option>
                        {config.connectors.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
                      </select>
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </section>

          <section className="card">
            <div className="row-between">
              <h2>Connettori</h2>
              <button type="button" className="btn" onClick={newConnector}>Nuovo connettore</button>
            </div>
            <p className="muted small">
              Gli agenti accedono a questi strumenti con l'utente tecnico del loro avatar (email nella scheda «Persone e avatar»).
              Le credenziali non si salvano qui: indichiamo solo il nome della variabile d'ambiente.
            </p>
            {config.connectors.map((x, i) => (
              <div key={x.id} className="cfg-row">
                <div className="cfg-main">
                  <div>
                    <strong>{x.name}</strong>
                    <div className="muted small">
                      {SPECS[x.system]?.label} · {CATEGORY_LABELS[x.category]} · {x.transport === 'rest' ? 'Connettore standard' : 'Server MCP'} ({MODE_LABELS[x.transport]})
                      {x.readOnly ? ' · sola lettura' : ''}
                    </div>
                    {(x.endpoint || x.settings?.command) && <div className="muted small mono">{x.endpoint || String(x.settings?.command ?? '')}</div>}
                  </div>
                  <div className="chips">
                    <button type="button" className="btn" onClick={() => setEditing({ index: i, connector: x })}>Configura</button>
                    <button type="button" className="btn btn-danger" onClick={() => update((c) => { c.connectors.splice(i, 1) })}>Rimuovi</button>
                  </div>
                </div>
              </div>
            ))}
          </section>

          {editing && (
            <ConnectorDialog key={editing.index ?? 'new'} connector={editing.connector} isNew={editing.index === null}
              onApply={applyConnector} onClose={() => setEditing(null)} />
          )}
        </>
      )}
    </div>
  )
}
