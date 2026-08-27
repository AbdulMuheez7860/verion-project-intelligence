import { useEffect, useRef, useState } from 'react'
import { Bot, Send, ShieldAlert } from 'lucide-react'
import { assistantApi } from '@/api/assistant'
import { isApiError } from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AssistantChatMessage, AssistantStatusResponse } from '@/types/api'

const SUGGESTED_PROMPTS = [
  'What should I fix first?',
  'Why is my security score low?',
  'What are my biggest technical-debt problems?',
  'What should I fix before an interview?',
]

interface DisplayMessage extends AssistantChatMessage {
  id: string
  evidenceLabels?: string[]
  hasSufficientEvidence?: boolean
}

export function AssistantPanel({ repositoryId }: { repositoryId: string }) {
  const [status, setStatus] = useState<AssistantStatusResponse | null>(null)
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let cancelled = false
    void assistantApi
      .status(repositoryId)
      .then((result) => {
        if (!cancelled) setStatus(result)
      })
      .catch(() => {
        if (!cancelled) setStatus({ available: false, reason: 'Could not reach the assistant.', hasAnalysisData: false })
      })
    return () => {
      cancelled = true
    }
  }, [repositoryId])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  async function send(message: string) {
    if (!message.trim() || sending) return
    setError(null)
    const userMessage: DisplayMessage = { id: `u-${Date.now()}`, role: 'user', content: message.trim() }
    const history: AssistantChatMessage[] = messages.map(({ role, content }) => ({ role, content }))
    setMessages((current) => [...current, userMessage])
    setInput('')
    setSending(true)
    try {
      const response = await assistantApi.chat(repositoryId, message.trim(), history)
      setMessages((current) => [
        ...current,
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          content: response.reply,
          evidenceLabels: response.evidence.map((e) => e.label),
          hasSufficientEvidence: response.hasSufficientEvidence,
        },
      ])
    } catch (err) {
      const message = isApiError(err) ? err.message : 'The assistant could not respond. Try again.'
      setError(message)
    } finally {
      setSending(false)
    }
  }

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="size-4 text-primary" aria-hidden="true" />
          <CardTitle>AI Project Assistant</CardTitle>
        </div>
        {status && !status.available ? <Badge tone="neutral">Unavailable</Badge> : null}
      </CardHeader>
      <CardContent className="space-y-4">
        {status && !status.available ? (
          <div className="flex items-start gap-2 rounded-md border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
            <ShieldAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <span>{status.reason ?? 'The AI assistant is not available for this repository yet.'}</span>
          </div>
        ) : null}

        {status?.available ? (
          <>
            <div
              ref={scrollRef}
              className="flex max-h-96 flex-col gap-3 overflow-y-auto rounded-md border border-border bg-muted/20 p-3"
            >
              {messages.length === 0 ? (
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Ask about this repository&apos;s actual analysis results — findings, scores, and what to fix first.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {SUGGESTED_PROMPTS.map((prompt) => (
                      <button
                        key={prompt}
                        type="button"
                        onClick={() => void send(prompt)}
                        className="rounded-full border border-border bg-background px-3 py-1 text-xs text-foreground hover:bg-muted"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}
              {messages.map((msg) => (
                <div key={msg.id} className={msg.role === 'user' ? 'ml-auto max-w-[85%]' : 'mr-auto max-w-[85%]'}>
                  <div
                    className={
                      msg.role === 'user'
                        ? 'rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground'
                        : 'rounded-lg border border-border bg-card px-3 py-2 text-sm'
                    }
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                  {msg.role === 'assistant' && msg.evidenceLabels && msg.evidenceLabels.length > 0 ? (
                    <p className="mt-1 text-xs text-muted-foreground">
                      Grounded in: {msg.evidenceLabels.join(', ')}
                    </p>
                  ) : null}
                  {msg.role === 'assistant' && msg.hasSufficientEvidence === false ? (
                    <p className="mt-1 text-xs text-warning">Verion did not have enough evidence for a full answer here.</p>
                  ) : null}
                </div>
              ))}
              {sending ? <p className="text-xs text-muted-foreground">Verion is thinking…</p> : null}
            </div>

            {error ? (
              <p className="text-xs text-destructive" role="alert">
                {error}
              </p>
            ) : null}

            <form
              className="flex gap-2"
              onSubmit={(event) => {
                event.preventDefault()
                void send(input)
              }}
            >
              <input
                type="text"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Ask about your findings, scores, or what to fix first…"
                className="h-9 flex-1 rounded-md border border-border bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                disabled={sending}
                maxLength={4000}
              />
              <Button type="submit" size="sm" disabled={sending || !input.trim()}>
                <Send className="size-3.5" />
                Send
              </Button>
            </form>
            <p className="text-[11px] text-muted-foreground">
              AI-generated, grounded in this repository&apos;s stored analysis. Verify against the underlying findings
              before acting on security-critical items.
            </p>
          </>
        ) : null}
      </CardContent>
    </Card>
  )
}
