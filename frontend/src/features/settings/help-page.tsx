import { BookOpen, Code2, GitBranch, HelpCircle, ShieldCheck, Sparkles } from 'lucide-react'
import { PageHeader } from '@/components/layout/page-header'
import { Input } from '@/components/ui/input'

const guides = [
  { icon: BookOpen, title: 'Getting started', text: 'Connect GitHub and run your first repository analysis.' },
  { icon: GitBranch, title: 'GitHub integration', text: 'Understand permissions, webhooks, and repository sync.' },
  { icon: ShieldCheck, title: 'Understanding risk scores', text: 'Learn how Verion weighs change complexity and findings.' },
  { icon: Code2, title: 'Code quality', text: 'Explore maintainability, complexity, and technical debt.' },
  { icon: Sparkles, title: 'AI reviews', text: 'See how AI context complements deterministic analysis.' },
  { icon: HelpCircle, title: 'Frequently asked questions', text: 'Answers to the questions teams ask most often.' },
]

export function HelpPage() {
  return (
    <div>
      <PageHeader
        eyebrow="Resources"
        title="Help center"
        description="Learn how Verion turns code changes into engineering decisions."
        action={<Input placeholder="Search help (coming soon)" className="max-w-xs" disabled aria-label="Search help" />}
      />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {guides.map((item) => {
          const Icon = item.icon
          return (
            <button
              key={item.title}
              type="button"
              disabled
              className="rounded-xl border border-border/80 bg-card p-5 text-left shadow-sm opacity-80"
              title="Documentation coming soon"
            >
              <Icon className="size-5 text-primary" aria-hidden="true" />
              <h2 className="mt-5 text-sm font-semibold">{item.title}</h2>
              <p className="mt-2 text-xs leading-5 text-muted-foreground">{item.text}</p>
            </button>
          )
        })}
      </div>
    </div>
  )
}
