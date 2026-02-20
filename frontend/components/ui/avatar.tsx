import * as React from 'react'
import Image from 'next/image'
import { cn } from '@/lib/utils'

interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  src?: string
  alt?: string
  fallback?: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

const sizeStyles = {
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-12 h-12 text-base',
  xl: 'w-16 h-16 text-lg',
}

const sizePixels = {
  sm: 32,
  md: 40,
  lg: 48,
  xl: 64,
}

export function Avatar({
  src,
  alt,
  fallback,
  size = 'md',
  className,
  children,
  ...props
}: AvatarProps) {
  const [error, setError] = React.useState(false)

  const initials = fallback
    ? fallback.slice(0, 2).toUpperCase()
    : alt?.slice(0, 2).toUpperCase() || '?'

  return (
    <div
      className={cn(
        'relative inline-flex items-center justify-center rounded-full overflow-hidden',
        'bg-gradient-to-br from-amber-500/20 to-orange-600/20 border border-white/10',
        sizeStyles[size],
        className
      )}
      {...props}
    >
      {src && !error ? (
        <Image
          src={src}
          alt={alt || 'Avatar'}
          width={sizePixels[size]}
          height={sizePixels[size]}
          className="object-cover"
          onError={() => setError(true)}
        />
      ) : (
        <span className="font-medium text-amber-400">{initials}</span>
      )}
      {children}
    </div>
  )
}

export function AvatarGroup({
  children,
  max = 4,
  className,
}: {
  children: React.ReactNode
  max?: number
  className?: string
}) {
  const childArray = React.Children.toArray(children)
  const visibleChildren = childArray.slice(0, max)
  const remainingCount = childArray.length - max

  return (
    <div className={cn('flex -space-x-2', className)}>
      {visibleChildren.map((child, index) => (
        <div key={index} className="ring-2 ring-[var(--background)] rounded-full">
          {child}
        </div>
      ))}
      {remainingCount > 0 && (
        <div className="w-8 h-8 rounded-full bg-white/10 border border-white/10 flex items-center justify-center text-xs text-zinc-400 ring-2 ring-[var(--background)]">
          +{remainingCount}
        </div>
      )}
    </div>
  )
}
