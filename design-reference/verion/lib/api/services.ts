import { analytics, notifications, pullRequests, repositories } from '@/lib/mock'
import type { Analytics, Notification, PullRequest, Repository } from '@/types/verion'

const API_URL = process.env.NEXT_PUBLIC_API_URL
async function request<T>(path: string, init?: RequestInit): Promise<T> { if (!API_URL) throw new Error('API_URL_NOT_CONFIGURED'); const response = await fetch(`${API_URL}${path}`, { ...init, credentials: 'include', headers: { 'Content-Type': 'application/json', ...init?.headers } }); if (!response.ok) throw new Error(`API_${response.status}`); return response.json() as Promise<T> }
async function withMock<T>(mock: T, path: string, init?: RequestInit) { if (!API_URL) return mock; try { return await request<T>(path, init) } catch { return mock } }
export const repositoryService = { list: () => withMock(repositories, '/repositories'), get: async (id: string) => { const match = repositories.find(r => r.id === id); return withMock(match, `/repositories/${id}`) } }
export const pullRequestService = { list: () => withMock(pullRequests, '/pull-requests'), get: async (id: number) => { const match = pullRequests.find(pr => pr.id === id); return withMock(match, `/pull-requests/${id}`) } }
export const analyticsService = { get: () => withMock(analytics, '/analytics') }
export const notificationService = { list: () => withMock(notifications, '/notifications'), markRead: (id: string) => withMock(notifications.find(n => n.id === id) ?? notifications[0], `/notifications/${id}/read`, { method: 'PATCH' }) }
export const authService = { login: (payload: { email: string; password: string }) => withMock({ authenticated: true }, '/auth/login', { method: 'POST', body: JSON.stringify(payload) }), signup: (payload: Record<string, string>) => withMock({ authenticated: true }, '/auth/signup', { method: 'POST', body: JSON.stringify(payload) }), logout: () => withMock(undefined, '/auth/logout', { method: 'POST' }) }
export const githubService = { connect: () => withMock({ status: 'connecting' }, '/integrations/github/connect', { method: 'POST' }), status: () => withMock({ status: 'not_connected' }, '/integrations/github') }
export const analysisService = { start: (id: string) => withMock({ repositoryId: id, status: 'queued' }, `/repositories/${id}/analyze`, { method: 'POST' }) }
export const securityService = { findings: () => withMock([], '/security/findings') }
export const qualityService = { findings: () => withMock([], '/quality/findings') }
export const dependencyService = { list: () => withMock([], '/dependencies') }
export const teamService = { members: () => withMock([], '/team/members') }
