import * as React from 'react'
import { cn } from '@/lib/utils'
import { X } from 'lucide-react'

interface ToastContextValue {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
}

interface Toast {
  id: string
  title?: string
  description?: string
  variant?: 'default' | 'success' | 'warning' | 'error'
  duration?: number
}

const ToastContext = React.createContext<ToastContextValue | null>(null)

export function useToast() {
  const context = React.useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within ToastProvider')
  return context
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([])

  const addToast = React.useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).slice(2, 11)
    const newToast = { ...toast, id }
    setToasts((prev) => [...prev, newToast])

    const duration = toast.duration ?? 5000
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, duration)
  }, [])

  const removeToast = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer />
    </ToastContext.Provider>
  )
}

function ToastContainer() {
  const context = React.useContext(ToastContext)
  if (!context) return null

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      {context.toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onClose={() => context.removeToast(toast.id)} />
      ))}
    </div>
  )
}

const variantStyles = {
  default: 'border-white/10 bg-[#12141a]',
  success: 'border-emerald-500/30 bg-emerald-500/10',
  warning: 'border-yellow-500/30 bg-yellow-500/10',
  error: 'border-rose-500/30 bg-rose-500/10',
}

const iconColors = {
  default: 'text-amber-400',
  success: 'text-emerald-400',
  warning: 'text-yellow-400',
  error: 'text-rose-400',
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  return (
    <div
      className={cn(
        'relative flex items-start gap-3 p-4 rounded-xl border shadow-lg shadow-black/30',
        'animate-fade-in-up backdrop-blur-xl',
        variantStyles[toast.variant || 'default']
      )}
    >
      <div className="flex-1">
        {toast.title && (
          <p className="font-medium text-white text-sm">{toast.title}</p>
        )}
        {toast.description && (
          <p className="text-sm text-zinc-400 mt-1">{toast.description}</p>
        )}
      </div>
      <button
        onClick={onClose}
        className="text-zinc-500 hover:text-white transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}
