import { type FormEvent, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthErrorAlert } from '@/components/forms/auth-error-alert'
import { FormField } from '@/components/forms/form-field'
import { PasswordInput } from '@/components/forms/password-input'
import { AuthLayout } from '@/components/layout/auth-layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { isApiError, isNetworkError } from '@/api/client'
import { useAuth } from '@/hooks/use-auth'
import { firstInvalidField, validateSignupForm } from '@/lib/auth-validation'

function mapSignupError(error: unknown): { message: string; requestId?: string } {
  if (isNetworkError(error)) {
    return { message: 'Cannot reach the Verion API. Check your connection and try again.' }
  }
  if (isApiError(error)) {
    if (error.status === 409) return { message: 'An account with this email already exists.', requestId: error.requestId }
    if (error.status === 422) return { message: error.message, requestId: error.requestId }
    if (error.status === 429) return { message: 'Too many attempts. Wait a moment and try again.', requestId: error.requestId }
    return { message: error.message, requestId: error.requestId }
  }
  return { message: 'Sign up failed. Please try again.' }
}

export function SignupPage() {
  const { signup } = useAuth()
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [team, setTeam] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [terms, setTerms] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | undefined>>({})
  const [formError, setFormError] = useState<{ message: string; requestId?: string } | null>(null)
  const [loading, setLoading] = useState(false)
  const nameRef = useRef<HTMLInputElement>(null)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setFormError(null)

    const errors = validateSignupForm({ name, team, email, password, confirm, terms })
    setFieldErrors(errors)
    if (firstInvalidField(errors)) {
      nameRef.current?.focus()
      return
    }

    setLoading(true)
    try {
      await signup({ name: name.trim(), email: email.trim(), team: team.trim(), password })
      navigate('/onboarding')
    } catch (error) {
      setFormError(mapSignupError(error))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Create your workspace" description="Set up Verion for your engineering organization.">
      <form onSubmit={(event) => void onSubmit(event)} className="space-y-5" noValidate>
        <FormField id="name" label="Full name" error={fieldErrors.name}>
          <Input
            ref={nameRef}
            id="name"
            autoComplete="name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            aria-invalid={Boolean(fieldErrors.name)}
          />
        </FormField>

        <FormField id="team" label="Company or team" error={fieldErrors.team}>
          <Input
            id="team"
            autoComplete="organization"
            value={team}
            onChange={(event) => setTeam(event.target.value)}
            aria-invalid={Boolean(fieldErrors.team)}
          />
        </FormField>

        <FormField id="email" label="Work email" error={fieldErrors.email}>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            aria-invalid={Boolean(fieldErrors.email)}
          />
        </FormField>

        <FormField
          id="password"
          label="Password"
          hint="At least 8 characters."
          error={fieldErrors.password}
        >
          <PasswordInput
            id="password"
            autoComplete="new-password"
            value={password}
            onChange={setPassword}
            invalid={Boolean(fieldErrors.password)}
          />
        </FormField>

        <FormField id="confirm" label="Confirm password" error={fieldErrors.confirm}>
          <PasswordInput
            id="confirm"
            autoComplete="new-password"
            value={confirm}
            onChange={setConfirm}
            invalid={Boolean(fieldErrors.confirm)}
          />
        </FormField>

        <FormField id="terms" label="Terms" error={fieldErrors.terms}>
          <label className="flex items-start gap-2 text-sm text-muted-foreground">
            <input
              id="terms"
              type="checkbox"
              checked={terms}
              onChange={(event) => setTerms(event.target.checked)}
              className="mt-1 size-4 rounded border-input"
            />
            <span>I accept the terms of service and privacy policy.</span>
          </label>
        </FormField>

        {formError ? <AuthErrorAlert message={formError.message} requestId={formError.requestId} /> : null}

        <Button type="submit" className="w-full" size="lg" loading={loading}>
          Create workspace
        </Button>

        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}
