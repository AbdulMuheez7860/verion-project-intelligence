import { PRDetailView } from '@/components/route-views'
export default async function PullRequestDetailPage({ params }: { params: Promise<{ id: string }> }) { const { id } = await params; return <PRDetailView id={Number(id)} /> }
