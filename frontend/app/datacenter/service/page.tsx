'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  dataserviceDocService,
  categoryLabels,
  methodColors,
  statusColors,
  categoryIcons,
  type APIDocumentation,
} from '@/services/dataserviceDocService'
import { Button, Badge } from '@/components/ui'
import { API_BASE_URL } from '@/services/apiConfig'
import {
  Search,
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
  Filter,
  X,
  Code,
  AlertCircle,
  Clock,
  Shield,
  Zap,
  RefreshCw,
  Play,
  Database,
  Activity,
  BarChart3,
  TrendingUp,
  Users,
  Calendar,
} from 'lucide-react'

interface UsageRecord {
  id: string
  endpoint: string
  method: string
  timestamp: string
  duration_ms: number
  status: number
  user_agent?: string
  ip?: string
}

interface UsageStats {
  total_requests: number
  successful_requests: number
  failed_requests: number
  avg_response_time: number
  top_endpoints: Array<{ endpoint: string; count: number }>
  daily_requests: Array<{ date: string; count: number }>
}

export default function DataServicePage() {
  const [documentation, setDocumentation] = useState<APIDocumentation | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [expandedServices, setExpandedServices] = useState<Set<string>>(new Set())
  const [expandedEndpoints, setExpandedEndpoints] = useState<Set<string>>(new Set())
  const [copiedText, setCopiedText] = useState<string | null>(null)
  const [activeView, setActiveView] = useState<'docs' | 'usage'>('docs')
  const [usageStats, setUsageStats] = useState<UsageStats | null>(null)
  const [usageRecords, setUsageRecords] = useState<UsageRecord[]>([])

  const fetchDocumentation = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await dataserviceDocService.getDocumentation()
      setDocumentation(data)
    } catch (err) {
      console.error('Failed to fetch documentation:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch documentation')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchUsageStats = useCallback(async () => {
    try {
      const response = await fetch('/api/datacenter/usage/stats')
      if (response.ok) {
        const data = await response.json()
        setUsageStats(data)
      }
    } catch (err) {
      console.error('Failed to fetch usage stats:', err)
    }
  }, [])

  const fetchUsageRecords = useCallback(async () => {
    try {
      const response = await fetch('/api/datacenter/usage/records?limit=50')
      if (response.ok) {
        const data = await response.json()
        setUsageRecords(data.records || [])
      }
    } catch (err) {
      console.error('Failed to fetch usage records:', err)
    }
  }, [])

  useEffect(() => {
    fetchDocumentation()
    fetchUsageStats()
    fetchUsageRecords()
  }, [fetchDocumentation, fetchUsageStats, fetchUsageRecords])

  const filteredServices = useMemo(() => {
    if (!documentation?.services) return []
    
    let services = documentation.services
    
    if (selectedCategory) {
      services = services.filter(s => s.category === selectedCategory)
    }
    
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      services = services.filter(service => {
        const nameMatch = service.name.toLowerCase().includes(query)
        const descMatch = service.description.toLowerCase().includes(query)
        const tagMatch = service.tags?.some(tag => tag.toLowerCase().includes(query))
        const endpointMatch = service.endpoints?.some(
          ep => ep.path.toLowerCase().includes(query) || 
                ep.description.toLowerCase().includes(query)
        )
        return nameMatch || descMatch || tagMatch || endpointMatch
      })
    }
    
    return services
  }, [documentation, selectedCategory, searchQuery])

  const toggleService = (serviceId: string) => {
    setExpandedServices(prev => {
      const next = new Set(prev)
      if (next.has(serviceId)) {
        next.delete(serviceId)
      } else {
        next.add(serviceId)
      }
      return next
    })
  }

  const toggleEndpoint = (endpointId: string) => {
    setExpandedEndpoints(prev => {
      const next = new Set(prev)
      if (next.has(endpointId)) {
        next.delete(endpointId)
      } else {
        next.add(endpointId)
      }
      return next
    })
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedText(text)
      setTimeout(() => setCopiedText(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const formatTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 animate-spin text-[var(--accent-gold)]" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass-panel p-8 text-center">
        <AlertCircle className="w-12 h-12 text-rose-400 mx-auto mb-4" />
        <p className="text-rose-400 mb-4">{error}</p>
        <Button onClick={fetchDocumentation} variant="outline">
          <RefreshCw className="w-4 h-4 mr-2" />
          重试
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <Button
            variant={activeView === 'docs' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveView('docs')}
            className={activeView === 'docs' ? 'bg-[var(--accent-gold)] text-black gap-2' : 'text-zinc-400 gap-2'}
          >
            <Database className="w-4 h-4" />
            API 文档
          </Button>
          <Button
            variant={activeView === 'usage' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveView('usage')}
            className={activeView === 'usage' ? 'bg-[var(--accent-gold)] text-black gap-2' : 'text-zinc-400 gap-2'}
          >
            <BarChart3 className="w-4 h-4" />
            使用情况
          </Button>
        </div>
        <Button variant="outline" size="sm" onClick={() => { fetchDocumentation(); fetchUsageStats(); fetchUsageRecords(); }}>
          <RefreshCw className="w-4 h-4 mr-2" />
          刷新
        </Button>
      </div>

      {activeView === 'usage' ? (
        <div className="space-y-6">
          <div className="grid grid-cols-4 gap-4">
            <div className="glass-panel p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center">
                  <Activity className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <p className="text-zinc-500 text-xs">总请求数</p>
                  <p className="text-2xl font-semibold text-white">{usageStats?.total_requests || 0}</p>
                </div>
              </div>
            </div>
            <div className="glass-panel p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                  <Check className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <p className="text-zinc-500 text-xs">成功请求</p>
                  <p className="text-2xl font-semibold text-white">{usageStats?.successful_requests || 0}</p>
                </div>
              </div>
            </div>
            <div className="glass-panel p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-rose-500/20 flex items-center justify-center">
                  <X className="w-5 h-5 text-rose-400" />
                </div>
                <div>
                  <p className="text-zinc-500 text-xs">失败请求</p>
                  <p className="text-2xl font-semibold text-white">{usageStats?.failed_requests || 0}</p>
                </div>
              </div>
            </div>
            <div className="glass-panel p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center">
                  <Clock className="w-5 h-5 text-violet-400" />
                </div>
                <div>
                  <p className="text-zinc-500 text-xs">平均响应时间</p>
                  <p className="text-2xl font-semibold text-white">{usageStats?.avg_response_time || 0}ms</p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div className="glass-panel p-5">
              <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-zinc-500" />
                热门端点
              </h3>
              <div className="space-y-3">
                {usageStats?.top_endpoints?.slice(0, 5).map((item, index) => (
                  <div key={item.endpoint} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-zinc-500 text-xs w-4">{index + 1}</span>
                      <code className="text-sm text-zinc-300">{item.endpoint}</code>
                    </div>
                    <Badge variant="secondary" className="bg-blue-500/20 text-blue-400">
                      {item.count}
                    </Badge>
                  </div>
                )) || (
                  <p className="text-zinc-500 text-sm">暂无数据</p>
                )}
              </div>
            </div>

            <div className="glass-panel p-5">
              <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                <Calendar className="w-4 h-4 text-zinc-500" />
                每日请求趋势
              </h3>
              <div className="space-y-2">
                {usageStats?.daily_requests?.slice(-7).map((item) => (
                  <div key={item.date} className="flex items-center justify-between">
                    <span className="text-zinc-400 text-sm">{item.date}</span>
                    <div className="flex-1 mx-4 h-2 bg-zinc-800 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-[var(--accent-gold)]"
                        style={{ 
                          width: `${Math.min((item.count / Math.max(...(usageStats?.daily_requests?.map(d => d.count) || [1]))) * 100, 100)}%` 
                        }}
                      />
                    </div>
                    <span className="text-zinc-400 text-sm w-12 text-right">{item.count}</span>
                  </div>
                )) || (
                  <p className="text-zinc-500 text-sm">暂无数据</p>
                )}
              </div>
            </div>
          </div>

          <div className="glass-panel overflow-hidden">
            <div className="p-4 border-b border-white/[0.05]">
              <h3 className="text-sm font-medium text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-zinc-500" />
                最近请求记录
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/[0.05] text-zinc-500 text-xs">
                    <th className="text-left p-4 font-medium">端点</th>
                    <th className="text-left p-4 font-medium">方法</th>
                    <th className="text-left p-4 font-medium">状态</th>
                    <th className="text-left p-4 font-medium">耗时</th>
                    <th className="text-left p-4 font-medium">时间</th>
                  </tr>
                </thead>
                <tbody>
                  {usageRecords.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="p-8 text-center text-zinc-500">
                        暂无请求记录
                      </td>
                    </tr>
                  ) : (
                    usageRecords.map((record) => (
                      <tr key={record.id} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                        <td className="p-4">
                          <code className="text-sm text-zinc-300">{record.endpoint}</code>
                        </td>
                        <td className="p-4">
                          <Badge 
                            variant="secondary" 
                            className={`${methodColors[record.method as keyof typeof methodColors] || 'bg-zinc-500/20 text-zinc-400'}`}
                          >
                            {record.method}
                          </Badge>
                        </td>
                        <td className="p-4">
                          <Badge 
                            variant="secondary" 
                            className={record.status < 400 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}
                          >
                            {record.status}
                          </Badge>
                        </td>
                        <td className="p-4 text-zinc-400 text-sm">{record.duration_ms}ms</td>
                        <td className="p-4 text-zinc-500 text-sm">{formatTime(record.timestamp)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                type="text"
                placeholder="搜索 API 端点..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/40"
              />
            </div>
            <div className="flex gap-2">
              {Object.entries(categoryLabels).map(([key, label]) => (
                <Button
                  key={key}
                  variant={selectedCategory === key ? 'outline' : 'ghost'}
                  size="sm"
                  onClick={() => setSelectedCategory(selectedCategory === key ? null : key)}
                  className={selectedCategory === key ? 'border-[var(--accent-gold)]/30 text-[var(--accent-gold)]' : 'text-zinc-500'}
                >
                  {label}
                </Button>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            {filteredServices.map((service) => {
              const isExpanded = expandedServices.has(service.service_id)
              const categoryIcon = categoryIcons[service.category as keyof typeof categoryIcons] || '📦'
              
              return (
                <div key={service.service_id} className="glass-panel overflow-hidden">
                  <div 
                    className="flex items-center justify-between p-4 cursor-pointer hover:bg-white/[0.02]"
                    onClick={() => toggleService(service.service_id)}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-[var(--accent-gold)]/20 flex items-center justify-center text-lg">
                        {categoryIcon}
                      </div>
                      <div>
                        <h3 className="font-medium text-white">{service.name}</h3>
                        <p className="text-xs text-zinc-500">{service.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant="secondary" className="bg-blue-500/20 text-blue-400">
                        {service.endpoints?.length || 0} 端点
                      </Badge>
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-zinc-500" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-zinc-500" />
                      )}
                    </div>
                  </div>
                  
                  {isExpanded && (
                    <div className="border-t border-white/[0.05] p-4 space-y-3">
                      {service.endpoints?.map((endpoint, idx) => {
                        const endpointId = `${service.service_id}-${idx}`
                        const isEndpointExpanded = expandedEndpoints.has(endpointId)
                        
                        return (
                          <div key={endpointId} className="bg-white/[0.02] rounded-lg overflow-hidden">
                            <div 
                              className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/[0.02]"
                              onClick={() => toggleEndpoint(endpointId)}
                            >
                              <div className="flex items-center gap-3">
                                <Badge 
                                  variant="secondary" 
                                  className={`${methodColors[endpoint.method as keyof typeof methodColors] || 'bg-zinc-500/20 text-zinc-400'}`}
                                >
                                  {endpoint.method}
                                </Badge>
                                <code className="text-sm text-zinc-300">{endpoint.path}</code>
                              </div>
                              <div className="flex items-center gap-2">
                                {endpoint.deprecated && (
                                  <Badge variant="secondary" className="bg-amber-500/20 text-amber-400">
                                    已废弃
                                  </Badge>
                                )}
                                {isEndpointExpanded ? (
                                  <ChevronDown className="w-4 h-4 text-zinc-500" />
                                ) : (
                                  <ChevronRight className="w-4 h-4 text-zinc-500" />
                                )}
                              </div>
                            </div>
                            
                            {isEndpointExpanded && (
                              <div className="border-t border-white/[0.05] p-4 space-y-4">
                                <p className="text-zinc-400 text-sm">{endpoint.description}</p>
                                
                                {endpoint.parameters && Object.keys(endpoint.parameters).length > 0 && (
                                  <div>
                                    <h4 className="text-xs font-medium text-zinc-500 mb-2">参数</h4>
                                    <div className="space-y-2">
                                      {Object.entries(endpoint.parameters).map(([name, param]) => (
                                        <div key={name} className="flex items-start gap-3 text-sm">
                                          <code className="text-violet-400">{name}</code>
                                          <span className="text-zinc-500">({param.type || 'string'})</span>
                                          <span className="text-zinc-400">{param.description || '-'}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                                
                                <div>
                                  <h4 className="text-xs font-medium text-zinc-500 mb-2">请求示例</h4>
                                  <div className="relative">
                                    <pre className="bg-zinc-900/50 rounded-lg p-4 text-sm text-zinc-300 overflow-x-auto">
                                      <code>{`curl -X ${endpoint.method} "${API_BASE_URL}${endpoint.path}" \\
  -H "Content-Type: application/json"`}</code>
                                    </pre>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => copyToClipboard(`curl -X ${endpoint.method} "${API_BASE_URL}${endpoint.path}" -H "Content-Type: application/json"`)}
                                      className="absolute top-2 right-2"
                                    >
                                      {copiedText ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                                    </Button>
                                  </div>
                                </div>
                                
                                {endpoint.response_example && (
                                  <div>
                                    <h4 className="text-xs font-medium text-zinc-500 mb-2">响应示例</h4>
                                    <pre className="bg-zinc-900/50 rounded-lg p-4 text-sm text-zinc-300 overflow-x-auto">
                                      <code>{JSON.stringify(endpoint.response_example, null, 2)}</code>
                                    </pre>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
