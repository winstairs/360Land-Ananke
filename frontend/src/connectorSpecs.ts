import type { Connector, ConnectorSettings } from './types'

// Parametri sensati per ogni strumento, distinti tra connettore standard (API REST) e server MCP.
// I segreti non si salvano: i campi 'env' contengono solo il nome della variabile d'ambiente.
export type Mode = Connector['transport']
export type FieldKind = 'text' | 'url' | 'select' | 'list' | 'number' | 'env'
export type Field = {
  key: string
  label: string
  kind: FieldKind
  options?: [string, string][]
  placeholder?: string
  help?: string
  required?: boolean
  initial?: string | number | string[]
}
export type AuthOption = { id: string; label: string; help?: string; fields: Field[] }
export type ModeSpec = {
  endpoint?: { label: string; placeholder: string; initial?: string; help?: string }
  auth: AuthOption[]
  fields?: Field[]
  help?: string
}
export type SystemSpec = {
  label: string
  category: Connector['category']
  scope: Field[]
  modes: Partial<Record<Mode, ModeSpec>>
}

export const ENV_NAME = /^[A-Z][A-Z0-9_]*$/

const env = (key: string, label: string, placeholder: string, help?: string): Field => ({ key, label, kind: 'env', placeholder, help, required: true, initial: placeholder })
const TECH_USER = "Vuota: si usa l'email dell'utente tecnico dell'avatar"

const oauthMcp: AuthOption = {
  id: 'oauth', label: "OAuth 2.1 con l'utente tecnico",
  help: "Il consenso si dà una volta accedendo con l'utente tecnico dell'avatar. Il flusso OAuth nella piattaforma è ancora una decisione aperta.", fields: [],
}
const oauth2Rest = (prefix: string): AuthOption => ({
  id: 'oauth2', label: 'OAuth 2.0 (app registrata)',
  fields: [{ key: 'clientId', label: 'Client ID', kind: 'text', required: true }, env('clientSecretEnv', 'Variabile del client secret', `${prefix}_OAUTH_CLIENT_SECRET`)],
})
const bearer = (label: string, placeholder: string, help?: string): AuthOption => ({
  id: 'bearer', label, help, fields: [env('tokenEnv', 'Variabile del token', placeholder)],
})
const atlassianToken = (prefix: string): AuthOption => ({
  id: 'api-token', label: 'Email + API token (Cloud)',
  fields: [{ key: 'username', label: "Email dell'account", kind: 'text', placeholder: 'agente@azienda.it', help: TECH_USER },
    env('tokenEnv', "Variabile dell'API token", `${prefix}_API_TOKEN`)],
})
const allowedTools: Field = { key: 'allowedTools', label: 'Strumenti MCP consentiti', kind: 'list', placeholder: 'tutti', help: 'Nomi separati da virgola; vuoto: tutti quelli esposti dal server' }
const timeout: Field = { key: 'timeoutSeconds', label: 'Timeout (secondi)', kind: 'number', initial: 60 }
const localFields = (command: string, args: string[], envVars: string[]): Field[] => [
  { key: 'command', label: 'Comando', kind: 'text', initial: command, required: true },
  { key: 'args', label: 'Argomenti', kind: 'list', initial: args, help: 'Separati da virgola' },
  { key: 'envVars', label: "Variabili d'ambiente passate al processo", kind: 'list', initial: envVars, help: 'Solo i nomi: i valori stanno nel file .env del worker' },
]
const localAuth: AuthOption[] = [{ id: 'env', label: "Credenziali nelle variabili d'ambiente del processo", fields: [] }]

const atlassian = (prefix: 'JIRA' | 'CONFLUENCE', restPlaceholder: string, apiVersions: [string, string][]): Partial<Record<Mode, ModeSpec>> => ({
  rest: {
    endpoint: { label: 'URL del sito', placeholder: restPlaceholder },
    fields: [
      { key: 'deployment', label: 'Installazione', kind: 'select', options: [['cloud', 'Cloud'], ['data-center', 'Data Center']], initial: 'cloud' },
      { key: 'apiVersion', label: 'Versione API', kind: 'select', options: apiVersions, initial: apiVersions[0][0] },
    ],
    auth: [atlassianToken(prefix), { id: 'pat', label: 'Personal Access Token (Data Center)', fields: [env('tokenEnv', 'Variabile del token', `${prefix}_PAT`)] }, oauth2Rest(prefix)],
  },
  'mcp-remote': {
    endpoint: { label: 'URL del server MCP (Rovo)', placeholder: 'https://mcp.atlassian.com/v2/mcp', initial: 'https://mcp.atlassian.com/v2/mcp', help: 'Stesso server per Jira e Confluence; solo Cloud' },
    fields: [{ key: 'siteUrl', label: 'Sito Atlassian', kind: 'url', placeholder: 'https://azienda.atlassian.net', required: true }, allowedTools, timeout],
    auth: [oauthMcp, { ...atlassianToken(prefix), help: "Richiede che l'amministratore abbia abilitato l'accesso con API token" }],
  },
  'mcp-local': {
    help: 'Server della comunità mcp-atlassian (MIT), funziona anche con Data Center',
    fields: localFields('uvx', ['mcp-atlassian'], [`${prefix}_URL`, `${prefix}_USERNAME`, `${prefix}_API_TOKEN`]),
    auth: localAuth,
  },
})

export const SPECS: Record<Connector['system'], SystemSpec> = {
  jira: {
    label: 'Jira', category: 'work-tracking',
    scope: [
      { key: 'projectKey', label: 'Chiave del progetto', kind: 'text', placeholder: 'ANANKE', required: true },
      { key: 'issueType', label: 'Tipo di issue predefinito', kind: 'text', initial: 'Task' },
      { key: 'jql', label: 'Filtro JQL', kind: 'text', placeholder: 'project = ANANKE AND labels = ananke', help: 'Limita le issue visibili agli agenti' },
    ],
    modes: atlassian('JIRA', 'https://azienda.atlassian.net', [['3', 'v3 (Cloud)'], ['2', 'v2 (Data Center)']]),
  },
  confluence: {
    label: 'Confluence', category: 'knowledge-base',
    scope: [
      { key: 'spaceKey', label: 'Chiave dello spazio', kind: 'text', placeholder: 'ANANKE', required: true },
      { key: 'parentPageId', label: 'Pagina padre (id)', kind: 'text', help: 'I documenti generati si creano sotto questa pagina' },
    ],
    modes: atlassian('CONFLUENCE', 'https://azienda.atlassian.net/wiki', [['v2', 'v2 (Cloud)'], ['v1', 'v1 (Data Center)']]),
  },
  clickup: {
    label: 'ClickUp', category: 'work-tracking',
    scope: [
      { key: 'workspaceId', label: 'Workspace (team id)', kind: 'text', required: true },
      { key: 'spaceId', label: 'Space id', kind: 'text' },
      { key: 'listId', label: 'Lista predefinita (id)', kind: 'text' },
    ],
    modes: {
      rest: {
        endpoint: { label: 'URL API', placeholder: 'https://api.clickup.com/api/v2', initial: 'https://api.clickup.com/api/v2' },
        auth: [bearer('Token personale', 'CLICKUP_API_TOKEN', "Token pk_… dell'utente tecnico"), oauth2Rest('CLICKUP')],
      },
      'mcp-remote': {
        endpoint: { label: 'URL del server MCP', placeholder: 'https://mcp.clickup.com/mcp', initial: 'https://mcp.clickup.com/mcp' },
        fields: [allowedTools, timeout],
        auth: [{ ...oauthMcp, help: `Il server MCP di ClickUp accetta solo OAuth. ${oauthMcp.help}` }],
      },
    },
  },
  plane: {
    label: 'Plane', category: 'work-tracking',
    scope: [
      { key: 'workspaceSlug', label: 'Workspace (slug)', kind: 'text', placeholder: 'ananke', required: true },
      { key: 'projectId', label: 'Progetto (id)', kind: 'text' },
    ],
    modes: {
      rest: {
        endpoint: { label: 'URL API', placeholder: 'https://plane.azienda.it/api/v1', help: 'Plane Cloud: https://api.plane.so/api/v1' },
        auth: [{ id: 'api-key', label: 'Chiave API (intestazione X-API-Key)', fields: [env('tokenEnv', 'Variabile della chiave', 'PLANE_API_KEY')] }],
      },
      'mcp-local': {
        help: 'Server MCP ufficiale di Plane (MIT)',
        fields: localFields('npx', ['-y', '@makeplane/plane-mcp-server'], ['PLANE_API_KEY', 'PLANE_WORKSPACE_SLUG', 'PLANE_API_HOST_URL']),
        auth: localAuth,
      },
    },
  },
  'google-drive': {
    label: 'Google Drive', category: 'file-storage',
    scope: [
      { key: 'sharedDriveId', label: 'Drive condiviso (id)', kind: 'text' },
      { key: 'folderId', label: 'Cartella radice (id)', kind: 'text', help: 'Gli agenti lavorano solo dentro questa cartella' },
    ],
    modes: {
      rest: {
        endpoint: { label: 'URL API', placeholder: 'https://www.googleapis.com/drive/v3', initial: 'https://www.googleapis.com/drive/v3' },
        auth: [
          {
            id: 'service-account', label: 'Service account con delega di dominio',
            fields: [env('keyFileEnv', 'Variabile con il percorso della chiave JSON', 'GOOGLE_APPLICATION_CREDENTIALS'),
              { key: 'subject', label: 'Utente da impersonare', kind: 'text', placeholder: 'agente@azienda.it', help: TECH_USER },
              { key: 'scope', label: 'Ambito OAuth', kind: 'select', options: [['drive.file', 'Solo file creati o aperti (drive.file)'], ['drive', 'Tutto il Drive (drive)']], initial: 'drive.file' }],
          },
          oauth2Rest('GOOGLE'),
        ],
      },
      'mcp-remote': {
        endpoint: { label: 'URL del server MCP', placeholder: 'https://drivemcp.googleapis.com/mcp/v1', initial: 'https://drivemcp.googleapis.com/mcp/v1', help: 'Developer preview di Google Workspace' },
        fields: [allowedTools, timeout],
        auth: [oauthMcp],
      },
    },
  },
  github: {
    label: 'GitHub', category: 'code-hosting',
    scope: [
      { key: 'owner', label: 'Organizzazione o utente', kind: 'text', placeholder: 'azienda', required: true },
      { key: 'repositories', label: 'Repository', kind: 'list', placeholder: 'tutti', help: "Separati da virgola; vuoto: tutti quelli dell'installazione" },
      { key: 'defaultBranch', label: 'Branch predefinito', kind: 'text', initial: 'main' },
    ],
    modes: {
      rest: {
        endpoint: { label: 'URL API', placeholder: 'https://api.github.com', initial: 'https://api.github.com', help: 'GitHub Enterprise Server: https://github.azienda.it/api/v3' },
        auth: [
          {
            id: 'github-app', label: 'GitHub App (consigliata)',
            fields: [{ key: 'appId', label: 'App ID', kind: 'text', required: true }, { key: 'installationId', label: 'Installation ID', kind: 'text', required: true },
              env('privateKeyEnv', 'Variabile della chiave privata', 'GITHUB_APP_PRIVATE_KEY')],
          },
          bearer('Token fine-grained', 'GITHUB_TOKEN'),
        ],
      },
      'mcp-remote': {
        endpoint: { label: 'URL del server MCP', placeholder: 'https://api.githubcopilot.com/mcp/', initial: 'https://api.githubcopilot.com/mcp/' },
        fields: [{ key: 'toolsets', label: 'Toolset', kind: 'list', initial: ['repos', 'issues', 'pull_requests'], help: 'Ad esempio repos, issues, pull_requests, actions, code_security' }, timeout],
        auth: [oauthMcp, bearer('Token fine-grained', 'GITHUB_PAT')],
      },
      'mcp-local': {
        help: 'Server MCP ufficiale di GitHub (MIT) in container',
        fields: [...localFields('docker', ['run', '-i', '--rm', '-e', 'GITHUB_PERSONAL_ACCESS_TOKEN', 'ghcr.io/github/github-mcp-server'], ['GITHUB_PERSONAL_ACCESS_TOKEN']),
          { key: 'toolsets', label: 'Toolset', kind: 'list', initial: ['repos', 'issues', 'pull_requests'] }],
        auth: localAuth,
      },
    },
  },
  gitlab: {
    label: 'GitLab', category: 'code-hosting',
    scope: [
      { key: 'group', label: 'Gruppo', kind: 'text', placeholder: 'azienda' },
      { key: 'projectPath', label: 'Progetto', kind: 'text', placeholder: 'azienda/ananke', required: true },
      { key: 'defaultBranch', label: 'Branch predefinito', kind: 'text', initial: 'main' },
    ],
    modes: {
      rest: {
        endpoint: { label: 'URL API', placeholder: 'https://gitlab.com/api/v4', initial: 'https://gitlab.com/api/v4', help: 'Self-managed: https://gitlab.azienda.it/api/v4' },
        auth: [bearer('Token di progetto o personale', 'GITLAB_TOKEN'), oauth2Rest('GITLAB')],
      },
      'mcp-remote': {
        endpoint: { label: 'URL del server MCP', placeholder: 'https://gitlab.com/api/v4/mcp', initial: 'https://gitlab.com/api/v4/mcp', help: 'Server MCP integrato in GitLab, anche self-managed' },
        fields: [allowedTools, timeout],
        auth: [oauthMcp],
      },
    },
  },
  slack: {
    label: 'Slack', category: 'communication',
    scope: [
      { key: 'defaultChannel', label: 'Canale predefinito', kind: 'text', placeholder: '#ananke' },
      { key: 'channels', label: 'Canali consentiti', kind: 'list', help: 'Separati da virgola' },
    ],
    modes: {
      rest: {
        endpoint: { label: 'URL API', placeholder: 'https://slack.com/api', initial: 'https://slack.com/api' },
        auth: [bearer('Bot token (xoxb-…)', 'SLACK_BOT_TOKEN')],
      },
      'mcp-remote': {
        endpoint: { label: 'URL del server MCP', placeholder: 'https://mcp.slack.com/mcp', initial: 'https://mcp.slack.com/mcp' },
        fields: [allowedTools, timeout],
        auth: [oauthMcp],
      },
    },
  },
  other: {
    label: 'Altro', category: 'work-tracking',
    scope: [],
    modes: {
      rest: {
        endpoint: { label: 'URL API', placeholder: 'https://…' },
        auth: [
          { id: 'none', label: 'Nessuna', fields: [] },
          bearer('Token Bearer', 'SERVICE_TOKEN'),
          { id: 'basic', label: 'Utente e password (Basic)', fields: [{ key: 'username', label: 'Utente', kind: 'text', required: true }, env('passwordEnv', 'Variabile della password', 'SERVICE_PASSWORD')] },
          { id: 'api-key', label: 'Chiave API in intestazione', fields: [{ key: 'headerName', label: 'Intestazione', kind: 'text', initial: 'X-API-Key', required: true }, env('tokenEnv', 'Variabile della chiave', 'SERVICE_API_KEY')] },
        ],
      },
      'mcp-remote': {
        endpoint: { label: 'URL del server MCP', placeholder: 'https://…/mcp' },
        fields: [allowedTools, timeout],
        auth: [oauthMcp, bearer('Token Bearer', 'SERVICE_TOKEN'), { id: 'none', label: 'Nessuna', fields: [] }],
      },
      'mcp-local': { fields: localFields('', [], []), auth: localAuth },
    },
  },
}

export const MODE_LABELS: Record<Mode, string> = { rest: 'API REST', 'mcp-remote': 'MCP remoto', 'mcp-local': 'MCP locale' }

export function modeSpec(c: Connector): ModeSpec | undefined {
  return SPECS[c.system].modes[c.transport]
}

export function authOf(c: Connector): AuthOption | undefined {
  const m = modeSpec(c)
  return m?.auth.find((a) => a.id === c.settings?.auth) ?? m?.auth[0]
}

/** Campi visibili per sistema, tipo di collegamento e autenticazione scelti. */
export function fieldsOf(c: Connector): Field[] {
  const m = modeSpec(c)
  return [...SPECS[c.system].scope, ...(m?.fields ?? []), ...(authOf(c)?.fields ?? [])]
}

/** Porta un connettore sul sistema e tipo indicati, proponendo i default senza perdere i valori già inseriti. */
export function retarget(c: Connector, system: Connector['system'], transport: Mode): Connector {
  const prev = modeSpec(c)
  const next: Connector = { ...c, system, transport, settings: { ...(c.settings ?? {}) } }
  if (system !== c.system) next.category = SPECS[system].category
  const m = modeSpec(next)
  if (!m) return next
  const s = next.settings as ConnectorSettings
  if (!c.endpoint || c.endpoint === prev?.endpoint?.initial || transport !== c.transport) next.endpoint = m.endpoint?.initial ?? ''
  // Atlassian: l'URL del sito passa tra l'endpoint REST e il campo siteUrl del server MCP
  if (system === c.system && transport !== c.transport) {
    if (transport === 'rest' && !next.endpoint && typeof s.siteUrl === 'string') next.endpoint = s.siteUrl
    if (c.transport === 'rest' && c.endpoint && m.fields?.some((f) => f.key === 'siteUrl') && !s.siteUrl) s.siteUrl = c.endpoint
  }
  if (!m.auth.some((a) => a.id === s.auth)) s.auth = m.auth[0].id
  for (const f of fieldsOf(next)) if (s[f.key] === undefined && f.initial !== undefined) s[f.key] = f.initial
  return next
}

/** Tiene solo i parametri dei campi visibili, così non restano valori di un'altra modalità. */
export function prune(c: Connector): Connector {
  const keep = new Set(['auth', ...fieldsOf(c).map((f) => f.key)])
  const settings = Object.fromEntries(Object.entries(c.settings ?? {}).filter(([k, v]) => keep.has(k) && v !== '' && !(Array.isArray(v) && v.length === 0)))
  const out: Connector = { ...c, settings }
  if (c.transport === 'mcp-local') delete out.endpoint
  return out
}

/** Errori di formato mostrati nel popup; la validazione definitiva resta lato server. */
export function fieldErrors(c: Connector): Record<string, string> {
  const e: Record<string, string> = {}
  const s = c.settings ?? {}
  const m = modeSpec(c)
  if (!c.name.trim()) e.name = 'Indica un nome'
  if (m?.endpoint && !/^https?:\/\/\S+$/.test(c.endpoint ?? '')) e.endpoint = 'Indirizzo http(s) obbligatorio'
  for (const f of fieldsOf(c)) {
    const v = s[f.key]
    const empty = v === undefined || v === '' || (Array.isArray(v) && v.length === 0)
    if (f.required && empty) e[f.key] = 'Obbligatorio'
    else if (!empty && f.kind === 'env' && !ENV_NAME.test(String(v))) e[f.key] = 'Solo maiuscole, cifre e _ (es. JIRA_API_TOKEN)'
    else if (!empty && f.kind === 'url' && !/^https?:\/\/\S+$/.test(String(v))) e[f.key] = 'Indirizzo http(s) non valido'
    else if (f.key === 'envVars' && Array.isArray(v) && v.some((n) => !ENV_NAME.test(n))) e[f.key] = 'Solo nomi di variabili (maiuscole, cifre e _)'
  }
  return e
}
