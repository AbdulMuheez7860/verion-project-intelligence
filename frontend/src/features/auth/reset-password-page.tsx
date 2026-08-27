import { type FormEvent, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { authService } from '@/api/authService'
import { isApiError, isNetworkError } from '@/api/client'
import { AuthErrorAlert } from '@/components/forms/auth-error-alert'
import { FormField } from '@/components/forms/form-field'
import { PasswordInput } from '@/components/forms/password-input'
import { AuthLayout } from '@/components/layout/auth-layout'
import { Button } from '@/components/ui/button'
import { validatePassword, validatePasswordConfirmation } from '@/lib/auth-validation'

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = useMemo(() => searchParams.get('token') ?? '', [searchParams])

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | undefined>>({})
  const [formError, setFormError] = useState<{ message: string; requestId?: string } | null>(null)
  const [completed, setCompleted] = useState(false)
  const [loading, setLoading] = useState(false)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setFormError(null)

    const errors: Record<string, string | undefined> = {}
    const passwordError = validatePassword(password)
    if (passwordError) errors.password = passwordError
    const confirmError = validatePasswordConfirmation(password, confirm)
    if (confirmError) errors.confirm = confirmError
    if (!token) errors.token = 'Reset token is missing or invalid.'
    setFieldErrors(errors)
    if (Object.values(errors).some(Boolean)) {
      return
    }

    setLoading(true)
    try {
      await authService.resetPassword(password, token)
      setCompleted(true)
    } catch (error) {
      if (isNetworkError(error)) {
        setFormError({ message: 'Cannot reach the Verion API. Check your connection and try again.' })
      } else if (isApiError(error)) {
        setFormError({ message: error.message, requestId: error.requestId })
      } else {
        setFormError({ message: 'Password reset failed. Please try again.' })
      }
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <AuthLayout title="Invalid reset link" description="This password reset link is missing a token or has expired.">
        <AuthErrorAlert message="Request a new reset link and try again." />
        <Button asChild className="mt-5 w-full" size="lg">
          <Link to="/forgot-password">Request reset link</Link>
        </Button>
      </AuthLayout>
    )
  }

  if (completed) {
    return (
      <AuthLayout title="Password updated" description="Your password has been reset. Sign in with your new credentials.">
        <Button asChild className="w-full" size="lg">
          <Link to="/login">Continue to sign in</Link>
        </Button>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Set a new password" description="Choose a strong password for your Verion account.">
      <form onSubmit={(event) => void onSubmit(event)} className="space-y-5" noValidate>
        <FormField id="password" label="New password" hint="At least 8 characters." error={fieldErrors.password}>
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

        {formError ? <AuthErrorAlert message={formError.message} requestId={formError.requestId} /> : null}

        <Button type="submit" className="w-full" size="lg" loading={loading}>
          Update password
        </Button>
      </form>
    </AuthLayout>
  )
}
