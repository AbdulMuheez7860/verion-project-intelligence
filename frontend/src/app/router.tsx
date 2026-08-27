import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import { AppShell } from '@/components/layout/app-shell'
import { ProtectedRoute, PublicOnlyRoute } from '@/components/layout/protected-route'
import { AnalyticsPage } from '@/features/analytics/analytics-page'
import { ForgotPasswordPage } from '@/features/auth/forgot-password-page'
import { LoginPage } from '@/features/auth/login-page'
import { ResetPasswordPage } from '@/features/auth/reset-password-page'
import { SignupPage } from '@/features/auth/signup-page'
import { CodeQualityPage } from '@/features/code-quality/code-quality-page'
import { DashboardPage } from '@/features/dashboard/dashboard-page'
import { DependenciesPage } from '@/features/dependencies/dependencies-page'
import { NotificationsPage } from '@/features/notifications/notifications-page'
import { OnboardingPage } from '@/features/onboarding/onboarding-page'
import { PullRequestDetailPage } from '@/features/pull-requests/pull-request-detail-page'
import { PullRequestsPage } from '@/features/pull-requests/pull-requests-page'
import { AnalysisRunDetailPage } from '@/features/repositories/analysis-run-detail-page'
import { AnalysisRunsPage } from '@/features/analysis-runs/analysis-runs-page'
import { GlobalAnalysisRunDetailPage } from '@/features/analysis-runs/analysis-run-detail-page'
import { ConnectRepositoryPage } from '@/features/repositories/connect-repository-page'
import { RepositoriesPage } from '@/features/repositories/repositories-page'
import { RepositoryDetailPage } from '@/features/repositories/repository-detail-page'
import { FindingDetailPage } from '@/features/security/finding-detail-page'
import { SecurityPage } from '@/features/security/security-page'
import { HelpPage } from '@/features/settings/help-page'
import {
  AccountSettingsPage,
  AnalysisSettingsPage,
  AuditLogSettingsPage,
  GeneralSettingsPage,
  IntegrationsSettingsPage,
  MembersSettingsPage,
  NotificationsSettingsPage,
  SecuritySettingsPage,
  SettingsLayout,
} from '@/features/settings/settings-pages'

function NotFoundPage() {
  return (
    <main className="grid min-h-screen place-items-center p-6">
      <div className="max-w-md text-center">
        <p className="font-mono text-sm text-primary">404</p>
        <h1 className="mt-3 text-2xl font-semibold">This page does not exist</h1>
        <p className="mt-2 text-sm text-muted-foreground">Check the address or return to the dashboard.</p>
        <a href="/app/dashboard" className="mt-5 inline-flex rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
          Go to dashboard
        </a>
      </div>
    </main>
  )
}

const router = createBrowserRouter([
  { path: '/', element: <Navigate to="/app/dashboard" replace /> },
  {
    element: <PublicOnlyRoute />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/signup', element: <SignupPage /> },
      { path: '/forgot-password', element: <ForgotPasswordPage /> },
      { path: '/reset-password', element: <ResetPasswordPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      { path: '/onboarding', element: <OnboardingPage /> },
      {
        element: <AppShell />,
        children: [
          { path: '/app', element: <Navigate to="/app/dashboard" replace /> },
          { path: '/app/dashboard', element: <DashboardPage /> },
          { path: '/app/repositories', element: <RepositoriesPage /> },
          { path: '/app/repositories/connect', element: <ConnectRepositoryPage /> },
          { path: '/app/repositories/:id', element: <RepositoryDetailPage /> },
          { path: '/app/repositories/:id/analysis/:analysisId', element: <AnalysisRunDetailPage /> },
          { path: '/app/analysis-runs', element: <AnalysisRunsPage /> },
          { path: '/app/analysis-runs/:analysisId', element: <GlobalAnalysisRunDetailPage /> },
          { path: '/app/pull-requests', element: <PullRequestsPage /> },
          { path: '/app/pull-requests/:id', element: <PullRequestDetailPage /> },
          { path: '/app/code-quality', element: <CodeQualityPage /> },
          { path: '/app/security', element: <SecurityPage /> },
          { path: '/app/security/findings/:findingId', element: <FindingDetailPage /> },
          { path: '/app/dependencies', element: <DependenciesPage /> },
          { path: '/app/analytics', element: <AnalyticsPage /> },
          { path: '/app/notifications', element: <NotificationsPage /> },
          {
            path: '/app/settings',
            element: <SettingsLayout />,
            children: [
              { index: true, element: <Navigate to="/app/settings/general" replace /> },
              { path: 'general', element: <GeneralSettingsPage /> },
              { path: 'members', element: <MembersSettingsPage /> },
              { path: 'integrations', element: <IntegrationsSettingsPage /> },
              { path: 'analysis', element: <AnalysisSettingsPage /> },
              { path: 'notifications', element: <NotificationsSettingsPage /> },
              { path: 'security', element: <SecuritySettingsPage /> },
              { path: 'audit-log', element: <AuditLogSettingsPage /> },
              { path: 'account', element: <AccountSettingsPage /> },
              { path: 'profile', element: <Navigate to="/app/settings/account" replace /> },
              { path: 'team', element: <Navigate to="/app/settings/members" replace /> },
              { path: 'help', element: <HelpPage /> },
            ],
          },
        ],
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
])

export function AppRouter() {
  return <RouterProvider router={router} />
}