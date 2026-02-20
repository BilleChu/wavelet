import { cn } from '@/lib/utils'

interface DividerProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: 'horizontal' | 'vertical'
  label?: string
}

export function Divider({
  orientation = 'horizontal',
  label,
  className,
  ...props
}: DividerProps) {
  if (orientation === 'vertical') {
    return (
      <div
        className={cn('w-px bg-white/10', className)}
        {...props}
      />
    )
  }

  if (label) {
    return (
      <div className={cn('flex items-center gap-4', className)} {...props}>
        <div className="flex-1 h-px bg-white/10" />
        <span className="text-sm text-zinc-500">{label}</span>
        <div className="flex-1 h-px bg-white/10" />
      </div>
    )
  }

  return (
    <div
      className={cn('h-px bg-white/10', className)}
      {...props}
    />
  )
}
