import { describe, expect, it } from 'vitest'
import {
  validateEmail,
  validateLoginForm,
  validatePassword,
  validatePasswordConfirmation,
  validateSignupForm,
} from '@/lib/auth-validation'

describe('auth validation', () => {
  it('validates email format', () => {
    expect(validateEmail('')).toMatch(/required/i)
    expect(validateEmail('not-an-email')).toMatch(/valid email/i)
    expect(validateEmail('user@acme.dev')).toBeNull()
  })

  it('validates password length', () => {
    expect(validatePassword('short')).toMatch(/8 characters/i)
    expect(validatePassword('password123')).toBeNull()
  })

  it('validates password confirmation', () => {
    expect(validatePasswordConfirmation('password123', 'different')).toMatch(/do not match/i)
    expect(validatePasswordConfirmation('password123', 'password123')).toBeNull()
  })

  it('validates login form fields', () => {
    const errors = validateLoginForm('', '')
    expect(errors.email).toBeTruthy()
    expect(errors.password).toBeTruthy()
  })

  it('validates signup form fields', () => {
    const errors = validateSignupForm({
      name: '',
      team: '',
      email: 'bad',
      password: 'short',
      confirm: 'other',
      terms: false,
    })
    expect(errors.name).toBeTruthy()
    expect(errors.team).toBeTruthy()
    expect(errors.email).toBeTruthy()
    expect(errors.password).toBeTruthy()
    expect(errors.confirm).toBeTruthy()
    expect(errors.terms).toBeTruthy()
  })
})
