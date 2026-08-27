import { useState } from 'react'
import { findingsApi } from '@/api/findings'
import { isApiError } from '@/api/client'
import type { Finding, FindingAIExplanation } from '@/types/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

function scannerLabel(engine?: string) {
  if (!engine) return 'Static analyzer'
  return engine.charAt(0).toUpperCase() + engine.slice(1)
}

export function FindingAIInsight({
  finding,
  onExplained,
}: {
  finding: Finding
  onExplained?: (explanation: FindingAIExplanation) => void
}) {
  const [explanation, setExplanation] = useState<FindingAIExplanation | null>(
    finding.aiExplanation ?? null,
  )
  const [status, setStatus] = useState<'idle' | 'loading' | 'error' | 'unavailable'>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  async function handleExplain(regenerate = false) {
    setStatus('loading')
    setErrorMessage(null)
    try {
      const result = await findingsApi.explainFinding(finding.id, regenerate)
      setExplanation(result)
      setStatus('idle')
      onExplained?.(result)
    } catch (error) {
      const message = isApiError(error)
        ? error.message
        : error instanceof Error
          ? error.message
          : 'Failed to generate explanation.'
      if (isApiError(error) && error.status === 503) {
        setStatus('unavailable')
        setErrorMessage('AI explanations are not configured. Add LLM_API_KEY to enable this feature.')
      } else {
        setStatus('error')
        setErrorMessage(message)
      }
    }
  }

  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <section className="rounded-md border border-border bg-card p-3.5">
        <div className="flex items-center gap-2">
          <Badge tone="neutral">{scannerLabel(finding.scannerEngine)}</Badge>
          {finding.ruleId ? (
            <span className="font-mono text-[11px] text-muted-foreground">{finding.ruleId}</span>
          ) : null}
        </div>
        <h3 className="mt-2.5 text-sm font-medium">Scanner finding</h3>
        <p className="mt-1.5 text-sm text-muted-foreground">{finding.description || finding.title}</p>
        {finding.remediation ? (
          <div className="mt-3">
            <p className="text-label">Scanner remediation</p>
            <p className="mt-1 text-sm">{finding.remediation}</p>
          </div>
        ) : null}
        <p className="mt-3 text-[11px] text-muted-foreground">
          Severity and status come from deterministic static analysis.
        </p>
      </section>

      <section className="rounded-md border border-border bg-muted/20 p-3.5">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium">AI explanation</h3>
          <Badge tone="neutral">AI</Badge>
        </div>

        {explanation ? (
          <div className="mt-2.5 space-y-3">
            <p className="text-sm">{explanation.explanation}</p>
            <div>
              <p className="text-label">Suggested remediation</p>
              <p className="mt-1 text-sm">{explanation.remediationSuggestion}</p>
            </div>
            <p className="text-[11px] text-muted-foreground">{explanation.disclaimer}</p>
            <Button type="button" variant="outline" size="sm" onClick={() => void handleExplain(true)}>
              Regenerate
            </Button>
          </div>
        ) : (
          <div className="mt-2.5">
            <p className="text-sm text-muted-foreground">
              Generate a plain-language explanation for this scanner finding.
            </p>
            {status === 'unavailable' ? (
              <p className="mt-2 text-sm text-muted-foreground">{errorMessage}</p>
            ) : null}
            {status === 'error' ? (
              <p className="mt-2 text-sm text-destructive" role="alert">
                {errorMessage}
              </p>
            ) : null}
            <Button
              type="button"
              className="mt-3"
              size="sm"
              variant="outline"
              disabled={status === 'loading' || status === 'unavailable'}
              onClick={() => void handleExplain(false)}
            >
              {status === 'loading' ? 'Explaining…' : 'Explain finding'}
            </Button>
          </div>
        )}
      </section>
    </div>
  )
}
