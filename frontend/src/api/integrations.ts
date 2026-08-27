import { apiRequest } from '@/api/client'

export type IntegrationStatus = 'not_connected' | 'connected' | 'error'

export interface GitHubIntegration {
  status: IntegrationStatus
  githubLogin?: string
  connectedRepositories: number
  configured: boolean
}

export interface GitHubRepositoryOption {
  githubId: number
  fullName: string
  name: string
  owner: string
  language?: string
  private: boolean
  defaultBranch?: string
  htmlUrl?: string
  alreadyConnected: boolean
}

export const integrationsApi = {
  getGitHub: () => apiRequest<GitHubIntegration>('/api/v1/integrations/github'),

  connectGitHub: () =>
    apiRequest<{ authorizeUrl: string }>('/api/v1/integrations/github/connect', { method: 'POST' }),

  disconnectGitHub: () =>
    apiRequest<void>('/api/v1/integrations/github', { method: 'DELETE' }),

  listGitHubRepositories: () =>
    apiRequest<GitHubRepositoryOption[]>('/api/v1/integrations/github/repositories'),
}
