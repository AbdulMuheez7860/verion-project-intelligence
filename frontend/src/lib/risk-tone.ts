import type { RiskLevel } from '@/types/api'

export type Tone = 'healthy' | 'warning' | 'critical' | 'neutral'

export function riskScoreTone(score: number | null | undefined): Tone {
  if (score == null) return 'neutral'
  if (score >= 60) return 'critical'
  if (score >= 40) return 'warning'
  return 'healthy'
}

export function riskLevelTone(risk?: RiskLevel | null): Tone {
  if (risk === 'high' || risk === 'critical') return 'critical'
  if (risk === 'medium') return 'warning'
  if (risk === 'low') return 'healthy'
  return 'neutral'
}
