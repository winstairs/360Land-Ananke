import { useEffect, useState } from 'react'
import { api } from './api'
import { Config } from './pages/Config'
import { Console } from './pages/Console'

export function App() {
  const [view, setView] = useState<'console' | 'config'>('console')
  const [mode, setMode] = useState('')

  useEffect(() => {
    api.health().then((h) => setMode(h.llmMode)).catch(() => setMode('non raggiungibile'))
  }, [])

  return (
    <>
      <header className="topbar">
        <div className="brand">
          <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">
            <rect x="2" y="2" width="10" height="10" rx="2" fill="#F5F4EF" /><rect x="16" y="2" width="10" height="10" rx="2" fill="#8C9BF0" />
            <rect x="2" y="16" width="10" height="10" rx="2" fill="#8C9BF0" /><rect x="16" y="16" width="10" height="10" rx="2" fill="#F5F4EF" />
          </svg>
          <div>
            <div className="brand-name">Ananke</div>
            <div className="brand-sub">Orchestrazione SDLC · agenti: {mode === 'mock' ? 'simulazione (nessuna chiamata ai modelli)' : mode || '…'}</div>
          </div>
        </div>
        <nav aria-label="Sezioni" className="nav">
          <button type="button" className={view === 'console' ? 'nav-on' : ''} aria-current={view === 'console' ? 'page' : undefined} onClick={() => setView('console')}>Console</button>
          <button type="button" className={view === 'config' ? 'nav-on' : ''} aria-current={view === 'config' ? 'page' : undefined} onClick={() => setView('config')}>Configurazione</button>
        </nav>
      </header>
      <main>{view === 'console' ? <Console /> : <Config />}</main>
    </>
  )
}
