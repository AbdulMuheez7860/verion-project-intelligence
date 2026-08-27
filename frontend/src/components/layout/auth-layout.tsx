import type { ReactNode } from 'react'
import { LogoLink } from '@/components/navigation/logo'

const valueProps = [
  'Understand engineering risk before it reaches production.',
  'Deterministic scanners, explainable scores, and actionable findings.',
  'Built for teams who need precision—not decorative dashboards.',
] as const

export function AuthLayout({
  title,
  description,
  children,
  footer,
}: {
  title: string
  description: string
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="grid min-h-screen bg-background lg:grid-cols-[minmax(0,1.1fr)_minmax(360px,440px)]">
      <section className="relative hidden flex-col justify-between overflow-hidden border-r border-border bg-primary px-10 py-10 text-primary-foreground lg:flex">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,oklch(1_0_0/0.08),transparent_45%)]" />
        <div className="relative">
          <LogoLink to="/login" variant="inverse" />
        </div>
        <div className="relative max-w-lg space-y-6">
          <h2 className="text-3xl font-semibold leading-tight tracking-tight">
            Engineering intelligence for production teams.
          </h2>
          <ul className="space-y-3">
            {valueProps.map((item) => (
              <li key={item} className="flex gap-3 text-sm leading-6 text-primary-foreground/85">
                <span className="mt-2 size-1.5 shrink-0 rounded-full bg-primary-foreground/70" aria-hidden="true" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-primary-foreground/70">Verion — precision over decoration.</p>
      </section>

      <section className="flex items-center justify-center px-4 py-8 sm:px-6">
        <div className="w-full max-w-md">
          <div className="mb-6 lg:hidden">
            <LogoLink to="/login" />
          </div>
          <div className="rounded-xl border border-border bg-card p-6 shadow-elevation-1 sm:p-8">
            <header className="mb-6">
              <h1 className="text-page-title">{title}</h1>
              <p className="mt-2 text-page-description">{description}</p>
            </header>
            {children}
            {footer ? <div className="mt-6 border-t border-border pt-4">{footer}</div> : null}
          </div>
        </div>
      </section>
    </div>
  )
}
