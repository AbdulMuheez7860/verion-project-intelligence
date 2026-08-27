export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

export type AnalysisStatus = 'not_started' | 'queued' | 'running' | 'complete' | 'failed'

export type FindingStatus = 'open' | 'acknowledged' | 'false_positive' | 'resolved' | 'suppressed'

export type PullRequestStatus = 'open' | 'merged' | 'closed'

export interface User {
  id: string
  name: string
  email: string
  avatarUrl?: string
  timezone?: string
}

export type MembershipRole = 'owner' | 'admin' | 'member' | 'viewer'

export interface Organization {
  id: string
  name: string
  slug: string
}

export interface Membership {
  id: string
  organizationId: string
  role: MembershipRole
}

export interface Session {
  user: User
  organization: Organization
  membership: Membership
}

export type Permission =
  | 'settings.read'
  | 'settings.update'
  | 'members.read'
  | 'members.invite'
  | 'members.update_role'
  | 'members.remove'
  | 'integrations.read'
  | 'integrations.manage'
  | 'analysis_settings.read'
  | 'audit.read'
  | 'account.update'
  | 'notifications.read'
  | 'notifications.preferences.update'

export interface OrganizationOverview {
  id: string
  name: string
  slug: string
  createdAt?: string | null
  currentUserRole: MembershipRole
  repositoryCount: number
  memberCount: number
}

export interface Member {
  id: string
  userId: string
  name: string
  email: string
  role: MembershipRole
  joinedAt?: string | null
  status: string
  isCurrentUser: boolean
}

export interface Invitation {
  id: string
  email: string
  role: MembershipRole
  status: string
  createdAt?: string | null
  expiresAt?: string | null
  emailDeliveryConfigured: boolean
}

export interface ScannerSupportItem {
  name: string
  supported: boolean
  reason?: string | null
}

export interface AnalysisSettings {
  automaticAnalysisOnConnect: boolean
  webhookTriggeredAnalysis: boolean
  analysisTimeoutSeconds: number
  codeQualityScanners: ScannerSupportItem[]
  securityScanners: ScannerSupportItem[]
  dependencyScanners: ScannerSupportItem[]
}

export interface AuditLog {
  id: string
  action: string
  actorUserId: string
  actorName: string
  resourceType?: string | null
  resourceId?: string | null
  metadata?: Record<string, unknown> | null
  createdAt?: string | null
}

export interface AuditLogListParams {
  page?: number
  pageSize?: number
  q?: string
  action?: string
  actorId?: string
  resourceType?: string
  from?: string
  to?: string
  sort?: 'created_at' | 'action'
  order?: 'asc' | 'desc'
}

export type NotificationSeverity = 'critical' | 'high' | 'warning' | 'info'

export type NotificationType =
  | 'security.critical_finding'
  | 'dependency.critical_vulnerability'
  | 'pr.high_risk'
  | 'quality.regression'
  | 'health.regression'
  | 'analysis.completed'
  | 'analysis.failed'
  | 'analysis.stale'
  | 'workspace.member_invited'
  | 'workspace.member_removed'
  | 'workspace.role_changed'
  | 'workspace.invitation_revoked'
  | 'integration.connected'
  | 'integration.disconnected'

export interface Notification {
  id: string
  type: NotificationType
  severity: NotificationSeverity
  title: string
  body: string
  href: string
  repositoryId?: string | null
  repositoryName?: string | null
  resourceType?: string | null
  resourceId?: string | null
  read: boolean
  createdAt?: string | null
}

export interface NotificationPreferences {
  securityAlerts: boolean
  dependencyAlerts: boolean
  prRiskAlerts: boolean
  analysisAlerts: boolean
  regressionAlerts: boolean
  workspaceAlerts: boolean
}

export interface Repository {
  id: string
  name: string
  owner: string
  language?: string
  healthScore?: number | null
  securityScore?: number | null
  codeQualityScore?: number | null
  dependencyScore?: number | null
  coveragePercent?: number | null
  openPullRequests: number
  riskLevel?: RiskLevel | null
  analysisStatus: AnalysisStatus
  lastAnalyzedAt?: string | null
  githubId?: number | null
  fullName?: string | null
  htmlUrl?: string | null
  defaultBranch?: string | null
  private?: boolean | null
  dependencyStatus?: 'healthy' | 'outdated' | 'vulnerable' | 'critical' | 'unknown' | null
  securityFindingCount?: number | null
  qualityFindingCount?: number | null
}

export type RepositorySortField =
  | 'name'
  | 'health'
  | 'risk'
  | 'last_analyzed'
  | 'open_pull_requests'
  | 'security'
  | 'security_findings'

export type SecurityStatusFilter = 'good' | 'warning' | 'poor' | 'unavailable'

export interface RepositoryListParams {
  page?: number
  pageSize?: number
  q?: string
  analysisStatus?: AnalysisStatus
  riskLevel?: RiskLevel
  securityStatus?: SecurityStatusFilter
  sort?: RepositorySortField
  order?: 'asc' | 'desc'
}

export interface AnalysisRun {
  id: string
  repositoryId: string
  repositoryName?: string
  status: string
  trigger: string
  triggerSource?: string | null
  commitSha?: string | null
  branch?: string | null
  startedAt?: string | null
  completedAt?: string | null
  durationSeconds?: number | null
  findingCount: number
  healthScore?: number | null
  error?: string | null
  createdAt?: string | null
}

export type AnalysisRunStatusFilter = 'queued' | 'running' | 'complete' | 'failed'
export type AnalysisRunTriggerFilter = 'manual' | 'webhook' | 'scheduled'
export type AnalysisRunSortField = 'started' | 'completed' | 'duration' | 'status'

export interface AnalysisRunListParams {
  page?: number
  pageSize?: number
  q?: string
  repositoryId?: string
  status?: AnalysisRunStatusFilter
  trigger?: AnalysisRunTriggerFilter
  from?: string
  to?: string
  sort?: AnalysisRunSortField
  order?: 'asc' | 'desc'
}

export interface AnalyzerSkippedItem {
  name: string
  reason: string
}

export interface AnalyzerFailedItem {
  name: string
  reason: string
}

export interface LanguageBreakdown {
  files: number
  codeLoc: number
  commentLoc: number
  blankLoc: number
  totalLoc: number
}

export interface RepositoryMetricsSummary {
  totalFiles: number
  sourceFiles: number
  testFiles: number
  configFiles: number
  documentationFiles: number
  otherFiles: number
  repositorySizeBytes: number
  totalLoc: number
  codeLoc: number
  commentLoc: number
  blankLoc: number
  commentToCodeRatio?: number | null
  testToSourceRatio?: number | null
  truncated: boolean
  languageDistribution: Record<string, LanguageBreakdown>
  methodology: string
}

export interface AnalyzerSummary {
  executed: string[]
  skipped: AnalyzerSkippedItem[]
  failed: AnalyzerFailedItem[]
  dependencyScan: boolean
  repositoryMetrics?: RepositoryMetricsSummary | null
  repositoryMetricsStatus: string
  repositoryMetricsError?: string | null
}

export interface AnalysisRunSnapshotSummary {
  id: string
  capturedAt?: string | null
  healthScore?: number | null
  securityScore?: number | null
  qualityScore?: number | null
  dependencyScore?: number | null
  prRiskScore?: number | null
}

export interface AnalysisRunCapabilities {
  canRetry: boolean
  canCancel: boolean
}

export interface AnalysisRunDetail extends AnalysisRun {
  analyzerSummary?: AnalyzerSummary | null
  healthSnapshot?: Record<string, unknown> | null
  findingsByCategory?: Record<string, number> | null
  snapshot?: AnalysisRunSnapshotSummary | null
  capabilities: AnalysisRunCapabilities
  repositoryHref: string
  analyticsHref?: string | null
}

export interface AnalysisRunActionResponse {
  status: string
  analysisRunId?: string | null
  message?: string | null
}

export interface RepositoryConnectionInfo {
  githubStatus: 'connected' | 'disconnected' | 'error' | string
  githubLogin?: string | null
  lastSynchronizedAt?: string | null
  canAnalyze: boolean
  analyzeBlockedReason?: string | null
}

export interface RepositoryHealthBreakdown {
  healthScore?: number | null
  securityScore?: number | null
  codeQualityScore?: number | null
  dependencyScore?: number | null
  prRiskAverage?: number | null
  riskLevel?: RiskLevel | null
  hasCompletedAnalysis: boolean
  healthDefinition: string
  securityDefinition: string
  qualityDefinition: string
  dependencyDefinition: string
  prRiskDefinition: string
}

export interface RepositoryRecommendedAction {
  id: string
  label: string
  description: string
  priority: string
}

export interface RepositoryIntelligence {
  repository: Repository
  health: RepositoryHealthBreakdown
  connection: RepositoryConnectionInfo
  latestAnalysis?: AnalysisRun | null
  securitySummary: SecuritySummary
  qualitySummary: QualitySummary
  dependencySummary: DependencySummary
  recommendedActions: RepositoryRecommendedAction[]
}

export interface HealthHistoryPoint {
  analysisId: string
  recordedAt?: string | null
  healthScore?: number | null
  securityScore?: number | null
  codeQualityScore?: number | null
  dependencyScore?: number | null
  riskLevel?: RiskLevel | null
  severityCounts?: SeverityCounts | null
}

export interface HealthHistoryResponse {
  points: HealthHistoryPoint[]
  hasSufficientHistory: boolean
  message: string
}

export interface RepositoryPullRequest extends PullRequest {
  verdict: PRVerdict
  verdictLabel: string
  verdictReason?: string | null
  riskLevel?: RiskLevel | null
  updatedAt?: string | null
}

export interface PullRequest {
  id: number
  repositoryId: string
  repositoryName: string
  title: string
  author: string
  riskScore?: number | null
  filesChanged: number
  coveragePercent?: number | null
  issuesCount: number
  status: PullRequestStatus
  createdAt: string
}

export type PullRequestSortField = 'risk_score' | 'updated_at' | 'created_at' | 'repository_name' | 'number'

export interface PullRequestListParams {
  page?: number
  pageSize?: number
  q?: string
  repositoryId?: string
  status?: PullRequestStatus
  riskLevel?: RiskLevel
  verdict?: PRVerdict
  author?: string
  sort?: PullRequestSortField
  order?: 'asc' | 'desc'
}

export interface PullRequestListItem {
  id: number
  number?: number | null
  repositoryId: string
  repositoryName: string
  title: string
  author: string
  status: PullRequestStatus
  draft: boolean
  riskScore?: number | null
  riskLevel?: RiskLevel | null
  verdict: PRVerdict
  verdictLabel: string
  securityImpact: number
  qualityImpact: number
  dependencyImpact: number
  filesChanged: number
  issuesCount: number
  riskScoredAt?: string | null
  updatedAt?: string | null
  createdAt: string
  htmlUrl?: string | null
}

export interface PRFreshness {
  status: string
  label: string
  detail?: string | null
  riskScoredAt?: string | null
  prUpdatedAt?: string | null
  repositoryLastAnalyzedAt?: string | null
  isStale: boolean
}

export interface MergeSafetyVerdict {
  key: PRVerdict
  label: string
  headline: string
  explanation?: string | null
  riskScore?: number | null
  riskLevel?: RiskLevel | null
}

export interface PRImpactCounts {
  security: number
  quality: number
  dependency: number
  total: number
}

export interface ChangedFileItem {
  path: string
  status: string
  additions: number
  deletions: number
  category?: string | null
}

export interface AffectedArea {
  key: string
  label: string
  fileCount: number
  findingCount: number
}

export interface PRRecommendation {
  id: string
  label: string
  description: string
  priority: string
}

export interface RepositoryHealthContext {
  repositoryId: string
  repositoryName: string
  healthScore?: number | null
  securityScore?: number | null
  codeQualityScore?: number | null
  riskLevel?: RiskLevel | null
  analysisStatus: string
  lastAnalyzedAt?: string | null
}

export interface PRAnalysisInfo {
  status: string
  repositoryAnalysisStatus?: string | null
  riskScoredAt?: string | null
  headSha?: string | null
  baseSha?: string | null
}

export interface PullRequestIntelligence {
  id: number
  number?: number | null
  title: string
  repositoryId: string
  repositoryName: string
  author: string
  status: PullRequestStatus
  draft: boolean
  description?: string | null
  htmlUrl?: string | null
  createdAt: string
  updatedAt?: string | null
  mergeSafety: MergeSafetyVerdict
  freshness: PRFreshness
  riskScoreDetail?: RiskScore | null
  securitySummary: SeverityCounts
  securityFindings: SecurityFinding[]
  qualityFindings: QualityFinding[]
  dependencyFindings: SecurityFinding[]
  impactCounts: PRImpactCounts
  changedFiles: ChangedFileItem[]
  affectedAreas: AffectedArea[]
  repositoryHealth?: RepositoryHealthContext | null
  analysis: PRAnalysisInfo
  recommendations: PRRecommendation[]
}

export interface RiskFactor {
  label: string
  contribution: number
  explanation: string
}

export interface RiskScore {
  value: number
  level: RiskLevel
  factors: RiskFactor[]
  engine?: string
}

export interface PullRequestDetail extends PullRequest {
  riskScoreDetail?: RiskScore | null
  description?: string
}

export interface FindingAIExplanation {
  explanation: string
  remediationSuggestion: string
  generatedAt: string
  model: string
  source: 'ai'
  disclaimer: string
}

export interface Finding {
  id: string
  title: string
  file: string
  line: number
  severity: RiskLevel
  status: FindingStatus
  category: string
  description?: string
  remediation?: string
  repositoryId?: string
  repositoryName?: string
  ruleId?: string
  scannerEngine?: string
  aiExplanation?: FindingAIExplanation | null
  createdAt?: string | null
  updatedAt?: string | null
  analysisId?: string | null
}

export interface SecurityFinding extends Finding {
  cwe?: string
  cve?: string
}

export interface QualityFinding extends Finding {
  rule: string
}

export interface Dependency {
  id: string
  packageName: string
  currentVersion: string
  latestVersion: string
  status: 'healthy' | 'outdated' | 'vulnerable' | 'critical' | 'unknown'
  vulnerability?: string | null
  license: string
  repositoryId?: string
  repositoryName?: string
  ecosystem?: string
  source?: string
  severity?: RiskLevel | null
  scannerEngine?: string
  analyzedAt?: string | null
}

export interface SeverityCounts {
  critical: number
  high: number
  medium: number
  low: number
}

export interface DashboardMetrics {
  repositoryHealth?: number | null
  prRisk?: number | null
  securityScore?: number | null
  codeQualityScore?: number | null
  testCoveragePercent?: number | null
  hasAnalysisData: boolean
  connectedRepositories: number
}

export interface SecuritySummary {
  score?: number | null
  severityCounts?: SeverityCounts | null
  hasAnalysisData: boolean
}

export interface SecurityPosture {
  label: string
  level: string
  explanation: string
}

export interface SecurityFreshness {
  status: string
  label: string
  isStale: boolean
  lastAnalyzedAt?: string | null
  analysisRunning: boolean
}

export interface SecurityTotals {
  open: number
  total: number
  repositoriesAffected: number
  connectedRepositories: number
}

export interface SecurityCategoryCounts {
  security: number
  secret: number
  dependency: number
}

export interface ScannerCoverage {
  executed: string[]
  supported: string[]
  hasData: boolean
  note?: string | null
}

export interface SecurityRepositoryOption {
  id: string
  name: string
  findingCount: number
}

export interface SecurityIntelligence {
  score?: number | null
  severityCounts?: SeverityCounts | null
  hasAnalysisData: boolean
  posture: SecurityPosture
  freshness: SecurityFreshness
  totals: SecurityTotals
  categoryCounts: SecurityCategoryCounts
  scannerCoverage: ScannerCoverage
  repositories: SecurityRepositoryOption[]
}

export type SecurityCategory = 'security' | 'secret' | 'dependency'
export type SecuritySortField = 'severity' | 'created_at' | 'updated_at' | 'file' | 'title' | 'repository_name'

export interface SecurityListParams {
  page?: number
  pageSize?: number
  q?: string
  repositoryId?: string
  severity?: RiskLevel
  status?: FindingStatus
  category?: SecurityCategory
  sort?: SecuritySortField
  order?: 'asc' | 'desc'
}

export interface QualitySummary {
  score?: number | null
  maintainabilityScore?: number | null
  averageComplexity?: number | null
  duplicationPercent?: number | null
  technicalDebtHours?: number | null
  hasAnalysisData: boolean
}

export interface QualityPosture {
  label: string
  level: string
  explanation: string
}

export interface QualityFreshness {
  status: string
  label: string
  isStale: boolean
  lastAnalyzedAt?: string | null
  analysisRunning: boolean
}

export interface QualityTotals {
  open: number
  total: number
  repositoriesAffected: number
  connectedRepositories: number
  critical: number
  high: number
}

export interface QualityScannerCoverage {
  executed: string[]
  supported: string[]
  hasData: boolean
  note?: string | null
}

export interface QualityRepositorySummary {
  id: string
  name: string
  findingCount: number
  openCount: number
  highestSeverity?: string | null
  qualityScore?: number | null
  analysisStatus?: string | null
  lastAnalyzedAt?: string | null
}

export interface QualityRuleSummary {
  ruleId: string
  analyzer?: string | null
  count: number
  highestSeverity: string
  repositoryCount: number
}

export interface UnavailableQualityMetric {
  key: string
  label: string
  reason: string
}

export interface QualityRecommendation {
  id: string
  label: string
  description: string
  priority: string
}

export interface QualityIntelligence {
  score?: number | null
  severityCounts?: SeverityCounts | null
  hasAnalysisData: boolean
  posture: QualityPosture
  freshness: QualityFreshness
  totals: QualityTotals
  scannerCoverage: QualityScannerCoverage
  repositories: QualityRepositorySummary[]
  topRules: QualityRuleSummary[]
  unavailableMetrics: UnavailableQualityMetric[]
  recommendations: QualityRecommendation[]
}

export type QualitySortField = 'severity' | 'created_at' | 'updated_at' | 'file' | 'title' | 'rule_id' | 'repository_name'

export interface QualityListParams {
  page?: number
  pageSize?: number
  q?: string
  repositoryId?: string
  severity?: RiskLevel
  status?: FindingStatus
  ruleId?: string
  sort?: QualitySortField
  order?: 'asc' | 'desc'
}

export interface DependencySummary {
  healthScore?: number | null
  totalPackages: number
  outdatedCount: number
  vulnerableCount: number
  abandonedCount: number
  hasAnalysisData: boolean
}

export interface DependencyPosture {
  label: string
  level: string
  explanation: string
}

export interface DependencyFreshness {
  status: string
  label: string
  isStale: boolean
  lastAnalyzedAt?: string | null
  analysisRunning: boolean
}

export interface DependencyTotals {
  total: number
  vulnerable: number
  critical: number
  healthy: number
  outdated: number
  repositoriesAffected: number
  connectedRepositories: number
}

export interface EcosystemCoverage {
  key: string
  label: string
  supported: boolean
  note?: string | null
}

export interface DependencyScannerCoverage {
  executed: string[]
  supported: string[]
  hasData: boolean
  note?: string | null
  ecosystems: EcosystemCoverage[]
}

export interface DependencyRepositorySummary {
  id: string
  name: string
  dependencyCount: number
  vulnerableCount: number
  highestSeverity?: RiskLevel | string | null
  lastAnalyzedAt?: string | null
  analysisStatus?: string | null
}

export interface DependencyPackageSummary {
  packageName: string
  count: number
  vulnerableCount: number
  highestSeverity: string
  repositoryCount: number
  vulnerability?: string | null
}

export interface UnavailableDependencyMetric {
  key: string
  label: string
  reason: string
}

export interface DependencyRecommendation {
  id: string
  label: string
  description: string
  priority: string
}

export interface DependencyIntelligence {
  healthScore?: number | null
  severityCounts?: SeverityCounts | null
  hasAnalysisData: boolean
  posture: DependencyPosture
  freshness: DependencyFreshness
  totals: DependencyTotals
  scannerCoverage: DependencyScannerCoverage
  repositories: DependencyRepositorySummary[]
  topPackages: DependencyPackageSummary[]
  unavailableMetrics: UnavailableDependencyMetric[]
  recommendations: DependencyRecommendation[]
}

export type DependencySortField =
  | 'package_name'
  | 'status'
  | 'current_version'
  | 'created_at'
  | 'repository_name'
  | 'severity'

export type DependencyEcosystem = 'python'

export interface DependencyListParams {
  page?: number
  pageSize?: number
  q?: string
  repositoryId?: string
  status?: 'healthy' | 'outdated' | 'vulnerable' | 'critical' | 'unknown'
  ecosystem?: DependencyEcosystem
  severity?: RiskLevel
  sort?: DependencySortField
  order?: 'asc' | 'desc'
}

export interface AnalyticsSummary {
  range: string
  prThroughput?: number | null
  mergeFrequencyPerDay?: number | null
  medianReviewTimeHours?: number | null
  averagePrSize?: number | null
  averageRisk?: number | null
  hasAnalysisData: boolean
  currentHealth?: number | null
  currentSecurity?: number | null
  currentQuality?: number | null
  currentPrRisk?: number | null
  trendDirection?: 'improving' | 'declining' | 'stable' | 'unavailable' | string
  analysisRunsCount?: number
  message?: string | null
}

export interface AnalyticsBaseline {
  available: boolean
  snapshotCount: number
  status: 'building' | 'established' | 'trending' | string
  firstCapturedAt?: string | null
  lastCapturedAt?: string | null
  message?: string | null
}

export interface HistoricalFreshness {
  lastSnapshotAt?: string | null
  lastAnalysisAt?: string | null
  staleRepositories: string[]
  neverAnalyzedRepositories: string[]
}

export interface HistoricalChange {
  metric: string
  label: string
  current?: number | null
  previous?: number | null
  delta?: number | null
  percentageChange?: number | null
  direction: string
  interpretation: string
  available: boolean
  repositoryId?: string | null
  repositoryName?: string | null
  detectedAt?: string | null
}

export interface AnalyticsTrendPoint {
  capturedAt: string
  repositoryId?: string
  repositoryName?: string
  value?: number | null
  total?: number | null
  critical?: number | null
  high?: number | null
  medium?: number | null
  low?: number | null
}

export interface AnalyticsRepositoryComparison {
  id: string
  name: string
  healthScore?: number | null
  securityScore?: number | null
  qualityScore?: number | null
  dependencyScore?: number | null
  prRiskScore?: number | null
  trendDirection: string
  lastAnalyzedAt?: string | null
  lastSnapshotAt?: string | null
  snapshotCount: number
}

export interface AnalyticsRepositoryOption {
  id: string
  name: string
  snapshotCount: number
}

export interface AnalyticsOverview {
  baseline: AnalyticsBaseline
  freshness: HistoricalFreshness
  healthTrend: AnalyticsTrendPoint[]
  securityTrend: AnalyticsTrendPoint[]
  qualityTrend: AnalyticsTrendPoint[]
  dependencyTrend: AnalyticsTrendPoint[]
  riskTrend: AnalyticsTrendPoint[]
  findingTrend: AnalyticsTrendPoint[]
  repositoryComparisons: AnalyticsRepositoryComparison[]
  regressions: HistoricalChange[]
  improvements: HistoricalChange[]
  repositoryOptions: AnalyticsRepositoryOption[]
  rangeDays: number
}

export interface AnalyticsOverviewParams {
  repositoryId?: string
  from?: string
  to?: string
}

export interface AttentionItem {
  id: string
  title: string
  description: string
  severity: RiskLevel
  href: string
  createdAt: string
  entityType?: string | null
  repositoryId?: string | null
  repositoryName?: string | null
  actionLabel?: string | null
}

export type OverviewStatus = 'healthy' | 'warning' | 'critical' | 'neutral' | 'unavailable'

export interface OverviewMetric {
  key: string
  label: string
  value: number | string | null
  definition: string
  href?: string | null
  status: OverviewStatus
}

export interface HealthDimension {
  key: string
  label: string
  score?: number | null
  definition: string
}

export interface EngineeringHealth {
  score?: number | null
  level?: RiskLevel | 'unavailable' | null
  definition: string
  dimensions: HealthDimension[]
  factors: string[]
}

export type PRVerdict =
  | 'safe_to_merge'
  | 'review_recommended'
  | 'high_risk'
  | 'critical_risk'
  | 'analysis_unavailable'

export interface RepositoryDashboardItem {
  id: string
  name: string
  healthScore?: number | null
  securityScore?: number | null
  codeQualityScore?: number | null
  dependencyScore?: number | null
  openPullRequests: number
  analysisStatus: string
  lastAnalyzedAt?: string | null
  riskLevel?: RiskLevel | null
}

export interface PullRequestDashboardItem {
  id: number
  repositoryId: string
  repositoryName: string
  title: string
  riskScore?: number | null
  riskLevel?: RiskLevel | null
  verdict: PRVerdict
  verdictLabel: string
  verdictReason?: string | null
  updatedAt?: string | null
  status: string
  issuesCount: number
}

export interface PullRequestSection {
  highRisk: PullRequestDashboardItem[]
  awaitingAnalysis: PullRequestDashboardItem[]
  recentlyAnalyzed: PullRequestDashboardItem[]
}

export interface SecurityOverview {
  severityCounts?: SeverityCounts | null
  total: number
  hasData: boolean
}

export interface AnalysisActivityItem {
  id: string
  repositoryId: string
  repositoryName: string
  commitSha?: string | null
  triggerSource: string
  startedAt?: string | null
  completedAt?: string | null
  durationSeconds?: number | null
  status: string
  error?: string | null
  findingCount: number
  healthScore?: number | null
  href: string
}

export interface RiskDistributionBucket {
  key: string
  label: string
  count: number
}

export interface RiskDistribution {
  buckets: RiskDistributionBucket[]
  total: number
  hasData: boolean
}

export interface TrendsSection {
  available: boolean
  message: string
  direction: 'improving' | 'declining' | 'stable' | 'unavailable'
  completedAnalysesCount: number
}

export interface RecommendedAction {
  id: string
  label: string
  description: string
  href: string
  priority: 'high' | 'medium' | 'low'
}

export interface DashboardSummaryResponse {
  generatedAt: string
  hasActiveAnalysis: boolean
  hasAnalysisData: boolean
  overview: OverviewMetric[]
  health: EngineeringHealth
  attention: AttentionItem[]
  repositories: RepositoryDashboardItem[]
  pullRequests: PullRequestSection
  security: SecurityOverview
  analysisActivity: AnalysisActivityItem[]
  riskDistribution: RiskDistribution
  trends: TrendsSection
  recommendedActions: RecommendedAction[]
}

export interface DashboardResponse {
  metrics: DashboardMetrics
  attentionItems: AttentionItem[]
  recentPullRequests: PullRequest[]
  repositoryHealthItems: RepositoryHealthItem[]
  highRiskChanges: HighRiskChange[]
  securitySeverityCounts?: SeverityCounts | null
}

export interface RepositoryHealthItem {
  id: string
  name: string
  healthScore?: number | null
}

export interface HighRiskChange {
  repositoryName: string
  pullRequestId: number
  pullRequestTitle: string
  riskScore: number
  findingsCount: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  hasNext: boolean
}

// --- AI Assistant ---

export type AssistantRole = 'user' | 'assistant'

export interface AssistantChatMessage {
  role: AssistantRole
  content: string
}

export interface AssistantEvidenceRef {
  findingId?: string | null
  kind: 'finding' | 'score' | 'dependency' | 'analyzer_status' | 'repository'
  label: string
}

export interface AssistantChatResponse {
  reply: string
  evidence: AssistantEvidenceRef[]
  hasSufficientEvidence: boolean
  model: string
  generatedAt: string
  disclaimer: string
}

export interface AssistantStatusResponse {
  available: boolean
  reason?: string | null
  hasAnalysisData: boolean
}

export interface ApiErrorBody {
  message: string
  code?: string
  requestId?: string
}

export class ApiError extends Error {
  readonly status: number
  readonly code?: string
  readonly requestId?: string

  constructor(status: number, message: string, code?: string, requestId?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
  }
}
