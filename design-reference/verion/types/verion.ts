export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'
export type AnalysisStatus = 'not_started' | 'queued' | 'running' | 'complete' | 'failed'
export type FindingStatus = 'open' | 'acknowledged' | 'false_positive' | 'resolved' | 'suppressed'
export type IntegrationStatus = 'not_connected' | 'connecting' | 'connected' | 'syncing' | 'error'

export interface User { id: string; name: string; email: string; avatarUrl?: string; timezone?: string }
export interface Organization { id: string; name: string; slug: string }
export interface Membership { id: string; userId: string; organizationId: string; role: 'owner' | 'admin' | 'member' | 'viewer' }
export interface Repository { id: string; name: string; owner: string; language: string; health: number; security: number; coverage: number; openPullRequests: number; risk: RiskLevel; analysisStatus: AnalysisStatus; lastAnalyzedAt?: string }
export interface PullRequest { id: number; repositoryId: string; repositoryName: string; title: string; author: string; riskScore: number; filesChanged: number; coverage: number; issues: number; status: 'open' | 'merged' | 'closed'; createdAt: string }
export interface RiskScore { value: number; level: RiskLevel; factors: Array<{ label: string; contribution: number; explanation: string }>; engine: 'Verion Risk Engine' }
export interface Analysis { id: string; repositoryId: string; status: AnalysisStatus; progress: number; riskScore?: RiskScore; startedAt?: string; completedAt?: string }
export interface Finding { id: string; title: string; file: string; line: number; severity: RiskLevel; status: FindingStatus; category: string; description: string; remediation: string }
export interface SecurityFinding extends Finding { cwe?: string; cvss?: number; confidence: number; firstDetected: string; lastDetected: string }
export interface QualityFinding extends Finding { rule: string; complexity?: number; debtMinutes?: number }
export interface Dependency { id: string; packageName: string; currentVersion: string; latestVersion: string; status: 'healthy' | 'outdated' | 'vulnerable' | 'critical'; vulnerability?: string; license: string }
export interface AIReview { id: string; pullRequestId: number; summary: string; confidence: number; findings: Array<{ severity: RiskLevel; file: string; line: number; why: string; recommendation: string }> }
export interface Notification { id: string; title: string; description: string; read: boolean; severity: RiskLevel; createdAt: string; href?: string }
export interface Integration { id: string; provider: 'github'; status: IntegrationStatus; organization?: string; repositories: number; webhookStatus: 'installed' | 'pending' | 'error' }
export interface AuditLog { id: string; actor: string; action: string; createdAt: string }
export interface Analytics { range: string; prThroughput: number; averageRisk: number; averagePrSize: number; timeToFirstReviewHours: number; timeToMergeHours: number; coverageTrend: number[]; qualityTrend: number[]; riskTrend: number[] }

export interface ApiError { message: string; status?: number; code?: string }
export type ApiResult<T> = { data: T; error: null } | { data: null; error: ApiError }
      
