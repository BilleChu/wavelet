import { cn } from '@/lib/utils'

interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: React.ReactNode
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
  ...props
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-16 px-4 text-center',
        className
      )}
      {...props}
    >
      {icon && (
        <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center text-zinc-600 mb-4">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-medium text-white mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-zinc-500 max-w-sm mb-6">{description}</p>
      )}
      {action}
    </div>
  )
}

interface ErrorStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string
  message?: string
  retry?: () => void
}

export function ErrorState({
  title = '出错了',
  message = '抱歉，发生了意外错误，请稍后重试。',
  retry,
  className,
  ...props
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-16 px-4 text-center',
        className
      )}
      {...props}
    >
      <div className="w-16 h-16 rounded-2xl bg-rose-500/10 flex items-center justify-center text-rose-400 mb-4">
        <svg
          className="w-8 h-8"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">{title}</h3>
      <p className="text-sm text-zinc-500 max-w-sm mb-6">{message}</p>
      {retry && (
        <button
          onClick={retry}
          className="px-4 py-2 bg-white/5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition-colors"
        >
          重试
        </button>
      )}
    </div>
  )
}
