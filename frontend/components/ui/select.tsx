import * as React from 'react'
import { cn } from '@/lib/utils'
import { ChevronDown, Check } from 'lucide-react'

interface SelectOption {
  value: string
  label: string
  disabled?: boolean
}

interface SelectContextValue {
  value: string
  onChange: (value: string) => void
  open: boolean
  setOpen: (open: boolean) => void
}

const SelectContext = React.createContext<SelectContextValue | null>(null)

interface SelectProps {
  value?: string
  defaultValue?: string
  onValueChange?: (value: string) => void
  children: React.ReactNode
  disabled?: boolean
}

export function Select({ value, defaultValue = '', onValueChange, children, disabled }: SelectProps) {
  const [open, setOpen] = React.useState(false)
  const [selectedValue, setSelectedValue] = React.useState(value ?? defaultValue)

  const handleChange = (newValue: string) => {
    setSelectedValue(newValue)
    onValueChange?.(newValue)
    setOpen(false)
  }

  return (
    <SelectContext.Provider value={{ value: selectedValue, onChange: handleChange, open, setOpen }}>
      <div className="relative" data-disabled={disabled}>
        {children}
      </div>
    </SelectContext.Provider>
  )
}

interface SelectTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  placeholder?: string
}

export function SelectTrigger({ className, placeholder, children, ...props }: SelectTriggerProps) {
  const context = React.useContext(SelectContext)
  if (!context) throw new Error('SelectTrigger must be used within Select')

  return (
    <button
      type="button"
      className={cn(
        'flex items-center justify-between w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white',
        'focus:outline-none focus:border-amber-500/50 focus:ring-2 focus:ring-amber-500/20',
        'transition-all duration-300 hover:bg-white/[0.07]',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className
      )}
      onClick={() => context.setOpen(!context.open)}
      {...props}
    >
      {children || <span className="text-zinc-500">{placeholder}</span>}
      <ChevronDown className={cn(
        'w-4 h-4 text-zinc-400 transition-transform duration-200',
        context.open && 'rotate-180'
      )} />
    </button>
  )
}

interface SelectContentProps extends React.HTMLAttributes<HTMLDivElement> {}

export function SelectContent({ className, children, ...props }: SelectContentProps) {
  const context = React.useContext(SelectContext)
  if (!context) throw new Error('SelectContent must be used within Select')

  if (!context.open) return null

  return (
    <div
      className={cn(
        'absolute top-full left-0 right-0 mt-2 z-50',
        'bg-[#12141a] border border-white/10 rounded-xl shadow-xl shadow-black/30',
        'overflow-hidden animate-fade-in',
        className
      )}
      {...props}
    >
      <div className="max-h-60 overflow-y-auto py-1">
        {children}
      </div>
    </div>
  )
}

interface SelectItemProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string
  disabled?: boolean
}

export function SelectItem({ value, disabled, className, children, ...props }: SelectItemProps) {
  const context = React.useContext(SelectContext)
  if (!context) throw new Error('SelectItem must be used within Select')

  const isSelected = context.value === value

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-4 py-2.5 cursor-pointer transition-colors',
        'hover:bg-white/5',
        isSelected && 'bg-amber-500/10 text-amber-400',
        disabled && 'opacity-50 cursor-not-allowed pointer-events-none',
        className
      )}
      onClick={() => !disabled && context.onChange(value)}
      {...props}
    >
      <span className="flex-1">{children}</span>
      {isSelected && <Check className="w-4 h-4" />}
    </div>
  )
}

export function SelectValue({ placeholder }: { placeholder?: string }) {
  const context = React.useContext(SelectContext)
  if (!context) throw new Error('SelectValue must be used within Select')

  return (
    <span className={context.value ? 'text-white' : 'text-zinc-500'}>
      {context.value || placeholder}
    </span>
  )
}
