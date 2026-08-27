import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { integrationsApi } from '@/api/integrations'
import { isApiError } from '@/api/client'
import { Logo } from '@/components/navigation/logo'
import { Button } from '@/components/ui/button'

export function OnboardingPage() {
  const [step, setStep] = useState(1)
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const handleConnectGitHub = async () => {
    setConnecting(true)
    setError(null)
    try {
      const { authorizeUrl } = await integrationsApi.connectGitHub()
      window.location.href = authorizeUrl
    } catch (err) {
      setConnecting(false)
      setError(isApiError(err) ? err.message : 'Unable to start GitHub connection.')
    }
  }

  return (
    <div className="min-h-screen bg-muted/20 p-5">
      <div className="mx-auto max-w-2xl">
        <Logo />
        <div className="mt-12 rounded-2xl border border-border bg-card p-8 text-center shadow-xl">
          <div className="mx-auto grid size-14 place-items-center rounded-2xl bg-primary text-primary-foreground">
            <Sparkles className="size-6" aria-hidden="true" />
          </div>
          <p className="mt-6 text-xs font-semibold uppercase tracking-wider text-primary">Step {step} of 3</p>
          <h1 className="mt-3 text-2xl font-semibold">
            {step === 1 ? 'Welcome to Verion' : step === 2 ? 'Connect GitHub' : "You're ready to analyze"}
          </h1>
          <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-muted-foreground">
            {step === 1
              ? 'Set up the signals your team needs to ship with confidence.'
              : step === 2
                ? 'Authorize Verion to access your repositories and receive webhook events for analysis.'
                : 'Head to Repositories to connect a repo and run your first analysis job.'}
          </p>
          {error ? (
            <p className="mx-auto mt-4 max-w-md rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive" role="alert">
              {error}
            </p>
          ) : null}
          <div className="mt-8 flex justify-center gap-3">
            <Button
              variant="outline"
              onClick={() => (step === 1 ? navigate('/app/dashboard') : setStep(step - 1))}
            >
              {step === 1 ? 'Skip setup' : 'Back'}
            </Button>
            {step === 2 ? (
              <Button disabled={connecting} onClick={() => void handleConnectGitHub()}>
                {connecting ? 'Redirecting…' : 'Connect GitHub'}
              </Button>
            ) : (
              <Button onClick={() => (step === 3 ? navigate('/app/repositories/connect') : setStep(step + 1))}>
                {step === 3 ? 'Connect a repository' : 'Continue'}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
