import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, label, error, hint, leftIcon, rightIcon, id, ...props }, ref) => {
    const inputId = id || `input-${Math.random().toString(36).slice(2, 11)}`
    
    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-zinc-300 mb-2"
          >
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500">
              {leftIcon}
            </div>
          )}
          <input
            type={type}
            id={inputId}
            className={cn(
              'w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-zinc-500',
              'focus:outline-none focus:border-amber-500/50 focus:ring-2 focus:ring-amber-500/20',
              'transition-all duration-300',
              'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-white/[0.02]',
              error && 'border-rose-500/50 focus:border-rose-500/50 focus:ring-rose-500/20',
              leftIcon && 'pl-12',
              rightIcon && 'pr-12',
              className
            )}
            ref={ref}
            {...props}
          />
          {rightIcon && (
            <div className="absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500">
              {rightIcon}
            </div>
          )}
        </div>
        {error && (
          <p className="mt-2 text-sm text-rose-400">{error}</p>
        )}
        {hint && !error && (
          <p className="mt-2 text-sm text-zinc-500">{hint}</p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
