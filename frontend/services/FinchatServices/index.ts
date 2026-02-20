import apiClient, { API_BASE_URL } from '../apiConfig'

export interface ChatResponse {
  success: boolean
  content: string
  intent?: string
  trace_id: string
  error?: string
}

export interface StreamMessage {
  type: 'status' | 'thinking' | 'progress' | 'tool_result' | 'error' | 'final' | 'content' | 'content_start'
  iteration?: number
  content?: string
  tool_name?: string
  tool_args?: Record<string, unknown>
  tool_result?: string
  success?: boolean
  duration_ms?: number
  progress?: number
  message?: string
  has_tool_calls?: boolean
}

export interface StreamCallbacks {
  onStatus?: (message: string, progress: number) => void
  onThinking?: (iteration: number, content: string, hasToolCalls: boolean) => void
  onToolCall?: (toolName: string, toolArgs: Record<string, unknown>) => void
  onToolResult?: (toolName: string, success: boolean, durationMs?: number, result?: string, toolArgs?: Record<string, unknown>) => void
  onProgress?: (message: string, progress: number, toolName?: string, toolArgs?: Record<string, unknown>) => void
  onError?: (error: string) => void
  onContentStart?: () => void
  onContentChunk?: (chunk: string) => void
  onFinal?: (content: string) => void
}

export const chatService = {
  async sendMessage(query: string, role?: string): Promise<ChatResponse> {
    const response = await apiClient.post<ChatResponse>('/api/chat', {
      meta: {
        trace_id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        source: 'web_client',
        platform: 'web',
      },
      user: {
        ldap_id: 'user',
        user_name: 'User',
        role: 'user',
      },
      query,
      role,
      stream: false,
    })
    return response.data
  },

  async *streamMessage(query: string, role?: string): AsyncGenerator<string> {
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        meta: {
          trace_id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          source: 'web_client',
          platform: 'web',
        },
        user: {
          ldap_id: 'user',
          user_name: 'User',
          role: 'user',
        },
        query,
        role,
      }),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No reader available')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            return
          }
          try {
            const parsed = JSON.parse(data)
            if (parsed.content) {
              yield parsed.content
            }
            if (parsed.error) {
              throw new Error(parsed.error)
            }
          } catch (e) {
            if (e instanceof SyntaxError) {
              continue
            }
            throw e
          }
        }
      }
    }
  },

  async streamMessageWithCallbacks(
    query: string,
    callbacks: StreamCallbacks,
    role?: string,
    sessionId?: string
  ): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        meta: {
          trace_id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          source: 'web_client',
          platform: 'web',
          extended_info: {
            session_id: sessionId,
          },
        },
        user: {
          ldap_id: 'user',
          user_name: 'User',
          role: 'user',
        },
        query,
        role,
      }),
    })

    if (!response.ok) {
      callbacks.onError?.(`HTTP error! status: ${response.status}`)
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      callbacks.onError?.('No reader available')
      throw new Error('No reader available')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            return
          }
          try {
            const parsed: StreamMessage = JSON.parse(data)
            
            switch (parsed.type) {
              case 'status':
                if (parsed.message) {
                  callbacks.onStatus?.(parsed.message, parsed.progress ?? 0)
                }
                break
              case 'thinking':
                if (parsed.iteration !== undefined && parsed.content) {
                  callbacks.onThinking?.(parsed.iteration, parsed.content, parsed.has_tool_calls ?? false)
                }
                break
              case 'progress':
                if (parsed.message) {
                  callbacks.onProgress?.(
                    parsed.message,
                    parsed.progress ?? 0,
                    parsed.tool_name,
                    parsed.tool_args
                  )
                  if (parsed.tool_name && parsed.tool_args) {
                    callbacks.onToolCall?.(parsed.tool_name, parsed.tool_args)
                  }
                }
                break
              case 'tool_result':
                if (parsed.tool_name) {
                  callbacks.onToolResult?.(
                    parsed.tool_name,
                    parsed.success ?? true,
                    parsed.duration_ms,
                    parsed.tool_result,
                    parsed.tool_args
                  )
                }
                break
              case 'content_start':
                callbacks.onContentStart?.()
                break
              case 'content':
                if (parsed.content) {
                  callbacks.onContentChunk?.(parsed.content)
                }
                break
              case 'final':
                if (parsed.content) {
                  callbacks.onFinal?.(parsed.content)
                }
                break
              case 'error':
                callbacks.onError?.(parsed.message || 'Unknown error')
                break
            }
          } catch (e) {
            if (e instanceof SyntaxError) {
              continue
            }
            throw e
          }
        }
      }
    }
  },
}
