import Link from 'next/link'

export default function NotFound() { return <main className="grid min-h-screen place-items-center bg-background p-6"><div className="max-w-md text-center"><p className="font-mono text-sm text-primary">404</p><h1 className="mt-3 text-2xl font-semibold">This Verion page does not exist</h1><p className="mt-2 text-sm text-muted-foreground">Check the address or return to a known workspace.</p><Link href="/" className="mt-5 inline-flex rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">Return home</Link></div></main> }
