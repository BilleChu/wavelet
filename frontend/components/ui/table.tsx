import * as React from 'react'
import { cn } from '@/lib/utils'

interface TableContextValue {
  striped?: boolean
  hoverable?: boolean
}

const TableContext = React.createContext<TableContextValue>({})

interface TableProps extends React.HTMLAttributes<HTMLTableElement> {
  striped?: boolean
  hoverable?: boolean
}

export function Table({ striped = true, hoverable = true, className, children, ...props }: TableProps) {
  return (
    <TableContext.Provider value={{ striped, hoverable }}>
      <div className="w-full overflow-x-auto rounded-xl border border-white/5">
        <table className={cn('w-full caption-bottom text-sm', className)} {...props}>
          {children}
        </table>
      </div>
    </TableContext.Provider>
  )
}

export function TableHeader({ className, children, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <thead className={cn('border-b border-white/10', className)} {...props}>
      {children}
    </thead>
  )
}

export function TableBody({ className, children, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return (
    <tbody className={cn('[&_tr:last-child]:border-0', className)} {...props}>
      {children}
    </tbody>
  )
}

export function TableRow({ className, children, ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  const { striped, hoverable } = React.useContext(TableContext)
  
  return (
    <tr
      className={cn(
        'border-b border-white/5 transition-colors',
        striped && 'even:bg-white/[0.02]',
        hoverable && 'hover:bg-white/5',
        className
      )}
      {...props}
    >
      {children}
    </tr>
  )
}

export function TableHead({ className, children, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn(
        'h-12 px-4 text-left align-middle font-medium text-zinc-400 text-sm',
        '[&:has([role=checkbox])]:pr-0',
        className
      )}
      {...props}
    >
      {children}
    </th>
  )
}

export function TableCell({ className, children, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={cn(
        'p-4 align-middle text-white [&:has([role=checkbox])]:pr-0',
        className
      )}
      {...props}
    >
      {children}
    </td>
  )
}

export function TableCaption({ className, children, ...props }: React.HTMLAttributes<HTMLTableCaptionElement>) {
  return (
    <caption className={cn('mt-4 text-sm text-zinc-500', className)} {...props}>
      {children}
    </caption>
  )
}

export function TableEmpty({ colSpan, message = '暂无数据' }: { colSpan: number; message?: string }) {
  return (
    <TableRow>
      <TableCell colSpan={colSpan} className="h-32 text-center text-zinc-500">
        {message}
      </TableCell>
    </TableRow>
  )
}
