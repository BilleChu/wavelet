/**
 * Chat Module Store using Zustand.
 *
 * Provides state management for:
 * - Chat sessions and history
 * - Active role/agent
 * - Message streaming state
 * - Tool call tracking
 */

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  toolCalls?: ToolCall[]
  status?: 'streaming' | 'complete' | 'error'
}

export interface ToolCall {
  id: string
  name: string
  args: Record<string, unknown>
  result?: unknown
  status: 'pending' | 'running' | 'complete' | 'error'
}

export interface ChatSession {
  id: string
  name: string
  messages: Message[]
  role: string
  createdAt: number
  updatedAt: number
}

export interface ChatRole {
  id: string
  name: string
  avatar?: string
  description?: string
  skillId?: string
}

interface ChatState {
  sessions: ChatSession[]
  currentSessionId: string | null
  roles: ChatRole[]
  activeRole: ChatRole | null
  isStreaming: boolean
  currentToolCalls: ToolCall[]
  
  createSession: (role?: string) => string
  deleteSession: (id: string) => void
  setCurrentSession: (id: string | null) => void
  
  addMessage: (sessionId: string, message: Omit<Message, 'id' | 'timestamp'>) => void
  updateMessage: (sessionId: string, messageId: string, updates: Partial<Message>) => void
  
  setRoles: (roles: ChatRole[]) => void
  setActiveRole: (role: ChatRole | null) => void
  
  setStreaming: (streaming: boolean) => void
  addToolCall: (toolCall: ToolCall) => void
  updateToolCall: (id: string, updates: Partial<ToolCall>) => void
  clearToolCalls: () => void
  
  getSession: (id: string) => ChatSession | undefined
  getCurrentSession: () => ChatSession | undefined
}

const generateId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`

const defaultRoles: ChatRole[] = [
  { id: 'warren_buffett', name: '巴菲特', skillId: 'buffett-investment' },
  { id: 'ray_dalio', name: '达里奥', skillId: 'macro-analysis' },
  { id: 'catherine_wood', name: '凯瑟琳·伍德', skillId: 'tech-indicator' },
]

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,
      roles: defaultRoles,
      activeRole: defaultRoles[0],
      isStreaming: false,
      currentToolCalls: [],
      
      createSession: (role) => {
        const id = generateId()
        const session: ChatSession = {
          id,
          name: `对话 ${get().sessions.length + 1}`,
          messages: [],
          role: role || get().activeRole?.id || '',
          createdAt: Date.now(),
          updatedAt: Date.now(),
        }
        set((state) => ({
          sessions: [session, ...state.sessions],
          currentSessionId: id,
        }))
        return id
      },
      
      deleteSession: (id) => set((state) => ({
        sessions: state.sessions.filter(s => s.id !== id),
        currentSessionId: state.currentSessionId === id ? null : state.currentSessionId,
      })),
      
      setCurrentSession: (id) => set({ currentSessionId: id }),
      
      addMessage: (sessionId, message) => set((state) => ({
        sessions: state.sessions.map(s =>
          s.id === sessionId
            ? {
                ...s,
                messages: [
                  ...s.messages,
                  {
                    ...message,
                    id: generateId(),
                    timestamp: Date.now(),
                  },
                ],
                updatedAt: Date.now(),
              }
            : s
        ),
      })),
      
      updateMessage: (sessionId, messageId, updates) => set((state) => ({
        sessions: state.sessions.map(s =>
          s.id === sessionId
            ? {
                ...s,
                messages: s.messages.map(m =>
                  m.id === messageId ? { ...m, ...updates } : m
                ),
                updatedAt: Date.now(),
              }
            : s
        ),
      })),
      
      setRoles: (roles) => set({ roles }),
      
      setActiveRole: (role) => set({ activeRole: role }),
      
      setStreaming: (streaming) => set({ isStreaming: streaming }),
      
      addToolCall: (toolCall) => set((state) => ({
        currentToolCalls: [...state.currentToolCalls, toolCall],
      })),
      
      updateToolCall: (id, updates) => set((state) => ({
        currentToolCalls: state.currentToolCalls.map(tc =>
          tc.id === id ? { ...tc, ...updates } : tc
        ),
      })),
      
      clearToolCalls: () => set({ currentToolCalls: [] }),
      
      getSession: (id) => get().sessions.find(s => s.id === id),
      
      getCurrentSession: () => {
        const state = get()
        return state.sessions.find(s => s.id === state.currentSessionId)
      },
    }),
    {
      name: 'openfinance-chat-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        sessions: state.sessions.slice(0, 10),
        currentSessionId: state.currentSessionId,
        activeRole: state.activeRole,
      }),
    }
  )
)
