import { useEffect, useState } from 'react'
import { api, ApiError } from '../api'
import type { GatewayStatus, LlmCatalog, LlmProvider } from '../types'

const KINDS: [LlmProvider['kind'], string][] = [['anthropic', 'Claude (Anthropic)'], ['openai', 'OpenAI'],
  ['openai-compatible', 'API compatibile OpenAI'], ['vllm', 'vLLM'], ['ollama', 'Ollama']]

// Modelli già compilati per «Nuovo provider»: l'utente completa indirizzo, chiave e modelli
const TEMPLATES: { label: string; make: () => Omit<LlmProvider, 'id'> & { slug: string } }[] = [
  { label: 'Claude (Anthropic)', make: () => ({ slug: 'anthropic', name: 'Claude (Anthropic)', kind: 'anthropic', deployment: 'cloud', apiKeyEnv: 'ANTHROPIC_API_KEY', enabled: true,
    models: [{ alias: '', upstream: '', family: 'claude', license: 'proprietary' }] }) },
  { label: 'OpenAI', make: () => ({ slug: 'openai', name: 'OpenAI', kind: 'openai', deployment: 'cloud', apiKeyEnv: 'OPENAI_API_KEY', enabled: true,
    models: [{ alias: '', upstream: '', family: 'gpt', license: 'proprietary' }] }) },
  { label: 'Server proprio con vLLM (es. Hetzner)', make: () => ({ slug: 'vllm', name: 'Server GPU (vLLM)', kind: 'vllm', deployment: 'self-hosted', host: 'Hetzner',
    baseUrl: 'https://<server>/v1', apiKeyEnv: 'HETZNER_LLM_API_KEY', enabled: true, models: [{ alias: '', upstream: '', family: '' }] }) },
  { label: 'Ollama', make: () => ({ slug: 'ollama', name: 'Ollama', kind: 'ollama', deployment: 'self-hosted', baseUrl: 'http://ollama:11434', enabled: true,
    models: [{ alias: '', upstream: '', family: '' }] }) },
  { label: 'API compatibile OpenAI', make: () => ({ slug: 'openai-compatible', name: 'Provider compatibile OpenAI', kind: 'openai-compatible', deployment: 'cloud',
    baseUrl: 'https://<provider>/v1', apiKeyEnv: 'OPEN_CLOUD_API_KEY', enabled: true, models: [{ alias: '', upstream: '', family: '' }] }) },
]

const SYNC_LABEL = { ok: 'Sincronizzato', error: 'Errore', skipped: 'Non attivo' } as const

/** Provider e modelli LLM della piattaforma: condivisi da tutte le metodologie, salvati a parte. */
export function LlmCatalogEditor({ onSaved }: { onSaved?: (catalog: LlmCatalog) => void }) {
  const [llm, setLlm] = useState<LlmCatalog | null>(null)
  const [version, setVersion] = useState(0)
  const [dirty, setDirty] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const [message, setMessage] = useState('')
  const [open, setOpen] = useState('')
  const [template, setTemplate] = useState(0)
  const [status, setStatus] = useState<GatewayStatus | null>(null)

  const loadStatus = () => api.gatewayStatus().then(setStatus).catch(() => undefined)

  useEffect(() => {
    api.llmCatalog().then((r) => { setLlm(r.catalog); setVersion(r.version) }).catch((e) => setMessage(String(e)))
    loadStatus()
  }, [])

  // Validazione lato server: controlla anche che le configurazioni di tutte le metodologie restino valide
  useEffect(() => {
    if (!llm || !dirty) return
    const t = setTimeout(() => api.validateLlmCatalog(llm).then((r) => setErrors(r.errors)).catch(() => undefined), 400)
    return () => clearTimeout(t)
  }, [llm, dirty])

  if (!llm) return <section className="card">{message || 'Caricamento dei modelli…'}</section>

  const update = (fn: (c: LlmCatalog) => void) => {
    setLlm((c) => {
      if (!c) return c
      const next = structuredClone(c)
      fn(next)
      return next
    })
    setDirty(true); setMessage('')
  }
  const setProvider = (i: number, fn: (p: LlmProvider) => void) => update((c) => { fn(c.providers[i]) })

  const save = async () => {
    try {
      const r = await api.saveLlmCatalog(llm)
      setVersion(r.version); setDirty(false); setErrors([]); setMessage(r.message)
      onSaved?.(llm)
      loadStatus()
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) {
        setErrors((e.detail as { errors?: string[] }).errors ?? []); setMessage('Salvataggio bloccato: correggi gli errori elencati.')
      } else setMessage(String(e))
    }
  }

  const addProvider = () => {
    const { slug, ...p } = TEMPLATES[template].make()
    let n = 1
    while (llm.providers.some((x) => x.id === `${slug}-${n}`)) n++
    const id = `${slug}-${n}`
    update((c) => { c.providers.push({ ...p, id, models: p.models.map((m) => ({ ...m, alias: `${id}-model` })) }) })
    setOpen(id)
  }

  const last = status?.lastSync

  return (
    <>
      <section className="card">
        <div className="row-between">
          <div>
            <h2>Provider e modelli</h2>
            <p className="muted small">
              Condivisi da tutte le metodologie. Il worker li pubblica sul gateway; le chiavi restano nel file <span className="mono">.env</span>:
              qui indichiamo solo il nome della variabile.
            </p>
          </div>
          <div className="chips">
            <span className={errors.length ? 'status status-err' : 'status status-ok'}>{errors.length ? `${errors.length} da correggere` : 'Modelli validi'}</span>
            <button type="button" className="btn btn-primary" onClick={save} disabled={!dirty}>Salva modelli</button>
          </div>
        </div>
        <div className="muted small">Versione salvata: {version === 0 ? 'default dai file del repository' : version}{dirty ? ' · modifiche non salvate' : ''}</div>
        {message && <div className="alert" role="status">{message}</div>}
        {errors.length > 0 && <ul className="errors">{errors.map((e) => <li key={e}>{e}</li>)}</ul>}

        {llm.providers.map((p, i) => {
          const isOpen = open === p.id
          const active = p.enabled ?? true
          return (
            <div key={p.id} className={`cfg-row${active ? '' : ' cfg-off'}`}>
              <div className="cfg-main">
                <button type="button" className="link-btn" aria-expanded={isOpen} onClick={() => setOpen(isOpen ? '' : p.id)}>
                  <strong>{p.name}</strong>
                  <span className="muted small">
                    {KINDS.find(([v]) => v === p.kind)?.[1]} · {p.deployment === 'cloud' ? 'cloud' : 'self-hosted'}{p.host ? ` · ${p.host}` : ''}
                    {' · '}{p.models.length} {p.models.length === 1 ? 'modello' : 'modelli'}{active ? '' : ' · disattivato'}
                  </span>
                </button>
                <div className="cfg-controls">
                  <label className="check">
                    <input type="checkbox" checked={active} onChange={() => setProvider(i, (x) => { x.enabled = !active })} /> Attivo
                  </label>
                  <button type="button" className="btn btn-danger" onClick={() => update((c) => { c.providers.splice(i, 1) })}>Rimuovi</button>
                </div>
              </div>
              {isOpen && (
                <div className="cfg-detail">
                  <div className="connector-fields">
                    <label className="field">Nome
                      <input value={p.name} onChange={(e) => setProvider(i, (x) => { x.name = e.target.value })} />
                    </label>
                    <label className="field">Tipo
                      <select value={p.kind} onChange={(e) => setProvider(i, (x) => { x.kind = e.target.value as LlmProvider['kind'] })}>
                        {KINDS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                      </select>
                    </label>
                    <label className="field">Dove gira
                      <select value={p.deployment} onChange={(e) => setProvider(i, (x) => { x.deployment = e.target.value as LlmProvider['deployment'] })}>
                        <option value="cloud">Servizio cloud</option>
                        <option value="self-hosted">Server nostro (self-hosted)</option>
                      </select>
                    </label>
                    <label className="field">Host
                      <input value={p.host ?? ''} placeholder="es. Hetzner GEX44" onChange={(e) => setProvider(i, (x) => { x.host = e.target.value })} />
                    </label>
                    <label className="field">Indirizzo dell'API
                      <input className="mono" value={p.baseUrl ?? ''} placeholder={p.kind === 'anthropic' || p.kind === 'openai' ? 'quello del servizio' : 'https://…/v1'}
                        onChange={(e) => setProvider(i, (x) => { if (e.target.value) x.baseUrl = e.target.value; else delete x.baseUrl })} />
                    </label>
                    <label className="field">Variabile della chiave API
                      <input className="mono" value={p.apiKeyEnv ?? ''} placeholder="es. OPENAI_API_KEY"
                        onChange={(e) => setProvider(i, (x) => { if (e.target.value) x.apiKeyEnv = e.target.value.toUpperCase(); else delete x.apiKeyEnv })} />
                    </label>
                  </div>
                  <label className="field">Note
                    <textarea rows={2} value={p.notes ?? ''} onChange={(e) => setProvider(i, (x) => { x.notes = e.target.value })} />
                  </label>
                  <div className="eyebrow">Modelli</div>
                  {p.models.map((m, j) => (
                    <div key={j} className="model-row">
                      <label className="field">Nome nel gateway (alias)
                        <input className="mono" value={m.alias} onChange={(e) => setProvider(i, (x) => { x.models[j].alias = e.target.value })} />
                      </label>
                      <label className="field">Modello presso il provider
                        <input className="mono" value={m.upstream} placeholder="es. claude-sonnet-5-5" onChange={(e) => setProvider(i, (x) => { x.models[j].upstream = e.target.value })} />
                      </label>
                      <label className="field">Famiglia
                        <input value={m.family} placeholder="es. claude, gpt, qwen" onChange={(e) => setProvider(i, (x) => { x.models[j].family = e.target.value })} />
                      </label>
                      <label className="field">Licenza
                        <input value={m.license ?? ''} onChange={(e) => setProvider(i, (x) => { x.models[j].license = e.target.value })} />
                      </label>
                      <div className="cfg-controls">
                        <label className="check">
                          <input type="checkbox" checked={m.enabled ?? true} onChange={() => setProvider(i, (x) => { x.models[j].enabled = !(m.enabled ?? true) })} /> Attivo
                        </label>
                        <button type="button" className="btn btn-danger" disabled={p.models.length === 1}
                          onClick={() => setProvider(i, (x) => { x.models.splice(j, 1) })}>Rimuovi</button>
                      </div>
                    </div>
                  ))}
                  <div>
                    <button type="button" className="btn" onClick={() => setProvider(i, (x) => {
                      x.models.push({ alias: `${x.id}-model-${x.models.length + 1}`, upstream: '', family: x.models[0]?.family ?? '' })
                    })}>Aggiungi modello</button>
                  </div>
                  <p className="muted small">La famiglia serve alla regola di revisione: chi revisiona deve usare una famiglia diversa da chi produce.</p>
                </div>
              )}
            </div>
          )
        })}

        <div className="cfg-controls">
          <label className="sr-only" htmlFor="llm-template">Tipo di provider da aggiungere</label>
          <select id="llm-template" value={template} onChange={(e) => setTemplate(Number(e.target.value))}>
            {TEMPLATES.map((t, i) => <option key={t.label} value={i}>{t.label}</option>)}
          </select>
          <button type="button" className="btn" onClick={addProvider}>Nuovo provider</button>
        </div>
      </section>

      <section className="card">
        <div className="row-between">
          <h2>Stato del gateway</h2>
          <button type="button" className="btn" onClick={loadStatus}>Aggiorna</button>
        </div>
        {status && (
          <>
            <div className="muted small">
              Modalità agenti: {status.llmMode === 'live' ? 'modelli reali' : 'simulazione'} · il worker sincronizza ogni {status.syncMinutes} minuti
            </div>
            {last ? (
              <div className={last.status === 'error' ? 'alert alert-error' : 'alert'} role="status">
                <strong>{SYNC_LABEL[last.status]}</strong> · versione {last.catalogVersion} · {new Date(last.checkedAt).toLocaleString('it-IT')}
                <div>{last.detail}</div>
                {last.status === 'ok' && last.catalogVersion !== status.catalogVersion && (
                  <div>La versione {status.catalogVersion} sarà applicata alla prossima sincronizzazione.</div>
                )}
              </div>
            ) : (
              <div className="alert">Nessuna sincronizzazione ancora eseguita.</div>
            )}
          </>
        )}
      </section>
    </>
  )
}
