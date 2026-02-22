'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
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
  Play,
  Pause,
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
  ChevronRight,
  Layers,
  ArrowRight,
  Target,
  Timer,
  FileText,
  BarChart3,
  X,
} from 'lucide-react'

interface DAGNode {
  id: string
  name: string
  type: string
  taskType: string
  params: Record<string, unknown>
  priority: number
  status: string
  dependencies: string[]
  startedAt: string | null
  completedAt: string | null
  retryCount: number
  error: string | null
  progress: number
  position: { x: number; y: number }
}

interface DAGEdge {
  id: string
  source: string
  target: string
  label: string
  condition: string | null
}

interface DAG {
  dagId: string
  name: string
  description: string
  status: string
  nodes: DAGNode[]
  edges: DAGEdge[]
  metadata: {
    schedule?: string
    timezone?: string
    totalNodes?: number
    totalEdges?: number
  }
}

interface DAGSummary {
  id: string
  name: string
  description: string
  totalTasks: number
  schedule: string
  timezone: string
  status: string
}

const statusConfig: Record<string, { color: string; bgColor: string; icon: React.ReactNode; label: string }> = {
  pending: { color: 'text-zinc-400', bgColor: 'bg-zinc-500/20', icon: <Clock className="w-4 h-4" />, label: '等待中' },
  queued: { color: 'text-blue-400', bgColor: 'bg-blue-500/20', icon: <Clock className="w-4 h-4" />, label: '队列中' },
  running: { color: 'text-amber-400', bgColor: 'bg-amber-500/20', icon: <Loader2 className="w-4 h-4 animate-spin" />, label: '运行中' },
  completed: { color: 'text-emerald-400', bgColor: 'bg-emerald-500/20', icon: <CheckCircle className="w-4 h-4" />, label: '已完成' },
  failed: { color: 'text-rose-400', bgColor: 'bg-rose-500/20', icon: <XCircle className="w-4 h-4" />, label: '失败' },
  cancelled: { color: 'text-zinc-500', bgColor: 'bg-zinc-500/20', icon: <X className="w-4 h-4" />, label: '已取消' },
  skipped: { color: 'text-zinc-500', bgColor: 'bg-zinc-500/20', icon: <ChevronRight className="w-4 h-4" />, label: '已跳过' },
}

const priorityConfig: Record<number, { color: string; label: string }> = {
  0: { color: 'text-rose-400', label: '紧急' },
  1: { color: 'text-amber-400', label: '高' },
  2: { color: 'text-blue-400', label: '普通' },
  3: { color: 'text-zinc-400', label: '低' },
  4: { color: 'text-zinc-500', label: '后台' },
}

const nodeTypeColors: Record<string, string> = {
  task: '#f59e0b',
  condition: '#8b5cf6',
  parallel: '#06b6d4',
  merge: '#10b981',
}

function TaskNodeComponent({ data }: { data: { label: string; taskType: string; status: string; nodeId: string; progress?: number; error?: string | null } }) {
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
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-zinc-500">{data.taskType}</span>
        <Badge variant="secondary" className={`${config.bgColor} ${config.color} text-xs`}>
          {config.label}
        </Badge>
      </div>
      {data.progress !== undefined && data.progress > 0 && data.progress < 1 && (
        <Progress value={data.progress * 100} className="h-1 mt-2" />
      )}
      {data.error && (
        <span className="text-xs text-rose-400 truncate block mt-1">{data.error.substring(0, 20)}...</span>
      )}
    </div>
  )
}

const nodeTypes = {
  taskNode: TaskNodeComponent,
}

export default function PipelinePage() {
  const router = useRouter()
  const [dags, setDags] = useState<DAGSummary[]>([])
  const [selectedDag, setSelectedDag] = useState<DAG | null>(null)
  const [nodes, setNodes, onNodesChange] = useState<Node[]>([])
  const [edges, setEdges, onEdgesChange] = useState<Edge[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [notification, setNotification] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)
  const [detailModal, setDetailModal] = useState(false)
  const [selectedNode, setSelectedNode] = useState<DAGNode | null>(null)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const showNotification = useCallback((type: 'success' | 'error' | 'info', message: string) => {
    setNotification({ type, message })
    setTimeout(() => setNotification(null), 5000)
  }, [])

  const fetchDAGs = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/pipeline/dags`)
      const data = await response.json()
      if (data.success) {
        setDags(data.dags)
      }
    } catch (error) {
      console.error('Failed to fetch DAGs:', error)
      showNotification('error', '获取DAG列表失败')
    } finally {
      setLoading(false)
    }
  }, [API_BASE_URL, showNotification])

  useEffect(() => {
    fetchDAGs()
    const interval = setInterval(fetchDAGs, 30000)
    return () => clearInterval(interval)
  }, [fetchDAGs])

  const fetchDAGDetail = async (dagId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/pipeline/dags/${dagId}/canvas`)
      const data = await response.json()
      if (data.success) {
        const dag: DAG = {
          dagId: data.metadata?.dagId || dagId,
          name: data.metadata?.name || dagId,
          description: data.metadata?.description || '',
          status: data.metadata?.status || 'pending',
          nodes: data.nodes.map((n: { id: string; data: Record<string, unknown>; position?: { x: number; y: number } }) => ({
            id: n.id,
            name: n.data?.label as string || n.id,
            type: 'taskNode',
            taskType: n.data?.taskType as string || 'unknown',
            params: {},
            priority: 2,
            status: n.data?.status as string || 'pending',
            dependencies: [],
            startedAt: null,
            completedAt: null,
            retryCount: 0,
            error: n.data?.error as string || null,
            progress: n.data?.progress as number || 0,
            position: n.position || { x: 0, y: 0 },
          })),
          edges: data.edges,
          metadata: data.metadata || {},
        }
        setSelectedDag(dag)
        
        const flowNodes: Node[] = data.nodes.map((n: { id: string; position: { x: number; y: number }; data: Record<string, unknown> }) => ({
          id: n.id,
          type: 'taskNode',
          position: n.position,
          data: n.data,
        }))
        
        const flowEdges: Edge[] = data.edges.map((e: { id: string; source: string; target: string; label?: string }) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label,
          animated: true,
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: '#f59e0b' },
        }))
        
        setNodes(flowNodes)
        setEdges(flowEdges)
      }
    } catch (error) {
      console.error('Failed to fetch DAG detail:', error)
      showNotification('error', '获取DAG详情失败')
    }
  }

  const executeDAG = async (dagId: string) => {
    setActionLoading(dagId)
    try {
      const response = await fetch(`${API_BASE_URL}/api/pipeline/dags/${dagId}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      const data = await response.json()
      if (data.success) {
        showNotification('success', `DAG ${dagId} 执行已启动`)
        fetchDAGs()
      } else {
        showNotification('error', data.error || '执行失败')
      }
    } catch {
      showNotification('error', '执行DAG失败')
    } finally {
      setActionLoading(null)
    }
  }

  const loadDAGConfig = async () => {
    setActionLoading('load-config')
    try {
      const response = await fetch(`${API_BASE_URL}/api/pipeline/dags/load-config`, {
        method: 'POST',
      })
      const data = await response.json()
      if (data.success) {
        showNotification('success', `已加载 ${data.total} 个DAG配置`)
        fetchDAGs()
      } else {
        showNotification('error', '加载配置失败')
      }
    } catch {
      showNotification('error', '加载DAG配置失败')
    } finally {
      setActionLoading(null)
    }
  }

  const onNodeClick = (_: React.MouseEvent, node: Node) => {
    const dagNode = selectedDag?.nodes.find((n) => n.id === node.id)
    if (dagNode) {
      setSelectedNode(dagNode)
      setDetailModal(true)
    }
  }

  const getStatusIcon = (status: string) => {
    const config = statusConfig[status] || statusConfig.pending
    return <div className={`w-5 h-5 rounded-full flex items-center justify-center ${config.bgColor}`}>{config.icon}</div>
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
          <h2 className="text-xl font-semibold text-white">任务链路管理</h2>
          <p className="text-sm text-zinc-500 mt-1">DAG任务编排与执行管理</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={fetchDAGs}
            disabled={loading}
            className="gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button
            variant="default"
            size="sm"
            onClick={loadDAGConfig}
            disabled={actionLoading === 'load-config'}
            className="gap-2 bg-[var(--accent-gold)] text-black hover:bg-[var(--accent-gold)]/90"
          >
            {actionLoading === 'load-config' ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Database className="w-4 h-4" />
            )}
            加载配置
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-white/[0.05] p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-white">DAG列表</h3>
              <Badge variant="secondary" className="bg-zinc-500/20 text-zinc-400">
                {dags.length} 个
              </Badge>
            </div>

            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {dags.map((dag) => (
                <div
                  key={dag.id}
                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                    selectedDag?.dagId === dag.id
                      ? 'bg-amber-500/10 border-amber-500/30'
                      : 'bg-[var(--bg-tertiary)] border-white/[0.05] hover:border-white/[0.1]'
                  }`}
                  onClick={() => fetchDAGDetail(dag.id)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(dag.status)}
                      <span className="text-sm font-medium text-white truncate">{dag.name}</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        executeDAG(dag.id)
                      }}
                      disabled={actionLoading === dag.id}
                      className="h-7 px-2"
                    >
                      {actionLoading === dag.id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Play className="w-3.5 h-3.5" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-zinc-500 mb-2 line-clamp-1">{dag.description}</p>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="bg-zinc-500/20 text-zinc-400 text-xs">
                      {dag.totalTasks} 任务
                    </Badge>
                    {dag.schedule && (
                      <Badge variant="secondary" className="bg-blue-500/20 text-blue-400 text-xs gap-1">
                        <Calendar className="w-3 h-3" />
                        {dag.schedule}
                      </Badge>
                    )}
                  </div>
                </div>
              ))}

              {dags.length === 0 && !loading && (
                <div className="text-center py-8 text-zinc-500">
                  <Layers className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">暂无DAG配置</p>
                  <p className="text-xs mt-1">点击"加载配置"按钮加载DAG</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-4">
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-white/[0.05] overflow-hidden">
            <div className="p-4 border-b border-white/[0.05]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-amber-400" />
                  <h3 className="text-sm font-medium text-white">
                    {selectedDag ? selectedDag.name : 'DAG流程图'}
                  </h3>
                </div>
                {selectedDag && (
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => executeDAG(selectedDag.dagId)}
                    disabled={actionLoading === selectedDag.dagId}
                    className="gap-2 bg-[var(--accent-gold)] text-black hover:bg-[var(--accent-gold)]/90"
                  >
                    {actionLoading === selectedDag.dagId ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                    执行
                  </Button>
                )}
              </div>
            </div>

            <div className="h-[500px] relative">
              {selectedDag ? (
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onNodeClick={onNodeClick}
                  nodeTypes={nodeTypes}
                  fitView
                  attributionPosition="bottom-left"
                >
                  <Background className="!bg-[var(--bg-tertiary)]" />
                  <Controls className="!bg-[var(--bg-secondary)] !border-white/[0.05] !rounded-lg" />
                  <MiniMap className="!bg-[var(--bg-secondary)] !border-white/[0.05] !rounded-lg" />
                </ReactFlow>
              ) : (
                <div className="h-full flex items-center justify-center text-zinc-500">
                  <div className="text-center">
                    <Layers className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>选择一个DAG查看流程图</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {selectedDag && (
            <div className="bg-[var(--bg-secondary)] rounded-xl border border-white/[0.05] p-4">
              <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-amber-400" />
                任务状态统计
              </h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(statusConfig).map(([status, config]) => {
                  const count = selectedDag.nodes.filter((n) => n.status === status).length
                  return (
                    <div
                      key={status}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${config.bgColor}`}
                    >
                      {config.icon}
                      <span className={`text-sm ${config.color}`}>
                        {config.label}: {count}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {detailModal && selectedNode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-white/[0.1] w-full max-w-lg mx-4 shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-white/[0.05]">
              <h3 className="text-lg font-semibold text-white">{selectedNode.name}</h3>
              <Button variant="ghost" size="sm" onClick={() => setDetailModal(false)}>
                <X className="w-4 h-4" />
              </Button>
            </div>
            <div className="p-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-zinc-500 mb-1">任务ID</p>
                  <p className="text-sm text-white font-mono">{selectedNode.id}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-500 mb-1">任务类型</p>
                  <p className="text-sm text-white">{selectedNode.taskType}</p>
                </div>
                <div>
                  <p className="text-xs text-zinc-500 mb-1">状态</p>
                  <Badge variant="secondary" className={`${statusConfig[selectedNode.status]?.bgColor} ${statusConfig[selectedNode.status]?.color}`}>
                    {statusConfig[selectedNode.status]?.label || selectedNode.status}
                  </Badge>
                </div>
                <div>
                  <p className="text-xs text-zinc-500 mb-1">优先级</p>
                  <span className={`text-sm ${priorityConfig[selectedNode.priority]?.color || 'text-zinc-400'}`}>
                    {priorityConfig[selectedNode.priority]?.label || '普通'}
                  </span>
                </div>
              </div>

              {selectedNode.dependencies.length > 0 && (
                <div>
                  <p className="text-xs text-zinc-500 mb-2">依赖任务</p>
                  <div className="flex flex-wrap gap-1">
                    {selectedNode.dependencies.map((dep) => (
                      <Badge key={dep} variant="outline" className="text-xs">
                        {dep}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {selectedNode.error && (
                <div>
                  <p className="text-xs text-rose-400 mb-1">错误信息</p>
                  <p className="text-sm text-rose-400 bg-rose-500/10 rounded-lg p-2">{selectedNode.error}</p>
                </div>
              )}
            </div>
            <div className="p-4 border-t border-white/[0.05] flex justify-end">
              <Button variant="outline" onClick={() => setDetailModal(false)}>
                关闭
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
