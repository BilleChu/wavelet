import * as React from 'react'
import { cn } from '@/lib/utils'
import { Slot } from '@radix-ui/react-slot'

interface DropdownMenuContextValue {
  open: boolean
  setOpen: (open: boolean) => void
}

const DropdownMenuContext = React.createContext<DropdownMenuContextValue | null>(null)

interface DropdownMenuProps {
  children: React.ReactNode
}

export function DropdownMenu({ children }: DropdownMenuProps) {
  const [open, setOpen] = React.useState(false)

  return (
    <DropdownMenuContext.Provider value={{ open, setOpen }}>
      <div className="relative inline-block">{children}</div>
    </DropdownMenuContext.Provider>
  )
}

interface DropdownMenuTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean
}

export function DropdownMenuTrigger({ className, children, asChild, ...props }: DropdownMenuTriggerProps) {
  const context = React.useContext(DropdownMenuContext)
  if (!context) throw new Error('DropdownMenuTrigger must be used within DropdownMenu')

  if (asChild) {
    const child = React.Children.only(children) as React.ReactElement
    return React.cloneElement(child, {
      ...child.props,
      onClick: () => context.setOpen(!context.open),
    })
  }

  return (
    <button
      type="button"
      className={cn('outline-none', className)}
      onClick={() => context.setOpen(!context.open)}
      {...props}
    >
      {children}
    </button>
  )
}

interface DropdownMenuContentProps extends React.HTMLAttributes<HTMLDivElement> {
  align?: 'start' | 'center' | 'end'
  sideOffset?: number
}

export function DropdownMenuContent({
  align = 'end',
  className,
  children,
  ...props
}: DropdownMenuContentProps) {
  const context = React.useContext(DropdownMenuContext)
  if (!context) throw new Error('DropdownMenuContent must be used within DropdownMenu')

  if (!context.open) return null

  const alignStyles = {
    start: 'left-0',
    center: 'left-1/2 -translate-x-1/2',
    end: 'right-0',
  }

  return (
    <>
      <div
        className="fixed inset-0 z-40"
        onClick={() => context.setOpen(false)}
      />
      <div
        className={cn(
          'absolute top-full mt-2 z-50 min-w-[180px]',
          'bg-[#12141a] border border-white/10 rounded-xl shadow-xl shadow-black/30',
          'overflow-hidden animate-fade-in',
          alignStyles[align],
          className
        )}
        {...props}
      >
        <div className="py-1">{children}</div>
      </div>
    </>
  )
}

interface DropdownMenuItemProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  inset?: boolean
}

export function DropdownMenuItem({ className, inset, children, ...props }: DropdownMenuItemProps) {
  const context = React.useContext(DropdownMenuContext)
  if (!context) throw new Error('DropdownMenuItem must be used within DropdownMenu')

  return (
    <button
      type="button"
      className={cn(
        'relative flex w-full cursor-pointer select-none items-center gap-2 px-4 py-2.5 text-sm',
        'text-zinc-300 outline-none transition-colors',
        'hover:bg-white/5 hover:text-white',
        'focus:bg-white/5 focus:text-white',
        inset && 'pl-8',
        className
      )}
      onClick={() => context.setOpen(false)}
      {...props}
    >
      {children}
    </button>
  )
}

export function DropdownMenuSeparator({ className }: { className?: string }) {
  return <div className={cn('my-1 h-px bg-white/5', className)} />
}

export function DropdownMenuLabel({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={cn('px-4 py-2 text-xs font-medium text-zinc-500', className)}>
      {children}
    </div>
  )
}
