import * as React from 'react'
import { cn } from '@/lib/utils'

interface TooltipContextValue {
  open: boolean
  setOpen: (open: boolean) => void
}

const TooltipContext = React.createContext<TooltipContextValue | null>(null)

interface TooltipProps {
  children: React.ReactNode
}

export function Tooltip({ children }: TooltipProps) {
  const [open, setOpen] = React.useState(false)

  return (
    <TooltipContext.Provider value={{ open, setOpen }}>
      <div className="relative inline-block">{children}</div>
    </TooltipContext.Provider>
  )
}

interface TooltipTriggerProps extends React.HTMLAttributes<HTMLDivElement> {
  asChild?: boolean
}

export function TooltipTrigger({ children, asChild, ...props }: TooltipTriggerProps) {
  const context = React.useContext(TooltipContext)
  if (!context) throw new Error('TooltipTrigger must be used within Tooltip')

  return (
    <div
      onMouseEnter={() => context.setOpen(true)}
      onMouseLeave={() => context.setOpen(false)}
      {...props}
    >
      {children}
    </div>
  )
}

interface TooltipContentProps extends React.HTMLAttributes<HTMLDivElement> {
  side?: 'top' | 'bottom' | 'left' | 'right'
  align?: 'start' | 'center' | 'end'
}

export function TooltipContent({
  side = 'top',
  align = 'center',
  className,
  children,
  ...props
}: TooltipContentProps) {
  const context = React.useContext(TooltipContext)
  if (!context) throw new Error('TooltipContent must be used within Tooltip')

  if (!context.open) return null

  const sideStyles = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  }

  const alignStyles = {
    start: '',
    center: '',
    end: '',
  }

  return (
    <div
      className={cn(
        'absolute z-50 px-3 py-1.5 text-sm',
        'bg-[#1a1b20] border border-white/10 rounded-lg shadow-xl',
        'text-zinc-300 whitespace-nowrap',
        'animate-fade-in',
        sideStyles[side],
        alignStyles[align],
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}
