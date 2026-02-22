'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Button, Badge, Progress } from '@/components/ui'
import {
  Database,
  Server,
  RefreshCw,
  Plus,
  Settings,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  Clock,
  Activity,
  HardDrive,
  Link,
  TestTube,
  Edit,
  Trash2,
  Power,
  PowerOff,
  ChevronRight,
  Zap,
} from 'lucide-react'

interface SourceConfig {
  source_id: string
  source_name: string
  source_type: string
  api_url: string | null
  enabled: boolean
  status: string
  rate_limit: number | null
  timeout_seconds: number
  retry_count: number
  created_at: string
  updated_at: string
}

interface SourceHealth {
  source_id: string
  status: string
  last_check: string
  last_success: string | null
  last_failure: string | null
  consecutive_failures: number
  total_requests: number
  successful_requests: number
  average_latency_ms: number
  error_rate: number
  error_message: string | null
}

interface ConnectionTestResult {
  success: boolean
  source_id: string
  tested_at: string
  latency_ms: number | null
  error_message: string | null
}

const sourceTypeConfig: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  api: { label: 'API接口', icon: <Server className="w-4 h-4" />, color: 'text-blue-400' },
  database: { label: '数据库', icon: <Database className="w-4 h-4" />, color: 'text-emerald-400' },
  file: { label: '文件', icon: <HardDrive className="w-4 h-4" />, color: 'text-amber-400' },
  stream: { label: '数据流', icon: <Activity className="w-4 h-4" />, color: 'text-purple-400' },
  websocket: { label: 'WebSocket', icon: <Link className="w-4 h-4" />, color: 'text-cyan-400' },
}

const statusConfig: Record<string, { color: string; bgColor: string; icon: React.ReactNode; label: string }> = {
  active: { color: 'text-emerald-400', bgColor: 'bg-emerald-500/20', icon: <CheckCircle className="w-4 h-4" />, label: '正常' },
  inactive: { color: 'text-zinc-400', bgColor: 'bg-zinc-500/20', icon: <PowerOff className="w-4 h-4" />, label: '未激活' },
  error: { color: 'text-rose-400', bgColor: 'bg-rose-500/20', icon: <XCircle className="w-4 h-4" />, label: '错误' },
  maintenance: { color: 'text-amber-400', bgColor: 'bg-amber-500/20', icon: <Settings className="w-4 h-4" />, label: '维护中' },
  unknown: { color: 'text-zinc-500', bgColor: 'bg-zinc-500/20', icon: <AlertCircle className="w-4 h-4" />, label: '未知' },
}

export default function DataCollectionPage() {
  const router = useRouter()
  const [sources, setSources] = useState<SourceConfig[]>([])
  const [healthData, setHealthData] = useState<Record<string, SourceHealth>>({})
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [notification, setNotification] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [selectedSource, setSelectedSource] = useState<SourceConfig | null>(null)
  const [testResults, setTestResults] = useState<Record<string, ConnectionTestResult>>({})

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const showNotification = useCallback((type: 'success' | 'error' | 'info', message: string) => {
    setNotification({ type, message })
    setTimeout(() => setNotification(null), 5000)
  }, [])

  const fetchSources = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/datacenter/sources`)
      const data = await response.json()
      if (data.success) {
        setSources(data.sources || [])
      }
    } catch (error) {
      console.error('Failed to fetch sources:', error)
      setSources(getDefaultSources())
    } finally {
      setLoading(false)
    }
  }, [API_BASE_URL])

  const fetchHealth = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/datacenter/sources/health`)
      const data = await response.json()
      if (data.success) {
        const healthMap: Record<string, SourceHealth> = {}
        for (const health of data.health || []) {
          healthMap[health.source_id] = health
        }
        setHealthData(healthMap)
      }
    } catch (error) {
      console.error('Failed to fetch health:', error)
    }
  }, [API_BASE_URL])

  useEffect(() => {
    fetchSources()
    fetchHealth()
    const interval = setInterval(fetchHealth, 60000)
    return () => clearInterval(interval)
  }, [fetchSources, fetchHealth])

  const getDefaultSources = (): SourceConfig[] => [
    {
      source_id: 'tushare',
      source_name: 'Tushare',
      source_type: 'api',
      api_url: 'https://api.tushare.pro',
      enabled: true,
      status: 'active',
      rate_limit: 200,
      timeout_seconds: 30,
      retry_count: 3,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      source_id: 'eastmoney',
      source_name: '东方财富',
      source_type: 'api',
      api_url: 'https://datacenter.eastmoney.com',
      enabled: true,
      status: 'active',
      rate_limit: 100,
      timeout_seconds: 30,
      retry_count: 3,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      source_id: 'akshare',
      source_name: 'AKShare',
      source_type: 'api',
      api_url: 'https://akshare.xyz',
      enabled: true,
      status: 'active',
      rate_limit: 50,
      timeout_seconds: 60,
      retry_count: 3,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      source_id: 'sina',
      source_name: '新浪财经',
      source_type: 'api',
      api_url: 'https://hq.sinajs.cn',
      enabled: true,
      status: 'active',
      rate_limit: 200,
      timeout_seconds: 15,
      retry_count: 2,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      source_id: 'jinshi',
      source_name: '金十数据',
      source_type: 'api',
      api_url: 'https://flash-api.jin10.com',
      enabled: false,
      status: 'inactive',
      rate_limit: 30,
      timeout_seconds: 30,
      retry_count: 3,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ]

  const testConnection = async (sourceId: string) => {
    setActionLoading(`test-${sourceId}`)
    try {
      const response = await fetch(`${API_BASE_URL}/api/datacenter/sources/${sourceId}/test`, {
        method: 'POST',
      })
      const data = await response.json()
      
      setTestResults(prev => ({
        ...prev,
        [sourceId]: data,
      }))
      
      if (data.success) {
        showNotification('success', `${sourceId} 连接测试成功 (${data.latency_ms?.toFixed(0)}ms)`)
      } else {
        showNotification('error', `${sourceId} 连接测试失败: ${data.error_message}`)
      }
    } catch {
      showNotification('error', '连接测试失败')
    } finally {
      setActionLoading(null)
    }
  }

  const toggleSource = async (sourceId: string, enabled: boolean) => {
    setActionLoading(`toggle-${sourceId}`)
    try {
      const response = await fetch(`${API_BASE_URL}/api/datacenter/sources/${sourceId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      })
      const data = await response.json()
      
      if (data.success) {
        setSources(prev => prev.map(s => 
          s.source_id === sourceId ? { ...s, enabled } : s
        ))
        showNotification('success', enabled ? '数据源已启用' : '数据源已禁用')
      }
    } catch {
      showNotification('error', '操作失败')
    } finally {
      setActionLoading(null)
    }
  }

  const getStatusIcon = (status: string) => {
    const config = statusConfig[status] || statusConfig.unknown
    return <div className={`w-5 h-5 rounded-full flex items-center justify-center ${config.bgColor}`}>{config.icon}</div>
  }

  const getHealthIndicator = (sourceId: string) => {
    const health = healthData[sourceId]
    if (!health) return null
    
    const successRate = health.total_requests > 0 
      ? (health.successful_requests / health.total_requests * 100).toFixed(1)
      : '0'
    
    return (
      <div className="flex items-center gap-4 text-xs text-zinc-500">
        <span>成功率: <span className={parseFloat(successRate) > 90 ? 'text-emerald-400' : 'text-amber-400'}>{successRate}%</span></span>
        <span>延迟: <span className="text-blue-400">{health.average_latency_ms.toFixed(0)}ms</span></span>
        <span>请求: {health.total_requests}</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {notification && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg ${
          notification.type === 'success' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
          notification.type === 'error' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
          'bg-blue-500/20 text-blue-400 border border-blue-500/30'
        }`}>
          {notification.message}
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">数据源配置</h2>
          <p className="text-sm text-zinc-500 mt-1">管理数据采集源连接参数和采集规则</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => { fetchSources(); fetchHealth(); }}
            disabled={loading}
            className="gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={() => setShowAddModal(true)}
            className="gap-2 bg-[var(--accent-gold)] text-black hover:bg-[var(--accent-gold)]/90"
          >
            <Plus className="w-4 h-4" />
            添加数据源
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-[var(--bg-secondary)] rounded-xl border border-white/[0.05] p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-zinc-500">总数据源</span>
            <Database className="w-4 h-4 text-zinc-500" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">{sources.length}</p>
        </div>
        <div className="bg-[var(--bg-secondary)] rounded-xl border border-white/[0.05] p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-zinc-500">已启用</span>
          </div>
          <p className="text-2xl font-bold text-emerald-400 mt-2">{sources.filter(s => s.enabled).length}</p>
        </div>
        <div className="bg-[var(--bg-secondary)] rounded-xl border border-white/[0.05] p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-zinc-500">正常运行</span>
          </div>
          <p className="text-2xl font-bold text-blue-400 mt-2">{sources.filter(s => s.status === 'active').length}</p>
        </div>
        <div className="bg-[var(--bg-secondary)] rounded-xl border border-white/[0.05] p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-zinc-500">异常</span>
          </div>
          <p className="text-2xl font-bold text-rose-400 mt-2">{sources.filter(s => s.status === 'error').length}</p>
        </div>
      </div>

      <div className="bg-[var(--bg-secondary)] rounded-xl border border-white/[0.05] overflow-hidden">
        <div className="p-4 border-b border-white/[0.05]">
          <h3 className="text-sm font-medium text-white">数据源列表</h3>
        </div>

        <div className="divide-y divide-white/[0.05]">
          {sources.map((source) => {
            const typeConfig = sourceTypeConfig[source.source_type] || sourceTypeConfig.api
            const statusConf = statusConfig[source.status] || statusConfig.unknown
            const testResult = testResults[source.source_id]
            
            return (
              <div key={source.source_id} className="p-4 hover:bg-white/[0.02] transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(source.status)}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white">{source.source_name}</span>
                        <Badge variant="secondary" className={`${statusConf.bgColor} ${statusConf.color} text-xs`}>
                          {statusConf.label}
                        </Badge>
                        <Badge variant="outline" className={`${typeConfig.color} text-xs gap-1`}>
                          {typeConfig.icon}
                          {typeConfig.label}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-zinc-500 font-mono">{source.api_url}</span>
                        {source.rate_limit && (
                          <span className="text-xs text-zinc-600">| {source.rate_limit} 次/分钟</span>
                        )}
                      </div>
                      {getHealthIndicator(source.source_id)}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {testResult && (
                      <Badge variant="secondary" className={`${testResult.success ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'} text-xs`}>
                        {testResult.success ? `${testResult.latency_ms?.toFixed(0)}ms` : '失败'}
                      </Badge>
                    )}
                    
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => testConnection(source.source_id)}
                      disabled={actionLoading === `test-${source.source_id}`}
                      className="gap-1"
                    >
                      {actionLoading === `test-${source.source_id}` ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <TestTube className="w-4 h-4" />
                      )}
                      测试
                    </Button>
                    
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => { setSelectedSource(source); setShowEditModal(true); }}
                      className="gap-1"
                    >
                      <Edit className="w-4 h-4" />
                      配置
                    </Button>
                    
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleSource(source.source_id, !source.enabled)}
                      disabled={actionLoading === `toggle-${source.source_id}`}
                      className={`gap-1 ${source.enabled ? 'text-rose-400 hover:text-rose-300' : 'text-emerald-400 hover:text-emerald-300'}`}
                    >
                      {actionLoading === `toggle-${source.source_id}` ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : source.enabled ? (
                        <PowerOff className="w-4 h-4" />
                      ) : (
                        <Power className="w-4 h-4" />
                      )}
                      {source.enabled ? '禁用' : '启用'}
                    </Button>
                  </div>
                </div>
              </div>
            )
          })}

          {sources.length === 0 && !loading && (
            <div className="p-8 text-center text-zinc-500">
              <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>暂无数据源配置</p>
              <p className="text-xs mt-1">点击"添加数据源"按钮创建</p>
            </div>
          )}
        </div>
      </div>

      <div className="bg-[var(--bg-secondary)] rounded-xl border border-white/[0.05] p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-white">采集规则配置</h3>
          <Button variant="outline" size="sm" className="gap-2">
            <Settings className="w-4 h-4" />
            管理规则
          </Button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-[var(--bg-tertiary)] rounded-lg p-3 border border-white/[0.05]">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-amber-400" />
              <span className="text-sm font-medium text-white">实时行情采集</span>
            </div>
            <p className="text-xs text-zinc-500">采集频率: 3秒/次</p>
            <p className="text-xs text-zinc-500">数据范围: 全A股</p>
          </div>
          
          <div className="bg-[var(--bg-tertiary)] rounded-lg p-3 border border-white/[0.05]">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-4 h-4 text-blue-400" />
              <span className="text-sm font-medium text-white">日线数据采集</span>
            </div>
            <p className="text-xs text-zinc-500">采集频率: 每日收盘后</p>
            <p className="text-xs text-zinc-500">数据范围: 全A股</p>
          </div>
          
          <div className="bg-[var(--bg-tertiary)] rounded-lg p-3 border border-white/[0.05]">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              <span className="text-sm font-medium text-white">财务数据采集</span>
            </div>
            <p className="text-xs text-zinc-500">采集频率: 季度更新</p>
            <p className="text-xs text-zinc-500">数据范围: 全A股</p>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-zinc-500">
        <span>数据采集页面专注于数据源连接配置，任务调度请使用</span>
        <Button
          variant="link"
          size="sm"
          onClick={() => router.push('/datacenter/pipeline')}
          className="text-[var(--accent-gold)] gap-1 p-0"
        >
          任务链路
          <ChevronRight className="w-3 h-3" />
        </Button>
      </div>

      {showEditModal && selectedSource && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-white/[0.1] p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">编辑数据源配置</h3>
              <button
                onClick={() => setShowEditModal(false)}
                className="text-zinc-400 hover:text-white"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-1">数据源ID</label>
                <input
                  type="text"
                  value={selectedSource.source_id}
                  disabled
                  className="w-full bg-[var(--bg-tertiary)] border border-white/[0.1] rounded-lg px-3 py-2 text-zinc-400"
                />
              </div>
              
              <div>
                <label className="block text-sm text-zinc-400 mb-1">名称</label>
                <input
                  type="text"
                  defaultValue={selectedSource.source_name}
                  id="edit-source-name"
                  className="w-full bg-[var(--bg-tertiary)] border border-white/[0.1] rounded-lg px-3 py-2 text-white"
                />
              </div>
              
              <div>
                <label className="block text-sm text-zinc-400 mb-1">API URL</label>
                <input
                  type="text"
                  defaultValue={selectedSource.api_url || ''}
                  id="edit-source-url"
                  className="w-full bg-[var(--bg-tertiary)] border border-white/[0.1] rounded-lg px-3 py-2 text-white"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">速率限制 (次/分钟)</label>
                  <input
                    type="number"
                    defaultValue={selectedSource.rate_limit || 100}
                    id="edit-source-ratelimit"
                    className="w-full bg-[var(--bg-tertiary)] border border-white/[0.1] rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">超时时间 (秒)</label>
                  <input
                    type="number"
                    defaultValue={selectedSource.timeout_seconds || 30}
                    id="edit-source-timeout"
                    className="w-full bg-[var(--bg-tertiary)] border border-white/[0.1] rounded-lg px-3 py-2 text-white"
                  />
                </div>
              </div>
              
              <div className="flex justify-end gap-2 mt-6">
                <Button
                  variant="outline"
                  onClick={() => setShowEditModal(false)}
                >
                  取消
                </Button>
                <Button
                  variant="default"
                  onClick={async () => {
                    const nameEl = document.getElementById('edit-source-name') as HTMLInputElement
                    const urlEl = document.getElementById('edit-source-url') as HTMLInputElement
                    const rateEl = document.getElementById('edit-source-ratelimit') as HTMLInputElement
                    const timeoutEl = document.getElementById('edit-source-timeout') as HTMLInputElement
                    
                    try {
                      const response = await fetch(`${API_BASE_URL}/api/datacenter/sources/${selectedSource.source_id}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          source_name: nameEl?.value,
                          api_url: urlEl?.value,
                          rate_limit: parseInt(rateEl?.value || '100'),
                          timeout_seconds: parseFloat(timeoutEl?.value || '30'),
                        }),
                      })
                      const data = await response.json()
                      
                      if (data.success) {
                        showNotification('success', '配置已保存')
                        setShowEditModal(false)
                        fetchSources()
                      } else {
                        showNotification('error', data.error || '保存失败')
                      }
                    } catch {
                      showNotification('error', '保存配置失败')
                    }
                  }}
                >
                  保存
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-white/[0.1] p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">添加数据源</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-zinc-400 hover:text-white"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-1">数据源ID *</label>
                <input
                  type="text"
                  id="add-source-id"
                  placeholder="例如: my_api"
                  className="w-full bg-[var(--bg-tertiary)] border border-white/[0.1] rounded-lg px-3 py-2 text-white"
                />
              </div>
              
              <div>
                <label className="block text-sm text-zinc-400 mb-1">名称 *</label>
                <input
                  type="text"
                  id="add-source-name"
                  placeholder="例如: 我的API"
                  className="w-full bg-[var(--bg-tertiary)] border border-white/[0.1] rounded-lg px-3 py-2 text-white"
                />
              </div>
              
              <div>
                <label className="block text-sm text-zinc-400 mb-1">类型</label>
                <select
                  id="add-source-type"
                  className="w-full bg-[var(--bg-tertiary)] border border-white/[0.1] rounded-lg px-3 py-2 text-white"
                >
                  <option value="api">API接口</option>
                  <option value="database">数据库</option>
                  <option value="file">文件</option>
                  <option value="websocket">WebSocket</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm text-zinc-400 mb-1">API URL</label>
                <input
                  type="text"
                  id="add-source-url"
                  placeholder="https://api.example.com"
                  className="w-full bg-[var(--bg-tertiary)] border border-white/[0.1] rounded-lg px-3 py-2 text-white"
                />
              </div>
              
              <div className="flex justify-end gap-2 mt-6">
                <Button
                  variant="outline"
                  onClick={() => setShowAddModal(false)}
                >
                  取消
                </Button>
                <Button
                  variant="default"
                  onClick={async () => {
                    const idEl = document.getElementById('add-source-id') as HTMLInputElement
                    const nameEl = document.getElementById('add-source-name') as HTMLInputElement
                    const typeEl = document.getElementById('add-source-type') as HTMLSelectElement
                    const urlEl = document.getElementById('add-source-url') as HTMLInputElement
                    
                    if (!idEl?.value || !nameEl?.value) {
                      showNotification('error', '请填写必填字段')
                      return
                    }
                    
                    try {
                      const response = await fetch(`${API_BASE_URL}/api/datacenter/sources`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                          source_id: idEl.value,
                          source_name: nameEl.value,
                          source_type: typeEl?.value || 'api',
                          api_url: urlEl?.value,
                        }),
                      })
                      const data = await response.json()
                      
                      if (data.success) {
                        showNotification('success', '数据源已添加')
                        setShowAddModal(false)
                        fetchSources()
                      } else {
                        showNotification('error', data.error || '添加失败')
                      }
                    } catch {
                      showNotification('error', '添加数据源失败')
                    }
                  }}
                >
                  添加
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
