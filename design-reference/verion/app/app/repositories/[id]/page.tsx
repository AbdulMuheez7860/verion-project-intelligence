import { RepositoryDetailView } from '@/components/route-views'
export default async function RepositoryDetailPage({ params }: { params: Promise<{ id: string }> }) { const { id } = await params; return <RepositoryDetailView id={id} /> }
