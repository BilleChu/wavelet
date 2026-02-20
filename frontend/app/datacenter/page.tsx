'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { datacenterService, type TaskDefinition, type TriggerDefinition, type DataSourceInfo, type OverviewData, type CreateTaskRequest } from '@/services/datacenterService'
import { Button, Badge } from '@/components/ui'
import {
  Play,
  Pause,
  Square,
  RefreshCw,
  Plus,
  Activity,
  Database,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Zap,
  Settings,
  Calendar,
  TrendingUp,
  X,
  ChevronRight,
  Timer,
  AlertCircle,
  FileText,
  Layers,
  ArrowRight,
  Server,
  HardDrive,
  Upload,
  Download,
} from 'lucide-react'

const statusConfig: Record<string, { color: string; bgColor: string; icon: React.ReactNode; label: string }> = {
  pending: { color: 'text-zinc-400', bgColor: 'bg-zinc-500/20', icon: <Clock className="w-4 h-4" />, label: '等待中' },
  queued: { color: 'text-blue-400', bgColor: 'bg-blue-500/20', icon: <Clock className="w-4 h-4" />, label: '队列中' },
  running: { color: 'text-amber-400', bgColor: 'bg-amber-500/20', icon: <Loader2 className="w-4 h-4 animate-spin" />, label: '运行中' },
  completed: { color: 'text-emerald-400', bgColor: 'bg-emerald-500/20', icon: <CheckCircle className="w-4 h-4" />, label: '已完成' },
  failed: { color: 'text-rose-400', bgColor: 'bg-rose-500/20', icon: <XCircle className="w-4 h-4" />, label: '失败' },
  cancelled: { color: 'text-zinc-500', bgColor: 'bg-zinc-500/20', icon: <Square className="w-4 h-4" />, label: '已取消' },
  paused: { color: 'text-yellow-400', bgColor: 'bg-yellow-500/20', icon: <Pause className="w-4 h-4" />, label: '已暂停' },
}

const triggerTypeConfig: Record<string, { label: string; icon: React.ReactNode }> = {
  interval: { label: '定时触发', icon: <Clock className="w-4 h-4" /> },
  cron: { label: 'Cron表达式', icon: <Calendar className="w-4 h-4" /> },
  once: { label: '单次触发', icon: <Zap className="w-4 h-4" /> },
  condition: { label: '条件触发', icon: <TrendingUp className="w-4 h-4" /> },
  manual: { label: '手动触发', icon: <Settings className="w-4 h-4" /> },
}

const taskTypeOptions = [
  { type: 'stock_list', name: '股票列表', description: '获取A股所有上市公司列表', data_source: 'eastmoney' },
  { type: 'realtime_quote', name: '实时行情', description: '获取股票实时行情数据', data_source: 'eastmoney' },
  { type: 'index_quote', name: '指数行情', description: '获取主要指数行情数据', data_source: 'eastmoney' },
  { type: 'north_money', name: '北向资金', description: '获取北向资金流向数据', data_source: 'eastmoney' },
  { type: 'financial_indicator', name: '财务指标', description: '获取上市公司财务指标', data_source: 'eastmoney' },
  { type: 'etf_quote', name: 'ETF行情', description: '获取ETF基金行情数据', data_source: 'eastmoney' },
  { type: 'industry_quote', name: '行业行情', description: '获取行业板块行情数据', data_source: 'eastmoney' },
  { type: 'concept_quote', name: '概念行情', description: '获取概念板块行情数据', data_source: 'eastmoney' },
  { type: 'company_profile', name: '公司档案', description: '获取公司档案并构建知识图谱', data_source: 'eastmoney' },
]

interface TaskChainNode {
  id: string
  name: string
  status: string
  started_at: string | null
  completed_at: string | null
  duration_ms: number | null
  records_processed: number
  records_failed: number
  error: string | null
}

export default function DataCollectionPage() {
  const router = useRouter()
  const [overview, setOverview] = useState<OverviewData | null>(null)
  const [tasks, setTasks] = useState<TaskDefinition[]>([])
  const [triggers, setTriggers] = useState<TriggerDefinition[]>([])
  const [sources, setSources] = useState<DataSourceInfo[]>([])
  const [chains, setChains] = useState<{ chain_id: string; name: string; status: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'tasks' | 'chains' | 'triggers' | 'sources'>('tasks')
  const [statusFilter, setStatusFilter] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showTaskDetail, setShowTaskDetail] = useState(false)
  const [selectedTask, setSelectedTask] = useState<TaskDefinition | null>(null)
  const [taskExecutions, setTaskExecutions] = useState<TaskChainNode[]>([])
  const [createLoading, setCreateLoading] = useState(false)
  const [newTask, setNewTask] = useState<CreateTaskRequest>({
    name: '',
    task_type: 'stock_list',
    params: {},
    priority: 'NORMAL',
  })
  const [dbConnected, setDbConnected] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [notification, setNotification] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:19100';
      const [overviewData, tasksData, triggersData, sourcesData, chainsData] = await Promise.all([
        datacenterService.getOverview(),
        datacenterService.getTasks({ status: statusFilter || undefined }),
        datacenterService.getTriggers(),
        datacenterService.getDataSources(),
        fetch(`${API_BASE_URL}/api/datacenter/chains`).then(r => r.json()),
      ])
      setOverview(overviewData)
      setTasks(tasksData.tasks)
      setTriggers(triggersData.triggers)
      setSources(sourcesData.sources)
      setChains(chainsData.chains || [])
      setDbConnected(true)
    } catch (error) {
      console.error('Failed to fetch data:', error)
      setDbConnected(false)
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  const showNotification = useCallback((type: 'success' | 'error' | 'info', message: string) => {
    setNotification({ type, message })
    setTimeout(() => setNotification(null), 5000)
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [fetchData])

  const handleStartAll = async () => {
    setActionLoading('start-all')
    try {
      const queueResult = await datacenterService.startQueue()
      if (!queueResult.success) {
        showNotification('error', '启动任务队列失败')
        return
      }
      const result = await datacenterService.startAllTasks()
      if (result.success) {
        showNotification('success', `已启动 ${result.started?.length || 0} 个数据采集任务，数据将写入数据库`)
      } else {
        showNotification('info', result.message || '任务已启动')
      }
      fetchData()
    } catch (error) {
      console.error('Failed to start all tasks:', error)
      showNotification('error', '启动任务失败，请检查数据库连接')
    } finally {
      setActionLoading(null)
    }
  }

  const handlePauseAll = async () => {
    setActionLoading('pause-all')
    try {
      const result = await datacenterService.pauseAllTasks()
      if (result.success) {
        showNotification('success', `已暂停 ${result.paused?.length || 0} 个任务`)
      }
      fetchData()
    } catch (error) {
      console.error('Failed to pause all tasks:', error)
      showNotification('error', '暂停任务失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleInitTasks = async () => {
    setActionLoading('init-tasks')
    try {
      const result = await datacenterService.initDefaultTasks()
      if (result.success) {
        showNotification('success', result.message || `已创建 ${result.created_count} 个默认任务`)
      }
      fetchData()
    } catch (error) {
      console.error('Failed to init tasks:', error)
      showNotification('error', '初始化任务失败')
    } finally {
      setActionLoading(null)
    }
  }

  const handleTaskAction = async (taskId: string, action: 'start' | 'pause' | 'cancel' | 'retry') => {
    setActionLoading(`${action}-${taskId}`)
    try {
      let result
      switch (action) {
        case 'start':
          result = await datacenterService.startTask(taskId)
          if (result.success) {
            showNotification('success', '任务已启动，数据将写入数据库')
          }
          break
        case 'pause':
          result = await datacenterService.pauseTask(taskId)
          if (result.success) {
            showNotification('info', '任务已暂停')
          }
          break
        case 'cancel':
          result = await datacenterService.cancelTask(taskId)
          if (result.success) {
            showNotification('info', '任务已取消')
          }
          break
        case 'retry':
          result = await datacenterService.retryTask(taskId)
          if (result.success) {
            showNotification('success', '任务重试已启动，数据将写入数据库')
          }
          break
      }
      fetchData()
    } catch (error) {
      console.error(`Failed to ${action} task:`, error)
      showNotification('error', `任务${action === 'start' ? '启动' : action === 'pause' ? '暂停' : action === 'cancel' ? '取消' : '重试'}失败`)
    } finally {
      setActionLoading(null)
    }
  }

  const handleTriggerAction = async (triggerId: string, action: 'enable' | 'disable' | 'execute') => {
    try {
      switch (action) {
        case 'enable':
          await datacenterService.enableTrigger(triggerId)
          break
        case 'disable':
          await datacenterService.disableTrigger(triggerId)
          break
        case 'execute':
          await datacenterService.executeTrigger(triggerId)
          break
      }
      fetchData()
    } catch (error) {
      console.error(`Failed to ${action} trigger:`, error)
    }
  }

  const handleCreateTask = async () => {
    if (!newTask.name.trim()) return
    
    setCreateLoading(true)
    try {
      const selectedType = taskTypeOptions.find(t => t.type === newTask.task_type)
      await datacenterService.createTask({
        ...newTask,
        data_source: selectedType?.data_source,
      })
      setShowCreateModal(false)
      setNewTask({
        name: '',
        task_type: 'stock_list',
        params: {},
        priority: 'NORMAL',
      })
      fetchData()
    } catch (error) {
      console.error('Failed to create task:', error)
    } finally {
      setCreateLoading(false)
    }
  }

  const handleViewTask = (task: TaskDefinition) => {
    router.push(`/datacenter/task/${task.task_id}`)
  }

  const formatTime = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatDuration = (ms: number | null) => {
    if (!ms) return '-'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}min`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-gold)]" />
      </div>
    )
  }

  return (
    <>
      {notification && (
        <div className="fixed top-4 right-4 z-50 animate-in slide-in-from-top-2">
          <div className={`flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg border ${
            notification.type === 'success' 
              ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-300'
              : notification.type === 'error'
              ? 'bg-rose-500/20 border-rose-500/30 text-rose-300'
              : 'bg-blue-500/20 border-blue-500/30 text-blue-300'
          }`}>
            {notification.type === 'success' && <CheckCircle className="w-5 h-5" />}
            {notification.type === 'error' && <XCircle className="w-5 h-5" />}
            {notification.type === 'info' && <AlertCircle className="w-5 h-5" />}
            <span className="text-sm font-medium">{notification.message}</span>
            <button onClick={() => setNotification(null)} className="ml-2 hover:opacity-70">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleStartAll}
            disabled={actionLoading === 'start-all'}
            className="gap-2 bg-emerald-500/10 border-emerald-500/30 hover:bg-emerald-500/20"
          >
            {actionLoading === 'start-all' ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            一键启动
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handlePauseAll}
            disabled={actionLoading === 'pause-all'}
            className="gap-2 bg-yellow-500/10 border-yellow-500/30 hover:bg-yellow-500/20"
          >
            {actionLoading === 'pause-all' ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Pause className="w-4 h-4" />
            )}
            一键暂停
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleInitTasks}
            disabled={actionLoading === 'init-tasks'}
            className="gap-2 bg-violet-500/10 border-violet-500/30 hover:bg-violet-500/20"
          >
            {actionLoading === 'init-tasks' ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
            初始化任务
          </Button>
        </div>
        <Button variant="outline" size="sm" onClick={fetchData} className="gap-2">
          <RefreshCw className="w-4 h-4" />
          刷新
        </Button>
      </div>

      <div className="grid grid-cols-5 gap-4 mb-6">
        <div className="glass-panel p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-amber-500/20 flex items-center justify-center">
              <Activity className="w-4 h-4 text-amber-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs">运行中</p>
              <p className="text-xl font-semibold text-white">{overview?.queue.running || 0}</p>
            </div>
          </div>
        </div>
        <div className="glass-panel p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/20 flex items-center justify-center">
              <CheckCircle className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs">已完成</p>
              <p className="text-xl font-semibold text-white">{overview?.queue.completed || 0}</p>
            </div>
          </div>
        </div>
        <div className="glass-panel p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-rose-500/20 flex items-center justify-center">
              <XCircle className="w-4 h-4 text-rose-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs">失败</p>
              <p className="text-xl font-semibold text-white">{overview?.queue.failed || 0}</p>
            </div>
          </div>
        </div>
        <div className="glass-panel p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-violet-500/20 flex items-center justify-center">
              <Zap className="w-4 h-4 text-violet-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs">成功率</p>
              <p className="text-xl font-semibold text-white">{overview?.success_rate || 0}%</p>
            </div>
          </div>
        </div>
        <div className="glass-panel p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-500/20 flex items-center justify-center">
              <Server className="w-4 h-4 text-blue-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs">数据存储</p>
              <p className="text-sm font-semibold text-white">PostgreSQL</p>
            </div>
          </div>
        </div>
      </div>

      <div className="glass-panel p-3 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-amber-500/20 flex items-center justify-center">
                <Download className="w-3.5 h-3.5 text-amber-400" />
              </div>
              <div>
                <p className="text-xs text-zinc-500">数据源</p>
                <p className="text-xs text-white font-medium">东方财富/AKShare</p>
              </div>
            </div>
            <ArrowRight className="w-3 h-3 text-zinc-600" />
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-violet-500/20 flex items-center justify-center">
                <Layers className="w-3.5 h-3.5 text-violet-400" />
              </div>
              <div>
                <p className="text-xs text-zinc-500">数据处理</p>
                <p className="text-xs text-white font-medium">验证/清洗/转换</p>
              </div>
            </div>
            <ArrowRight className="w-3 h-3 text-zinc-600" />
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                <Upload className="w-3.5 h-3.5 text-emerald-400" />
              </div>
              <div>
                <p className="text-xs text-zinc-500">数据存储</p>
                <p className="text-xs text-white font-medium">PostgreSQL 数据库</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-zinc-500">
            <HardDrive className="w-3.5 h-3.5" />
            <span>所有采集数据直接写入数据库</span>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between mb-4 border-b border-white/[0.05] pb-4">
        <div className="flex gap-2">
          {[
            { key: 'tasks', label: '任务管理', icon: <Activity className="w-4 h-4" /> },
            { key: 'chains', label: '任务链路', icon: <Layers className="w-4 h-4" /> },
            { key: 'triggers', label: '触发器', icon: <Zap className="w-4 h-4" /> },
            { key: 'sources', label: '数据源', icon: <Database className="w-4 h-4" /> },
          ].map((tab) => (
            <Button
              key={tab.key}
              variant={activeTab === tab.key ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setActiveTab(tab.key as typeof activeTab)}
              className={activeTab === tab.key 
                ? 'bg-[var(--accent-gold)] text-black gap-2' 
                : 'text-zinc-400 hover:text-white gap-2'
              }
            >
              {tab.icon}
              {tab.label}
            </Button>
          ))}
        </div>
        {activeTab === 'tasks' && (
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => setShowCreateModal(true)}
            className="border-[var(--accent-gold)]/30 text-[var(--accent-gold)] gap-2"
          >
            <Plus className="w-4 h-4" />
            新建任务
          </Button>
        )}
      </div>

      {activeTab === 'tasks' && (
        <div className="space-y-4">
          <div className="flex gap-2">
            {[
              { key: null, label: '全部' },
              { key: 'running', label: '运行中' },
              { key: 'queued', label: '队列中' },
              { key: 'completed', label: '已完成' },
              { key: 'failed', label: '失败' },
              { key: 'paused', label: '已暂停' },
            ].map((filter) => (
              <Button
                key={filter.key || 'all'}
                variant={statusFilter === filter.key ? 'outline' : 'ghost'}
                size="sm"
                onClick={() => setStatusFilter(filter.key)}
                className={statusFilter === filter.key 
                  ? 'border-[var(--accent-gold)]/30 text-[var(--accent-gold)]' 
                  : 'text-zinc-500'
                }
              >
                {filter.label}
              </Button>
            ))}
          </div>

          <div className="glass-panel overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/[0.05] text-zinc-500 text-xs">
                    <th className="text-left p-4 font-medium">任务名称</th>
                    <th className="text-left p-4 font-medium">类型</th>
                    <th className="text-left p-4 font-medium">状态</th>
                    <th className="text-left p-4 font-medium">进度</th>
                    <th className="text-left p-4 font-medium">数据源</th>
                    <th className="text-left p-4 font-medium">创建时间</th>
                    <th className="text-right p-4 font-medium">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-12">
                        <div className="flex flex-col items-center text-center">
                          <div className="w-16 h-16 rounded-2xl bg-zinc-800/50 flex items-center justify-center mb-4">
                            <Activity className="w-8 h-8 text-zinc-600" />
                          </div>
                          <p className="text-zinc-400 font-medium mb-2">暂无任务数据</p>
                          <p className="text-zinc-600 text-sm mb-4">点击下方按钮创建您的第一个数据采集任务</p>
                          <div className="flex gap-3">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={handleInitTasks}
                              className="gap-2 border-violet-500/30 text-violet-400 hover:bg-violet-500/10"
                            >
                              <Layers className="w-4 h-4" />
                              初始化默认任务
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => setShowCreateModal(true)}
                              className="gap-2 bg-[var(--accent-gold)] text-black hover:bg-[var(--accent-gold)]/90"
                            >
                              <Plus className="w-4 h-4" />
                              新建任务
                            </Button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    tasks.map((task) => {
                      const config = statusConfig[task.status] || statusConfig.pending
                      return (
                        <tr 
                          key={task.task_id} 
                          className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors cursor-pointer"
                          onClick={() => handleViewTask(task)}
                        >
                          <td className="p-4">
                            <div className="font-medium text-white">{task.name}</div>
                            <div className="text-xs text-zinc-600 mt-0.5">{task.task_id}</div>
                          </td>
                          <td className="p-4 text-zinc-400 text-sm">{task.task_type}</td>
                          <td className="p-4">
                            <Badge variant="secondary" className={`${config.bgColor} ${config.color} gap-1`}>
                              {config.icon}
                              {config.label}
                            </Badge>
                          </td>
                          <td className="p-4">
                            <div className="flex items-center gap-2 min-w-[120px]">
                              <div className="flex-1 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-[var(--accent-gold)] transition-all"
                                  style={{ width: `${task.progress}%` }}
                                />
                              </div>
                              <span className="text-xs text-zinc-500 w-10">{task.progress.toFixed(0)}%</span>
                            </div>
                          </td>
                          <td className="p-4 text-zinc-400 text-sm">{task.data_source || '-'}</td>
                          <td className="p-4 text-zinc-500 text-sm">{formatTime(task.created_at)}</td>
                          <td className="p-4">
                            <div className="flex justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                              {task.status === 'paused' && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleTaskAction(task.task_id, 'start')}
                                  disabled={actionLoading === `start-${task.task_id}`}
                                  className="text-emerald-400 hover:bg-emerald-500/10 h-8 w-8 p-0"
                                  title="启动任务并写入数据库"
                                >
                                  {actionLoading === `start-${task.task_id}` ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <Play className="w-4 h-4" />
                                  )}
                                </Button>
                              )}
                              {task.status === 'running' && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleTaskAction(task.task_id, 'pause')}
                                  disabled={actionLoading === `pause-${task.task_id}`}
                                  className="text-yellow-400 hover:bg-yellow-500/10 h-8 w-8 p-0"
                                  title="暂停任务"
                                >
                                  {actionLoading === `pause-${task.task_id}` ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <Pause className="w-4 h-4" />
                                  )}
                                </Button>
                              )}
                              {task.status === 'failed' && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleTaskAction(task.task_id, 'retry')}
                                  disabled={actionLoading === `retry-${task.task_id}`}
                                  className="text-blue-400 hover:bg-blue-500/10 h-8 w-8 p-0"
                                  title="重试任务"
                                >
                                  {actionLoading === `retry-${task.task_id}` ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <RefreshCw className="w-4 h-4" />
                                  )}
                                </Button>
                              )}
                              {(task.status === 'queued' || task.status === 'running') && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => handleTaskAction(task.task_id, 'cancel')}
                                  disabled={actionLoading === `cancel-${task.task_id}`}
                                  className="text-rose-400 hover:bg-rose-500/10 h-8 w-8 p-0"
                                  title="取消任务"
                                >
                                  {actionLoading === `cancel-${task.task_id}` ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <Square className="w-4 h-4" />
                                  )}
                                </Button>
                              )}
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleViewTask(task)}
                                className="text-zinc-400 hover:bg-zinc-500/10 h-8 w-8 p-0"
                                title="查看详情"
                              >
                                <ChevronRight className="w-4 h-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'triggers' && (
        <div className="space-y-4">
          {triggers.length === 0 ? (
            <div className="glass-panel p-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-zinc-800/50 flex items-center justify-center mx-auto mb-4">
                <Zap className="w-8 h-8 text-zinc-600" />
              </div>
              <p className="text-zinc-400 font-medium mb-2">暂无触发器</p>
              <p className="text-zinc-600 text-sm">创建触发器可以自动定时执行数据采集任务</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {triggers.map((trigger) => {
                const typeConfig = triggerTypeConfig[trigger.trigger_type] || triggerTypeConfig.manual
                return (
                  <div key={trigger.trigger_id} className="glass-panel p-5 hover:border-white/[0.1] transition-colors">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center">
                          {typeConfig.icon}
                        </div>
                        <div>
                          <h3 className="font-medium text-white">{trigger.name}</h3>
                          <p className="text-xs text-zinc-600">{typeConfig.label}</p>
                        </div>
                      </div>
                      <Badge
                        variant="secondary"
                        className={trigger.status === 'enabled' 
                          ? 'bg-emerald-500/20 text-emerald-400' 
                          : 'bg-zinc-500/20 text-zinc-400'
                        }
                      >
                        {trigger.status === 'enabled' ? '已启用' : '已禁用'}
                      </Badge>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                      <div>
                        <p className="text-zinc-600 text-xs mb-1">触发次数</p>
                        <p className="text-white">{trigger.trigger_count}</p>
                      </div>
                      <div>
                        <p className="text-zinc-600 text-xs mb-1">错误次数</p>
                        <p className={trigger.error_count > 0 ? 'text-rose-400' : 'text-white'}>
                          {trigger.error_count}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex justify-end gap-2 pt-3 border-t border-white/[0.05]">
                      {trigger.status === 'enabled' ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleTriggerAction(trigger.trigger_id, 'disable')}
                          className="text-yellow-400 hover:bg-yellow-500/10"
                        >
                          <Pause className="w-4 h-4 mr-1" />
                          禁用
                        </Button>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleTriggerAction(trigger.trigger_id, 'enable')}
                          className="text-emerald-400 hover:bg-emerald-500/10"
                        >
                          <Play className="w-4 h-4 mr-1" />
                          启用
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleTriggerAction(trigger.trigger_id, 'execute')}
                        className="text-[var(--accent-gold)] hover:bg-[var(--accent-gold)]/10"
                      >
                        <Zap className="w-4 h-4 mr-1" />
                        立即执行
                      </Button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {activeTab === 'chains' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                try {
                  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:19100';
                  await fetch(`${API_BASE_URL}/api/datacenter/chains/default`, { method: 'POST' })
                  fetchData()
                } catch (error) {
                  console.error('Failed to create chain:', error)
                }
              }}
              className="border-[var(--accent-gold)]/30 text-[var(--accent-gold)] gap-2"
            >
              <Plus className="w-4 h-4" />
              创建默认链路
            </Button>
          </div>
          
          {chains.length === 0 ? (
            <div className="glass-panel p-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-zinc-800/50 flex items-center justify-center mx-auto mb-4">
                <Layers className="w-8 h-8 text-zinc-600" />
              </div>
              <p className="text-zinc-400 font-medium mb-2">暂无任务链路</p>
              <p className="text-zinc-600 text-sm mb-4">创建任务链路可以编排多个任务的执行顺序</p>
              <Button
                variant="outline"
                onClick={async () => {
                  try {
                    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:19100';
                    await fetch(`${API_BASE_URL}/api/datacenter/chains/default`, { method: 'POST' })
                    fetchData()
                  } catch (error) {
                    console.error('Failed to create chain:', error)
                  }
                }}
                className="gap-2"
              >
                <Plus className="w-4 h-4" />
                创建默认链路
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {chains.map((chain) => {
                const chainConfig = statusConfig[chain.status] || statusConfig.pending
                return (
                  <div 
                    key={chain.chain_id} 
                    className="glass-panel p-5 hover:border-white/[0.1] transition-colors cursor-pointer"
                    onClick={() => router.push(`/datacenter/task/${chain.chain_id}`)}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
                          <Layers className="w-5 h-5 text-amber-400" />
                        </div>
                        <div>
                          <h3 className="font-medium text-white">{chain.name}</h3>
                          <p className="text-xs text-zinc-600">{chain.chain_id}</p>
                        </div>
                      </div>
                      <Badge
                        variant="secondary"
                        className={`${chainConfig.bgColor} ${chainConfig.color}`}
                      >
                        {chainConfig.label}
                      </Badge>
                    </div>
                    
                    <div className="flex justify-end gap-2 pt-3 border-t border-white/[0.05]">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          router.push(`/datacenter/task/${chain.chain_id}`)
                        }}
                        className="text-[var(--accent-gold)] hover:bg-[var(--accent-gold)]/10"
                      >
                        <ChevronRight className="w-4 h-4 mr-1" />
                        查看详情
                      </Button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {activeTab === 'sources' && (
        <div>
          {sources.length === 0 ? (
            <div className="glass-panel p-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-zinc-800/50 flex items-center justify-center mx-auto mb-4">
                <Database className="w-8 h-8 text-zinc-600" />
              </div>
              <p className="text-zinc-400 font-medium mb-2">暂无数据源</p>
              <p className="text-zinc-600 text-sm">系统将自动检测可用的数据源</p>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-4">
              {sources.map((source) => (
                <div key={source.source_id} className="glass-panel p-5 hover:border-white/[0.1] transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-[var(--accent-gold)]/20 flex items-center justify-center">
                      <Database className="w-5 h-5 text-[var(--accent-gold)]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-white truncate">{source.name}</h3>
                      <p className="text-xs text-zinc-600">{source.category}</p>
                    </div>
                    <Badge
                      variant="secondary"
                      className={source.is_available 
                        ? 'bg-emerald-500/20 text-emerald-400' 
                        : 'bg-rose-500/20 text-rose-400'
                      }
                    >
                      {source.is_available ? '可用' : '不可用'}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowCreateModal(false)} />
          <div className="relative w-full max-w-lg bg-[var(--bg-secondary)] border border-white/[0.08] rounded-2xl shadow-2xl">
            <div className="flex items-center justify-between p-6 border-b border-white/[0.05]">
              <h3 className="text-lg font-semibold text-white">新建任务</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">任务名称</label>
                <input
                  type="text"
                  value={newTask.name}
                  onChange={(e) => setNewTask({ ...newTask, name: e.target.value })}
                  placeholder="输入任务名称"
                  className="w-full px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/40"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">任务类型</label>
                <select
                  value={newTask.task_type}
                  onChange={(e) => setNewTask({ ...newTask, task_type: e.target.value })}
                  className="w-full px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:border-violet-500/40"
                >
                  {taskTypeOptions.map((opt) => (
                    <option key={opt.type} value={opt.type} className="bg-zinc-900">
                      {opt.name} - {opt.description}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">优先级</label>
                <select
                  value={newTask.priority}
                  onChange={(e) => setNewTask({ ...newTask, priority: e.target.value as CreateTaskRequest['priority'] })}
                  className="w-full px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:border-violet-500/40"
                >
                  <option value="CRITICAL" className="bg-zinc-900">紧急</option>
                  <option value="HIGH" className="bg-zinc-900">高</option>
                  <option value="NORMAL" className="bg-zinc-900">普通</option>
                  <option value="LOW" className="bg-zinc-900">低</option>
                  <option value="BACKGROUND" className="bg-zinc-900">后台</option>
                </select>
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 p-6 border-t border-white/[0.05]">
              <Button variant="secondary" onClick={() => setShowCreateModal(false)}>取消</Button>
              <Button onClick={handleCreateTask} disabled={createLoading || !newTask.name.trim()}>
                {createLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
                创建并启动
              </Button>
            </div>
          </div>
        </div>
      )}

      {showTaskDetail && selectedTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowTaskDetail(false)} />
          <div className="relative w-full max-w-3xl bg-[var(--bg-secondary)] border border-white/[0.08] rounded-2xl shadow-2xl max-h-[80vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between p-6 border-b border-white/[0.05]">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
                  <FileText className="w-5 h-5 text-amber-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">{selectedTask.name}</h3>
                  <p className="text-xs text-zinc-500">{selectedTask.task_id}</p>
                </div>
              </div>
              <button onClick={() => setShowTaskDetail(false)} className="text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6">
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="glass-panel p-4">
                  <p className="text-zinc-500 text-xs mb-1">状态</p>
                  <div className="flex items-center gap-2">
                    {statusConfig[selectedTask.status]?.icon}
                    <span className={`font-medium ${statusConfig[selectedTask.status]?.color}`}>
                      {statusConfig[selectedTask.status]?.label || selectedTask.status}
                    </span>
                  </div>
                </div>
                <div className="glass-panel p-4">
                  <p className="text-zinc-500 text-xs mb-1">进度</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-zinc-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[var(--accent-gold)] transition-all"
                        style={{ width: `${selectedTask.progress}%` }}
                      />
                    </div>
                    <span className="text-white text-sm">{selectedTask.progress.toFixed(0)}%</span>
                  </div>
                </div>
                <div className="glass-panel p-4">
                  <p className="text-zinc-500 text-xs mb-1">优先级</p>
                  <span className="text-white font-medium">{selectedTask.priority}</span>
                </div>
              </div>

              {selectedTask.error && (
                <div className="glass-panel p-4 mb-6 border-rose-500/30 bg-rose-500/5">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-rose-400 mt-0.5" />
                    <div>
                      <p className="text-rose-400 font-medium mb-1">错误信息</p>
                      <p className="text-zinc-300 text-sm">{selectedTask.error}</p>
                    </div>
                  </div>
                </div>
              )}

              <div className="glass-panel p-4">
                <h4 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-zinc-500" />
                  执行链路 ({taskExecutions.length})
                </h4>
                
                {taskExecutions.length === 0 ? (
                  <div className="text-center py-8 text-zinc-500 text-sm">
                    暂无执行记录
                  </div>
                ) : (
                  <div className="space-y-3">
                    {taskExecutions.map((execution, index) => {
                      const execConfig = statusConfig[execution.status] || statusConfig.pending
                      return (
                        <div 
                          key={execution.id}
                          className="flex items-center gap-4 p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]"
                        >
                          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-zinc-800 text-zinc-400 text-sm font-medium">
                            {index + 1}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-white font-medium text-sm">{execution.name}</span>
                              <Badge variant="secondary" className={`${execConfig.bgColor} ${execConfig.color} text-xs`}>
                                {execConfig.label}
                              </Badge>
                            </div>
                            <div className="flex items-center gap-4 text-xs text-zinc-500">
                              <span>处理: {execution.records_processed} 条</span>
                              {execution.records_failed > 0 && (
                                <span className="text-rose-400">失败: {execution.records_failed} 条</span>
                              )}
                              <span>耗时: {formatDuration(execution.duration_ms)}</span>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 p-6 border-t border-white/[0.05]">
              {selectedTask.status === 'paused' && (
                <Button
                  variant="outline"
                  onClick={() => {
                    handleTaskAction(selectedTask.task_id, 'start')
                    setShowTaskDetail(false)
                  }}
                  className="gap-2 border-emerald-500/30 text-emerald-400"
                >
                  <Play className="w-4 h-4" />
                  启动任务
                </Button>
              )}
              {selectedTask.status === 'running' && (
                <Button
                  variant="outline"
                  onClick={() => {
                    handleTaskAction(selectedTask.task_id, 'pause')
                    setShowTaskDetail(false)
                  }}
                  className="gap-2 border-yellow-500/30 text-yellow-400"
                >
                  <Pause className="w-4 h-4" />
                  暂停任务
                </Button>
              )}
              {selectedTask.status === 'failed' && (
                <Button
                  variant="outline"
                  onClick={() => {
                    handleTaskAction(selectedTask.task_id, 'retry')
                    setShowTaskDetail(false)
                  }}
                  className="gap-2 border-blue-500/30 text-blue-400"
                >
                  <RefreshCw className="w-4 h-4" />
                  重试任务
                </Button>
              )}
              <Button variant="secondary" onClick={() => setShowTaskDetail(false)}>
                关闭
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
