import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { DependenciesPage } from '@/features/dependencies/dependencies-page'
import type { Dependency, DependencyIntelligence, PaginatedResponse } from '@/types/api'

const { intelligenceFixture, dependenciesFixture } = vi.hoisted(() => {
  const intelligence: DependencyIntelligence = {
    healthScore: 90,
    severityCounts: { critical: 1, high: 0, medium: 1, low: 0 },
    hasAnalysisData: true,
    posture: {
      label: 'CRITICAL EXPOSURE',
      level: 'critical',
      explanation: '1 critical vulnerability in dependencies. Patch or upgrade affected packages before release.',
    },
    freshness: {
      status: 'current',
      label: 'Analysis current',
      isStale: false,
      lastAnalyzedAt: new Date().toISOString(),
      analysisRunning: false,
    },
    totals: {
      total: 2,
      vulnerable: 1,
      critical: 0,
      healthy: 1,
      outdated: 0,
      repositoriesAffected: 1,
      connectedRepositories: 1,
    },
    scannerCoverage: {
      executed: ['pip-audit'],
      supported: ['pip-audit'],
      hasData: true,
      note: 'Coverage reflects pip-audit execution against requirements.txt.',
      ecosystems: [
        { key: 'python', label: 'Python (requirements.txt)', supported: true, note: 'Scanned via pip-audit.' },
        { key: 'npm', label: 'npm / package-lock', supported: false, note: 'Not currently scanned.' },
      ],
    },
    repositories: [
      {
        id: 'repo-1',
        name: 'acme/api',
        dependencyCount: 2,
        vulnerableCount: 1,
        highestSeverity: 'critical',
        lastAnalyzedAt: new Date().toISOString(),
        analysisStatus: 'complete',
      },
    ],
    topPackages: [
      {
        packageName: 'requests',
        count: 2,
        vulnerableCount: 1,
        highestSeverity: 'critical',
        repositoryCount: 1,
        vulnerability: 'PYSEC-2023-1',
      },
    ],
    unavailableMetrics: [
      {
        key: 'outdated_detection',
        label: 'Outdated dependency detection',
        reason: 'pip-audit reports vulnerabilities only.',
      },
    ],
    recommendations: [
      {
        id: 'critical-deps',
        label: 'Patch critical dependency vulnerabilities',
        description: '1 critical vulnerability requires immediate attention.',
        priority: 'high',
      },
    ],
  }

  const dependencies: PaginatedResponse<Dependency> = {
    items: [
      {
        id: 'dep-1',
        packageName: 'requests',
        currentVersion: '2.28.0',
        latestVersion: '2.28.0',
        status: 'vulnerable',
        vulnerability: 'PYSEC-2023-1',
        license: 'unknown',
        repositoryId: 'repo-1',
        repositoryName: 'acme/api',
        ecosystem: 'python',
        source: 'requirements.txt',
        severity: 'critical',
        scannerEngine: 'pip-audit',
        analyzedAt: new Date().toISOString(),
      },
    ],
    total: 1,
    page: 1,
    pageSize: 20,
    hasNext: false,
  }

  return { intelligenceFixture: intelligence, dependenciesFixture: dependencies }
})

vi.mock('@/api/findings', () => ({
  findingsApi: {
    dependencyIntelligence: vi.fn().mockResolvedValue(intelligenceFixture),
    dependencies: vi.fn().mockResolvedValue(dependenciesFixture),
  },
}))

describe('DependenciesPage', () => {
  it('renders dependency posture, metrics, and workspace table', async () => {
    render(
      <MemoryRouter>
        <DependenciesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('CRITICAL EXPOSURE')).toBeInTheDocument()
    expect(await screen.findByText('requests')).toBeInTheDocument()
    expect(screen.getByText('Severity distribution')).toBeInTheDocument()
    expect(screen.getByText('Repository impact')).toBeInTheDocument()
    expect(screen.getByText('Scanner coverage by ecosystem')).toBeInTheDocument()
    expect(screen.getByText('Not currently scanned')).toBeInTheDocument()
    expect(screen.getByText('Patch critical dependency vulnerabilities')).toBeInTheDocument()
  })
})
