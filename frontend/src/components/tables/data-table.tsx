import type { HTMLAttributes, ReactNode, TdHTMLAttributes, TableHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export function DataTable({
  children,
  className,
  ...props
}: TableHTMLAttributes<HTMLTableElement> & { children: ReactNode }) {
  return (
    <div className={cn('overflow-x-auto rounded-lg border border-border bg-card', className)}>
      <table className="w-full min-w-[640px] border-collapse text-left text-[13px] leading-5" {...props}>
        {children}
      </table>
    </div>
  )
}

export function DataTableHead({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <thead className={cn('border-b border-border bg-muted/40 text-[11px] font-medium uppercase tracking-wide text-muted-foreground', className)}>
      {children}
    </thead>
  )
}

export function DataTableHeaderCell({
  children,
  className,
  align = 'left',
}: {
  children: ReactNode
  className?: string
  align?: 'left' | 'right' | 'center'
}) {
  return (
    <th
      scope="col"
      className={cn(
        'px-4 py-2.5 font-medium',
        align === 'right' && 'text-right',
        align === 'center' && 'text-center',
        className,
      )}
    >
      {children}
    </th>
  )
}

export function DataTableBody({ children }: { children: ReactNode }) {
  return <tbody className="divide-y divide-border">{children}</tbody>
}

export function DataTableRow({
  children,
  className,
  ...props
}: HTMLAttributes<HTMLTableRowElement> & { children: ReactNode }) {
  return (
    <tr className={cn('transition-colors hover:bg-muted/25 focus-within:bg-muted/25', className)} {...props}>
      {children}
    </tr>
  )
}

export function DataTableCell({
  children,
  className,
  mono = false,
  align = 'left',
  ...props
}: TdHTMLAttributes<HTMLTableCellElement> & {
  children: ReactNode
  mono?: boolean
  align?: 'left' | 'right' | 'center'
}) {
  return (
    <td
      className={cn(
        'px-4 py-2.5 align-middle',
        mono && 'font-mono tabular-nums text-[12px]',
        align === 'right' && 'text-right',
        align === 'center' && 'text-center',
        className,
      )}
      {...props}
    >
      {children}
    </td>
  )
}

export function DataList({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('overflow-hidden rounded-lg border border-border bg-card', className)}>{children}</div>
}

export function DataListHeader({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'hidden border-b border-border bg-muted/40 px-4 py-2.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground md:grid',
        className,
      )}
    >
      {children}
    </div>
  )
}
