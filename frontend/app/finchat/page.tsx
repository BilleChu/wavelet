'use client'

import { useState, useRef, useEffect } from 'react'
import { chatService, type ChatResponse, type StreamCallbacks } from '@/services/FinchatServices'
import { Send, Bot, User, Loader2, Sparkles, Copy, Check, RefreshCw, ChevronDown, MessageSquare, Wrench, CheckCircle, XCircle, Square } from 'lucide-react'
import { Button, Badge, DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from '@/components/ui'
import StreamMarkdown from '@/components/ui/StreamMarkdown'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  roleInfo?: {
    id: string
    name: string
  }
  isStreaming?: boolean
  status?: string
  statusMessage?: string
  toolCalls?: { id: string; name: string; success: boolean; duration?: number; result?: string; args?: Record<string, unknown> }[]
  thinkingSteps?: { iteration: number; content: string; hasToolCalls: boolean }[]
}

interface ProcessingStatus {
  status: string
  message: string
  toolCalls: { id: string; name: string; success: boolean; duration?: number; result?: string; args?: Record<string, unknown> }[]
}

interface ProgressStage {
  stage: string
  message: string
  progress: number
  toolName?: string
  toolId?: string
  toolArgs?: string
  toolResult?: string
  timestamp: Date
}

const roles = [
  { id: '', name: '默认助手', description: '通用金融分析', avatar: '🤖', gradient: 'from-amber-500 to-orange-600' },
  { id: 'warren_buffett', name: '巴菲特', description: '价值投资大师', avatar: '💼', gradient: 'from-blue-500 to-indigo-600' },
  { id: 'ray_dalio', name: '达里奥', description: '全天候策略', avatar: '🌊', gradient: 'from-cyan-500 to-teal-600' },
  { id: 'catherine_wood', name: '凯瑟琳·伍德', description: '创新科技投资', avatar: '🚀', gradient: 'from-violet-500 to-purple-600' },
]

const suggestions = [
  { text: '浦发银行的市盈率是多少', icon: '📈', category: '估值查询', color: '#f59e0b' },
  { text: '分析一下银行业的发展趋势', icon: '🏦', category: '行业研究', color: '#8b5cf6' },
  { text: '巴菲特怎么看比亚迪', icon: '💡', category: '投资观点', color: '#06b6d4' },
  { text: '贵州茅台的投资价值分析', icon: '🎯', category: '深度分析', color: '#10b981' },
]

export default function FinchatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedRole, setSelectedRole] = useState(roles[0])
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus | null>(null)
  const [progressStages, setProgressStages] = useState<ProgressStage[]>([])
  const [sessionId, setSessionId] = useState<string>('')

  useEffect(() => {
    // Initialize session ID on client side only
    const params = new URLSearchParams(window.location.search)
    const existingSession = params.get('session')
    if (existingSession) {
      setSessionId(existingSession)
    } else {
      setSessionId(`session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)
    }
  }, [])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const query = params.get('q')
    if (query) {
      setInput(query)
    }
    // Update session ID from URL if present
    const sessionParam = params.get('session')
    if (sessionParam && sessionParam !== sessionId) {
      setSessionId(sessionParam)
    }
  }, [])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setProcessingStatus({ status: 'thinking', message: '正在分析您的问题...', toolCalls: [] })
    setProgressStages([]) // Reset progress stages

    // Create assistant message immediately to show thinking process
    const assistantMessageId = (Date.now() + 1).toString()
    
    // 立即创建 assistant 消息，不等待 onContentStart
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      roleInfo: selectedRole.id ? { id: selectedRole.id, name: selectedRole.name } : undefined,
      isStreaming: true,
      toolCalls: [],
      thinkingSteps: [],
    }
    setMessages((prev) => [...prev, assistantMessage])
    
    let hasContent = false

    try {
      await chatService.streamMessageWithCallbacks(
        input,
        {
          onStatus: (message, progress) => {
            setProcessingStatus((prev) => ({
              status: 'thinking',
              message,
              toolCalls: prev?.toolCalls || [],
            }))
          },
          onContentStart: () => {
            // 消息已经在前面创建了，这里不需要再创建
          },
          onContentChunk: (chunk) => {
            hasContent = true
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, content: msg.content + chunk }
                  : msg
              )
            )
          },
          onToolCall: (toolName, toolArgs, toolCallId) => {
            const id = toolCallId || `${toolName}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
            const newToolCall = { id, name: toolName, success: true, args: toolArgs } as { id: string; name: string; success: boolean; duration?: number; result?: string; args?: Record<string, unknown> }
            setProcessingStatus((prev) => ({
              status: 'tool_call',
              message: `正在调用工具：${toolName}`,
              toolCalls: [...(prev?.toolCalls || []), newToolCall],
            }))
            setProgressStages((prev) => [...prev, {
              stage: 'tool_call',
              message: `准备调用工具：${toolName}`,
              progress: 0.2,
              toolName,
              toolId: id,
              timestamp: new Date(),
            }])
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? {
                      ...msg,
                      toolCalls: [...(msg.toolCalls || []), newToolCall],
                    }
                  : msg
              )
            )
          },
          onToolResult: (toolName, success, durationMs, result, toolArgs, toolCallId) => {
            setProcessingStatus((prev) => ({
              status: 'tool_result',
              message: success
                ? `工具 ${toolName} 执行完成 (${durationMs?.toFixed(0)}ms)`
                : `工具 ${toolName} 执行失败`,
              toolCalls: (prev?.toolCalls || []).map((tc) =>
                tc.id === toolCallId || (tc.name === toolName && tc.result === undefined) ? { ...tc, success, duration: durationMs, result, args: toolArgs } : tc
              ),
            }))
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? {
                      ...msg,
                      toolCalls: (msg.toolCalls || []).map((tc) =>
                        tc.id === toolCallId || (tc.name === toolName && tc.result === undefined) ? { ...tc, success, duration: durationMs, result, args: toolArgs } : tc
                      ),
                    }
                  : msg
              )
            )
            setProgressStages((prev) => prev.map(stage => 
              stage.toolId === toolCallId || stage.toolName === toolName
                ? { 
                    ...stage, 
                    stage: success ? 'tool_complete' : 'tool_error', 
                    progress: success ? 1 : 0,
                    message: success ? `✓ ${toolName} 已完成` : `✗ ${toolName} 失败`,
                    toolResult: result
                  }
                : stage
            ))
          },
          onThinking: (iteration, content, hasToolCalls) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? {
                      ...msg,
                      thinkingSteps: [...(msg.thinkingSteps || []), { iteration, content, hasToolCalls }],
                    }
                  : msg
              )
            )
          },
          onProgress: (message, progress, toolName, toolArgs) => {
            setProcessingStatus((prev) => ({
              status: 'progress',
              message,
              toolCalls: prev?.toolCalls || [],
            }))
            setProgressStages((prev) => [...prev, {
              stage: 'progress',
              message,
              progress,
              toolName,
              toolArgs: toolArgs ? JSON.stringify(toolArgs) : undefined,
              timestamp: new Date(),
            }])
          },
          onError: (error) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, content: `抱歉，处理过程中出现错误：${error}`, isStreaming: false }
                  : msg
              )
            )
          },
          onFinal: (content) => {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId
                  ? { ...msg, isStreaming: false }
                  : msg
              )
            )
          },
        },
        selectedRole.id || undefined,
        sessionId
      )

      // Mark streaming as complete but keep tool calls visible
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? { ...msg, isStreaming: false, status: undefined, statusMessage: undefined }
            : msg
        )
      )
    } catch (error) {
      // Handle network/HTTP errors
      setMessages((prev) => {
        const existingMsg = prev.find(m => m.id === assistantMessageId)
        if (existingMsg) {
          return prev.map(msg =>
            msg.id === assistantMessageId
              ? { ...msg, content: '抱歉，服务暂时不可用，请稍后重试。', isStreaming: false }
              : msg
          )
        } else {
          // Create error message if no assistant message exists
          const errorMessage: Message = {
            id: assistantMessageId,
            role: 'assistant',
            content: '抱歉，服务暂时不可用，请稍后重试。',
            timestamp: new Date(),
            roleInfo: selectedRole.id ? { id: selectedRole.id, name: selectedRole.name } : undefined,
            isStreaming: false,
          }
          return [...prev, errorMessage]
        }
      })
    } finally {
      setLoading(false)
      setProcessingStatus(null)
      // Keep progress stages visible - don't clear them!
      // setProgressStages([])
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const copyToClipboard = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const clearConversation = async () => {
    setMessages([])
    setProgressStages([])
    setProcessingStatus(null)
    try {
      await chatService.clearHistory(sessionId)
      const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      setSessionId(newSessionId)
    } catch (error) {
      console.error('Failed to clear history:', error)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-[var(--bg-primary)]">
      {/* Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-amber-500/10 rounded-full blur-[100px]" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-[100px]" />
      </div>

      {/* Header */}
      <div className="relative z-10 border-b border-white/[0.05] bg-[var(--bg-primary)]/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-9 h-9 rounded-xl bg-gradient-to-br ${selectedRole.gradient} flex items-center justify-center text-lg shadow-lg`}>
                {selectedRole.avatar}
              </div>
              <div>
                <h1 className="text-base font-semibold text-white">{selectedRole.name}</h1>
                <p className="text-xs text-zinc-400">{selectedRole.description}</p>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="gap-2 text-zinc-400 hover:text-white"
                  >
                    <ChevronDown className="w-4 h-4" />
                    <span className="text-sm">{selectedRole.name}</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  {roles.map((role) => (
                    <DropdownMenuItem
                      key={role.id}
                      onClick={() => setSelectedRole(role)}
                      className={`flex items-center gap-3 py-3 ${selectedRole.id === role.id ? 'bg-amber-500/10' : ''}`}
                    >
                      <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${role.gradient} flex items-center justify-center text-sm`}>
                        {role.avatar}
                      </div>
                      <div className="flex-1">
                        <div className="font-medium text-sm">{role.name}</div>
                        <div className="text-xs text-zinc-500">{role.description}</div>
                      </div>
                      {selectedRole.id === role.id && (
                        <Check className="w-4 h-4 text-amber-500" />
                      )}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
              
              {messages.length > 0 && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={clearConversation}
                  title="清空对话"
                  className="text-zinc-400 hover:text-white"
                >
                  <RefreshCw className="w-4 h-4" />
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto relative z-10">
        <div className="max-w-4xl mx-auto px-6 py-8">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 animate-fade-in">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center mb-8 shadow-2xl shadow-amber-500/30 animate-float">
                <Bot className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-3">
                您好！我是 OpenFinance 智能助手
              </h2>
              <p className="text-zinc-400 text-center max-w-md mb-10 leading-relaxed">
                我可以帮您分析股票、行业、宏观经济，并提供投资建议。
                选择一个角色开始对话，或直接输入您的问题。
              </p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl">
                {suggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => setInput(suggestion.text)}
                    className="group flex items-center gap-4 p-4 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:border-white/[0.1] hover:bg-white/[0.04] transition-all duration-300 text-left"
                    style={{ animationDelay: `${index * 0.1}s` }}
                  >
                    <div 
                      className="w-11 h-11 rounded-xl flex items-center justify-center text-xl flex-shrink-0"
                      style={{ backgroundColor: `${suggestion.color}15` }}
                    >
                      {suggestion.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <span className="text-sm text-zinc-300 group-hover:text-white transition-colors block">
                        {suggestion.text}
                      </span>
                      <Badge variant="secondary" size="sm" className="mt-1.5">
                        {suggestion.category}
                      </Badge>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((message, index) => (
                <div
                  key={message.id}
                  className={`flex gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in-up`}
                  style={{ animationDelay: `${index * 0.05}s` }}
                >
                  {message.role === 'assistant' && (
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/20 flex-shrink-0">
                      <Bot className="w-5 h-5 text-white" />
                    </div>
                  )}
                  
                  <div className={`max-w-[75%] ${message.role === 'user' ? 'order-first' : ''}`}>
                    <div
                      className={`p-5 rounded-2xl ${
                        message.role === 'user'
                          ? 'bg-gradient-to-br from-amber-500/15 to-orange-600/10 border border-amber-500/20'
                          : 'bg-white/[0.03] border border-white/[0.05]'
                      }`}
                    >
                      {/* Show thinking steps at the TOP of assistant message */}
                      {message.role === 'assistant' && message.thinkingSteps && message.thinkingSteps.length > 0 && (
                        <div className="mb-3 pb-3 border-b border-white/[0.05]">
                          <details className="group">
                            <summary className="text-xs text-zinc-500 mb-2 flex items-center gap-1 cursor-pointer hover:text-zinc-400">
                              <Sparkles className="w-3 h-3" />
                              思考过程 ({message.thinkingSteps.length} 轮)
                              <ChevronDown className="w-3 h-3 ml-auto group-open:rotate-180 transition-transform" />
                            </summary>
                            <div className="mt-2 space-y-2 max-h-60 overflow-y-auto">
                              {message.thinkingSteps.map((step, idx) => (
                                <div key={idx} className="bg-white/[0.02] rounded-lg p-2 text-xs">
                                  <div className="flex items-center gap-2 mb-1">
                                    <Badge variant="secondary" size="sm">第 {step.iteration} 轮</Badge>
                                    {step.hasToolCalls && (
                                      <Badge variant="outline" size="sm" className="text-amber-400 border-amber-400/30">
                                        调用工具
                                      </Badge>
                                    )}
                                  </div>
                                  <p className="text-zinc-400 whitespace-pre-wrap line-clamp-3">{step.content}</p>
                                </div>
                              ))}
                            </div>
                          </details>
                        </div>
                      )}
                      
                      {/* Show tool calls with detailed results */}
                      {message.role === 'assistant' && message.toolCalls && message.toolCalls.length > 0 && (
                        <div className="mb-3 pb-3 border-b border-white/[0.05]">
                          <div className="text-xs text-zinc-500 mb-2 flex items-center gap-1">
                            <Wrench className="w-3 h-3" />
                            工具调用 ({message.toolCalls.length})
                          </div>
                          <div className="space-y-2">
                            {message.toolCalls.map((tc, idx) => (
                              <details key={idx} className="group bg-white/[0.02] rounded-lg">
                                <summary className="flex items-center gap-2 p-2 cursor-pointer hover:bg-white/[0.02]">
                                  {tc.success ? (
                                    <CheckCircle className="w-4 h-4 text-green-400" />
                                  ) : (
                                    <XCircle className="w-4 h-4 text-red-400" />
                                  )}
                                  <span className="text-sm text-zinc-300 font-medium">{tc.name}</span>
                                  {tc.duration && (
                                    <span className="text-xs text-zinc-500">{tc.duration.toFixed(0)}ms</span>
                                  )}
                                  <ChevronDown className="w-3 h-3 ml-auto text-zinc-500 group-open:rotate-180 transition-transform" />
                                </summary>
                                <div className="px-2 pb-2 space-y-2">
                                  {tc.args && Object.keys(tc.args).length > 0 && (
                                    <div>
                                      <div className="text-xs text-zinc-500 mb-1">参数:</div>
                                      <pre className="text-xs text-zinc-400 bg-black/20 rounded p-2 overflow-x-auto">
                                        {JSON.stringify(tc.args, null, 2)}
                                      </pre>
                                    </div>
                                  )}
                                  {tc.result && (
                                    <div>
                                      <div className="text-xs text-zinc-500 mb-1">结果:</div>
                                      <pre className="text-xs text-zinc-400 bg-black/20 rounded p-2 overflow-x-auto max-h-40 whitespace-pre-wrap">
                                        {tc.result}
                                      </pre>
                                    </div>
                                  )}
                                </div>
                              </details>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Show streaming/loading status */}
                      {message.role === 'assistant' && message.isStreaming && (
                        <div className="mb-3 pb-3 border-b border-white/[0.05]">
                          <div className="flex items-center gap-3">
                            <Loader2 className="w-4 h-4 animate-spin text-amber-400" />
                            <span className="text-zinc-400 text-sm">{processingStatus?.message || '正在思考中...'}</span>
                          </div>
                          {progressStages.length > 0 && (
                            <div className="mt-3 space-y-1.5 max-h-32 overflow-y-auto">
                              {progressStages.map((stage, idx) => (
                                <div key={idx} className="flex items-start gap-2 text-xs">
                                  <div className={`mt-0.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                                    stage.progress > 0.5 ? 'bg-green-500' : 
                                    stage.progress > 0 ? 'bg-amber-500 animate-pulse' : 
                                    'bg-zinc-600'
                                  }`} />
                                  <div className="text-zinc-500 truncate">{stage.message}</div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                      {/* Then show content with markdown rendering */}
                      {message.content && (
                        <StreamMarkdown content={message.content} />
                      )}
                      <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/[0.05]">
                        <span className="text-xs text-zinc-600">
                          {message.timestamp.toLocaleTimeString()}
                        </span>
                        {message.role === 'assistant' && (
                          <button
                            onClick={() => copyToClipboard(message.content, message.id)}
                            className="text-zinc-600 hover:text-amber-400 transition-colors"
                          >
                            {copiedId === message.id ? (
                              <Check className="w-4 h-4" />
                            ) : (
                              <Copy className="w-4 h-4" />
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {message.role === 'user' && (
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg shadow-violet-500/20 flex-shrink-0">
                      <User className="w-5 h-5 text-white" />
                    </div>
                  )}
                </div>
              ))}

              {/* Loading indicator integrated into streaming message - only show if no assistant message exists */}
              {loading && !messages.some(m => m.role === 'assistant' && m.isStreaming) && (
                <div className="flex gap-4 animate-fade-in">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/20 flex-shrink-0 animate-pulse-glow">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div className="p-5 rounded-2xl bg-white/[0.03] border border-white/[0.05] min-w-[200px] flex-1 space-y-3">
                    <div className="flex items-center gap-3">
                      <Loader2 className="w-5 h-5 animate-spin text-amber-400" />
                      <span className="text-zinc-400">{processingStatus?.message || '正在思考中...'}</span>
                    </div>
                    
                    {/* Progress Bar */}
                    {progressStages.length > 0 && (
                      <div className="w-full bg-white/[0.05] rounded-full h-2 overflow-hidden">
                        <div 
                          className="bg-gradient-to-r from-amber-500 to-orange-500 h-full transition-all duration-500 ease-out"
                          style={{ 
                            width: `${Math.min(100, Math.max(0, progressStages[progressStages.length - 1].progress * 100))}%` 
                          }}
                        />
                      </div>
                    )}
                    
                    {/* Progress Stages Timeline - Shows the thinking process */}
                    {progressStages.length > 0 && (
                      <div className="max-h-48 overflow-y-auto space-y-1.5 pr-2">
                        <div className="text-xs text-zinc-500 mb-1">处理过程：</div>
                        {progressStages.map((stage, idx) => (
                          <div key={idx} className="flex items-start gap-2 text-xs">
                            <div className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${
                              stage.progress > 0.5 ? 'bg-green-500' : 
                              stage.progress > 0 ? 'bg-amber-500 animate-pulse' : 
                              'bg-zinc-600'
                            }`} />
                            <div className="flex-1 min-w-0">
                              <div className="text-zinc-400 truncate">{stage.message}</div>
                              {stage.toolArgs && (
                                <div className="text-zinc-600 text-[10px] mt-0.5 italic">
                                  {stage.toolArgs}
                                </div>
                              )}
                            </div>
                            <div className="text-zinc-600 text-[10px] flex-shrink-0">
                              {Math.round(stage.progress * 100)}%
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="relative z-10 border-t border-white/[0.05] bg-[var(--bg-primary)]/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入您的问题，例如：浦发银行的市盈率是多少？"
                className="w-full px-5 py-4 bg-white/[0.03] border border-white/[0.08] rounded-2xl resize-none focus:outline-none focus:border-amber-500/40 focus:bg-white/[0.05] text-white placeholder-zinc-500 transition-all text-[15px]"
                rows={1}
                style={{ minHeight: '56px', maxHeight: '120px' }}
              />
            </div>
            {loading ? (
              <Button
                onClick={async () => {
                  await chatService.stopGeneration()
                  setLoading(false)
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.isStreaming ? { ...msg, isStreaming: false } : msg
                    )
                  )
                }}
                size="lg"
                className="h-14 px-6 bg-red-600 hover:bg-red-700"
              >
                <Square className="w-5 h-5" />
                <span className="hidden sm:inline ml-2">停止</span>
              </Button>
            ) : (
              <Button
                onClick={handleSend}
                disabled={!input.trim()}
                size="lg"
                className="h-14 px-6"
              >
                <Send className="w-5 h-5" />
                <span className="hidden sm:inline ml-2">发送</span>
              </Button>
            )}
          </div>
          <div className="flex items-center justify-between mt-3 px-1">
            <p className="text-xs text-zinc-600">
              按 Enter 发送，Shift + Enter 换行
            </p>
            {sessionId && (
              <p className="text-xs text-zinc-700 font-mono">
                Session: {sessionId.slice(-8)}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
