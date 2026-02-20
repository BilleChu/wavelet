/**
 * Global Application Store using Zustand.
 *
 * Provides centralized state management for:
 * - User preferences and session
 * - Theme settings
 * - Global notifications
 * - Cached data
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface UserPreferences {
  defaultMarket: string
  defaultDateRange: string
  chartTheme: 'light' | 'dark'
  language: 'zh' | 'en'
}

export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message?: string
  timestamp: number
  read: boolean
}

interface AppState {
  theme: 'light' | 'dark'
  sidebarCollapsed: boolean
  preferences: UserPreferences
  notifications: Notification[]
  
  setTheme: (theme: 'light' | 'dark') => void
  toggleSidebar: () => void
  setPreferences: (preferences: Partial<UserPreferences>) => void
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void
  markNotificationRead: (id: string) => void
  clearNotifications: () => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      theme: 'dark',
      sidebarCollapsed: false,
      preferences: {
        defaultMarket: '沪深A',
        defaultDateRange: '1m',
        chartTheme: 'dark',
        language: 'zh',
      },
      notifications: [],
      
      setTheme: (theme) => set({ theme }),
      
      toggleSidebar: () => set((state) => ({ 
        sidebarCollapsed: !state.sidebarCollapsed 
      })),
      
      setPreferences: (preferences) => set((state) => ({
        preferences: { ...state.preferences, ...preferences },
      })),
      
      addNotification: (notification) => set((state) => ({
        notifications: [
          ...state.notifications,
          {
            ...notification,
            id: `notif-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            timestamp: Date.now(),
            read: false,
          },
        ],
      })),
      
      markNotificationRead: (id) => set((state) => ({
        notifications: state.notifications.map((n) =>
          n.id === id ? { ...n, read: true } : n
        ),
      })),
      
      clearNotifications: () => set({ notifications: [] }),
    }),
    {
      name: 'openfinance-app-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
        preferences: state.preferences,
      }),
    }
  )
)
