import { type FormEvent, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2 } from 'lucide-react'
import { authService } from '@/api/authService'
import { isApiError, isNetworkError } from '@/api/client'
import { AuthErrorAlert } from '@/components/forms/auth-error-alert'
import { FormField } from '@/components/forms/form-field'
import { AuthLayout } from '@/components/layout/auth-layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { validateEmail } from '@/lib/auth-validation'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [formError, setFormError] = useState<{ message: string; requestId?: string } | null>(null)
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)
  const emailRef = useRef<HTMLInputElement>(null)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setFormError(null)

    const emailError = validateEmail(email)
    if (emailError) {
      setFieldError(emailError)
      emailRef.current?.focus()
      return
    }
    setFieldError(null)

    setLoading(true)
    try {
      await authService.forgotPassword(email.trim())
      setSubmitted(true)
    } catch (error) {
      if (isNetworkError(error)) {
        setFormError({ message: 'Cannot reach the Verion API. Check your connection and try again.' })
      } else if (isApiError(error)) {
        setFormError({ message: error.message, requestId: error.requestId })
      } else {
        setFormError({ message: 'Request failed. Please try again.' })
      }
    } finally {
      setLoading(false)
    }
  }

  if (submitted) {
    return (
      <AuthLayout
        title="Check your inbox"
        description="If an account exists for that email, password reset instructions have been sent."
      >
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="grid size-12 place-items-center rounded-full border border-success/30 bg-success/10 text-success">
            <CheckCircle2 className="size-6" aria-hidden="true" />
          </div>
          <p className="text-supporting">
            Email delivery is not configured in this environment. Use a reset token from your administrator if provided.
          </p>
          <Button asChild className="w-full" size="lg">
            <Link to="/login">Back to sign in</Link>
          </Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Reset your password" description="Enter your email and we will send reset instructions if an account exists.">
      <form onSubmit={(event) => void onSubmit(event)} className="space-y-5" noValidate>
        <FormField id="email" label="Email address" error={fieldError ?? undefined}>
          <Input
            ref={emailRef}
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            aria-invalid={Boolean(fieldError)}
          />
        </FormField>

        {formError ? <AuthErrorAlert message={formError.message} requestId={formError.requestId} /> : null}

        <Button type="submit" className="w-full" size="lg" loading={loading}>
          Send reset link
        </Button>

        <p className="text-center text-sm">
          <Link to="/login" className="font-medium text-primary hover:underline">
            Back to sign in
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}
