import * as React from 'react'
import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'secondary' | 'outline' | 'ghost' | 'link' | 'danger'
  size?: 'default' | 'sm' | 'lg' | 'icon'
  loading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

export function Button({
  className,
  variant = 'default',
  size = 'default',
  loading = false,
  leftIcon,
  rightIcon,
  children,
  disabled,
  ...props
}: ButtonProps) {
  const baseStyles = cn(
    'inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all duration-300',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)]',
    'disabled:pointer-events-none disabled:opacity-50'
  )

  const variants = {
    default: 'bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:shadow-lg hover:shadow-amber-500/30 hover:-translate-y-0.5 active:translate-y-0',
    secondary: 'bg-white/10 text-white hover:bg-white/15 active:bg-white/10',
    outline: 'border border-white/10 bg-transparent text-zinc-300 hover:bg-white/5 hover:text-white hover:border-amber-500/30',
    ghost: 'text-zinc-400 hover:text-white hover:bg-white/5',
    link: 'text-amber-400 underline-offset-4 hover:underline hover:text-amber-300',
    danger: 'bg-gradient-to-r from-rose-500 to-pink-500 text-white hover:shadow-lg hover:shadow-rose-500/30',
  }

  const sizes = {
    default: 'h-11 px-5 py-2.5 text-sm',
    sm: 'h-9 px-4 text-sm',
    lg: 'h-12 px-8 text-base',
    icon: 'h-11 w-11',
  }

  return (
    <button
      className={cn(baseStyles, variants[variant], sizes[size], className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        leftIcon
      )}
      {children}
      {!loading && rightIcon}
    </button>
  )
}
