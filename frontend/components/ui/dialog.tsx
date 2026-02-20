import * as React from 'react'
import { cn } from '@/lib/utils'
import { X } from 'lucide-react'

interface DialogContextValue {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const DialogContext = React.createContext<DialogContextValue | null>(null)

interface DialogProps {
  open?: boolean
  onOpenChange?: (open: boolean) => void
  children: React.ReactNode
}

export function Dialog({ open = false, onOpenChange, children }: DialogProps) {
  const [internalOpen, setInternalOpen] = React.useState(open)
  const isOpen = onOpenChange ? open : internalOpen
  const setIsOpen = onOpenChange || setInternalOpen

  return (
    <DialogContext.Provider value={{ open: isOpen, onOpenChange: setIsOpen }}>
      {children}
    </DialogContext.Provider>
  )
}

interface DialogTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean
}

export function DialogTrigger({ children, asChild, ...props }: DialogTriggerProps) {
  const context = React.useContext(DialogContext)
  if (!context) throw new Error('DialogTrigger must be used within Dialog')

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children as React.ReactElement<{ onClick?: () => void }>, {
      onClick: () => context.onOpenChange(true),
    })
  }

  return (
    <button type="button" onClick={() => context.onOpenChange(true)} {...props}>
      {children}
    </button>
  )
}

interface DialogContentProps extends React.HTMLAttributes<HTMLDivElement> {
  showClose?: boolean
}

export function DialogContent({ className, children, showClose = true, ...props }: DialogContentProps) {
  const context = React.useContext(DialogContext)
  if (!context) throw new Error('DialogContent must be used within Dialog')

  if (!context.open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={() => context.onOpenChange(false)}
      />
      <div
        className={cn(
          'relative z-10 w-full max-w-lg mx-4',
          'bg-[#12141a] border border-white/10 rounded-2xl shadow-2xl shadow-black/50',
          'animate-fade-in-up',
          className
        )}
        {...props}
      >
        {showClose && (
          <button
            type="button"
            onClick={() => context.onOpenChange(false)}
            className="absolute top-4 right-4 p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        )}
        {children}
      </div>
    </div>
  )
}

export function DialogHeader({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('px-6 pt-6 pb-4', className)} {...props}>
      {children}
    </div>
  )
}

export function DialogTitle({ className, children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h2 className={cn('text-xl font-serif text-white', className)} {...props}>
      {children}
    </h2>
  )
}

export function DialogDescription({ className, children, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={cn('text-sm text-zinc-400 mt-2', className)} {...props}>
      {children}
    </p>
  )
}

export function DialogFooter({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('px-6 py-4 border-t border-white/5 flex items-center justify-end gap-3', className)} {...props}>
      {children}
    </div>
  )
}
