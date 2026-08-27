'use client'

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) { return <div className="grid min-h-[60vh] place-items-center p-6"><div className="max-w-md text-center"><h1 className="text-xl font-semibold">Workspace data could not load</h1><p className="mt-2 text-sm text-muted-foreground">Try again, or return to the dashboard if the issue continues.</p><button onClick={reset} className="mt-5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">Try again</button></div></div> }
