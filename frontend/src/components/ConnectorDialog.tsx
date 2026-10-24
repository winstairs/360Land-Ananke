import { useEffect, useRef, useState } from 'react'
import { authOf, fieldErrors, MODE_LABELS, modeSpec, prune, retarget, SPECS, type Field, type Mode } from '../connectorSpecs'
import type { Connector } from '../types'

type Props = { connector: Connector; isNew: boolean; onApply: (c: Connector) => void; onClose: () => void }

const CATEGORIES: [Connector['category'], string][] = [['work-tracking', 'Gestione del lavoro'], ['knowledge-base', 'Documentazione'],
  ['file-storage', 'Archivio file'], ['code-hosting', 'Codice'], ['communication', 'Comunicazione']]
const STATUSES: [NonNullable<Connector['status']>, string][] = [['ga', 'Stabile'], ['preview', 'Anteprima'], ['community', 'Comunità']]

/** Popup di configurazione di un connettore: lavora su una bozza e la applica solo con «Applica». */
export function ConnectorDialog({ connector, isNew, onApply, onClose }: Props) {
  const ref = useRef<HTMLDialogElement>(null)
  const [d, setD] = useState<Connector>(() => retarget(connector, connector.system, connector.transport))
  const [touched, setTouched] = useState(false)

  // Il dialog nativo gestisce focus, Esc e sfondo; si chiude da solo quando il componente viene smontato
  useEffect(() => {
    const el = ref.current
    if (el && !el.open) el.showModal()
  }, [])

  const spec = SPECS[d.system]
  const mode = modeSpec(d)
  const auth = authOf(d)
  const errors = fieldErrors(d)
  const invalid = Object.keys(errors).length > 0
  const isMcp = d.transport !== 'rest'
  const mcpModes = (['mcp-remote', 'mcp-local'] as Mode[]).filter((x) => spec.modes[x])
  const set = (fn: (c: Connector) => void) => setD((c) => { const n = structuredClone(c); fn(n); return n })
  const setSetting = (k: string, v: string | number | string[] | undefined) => set((c) => {
    c.settings = { ...(c.settings ?? {}) }
    if (v === undefined) delete c.settings[k]
    else c.settings[k] = v
  })
  const err = (k: string) => (touched && errors[k] ? <span className="err small">{errors[k]}</span> : null)
  const id = (k: string) => `cn-${k}`

  const renderField = (f: Field) => {
    const v = d.settings?.[f.key]
    const help = f.help && <span className="muted small">{f.help}</span>
    const label = <span>{f.label}{f.required && <span aria-hidden="true"> *</span>}</span>
    if (f.kind === 'select') {
      return (
        <label key={f.key} className="field">{label}
          <select value={String(v ?? f.initial ?? '')} onChange={(e) => setSetting(f.key, e.target.value)}>
            {f.options?.map(([o, l]) => <option key={o} value={o}>{l}</option>)}
          </select>
          {help}
        </label>
      )
    }
    const text = Array.isArray(v) ? v.join(', ') : v === undefined ? '' : String(v)
    return (
      <label key={f.key} className="field">{label}
        <input id={id(f.key)} className={f.kind === 'env' || f.kind === 'url' ? 'mono' : undefined} value={text}
          type={f.kind === 'number' ? 'number' : 'text'} placeholder={f.placeholder} aria-invalid={touched && !!errors[f.key]}
          onChange={(e) => {
            const raw = e.target.value
            if (f.kind === 'list') setSetting(f.key, raw.split(',').map((x) => x.trim()).filter(Boolean))
            else if (f.kind === 'number') setSetting(f.key, raw === '' ? undefined : Number(raw))
            else setSetting(f.key, f.kind === 'env' ? raw.toUpperCase() : raw)
          }} />
        {help}
        {err(f.key)}
      </label>
    )
  }

  const apply = () => {
    setTouched(true)
    if (!invalid) onApply(prune(d))
  }

  return (
    <dialog ref={ref} className="modal" aria-labelledby="cn-title" onClose={onClose}>
      <form method="dialog" className="modal-body" onSubmit={(e) => { e.preventDefault(); apply() }}>
        <div className="row-between">
          <h2 id="cn-title">{isNew ? 'Nuovo connettore' : `Configura ${connector.name}`}</h2>
          <span className="muted small mono">{d.id}</span>
        </div>

        <fieldset className="modal-section">
          <legend className="eyebrow">Generale</legend>
          <div className="connector-fields">
            <label className="field">Nome
              <input value={d.name} onChange={(e) => set((c) => { c.name = e.target.value })} />
              {err('name')}
            </label>
            <label className="field">Strumento
              <select value={d.system} onChange={(e) => {
                const sys = e.target.value as Connector['system']
                const modes = SPECS[sys].modes
                setD((c) => retarget(c, sys, modes[c.transport] ? c.transport : (Object.keys(modes)[0] as Mode)))
              }}>
                {Object.entries(SPECS).map(([v, s]) => <option key={v} value={v}>{s.label}</option>)}
              </select>
            </label>
            <label className="field">Uso
              <select value={d.category} onChange={(e) => set((c) => { c.category = e.target.value as Connector['category'] })}>
                {CATEGORIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>
            <label className="field">Maturità
              <select value={d.status ?? ''} onChange={(e) => set((c) => {
                if (e.target.value) c.status = e.target.value as Connector['status']
                else delete c.status
              })}>
                <option value="">— non indicata —</option>
                {STATUSES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>
          </div>
          <label className="check">
            <input type="checkbox" checked={d.readOnly ?? false} onChange={() => set((c) => { c.readOnly = !d.readOnly })} />
            Sola lettura: gli agenti non possono scrivere su questo strumento
          </label>
        </fieldset>

        <fieldset className="modal-section">
          <legend className="eyebrow">Tipo di connettore</legend>
          <div className="seg" role="radiogroup" aria-label="Tipo di connettore">
            <button type="button" role="radio" aria-checked={!isMcp} className={!isMcp ? 'seg-on' : ''} disabled={!spec.modes.rest}
              onClick={() => setD((c) => retarget(c, c.system, 'rest'))}>
              <strong>Connettore standard</strong><span className="small">API REST dello strumento</span>
            </button>
            <button type="button" role="radio" aria-checked={isMcp} className={isMcp ? 'seg-on' : ''} disabled={mcpModes.length === 0}
              onClick={() => { if (!isMcp) setD((c) => retarget(c, c.system, mcpModes[0])) }}>
              <strong>Server MCP</strong><span className="small">Strumenti esposti con Model Context Protocol</span>
            </button>
          </div>
          {isMcp && mcpModes.length > 1 && (
            <div className="chips" role="radiogroup" aria-label="Dove gira il server MCP">
              {mcpModes.map((x) => (
                <label key={x} className="check">
                  <input type="radio" name="mcp-mode" checked={d.transport === x} onChange={() => setD((c) => retarget(c, c.system, x))} />
                  {x === 'mcp-remote' ? 'Remoto (HTTP, gestito dal fornitore)' : 'Locale (processo avviato dal worker)'}
                </label>
              ))}
            </div>
          )}
          {mode?.help && <p className="muted small">{mode.help}</p>}
        </fieldset>

        {mode && (
          <fieldset className="modal-section">
            <legend className="eyebrow">Collegamento · {MODE_LABELS[d.transport]}</legend>
            <div className="connector-fields">
              {mode.endpoint && (
                <label className="field"><span>{mode.endpoint.label}<span aria-hidden="true"> *</span></span>
                  <input className="mono" value={d.endpoint ?? ''} placeholder={mode.endpoint.placeholder} aria-invalid={touched && !!errors.endpoint}
                    onChange={(e) => set((c) => { c.endpoint = e.target.value })} />
                  {mode.endpoint.help && <span className="muted small">{mode.endpoint.help}</span>}
                  {err('endpoint')}
                </label>
              )}
              {mode.fields?.map(renderField)}
            </div>
          </fieldset>
        )}

        {mode && (
          <fieldset className="modal-section">
            <legend className="eyebrow">Autenticazione</legend>
            {mode.auth.length > 1 ? (
              <label className="field">Metodo
                <select value={auth?.id} onChange={(e) => setD((c) => retarget({ ...c, settings: { ...c.settings, auth: e.target.value } }, c.system, c.transport))}>
                  {mode.auth.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
                </select>
              </label>
            ) : <div className="small"><strong>{auth?.label}</strong></div>}
            {auth?.help && <p className="muted small">{auth.help}</p>}
            {auth && auth.fields.length > 0 && <div className="connector-fields">{auth.fields.map(renderField)}</div>}
            <p className="muted small">I segreti non si salvano qui: indichiamo solo il nome della variabile d'ambiente che li contiene.</p>
          </fieldset>
        )}

        {spec.scope.length > 0 && (
          <fieldset className="modal-section">
            <legend className="eyebrow">Ambito di lavoro degli agenti</legend>
            <div className="connector-fields">{spec.scope.map(renderField)}</div>
          </fieldset>
        )}

        <label className="field">Note
          <textarea rows={2} value={d.notes ?? ''} onChange={(e) => set((c) => { c.notes = e.target.value })} />
        </label>

        {touched && invalid && <div className="alert alert-error" role="alert">Completa i campi segnalati prima di applicare.</div>}
        <div className="modal-actions">
          <button type="button" className="btn" onClick={() => ref.current?.close()}>Annulla</button>
          <button type="submit" className="btn btn-primary">Applica</button>
        </div>
      </form>
    </dialog>
  )
}
