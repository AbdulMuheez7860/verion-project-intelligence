import { type FormEvent, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AuthErrorAlert } from '@/components/forms/auth-error-alert'
import { FormField } from '@/components/forms/form-field'
import { PasswordInput } from '@/components/forms/password-input'
import { AuthLayout } from '@/components/layout/auth-layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { isApiError, isNetworkError } from '@/api/client'
import { useAuth } from '@/hooks/use-auth'
import { firstInvalidField, validateLoginForm } from '@/lib/auth-validation'

function mapAuthError(error: unknown): { message: string; requestId?: string } {
  if (isNetworkError(error)) {
    return { message: 'Cannot reach the Verion API. Check your connection and try again.' }
  }
  if (isApiError(error)) {
    if (error.status === 401) return { message: 'Invalid email or password.', requestId: error.requestId }
    if (error.status === 429) return { message: 'Too many attempts. Wait a moment and try again.', requestId: error.requestId }
    return { message: error.message, requestId: error.requestId }
  }
  return { message: 'Sign in failed. Please try again.' }
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/app/dashboard'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | undefined>>({})
  const [formError, setFormError] = useState<{ message: string; requestId?: string } | null>(null)
  const [loading, setLoading] = useState(false)
  const emailRef = useRef<HTMLInputElement>(null)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setFormError(null)

    const errors = validateLoginForm(email, password)
    setFieldErrors(errors)
    const firstField = firstInvalidField(errors)
    if (firstField === 'email') emailRef.current?.focus()
    if (firstField) return

    setLoading(true)
    try {
      await login(email.trim(), password)
      navigate(from, { replace: true })
    } catch (error) {
      setFormError(mapAuthError(error))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Welcome back" description="Sign in to your engineering workspace.">
      <form onSubmit={(event) => void onSubmit(event)} className="space-y-5" noValidate>
        <FormField id="email" label="Email address" error={fieldErrors.email}>
          <Input
            ref={emailRef}
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            aria-invalid={Boolean(fieldErrors.email)}
          />
        </FormField>

        <FormField id="password" label="Password" error={fieldErrors.password}>
          <PasswordInput
            id="password"
            autoComplete="current-password"
            value={password}
            onChange={setPassword}
            invalid={Boolean(fieldErrors.password)}
          />
        </FormField>

        {formError ? <AuthErrorAlert message={formError.message} requestId={formError.requestId} /> : null}

        <Button type="submit" className="w-full" size="lg" loading={loading}>
          Sign in
        </Button>

        <div className="flex items-center justify-between text-sm">
          <Link to="/forgot-password" className="font-medium text-primary hover:underline">
            Forgot password?
          </Link>
          <Link to="/signup" className="text-muted-foreground hover:text-foreground">
            Create account
          </Link>
        </div>
      </form>
    </AuthLayout>
  )
}
