import type { Analytics, Notification, PullRequest, Repository } from '@/types/verion'

export const repositories: Repository[] = [
  { id: 'payment-service', name: 'payment-service', owner: 'acme-platform', language: 'TypeScript', health: 86, security: 91, coverage: 82, openPullRequests: 4, risk: 'low', analysisStatus: 'complete', lastAnalyzedAt: '12 min ago' },
  { id: 'identity-platform', name: 'identity-platform', owner: 'acme-platform', language: 'Go', health: 74, security: 84, coverage: 76, openPullRequests: 7, risk: 'medium', analysisStatus: 'complete', lastAnalyzedAt: '36 min ago' },
  { id: 'commerce-api', name: 'commerce-api', owner: 'acme-commerce', language: 'Python', health: 91, security: 95, coverage: 89, openPullRequests: 2, risk: 'low', analysisStatus: 'complete', lastAnalyzedAt: '1 hr ago' },
  { id: 'customer-portal', name: 'customer-portal', owner: 'acme-platform', language: 'TypeScript', health: 62, security: 72, coverage: 64, openPullRequests: 9, risk: 'high', analysisStatus: 'running', lastAnalyzedAt: '3 hrs ago' },
]
export const pullRequests: PullRequest[] = [
  { id: 142, repositoryId: 'payment-service', repositoryName: 'payment-service', title: 'Improve payment authorization', author: 'Alex Morgan', riskScore: 72, filesChanged: 18, coverage: 58, issues: 3, status: 'open', createdAt: '2h ago' },
  { id: 138, repositoryId: 'identity-platform', repositoryName: 'identity-platform', title: 'Add session rotation middleware', author: 'Jordan Lee', riskScore: 48, filesChanged: 9, coverage: 91, issues: 0, status: 'open', createdAt: '5h ago' },
]
export const notifications: Notification[] = [
  { id: 'n1', title: 'Critical vulnerability detected', description: 'payment-service · CWE-862', read: false, severity: 'critical', createdAt: '18 min ago', href: '/app/security' },
  { id: 'n2', title: 'PR #142 requires attention', description: 'Risk score 72 · High', read: false, severity: 'high', createdAt: '2h ago', href: '/app/pull-requests/142' },
  { id: 'n3', title: 'Repository analysis completed', description: 'commerce-api · Health 91', read: true, severity: 'low', createdAt: '1h ago', href: '/app/repositories/commerce-api' },
]
export const analytics: Analytics = { range: '30d', prThroughput: 42, averageRisk: 32, averagePrSize: 14, timeToFirstReviewHours: 3.4, timeToMergeHours: 18.2, coverageTrend: [72, 74, 75, 77, 78, 79], qualityTrend: [78, 80, 81, 84, 85, 87], riskTrend: [44, 41, 39, 36, 34, 32] }
