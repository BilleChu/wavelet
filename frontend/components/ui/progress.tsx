import { cn } from '@/lib/utils'

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number
  max?: number
  variant?: 'default' | 'success' | 'warning' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  showValue?: boolean
}

const variantStyles = {
  default: 'bg-gradient-to-r from-amber-500 to-orange-500',
  success: 'bg-gradient-to-r from-emerald-500 to-teal-500',
  warning: 'bg-gradient-to-r from-yellow-500 to-amber-500',
  danger: 'bg-gradient-to-r from-rose-500 to-pink-500',
}

const sizeStyles = {
  sm: 'h-1',
  md: 'h-2',
  lg: 'h-3',
}

export function Progress({
  value = 0,
  max = 100,
  variant = 'default',
  size = 'md',
  showValue = false,
  className,
  ...props
}: ProgressProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100))

  return (
    <div className={cn('w-full', className)} {...props}>
      <div className={cn('w-full bg-white/5 rounded-full overflow-hidden', sizeStyles[size])}>
        <div
          className={cn('h-full rounded-full transition-all duration-500 ease-out', variantStyles[variant])}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showValue && (
        <p className="text-xs text-zinc-500 mt-1 text-right">{Math.round(percentage)}%</p>
      )}
    </div>
  )
}

export function CircularProgress({
  value = 0,
  max = 100,
  size = 48,
  strokeWidth = 4,
  variant = 'default',
  showValue = false,
  className,
}: {
  value?: number
  max?: number
  size?: number
  strokeWidth?: number
  variant?: 'default' | 'success' | 'warning' | 'danger'
  showValue?: boolean
  className?: string
}) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100))
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const offset = circumference - (percentage / 100) * circumference

  const colors = {
    default: '#f59e0b',
    success: '#10b981',
    warning: '#eab308',
    danger: '#f43f5e',
  }

  return (
    <div className={cn('relative inline-flex', className)} style={{ width: size, height: size }}>
      <svg className="transform -rotate-90" width={size} height={size}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={colors[variant]}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-500 ease-out"
        />
      </svg>
      {showValue && (
        <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-white">
          {Math.round(percentage)}%
        </span>
      )}
    </div>
  )
}
