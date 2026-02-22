'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Button, Badge, Progress } from '@/components/ui'
import {
  ArrowLeft,
  Play,
  Pause,
  Square,
  RefreshCw,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Activity,
  Database,
  Zap,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Layers,
  Target,
  Timer,
  FileText,
  BarChart3,
} from 'lucide-react'

interface TaskNode {
  node_id: string
  name: string
  node_type: string
  task_type: string
  task_params: Record<string, unknown>
  status: string
  started_at: string | null
  completed_at: string | null
  result: Record<string, unknown> | null
  error: string | null
}

interface TaskEdge {
  edge_id: string
  source_id: string
  target_id: string
  label: string
}

interface DataTarget {
  target_id: string
  target_type: string
  target_name: string
  target_location: string
  status: string
  records_synced: number
}

interface TaskChain {
  chain_id: string
  name: string
  description: string
  nodes: Record<string, TaskNode>
  edges: TaskEdge[]
  status: string
  created_at: string
  started_at: string | null
  completed_at: string | null
  context: Record<string, unknown>
  data_targets: DataTarget[]
}

interface SingleTask {
  task_id: string
  name: string
  task_type: string
  status: string
  priority: string
  progress: number
  progress_message: string
  data_source: string | null
  data_type: string | null
  params: Record<string, unknown>
  created_at: string
  started_at: string | null
  completed_at: string | null
  result: Record<string, unknown> | null
  error: string | null
  retry_count: number
  max_retries: number
  dependencies: string[]
}

interface TaskExecution {
  execution_id: string
  task_id: string
  chain_id: string | null
  status: string
  started_at: string
  completed_at: string | null
  duration_ms: number | null
  records_processed: number
  records_failed: number
  result: Record<string, unknown> | null
  error: string | null
}

const statusConfig: Record<string, { color: string; bgColor: string; icon: React.ReactNode; label: string }> = {
  pending: { color: 'text-zinc-400', bgColor: 'bg-zinc-500/20', icon: <Clock className="w-4 h-4" />, label: '等待中' },
  queued: { color: 'text-blue-400', bgColor: 'bg-blue-500/20', icon: <Clock className="w-4 h-4" />, label: '队列中' },
  running: { color: 'text-amber-400', bgColor: 'bg-amber-500/20', icon: <Loader2 className="w-4 h-4 animate-spin" />, label: '运行中' },
  completed: { color: 'text-emerald-400', bgColor: 'bg-emerald-500/20', icon: <CheckCircle className="w-4 h-4" />, label: '已完成' },
  failed: { color: 'text-rose-400', bgColor: 'bg-rose-500/20', icon: <XCircle className="w-4 h-4" />, label: '失败' },
  cancelled: { color: 'text-zinc-500', bgColor: 'bg-zinc-500/20', icon: <XCircle className="w-4 h-4" />, label: '已取消' },
  paused: { color: 'text-yellow-400', bgColor: 'bg-yellow-500/20', icon: <Pause className="w-4 h-4" />, label: '已暂停' },
}

const priorityConfig: Record<string, { color: string; label: string }> = {
  CRITICAL: { color: 'text-rose-400', label: '紧急' },
  HIGH: { color: 'text-amber-400', label: '高' },
  NORMAL: { color: 'text-blue-400', label: '普通' },
  LOW: { color: 'text-zinc-400', label: '低' },
  BACKGROUND: { color: 'text-zinc-500', label: '后台' },
}

const nodeTypeColors: Record<string, string> = {
  task: '#f59e0b',
  condition: '#8b5cf6',
  parallel: '#06b6d4',
  merge: '#10b981',
}

function TaskNodeComponent({ data }: { data: { label: string; taskType: string; status: string; nodeId: string } }) {
  const config = statusConfig[data.status] || statusConfig.pending
  
  return (
    <div className="px-4 py-3 rounded-xl border-2 shadow-lg min-w-[180px]" 
         style={{ 
           borderColor: nodeTypeColors.task, 
           backgroundColor: 'rgba(23, 23, 23, 0.95)',
         }}>
      <div className="flex items-center gap-2 mb-2">
        <div className={`w-6 h-6 rounded-full flex items-center justify-center ${config.bgColor}`}>
          {config.icon}
        </div>
        <span className="text-sm font-medium text-white truncate">{data.label}</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-zinc-500">{data.taskType}</span>
        <Badge variant="secondary" className={`${config.bgColor} ${config.color} text-xs`}>
          {config.label}
        </Badge>
      </div>
    </div>
  )
}

const nodeTypes = {
  taskNode: TaskNodeComponent,
}

export default function TaskDetailPage() {
  const params = useParams()
  const router = useRouter()
  const taskId = params.taskId as string
  
  const [chain, setChain] = useState<TaskChain | null>(null)
  const [task, setTask] = useState<SingleTask | null>(null)
  const [executions, setExecutions] = useState<TaskExecution[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['info', 'executions']))
  const [isChain, setIsChain] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const chainRes = await fetch(`${API_BASE_URL}/api/datacenter/chains/${taskId}`)
      if (chainRes.ok) {
        const data = await chainRes.json()
        setChain(data)
        setIsChain(true)
      } else {
        const taskRes = await fetch(`${API_BASE_URL}/api/datacenter/tasks/${taskId}`)
        if (taskRes.ok) {
          const data = await taskRes.json()
          setTask(data)
          setIsChain(false)
        }
      }

      const execRes = await fetch(`${API_BASE_URL}/api/datacenter/executions?task_id=${taskId}&limit=20`)
      if (execRes.ok) {
        const data = await execRes.json()
        setExecutions(data.executions || [])
      }
    } catch (error) {
      console.error('Failed to fetch task data:', error)
    } finally {
      setLoading(false)
    }
  }, [taskId])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [fetchData])

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev)
      if (next.has(section)) {
        next.delete(section)
      } else {
        next.add(section)
      }
      return next
    })
  }

  const handleTaskAction = async (action: 'start' | 'pause' | 'cancel') => {
    setActionLoading(true)
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      await fetch(`${API_BASE_URL}/api/datacenter/tasks/${taskId}/${action}`, { method: 'PUT' })
      fetchData()
    } catch (error) {
      console.error(`Failed to ${action} task:`, error)
    } finally {
      setActionLoading(false)
    }
  }

  const handleExecuteChain = async () => {
    setActionLoading(true)
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      await fetch(`${API_BASE_URL}/api/datacenter/chains/${taskId}/execute`, { method: 'POST' })
      fetchData()
    } catch (error) {
      console.error('Failed to execute chain:', error)
    } finally {
      setActionLoading(false)
    }
  }

  const formatTime = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const formatDuration = (ms: number | null) => {
    if (!ms) return '-'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}min`
  }

  const buildFlowElements = (): { nodes: Node[]; edges: Edge[] } => {
    if (!chain) return { nodes: [], edges: [] }

    const nodes: Node[] = []
    const edges: Edge[] = []
    
    const levels: Record<string, number> = {}
    
    const calculateLevels = (nodeId: string, level: number) => {
      if (levels[nodeId] !== undefined && levels[nodeId] >= level) return
      levels[nodeId] = level
      
      chain.edges
        .filter(e => e.source_id === nodeId)
        .forEach(e => calculateLevels(e.target_id, level + 1))
    }
    
    Object.keys(chain.nodes)
      .filter(id => !chain.edges.some(e => e.target_id === id))
      .forEach(id => calculateLevels(id, 0))

    const levelGroups: Record<number, string[]> = {}
    Object.entries(levels).forEach(([id, level]) => {
      if (!levelGroups[level]) levelGroups[level] = []
      levelGroups[level].push(id)
    })

    Object.entries(chain.nodes).forEach(([nodeId, node]) => {
      const level = levels[nodeId] || 0
      const nodesAtLevel = levelGroups[level] || []
      const indexInLevel = nodesAtLevel.indexOf(nodeId)
      
      nodes.push({
        id: nodeId,
        type: 'taskNode',
        position: {
          x: 100 + level * 280,
          y: 100 + indexInLevel * 150,
        },
        data: {
          label: node.name,
          taskType: node.task_type,
          status: node.status,
          nodeId: nodeId,
        },
      })
    })

    chain.edges.forEach(edge => {
      edges.push({
        id: edge.edge_id,
        source: edge.source_id,
        target: edge.target_id,
        animated: true,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: '#f59e0b',
        },
        style: {
          stroke: '#f59e0b',
          strokeWidth: 2,
        },
      })
    })

    return { nodes, edges }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--accent-gold)]" />
      </div>
    )
  }

  if (!chain && !task) {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <AlertCircle className="w-12 h-12 text-zinc-600 mb-4" />
        <p className="text-zinc-400 mb-4">任务不存在或未找到</p>
        <Button variant="outline" onClick={() => router.push('/datacenter')}>
          返回数据中心
        </Button>
      </div>
    )
  }

  const { nodes: flowNodes, edges: flowEdges } = buildFlowElements()
  const entity = chain || task
  const config = statusConfig[entity?.status || 'pending']

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push('/datacenter')}
            className="text-zinc-400 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回
          </Button>
          <div>
            <h1 className="text-xl font-semibold text-white">{entity?.name}</h1>
            <p className="text-sm text-zinc-500">ID: {(entity as SingleTask)?.task_id || (entity as TaskChain)?.chain_id}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge className={`${config.bgColor} ${config.color} gap-1`}>
            {config.icon}
            {config.label}
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchData}
            className="gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            刷新
          </Button>
          {isChain ? (
            <Button
              size="sm"
              onClick={handleExecuteChain}
              disabled={actionLoading || chain?.status === 'running'}
              className="gap-2 bg-[var(--accent-gold)] text-black"
            >
              {actionLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              执行任务链
            </Button>
          ) : task && (
            <div className="flex gap-2">
              {task.status === 'paused' && (
                <Button
                  size="sm"
                  onClick={() => handleTaskAction('start')}
                  disabled={actionLoading}
                  className="gap-2 bg-emerald-500 text-white"
                >
                  <Play className="w-4 h-4" />
                  启动
                </Button>
              )}
              {task.status === 'running' && (
                <Button
                  size="sm"
                  onClick={() => handleTaskAction('pause')}
                  disabled={actionLoading}
                  variant="outline"
                  className="gap-2"
                >
                  <Pause className="w-4 h-4" />
                  暂停
                </Button>
              )}
              {(task.status === 'queued' || task.status === 'running') && (
                <Button
                  size="sm"
                  onClick={() => handleTaskAction('cancel')}
                  disabled={actionLoading}
                  variant="outline"
                  className="gap-2 text-rose-400 border-rose-500/30"
                >
                  <Square className="w-4 h-4" />
                  取消
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      {isChain && chain ? (
        <>
          <div className="grid grid-cols-4 gap-4">
            <div className="glass-panel p-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-blue-500/20 flex items-center justify-center">
                  <Layers className="w-4 h-4 text-blue-400" />
                </div>
                <div>
                  <p className="text-zinc-500 text-xs">任务节点</p>
                  <p className="text-xl font-semibold text-white">{Object.keys(chain.nodes).length}</p>
                </div>
              </div>
            </div>
            <div className="glass-panel p-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-violet-500/20 flex items-center justify-center">
                  <Activity className="w-4 h-4 text-violet-400" />
                </div>
                <div>
                  <p className="text-zinc-500 text-xs">执行次数</p>
                  <p className="text-xl font-semibold text-white">{executions.length}</p>
                </div>
              </div>
            </div>
            <div className="glass-panel p-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                  <Target className="w-4 h-4 text-emerald-400" />
                </div>
                <div>
                  <p className="text-zinc-500 text-xs">数据目标</p>
                  <p className="text-xl font-semibold text-white">{chain.data_targets?.length || 0}</p>
                </div>
              </div>
            </div>
            <div className="glass-panel p-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-amber-500/20 flex items-center justify-center">
                  <Timer className="w-4 h-4 text-amber-400" />
                </div>
                <div>
                  <p className="text-zinc-500 text-xs">创建时间</p>
                  <p className="text-sm font-medium text-white">{formatTime(chain.created_at)}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="glass-panel overflow-hidden">
            <button
              className="w-full p-4 flex items-center justify-between hover:bg-white/[0.02]"
              onClick={() => toggleSection('flow')}
            >
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-400" />
                <span className="font-medium text-white">DAG 任务流</span>
              </div>
              {expandedSections.has('flow') ? (
                <ChevronDown className="w-5 h-5 text-zinc-400" />
              ) : (
                <ChevronRight className="w-5 h-5 text-zinc-400" />
              )}
            </button>
            
            {expandedSections.has('flow') && (
              <div className="h-[400px] border-t border-white/[0.05]">
                <ReactFlow
                  nodes={flowNodes}
                  edges={flowEdges}
                  nodeTypes={nodeTypes}
                  fitView
                  attributionPosition="bottom-left"
                >
                  <Background color="#333" gap={16} />
                  <Controls />
                  <MiniMap 
                    nodeColor={(node) => nodeTypeColors[node.data?.taskType] || '#f59e0b'}
                    maskColor="rgba(0,0,0,0.8)"
                  />
                </ReactFlow>
              </div>
            )}
          </div>

          <div className="glass-panel overflow-hidden">
            <button
              className="w-full p-4 flex items-center justify-between hover:bg-white/[0.02]"
              onClick={() => toggleSection('nodes')}
            >
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-blue-400" />
                <span className="font-medium text-white">任务节点详情</span>
                <Badge variant="secondary" className="bg-blue-500/20 text-blue-400">
                  {Object.keys(chain.nodes).length}
                </Badge>
              </div>
              {expandedSections.has('nodes') ? (
                <ChevronDown className="w-5 h-5 text-zinc-400" />
              ) : (
                <ChevronRight className="w-5 h-5 text-zinc-400" />
              )}
            </button>
            
            {expandedSections.has('nodes') && (
              <div className="border-t border-white/[0.05]">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-white/[0.05] text-zinc-500 text-xs">
                        <th className="text-left p-4 font-medium">节点名称</th>
                        <th className="text-left p-4 font-medium">任务类型</th>
                        <th className="text-left p-4 font-medium">状态</th>
                        <th className="text-left p-4 font-medium">开始时间</th>
                        <th className="text-left p-4 font-medium">完成时间</th>
                        <th className="text-left p-4 font-medium">错误信息</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(chain.nodes).map(([nodeId, node]) => {
                        const nodeConfig = statusConfig[node.status] || statusConfig.pending
                        return (
                          <tr key={nodeId} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                            <td className="p-4">
                              <div className="font-medium text-white">{node.name}</div>
                              <div className="text-xs text-zinc-600">{nodeId}</div>
                            </td>
                            <td className="p-4 text-zinc-400 text-sm">{node.task_type}</td>
                            <td className="p-4">
                              <Badge variant="secondary" className={`${nodeConfig.bgColor} ${nodeConfig.color} gap-1`}>
                                {nodeConfig.icon}
                                {nodeConfig.label}
                              </Badge>
                            </td>
                            <td className="p-4 text-zinc-400 text-sm">{formatTime(node.started_at)}</td>
                            <td className="p-4 text-zinc-400 text-sm">{formatTime(node.completed_at)}</td>
                            <td className="p-4">
                              {node.error && (
                                <span className="text-rose-400 text-sm truncate max-w-[200px] block">{node.error}</span>
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </>
      ) : task && (
        <>
          <div className="grid grid-cols-4 gap-4">
            <div className="glass-panel p-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-blue-500/20 flex items-center justify-center">
                  <Activity className="w-4 h-4 text-blue-400" />
                </div>
                <div>
                  <p className="text-zinc-500 text-xs">任务类型</p>
                  <p className="text-sm font-medium text-white">{task.task_type}</p>
                </div>
              </div>
            </div>
            <div className="glass-panel p-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-violet-500/20 flex items-center justify-center">
                  <BarChart3 className="w-4 h-4 text-violet-400" />
                </div>
                <div>
                  <p className="text-zinc-500 text-xs">优先级</p>
                  <p className={`text-sm font-medium ${priorityConfig[task.priority]?.color || 'text-white'}`}>
                    {priorityConfig[task.priority]?.label || task.priority}
                  </p>
                </div>
              </div>
            </div>
            <div className="glass-panel p-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                  <Database className="w-4 h-4 text-emerald-400" />
                </div>
                <div>
                  <p className="text-zinc-500 text-xs">数据源</p>
                  <p className="text-sm font-medium text-white">{task.data_source || '-'}</p>
                </div>
              </div>
            </div>
            <div className="glass-panel p-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-amber-500/20 flex items-center justify-center">
                  <Timer className="w-4 h-4 text-amber-400" />
                </div>
                <div>
                  <p className="text-zinc-500 text-xs">创建时间</p>
                  <p className="text-sm font-medium text-white">{formatTime(task.created_at)}</p>
                </div>
              </div>
            </div>
          </div>

          <div className="glass-panel overflow-hidden">
            <button
              className="w-full p-4 flex items-center justify-between hover:bg-white/[0.02]"
              onClick={() => toggleSection('info')}
            >
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-400" />
                <span className="font-medium text-white">任务信息</span>
              </div>
              {expandedSections.has('info') ? (
                <ChevronDown className="w-5 h-5 text-zinc-400" />
              ) : (
                <ChevronRight className="w-5 h-5 text-zinc-400" />
              )}
            </button>
            
            {expandedSections.has('info') && (
              <div className="border-t border-white/[0.05] p-4 space-y-4">
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <p className="text-zinc-500 text-xs mb-1">任务进度</p>
                    <div className="flex items-center gap-3">
                      <Progress value={task.progress} className="flex-1 h-2" />
                      <span className="text-sm text-white">{task.progress.toFixed(0)}%</span>
                    </div>
                    {task.progress_message && (
                      <p className="text-xs text-zinc-500 mt-1">{task.progress_message}</p>
                    )}
                  </div>
                  <div>
                    <p className="text-zinc-500 text-xs mb-1">重试次数</p>
                    <p className="text-sm text-white">{task.retry_count} / {task.max_retries}</p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-6">
                  <div>
                    <p className="text-zinc-500 text-xs mb-1">开始时间</p>
                    <p className="text-sm text-white">{formatTime(task.started_at)}</p>
                  </div>
                  <div>
                    <p className="text-zinc-500 text-xs mb-1">完成时间</p>
                    <p className="text-sm text-white">{formatTime(task.completed_at)}</p>
                  </div>
                  <div>
                    <p className="text-zinc-500 text-xs mb-1">数据类型</p>
                    <p className="text-sm text-white">{task.data_type || '-'}</p>
                  </div>
                </div>

                {task.params && Object.keys(task.params).length > 0 && (
                  <div>
                    <p className="text-zinc-500 text-xs mb-2">任务参数</p>
                    <pre className="bg-zinc-900/50 rounded-lg p-3 text-sm text-zinc-300 overflow-x-auto">
                      {JSON.stringify(task.params, null, 2)}
                    </pre>
                  </div>
                )}

                {task.error && (
                  <div>
                    <p className="text-rose-400 text-xs mb-2">错误信息</p>
                    <pre className="bg-rose-500/10 rounded-lg p-3 text-sm text-rose-300 overflow-x-auto">
                      {task.error}
                    </pre>
                  </div>
                )}

                {task.result && (
                  <div>
                    <p className="text-zinc-500 text-xs mb-2">执行结果</p>
                    <pre className="bg-zinc-900/50 rounded-lg p-3 text-sm text-zinc-300 overflow-x-auto">
                      {JSON.stringify(task.result, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}

      <div className="glass-panel overflow-hidden">
        <button
          className="w-full p-4 flex items-center justify-between hover:bg-white/[0.02]"
          onClick={() => toggleSection('executions')}
        >
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-violet-400" />
            <span className="font-medium text-white">执行历史</span>
            <Badge variant="secondary" className="bg-violet-500/20 text-violet-400">
              {executions.length}
            </Badge>
          </div>
          {expandedSections.has('executions') ? (
            <ChevronDown className="w-5 h-5 text-zinc-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-zinc-400" />
          )}
        </button>
        
        {expandedSections.has('executions') && (
          <div className="border-t border-white/[0.05]">
            {executions.length === 0 ? (
              <div className="p-8 text-center text-zinc-500">
                暂无执行记录
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/[0.05] text-zinc-500 text-xs">
                      <th className="text-left p-4 font-medium">执行ID</th>
                      <th className="text-left p-4 font-medium">状态</th>
                      <th className="text-left p-4 font-medium">开始时间</th>
                      <th className="text-left p-4 font-medium">耗时</th>
                      <th className="text-left p-4 font-medium">处理记录</th>
                      <th className="text-left p-4 font-medium">失败记录</th>
                    </tr>
                  </thead>
                  <tbody>
                    {executions.map((exec) => {
                      const execConfig = statusConfig[exec.status] || statusConfig.pending
                      return (
                        <tr key={exec.execution_id} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                          <td className="p-4">
                            <span className="text-zinc-300 font-mono text-sm">{exec.execution_id.slice(0, 8)}</span>
                          </td>
                          <td className="p-4">
                            <Badge variant="secondary" className={`${execConfig.bgColor} ${execConfig.color} gap-1`}>
                              {execConfig.icon}
                              {execConfig.label}
                            </Badge>
                          </td>
                          <td className="p-4 text-zinc-400 text-sm">{formatTime(exec.started_at)}</td>
                          <td className="p-4 text-zinc-400 text-sm">{formatDuration(exec.duration_ms)}</td>
                          <td className="p-4 text-zinc-400 text-sm">{exec.records_processed.toLocaleString()}</td>
                          <td className="p-4">
                            {exec.records_failed > 0 ? (
                              <span className="text-rose-400">{exec.records_failed}</span>
                            ) : (
                              <span className="text-zinc-500">0</span>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
