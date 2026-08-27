'use client'

import { usePathname, useRouter } from 'next/navigation'
import { AppShell } from '@/components/verion-app'
import { ProtectedGate } from '@/components/route-views'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  return <ProtectedGate><AppShell path={pathname} onNavigate={(href) => router.push(href)}>{children}</AppShell></ProtectedGate>
}
