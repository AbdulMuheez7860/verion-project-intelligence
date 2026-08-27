export interface FieldErrors {
  [field: string]: string | undefined
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function validateEmail(email: string): string | null {
  const value = email.trim()
  if (!value) return 'Email is required.'
  if (!EMAIL_PATTERN.test(value)) return 'Enter a valid email address.'
  return null
}

export function validatePassword(password: string): string | null {
  if (!password) return 'Password is required.'
  if (password.length < 8) return 'Password must be at least 8 characters.'
  return null
}

export function validatePasswordConfirmation(password: string, confirm: string): string | null {
  if (!confirm) return 'Confirm your password.'
  if (password !== confirm) return 'Passwords do not match.'
  return null
}

export function validateSignupForm(input: {
  name: string
  team: string
  email: string
  password: string
  confirm: string
  terms: boolean
}): FieldErrors {
  const errors: FieldErrors = {}

  if (!input.name.trim()) errors.name = 'Full name is required.'
  if (!input.team.trim()) errors.team = 'Company or team is required.'

  const emailError = validateEmail(input.email)
  if (emailError) errors.email = emailError

  const passwordError = validatePassword(input.password)
  if (passwordError) errors.password = passwordError

  const confirmError = validatePasswordConfirmation(input.password, input.confirm)
  if (confirmError) errors.confirm = confirmError

  if (!input.terms) errors.terms = 'Accept the terms to continue.'

  return errors
}

export function validateLoginForm(email: string, password: string): FieldErrors {
  const errors: FieldErrors = {}
  const emailError = validateEmail(email)
  if (emailError) errors.email = emailError
  const passwordError = validatePassword(password)
  if (passwordError) errors.password = passwordError
  return errors
}

export function firstInvalidField(errors: FieldErrors): string | null {
  return Object.keys(errors).find((key) => errors[key]) ?? null
}
