'use client'

import { useEffect, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Dashboard, DataPage, Help, Landing, Onboarding, PullRequests, Repositories, Settings } from '@/components/verion-app'
import { AuthForm } from '@/components/auth/auth-forms'
import { demoAuthAdapter } from '@/lib/auth/demo-auth-adapter'
import { RepositoryDetail } from '@/components/repositories/repository-detail'
import { SettingsSection } from '@/components/settings/settings-sections'
import { PullRequestDetail } from '@/components/pull-requests/pr-detail'

export function PublicLanding() { const router = useRouter(); return <Landing onNavigate={(href) => router.push(href)} /> }
export function AuthView({ mode }: { mode: 'login' | 'signup' | 'forgot' | 'reset' }) { return <AuthForm mode={mode} /> }
export function OnboardingView() { const router = useRouter(); return <Onboarding onNavigate={(href) => router.push(href)} /> }
export function DashboardView() { const router = useRouter(); return <Dashboard onNavigate={(href) => router.push(href)} /> }
export function RepositoriesView() { const router = useRouter(); return <Repositories onNavigate={(href) => router.push(href)} /> }
export function PullRequestsView() { const router = useRouter(); return <PullRequests onNavigate={(href) => router.push(href)} /> }
export function SettingsView() { const router = useRouter(); return <Settings onNavigate={(href) => router.push(href)} /> }
export function FeatureView({ kind }: { kind: 'quality' | 'security' | 'dependencies' | 'analytics' }) { return <DataPage kind={kind} /> }
export function PRDetailView({ id }: { id: number }) { return <PullRequestDetail id={id} /> }
export function RepositoryDetailView({ id }: { id: string }) { return <RepositoryDetail id={id} /> }
export function SettingsSectionView({ section }: { section: 'profile' | 'team' | 'integrations' | 'notifications' | 'security' }) { return <SettingsSection section={section} /> }
export function HelpView() { return <Help /> }

export function ProtectedGate({ children }: { children: React.ReactNode }) { const router = useRouter(); const pathname = usePathname(); const [ready, setReady] = useState(false); useEffect(() => { const session = demoAuthAdapter.getSession(); if (!session) router.replace(`/login?next=${encodeURIComponent(pathname)}`); else queueMicrotask(() => setReady(true)) }, [pathname, router]); if (!ready) return <div className="grid min-h-[60vh] place-items-center text-sm text-muted-foreground" role="status">Loading your workspace…</div>; return <>{children}</> }
