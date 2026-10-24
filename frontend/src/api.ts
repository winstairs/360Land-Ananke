import type { GatewayStatus, LlmCatalog, ModelBundle, PersonaDetail, PlatformConfig, Project, ProjectDetail, RaciColumn } from './types'

export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(typeof detail === 'string' ? detail : `Errore ${status}`)
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  const body = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, body?.detail ?? body)
  return body as T
}

export const api = {
  health: () => req<{ status: string; llmMode: string }>('/health'),
  projects: () => req<Project[]>('/projects'),
  project: (id: string) => req<ProjectDetail>(`/projects/${id}`),
  raci: (id: string, stage: string) => req<RaciColumn[]>(`/projects/${id}/stages/${stage}/raci`),
  persona: (id: string, persona: string) => req<PersonaDetail>(`/projects/${id}/personas/${persona}`),
  runTask: (id: string, slot: string, taskId: string) =>
    req<{ id: number; message: string }>(`/projects/${id}/runs`, { method: 'POST', body: JSON.stringify({ slot, taskId }) }),
  decideGate: (id: string, body: { outcome: 'approved' | 'rejected'; personaId: string; targetStage?: string }) =>
    req<{ message: string }>(`/projects/${id}/gate-decisions`, { method: 'POST', body: JSON.stringify(body) }),
  model: (m: string) => req<ModelBundle>(`/methodologies/${m}/model`),
  config: (m: string) => req<{ version: number; config: PlatformConfig }>(`/methodologies/${m}/config`),
  validateConfig: (m: string, config: PlatformConfig) =>
    req<{ valid: boolean; errors: string[] }>(`/methodologies/${m}/config/validate`, { method: 'POST', body: JSON.stringify(config) }),
  saveConfig: (m: string, config: PlatformConfig) =>
    req<{ version: number; message: string }>(`/methodologies/${m}/config`, { method: 'PUT', body: JSON.stringify(config) }),
  llmCatalog: () => req<{ version: number; catalog: LlmCatalog }>('/llm/catalog'),
  validateLlmCatalog: (catalog: LlmCatalog) =>
    req<{ valid: boolean; errors: string[] }>('/llm/catalog/validate', { method: 'POST', body: JSON.stringify(catalog) }),
  saveLlmCatalog: (catalog: LlmCatalog) =>
    req<{ version: number; message: string }>('/llm/catalog', { method: 'PUT', body: JSON.stringify(catalog) }),
  gatewayStatus: () => req<GatewayStatus>('/llm/gateway-status'),
}
