import { cn } from '@/lib/utils'

interface SpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'md' | 'lg'
  variant?: 'default' | 'light'
}

const sizeStyles = {
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
}

export function Spinner({ size = 'md', variant = 'default', className, ...props }: SpinnerProps) {
  return (
    <div
      className={cn(
        'animate-spin rounded-full border-2 border-transparent',
        sizeStyles[size],
        variant === 'default' ? 'border-t-amber-500 border-r-amber-500' : 'border-t-white border-r-white',
        className
      )}
      {...props}
    />
  )
}

interface LoadingProps {
  text?: string
  className?: string
}

export function Loading({ text = '加载中...', className }: LoadingProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3 py-12', className)}>
      <Spinner size="lg" />
      <p className="text-sm text-zinc-500">{text}</p>
    </div>
  )
}

export function PageLoading() {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-[var(--background)]">
      <div className="flex flex-col items-center gap-4">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center animate-pulse-glow">
          <Spinner size="lg" variant="light" />
        </div>
        <p className="text-zinc-400">加载中...</p>
      </div>
    </div>
  )
}
