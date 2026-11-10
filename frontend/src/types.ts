export type Face = { skin?: string; hair?: string; shirt?: string; longHair?: boolean }

export type PersonaCard = {
  id: string
  kind: 'human' | 'avatar'
  name: string
  title: string
  face: Face
}

export type Project = {
  id: string
  name: string
  client: string
  methodology: 'waterfall' | 'scrum'
  methodologyLabel: string
  currentStage: string
  currentStageName: string
  stageStartedAt: string
  sprint: number | null
}

export type Stage = {
  id: string
  name: string
  kind: string
  status: 'done' | 'active' | 'future' | 'continuous'
  timebox: string | null
  iterative: boolean
  gate: string | null
}

export type Gate = {
  stage: string
  stageName: string
  id: string
  name: string
  criteria: string[]
  approvers: (PersonaCard & { role: string })[]
  targets: { id: string; name: string }[]
}

export type ProjectDetail = Project & { stages: Stage[]; gate: Gate | null }

export type RaciPerson = PersonaCard & { roles: string[]; slots: string[] }
export type RaciColumn = { letter: string; label: string; people: RaciPerson[] }

export type Task = {
  id: string
  name: string
  cron: string
  enabled: boolean
  action: string
  activeInCurrentStage: boolean
  nextRun: string | null
}

export type SlotDetail = {
  slot: string
  agentName: string
  stage: string | null
  stageName: string
  preset: string | null
  presetName: string | null
  model: string | null
  autonomy: string
  responsibilities: string[]
  tasks: Task[]
}

export type Run = {
  id: number
  slot: string
  taskId: string
  taskName: string
  trigger: 'cron' | 'manual'
  status: 'queued' | 'running' | 'done' | 'failed' | 'skipped'
  output: string | null
  createdAt: string
}

export type PersonaDetail = PersonaCard & {
  email: string | null
  delegates: string[]
  processRoles: string[]
  slots: SlotDetail[]
  approvesCurrentGate: boolean
  runs: Run[]
}

// Configurazione: tipizzata solo nei campi usati dalla GUI, il resto passa invariato.
export type ConfigPersona = PersonaCard & { email?: string; delegates?: string[] }
export type RoleAssignment = { role: string; mode: 'human' | 'agent' | 'hybrid'; personas?: string[]; notes?: string }
export type SlotAssignment = {
  slot: string
  persona: string
  agentName?: string
  preset?: string
  instructions?: string
  autonomy?: 'advisory' | 'supervised' | 'autonomous'
  connectors?: string[]
  maxIterations?: number
  taskOverrides?: Record<string, { cron?: string; enabled?: boolean }>
  enabled?: boolean
}
export type Connector = {
  id: string
  name: string
  system: 'jira' | 'confluence' | 'clickup' | 'plane' | 'google-drive' | 'github' | 'gitlab' | 'slack' | 'other'
  category: 'work-tracking' | 'knowledge-base' | 'file-storage' | 'code-hosting' | 'communication'
  transport: 'mcp-remote' | 'mcp-local' | 'rest'
  endpoint?: string
  status?: 'ga' | 'preview' | 'community'
  readOnly?: boolean
  notes?: string
  settings?: ConnectorSettings
}
export type ConnectorSettings = Record<string, string | number | boolean | string[]>
export type Bindings = {
  workTracking: string
  knowledgeBase: string
  fileStorage?: string
  codeHosting?: string
  artifactStorage?: Record<string, string>
}
export type AgentPreset = {
  id: string
  name: string
  kind: 'llm-agent' | 'external-agent'
  runtime: string
  model?: string
  fallbackModel?: string
  temperature?: number
  [key: string]: unknown
}
export type PlatformConfig = {
  personas: ConfigPersona[]
  roleAssignments: RoleAssignment[]
  slotAssignments: SlotAssignment[]
  agentPresets: AgentPreset[]
  connectors: Connector[]
  bindings: Bindings
  [key: string]: unknown
}

export type ModelBundle = {
  process: {
    roles: { id: string; name: string }[]
    stages: { id: string; name: string; order: number; outputs?: string[] }[]
    artifacts: { id: string; name: string }[]
  }
  topology: {
    supervisor: { name: string; agents: TopologyAgent[] }
    orchestrators: { id: string; name: string; stage: string; agents: TopologyAgent[] }[]
  }
}
export type TopologyAgent = {
  id: string
  name: string
  supportsRole: string
  scheduledTasks?: { id: string; name: string; cron: string }[]
}

// Catalogo LLM di piattaforma (models/platform/llm-catalog.json e versioni salvate)
export type LlmModel = { alias: string; upstream: string; family: string; license?: string; tags?: string[]; enabled?: boolean }
export type LlmProvider = {
  id: string
  name: string
  kind: 'anthropic' | 'openai' | 'openai-compatible' | 'vllm' | 'ollama'
  deployment: 'cloud' | 'self-hosted'
  host?: string
  baseUrl?: string
  apiKeyEnv?: string
  enabled?: boolean
  notes?: string
  models: LlmModel[]
}
export type LlmCatalog = { id: string; version: string; description?: string; providers: LlmProvider[] }
export type GatewayStatus = {
  llmMode: string
  catalogVersion: number
  syncMinutes: number
  lastSync: { status: 'ok' | 'error' | 'skipped'; detail: string; catalogVersion: number; checkedAt: string } | null
}

export type StageArtifact = { id: number; type: string; name: string; version: number; slot: string; content: string; createdAt: string }
export type StageReview = {
  id: number; artifactId: number; artifactVersion: number; reviewer: string; taskId: string
  verdict: 'approved' | 'changes_requested'; findings: string | null; createdAt: string
}
export type EvidenceCriterion = { criterion: string; status: 'met' | 'unmet' | 'unknown'; evidence: string }
export type StageWork = {
  artifacts: StageArtifact[]
  reviews: StageReview[]
  evidence: { criteria: EvidenceCriterion[]; createdAt: string } | null
}
