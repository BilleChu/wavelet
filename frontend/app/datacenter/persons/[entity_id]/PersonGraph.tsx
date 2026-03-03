'use client'

import { useState, useEffect, useCallback } from 'react'
import { Button, Badge } from '@/components/ui'
import {
  Network,
  RefreshCw,
  Building2,
  TrendingUp,
  Users,
  ExternalLink,
  ZoomIn,
  ZoomOut,
  Briefcase,
} from 'lucide-react'

interface GraphNode {
  id: string
  name: string
  type: string
  category: string
  properties: Record<string, any>
  code?: string
  industry?: string
}

interface GraphEdge {
  id: string
  source: string
  target: string
  type: string
  weight: number
  properties: Record<string, any>
}

interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  center: string
  stats: {
    node_count: number
    edge_count: number
  }
}

const nodeTypeColors: Record<string, string> = {
  person: '#8b5cf6',
  company: '#3b82f6',
  industry: '#10b981',
  stock: '#f59e0b',
  concept: '#ec4899',
  fund: '#06b6d4',
}

const nodeTypeIcons: Record<string, any> = {
  person: Users,
  company: Building2,
  industry: Briefcase,
  stock: TrendingUp,
  concept: Network,
  fund: TrendingUp,
}

const relationTypeLabels: Record<string, string> = {
  works_for: '就职于',
  focuses_on: '关注',
  invested_in: '投资',
  manages: '管理',
  belongs_to: '属于',
}

interface PersonGraphProps {
  entityId: string
}

export default function PersonGraph({ entityId }: PersonGraphProps) {
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [depth, setDepth] = useState(1)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)

  const fetchGraph = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/persons/${entityId}/graph?depth=${depth}`)
      if (response.ok) {
        const data: GraphData = await response.json()
        setGraphData(data)
      }
    } catch (err) {
      console.error('Failed to fetch graph:', err)
    } finally {
      setLoading(false)
    }
  }, [entityId, depth])

  useEffect(() => {
    fetchGraph()
  }, [fetchGraph])

  const getRelatedEdges = (nodeId: string) => {
    if (!graphData) return []
    return graphData.edges.filter(
      (e) => e.source === nodeId || e.target === nodeId
    )
  }

  const getRelatedNodes = (nodeId: string) => {
    if (!graphData) return []
    const edges = getRelatedEdges(nodeId)
    const nodeIds = new Set<string>()
    edges.forEach((e) => {
      if (e.source !== nodeId) nodeIds.add(e.source)
      if (e.target !== nodeId) nodeIds.add(e.target)
    })
    return graphData.nodes.filter((n) => nodeIds.has(n.id))
  }

  if (loading) {
    return (
      <div className="glass-panel p-6">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 animate-spin text-[var(--accent-gold)]" />
        </div>
      </div>
    )
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="glass-panel p-6">
        <div className="flex flex-col items-center justify-center h-64 text-zinc-500">
          <Network className="w-16 h-16 mb-4 opacity-50" />
          <p>暂无知识图谱数据</p>
          <p className="text-xs mt-2">该人物尚未与其他实体建立关联</p>
        </div>
      </div>
    )
  }

  const centerNode = graphData.nodes.find((n) => n.id === graphData.center)

  return (
    <div className="glass-panel overflow-hidden">
      <div className="p-4 border-b border-white/[0.05] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-medium text-white flex items-center gap-2">
            <Network className="w-4 h-4 text-zinc-500" />
            知识图谱关联
          </h3>
          <Badge variant="secondary" className="bg-zinc-500/20 text-zinc-400">
            {graphData.stats.node_count} 节点 / {graphData.stats.edge_count} 关系
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 text-xs text-zinc-500">
            <span>深度:</span>
            {[1, 2].map((d) => (
              <button
                key={d}
                onClick={() => setDepth(d)}
                className={`w-6 h-6 rounded flex items-center justify-center ${
                  depth === d
                    ? 'bg-violet-500/20 text-violet-400'
                    : 'bg-white/[0.02] text-zinc-500 hover:bg-white/[0.05]'
                }`}
              >
                {d}
              </button>
            ))}
          </div>
          <Button variant="outline" size="sm" onClick={fetchGraph}>
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 p-4">
        <div className="col-span-2 bg-white/[0.02] rounded-xl p-4 min-h-[400px] relative">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="relative w-full h-full">
              {centerNode && (
                <div
                  className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10"
                  onMouseEnter={() => setHoveredNode(centerNode.id)}
                  onMouseLeave={() => setHoveredNode(null)}
                >
                  <div
                    className="w-20 h-20 rounded-full flex flex-col items-center justify-center cursor-pointer transition-all shadow-lg"
                    style={{
                      backgroundColor: `${nodeTypeColors[centerNode.type]}20`,
                      border: `2px solid ${nodeTypeColors[centerNode.type]}`,
                    }}
                  >
                    <span className="text-white font-bold text-lg">
                      {centerNode.name.charAt(0)}
                    </span>
                    <span className="text-zinc-400 text-xs mt-0.5 truncate max-w-full px-1">
                      {centerNode.name}
                    </span>
                  </div>
                </div>
              )}

              {graphData.nodes
                .filter((n) => n.id !== graphData.center)
                .map((node, index) => {
                  const angle = (index * 2 * Math.PI) / (graphData.nodes.length - 1)
                  const radius = 140
                  const x = Math.cos(angle) * radius
                  const y = Math.sin(angle) * radius

                  return (
                    <div
                      key={node.id}
                      className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
                      style={{
                        transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`,
                      }}
                      onMouseEnter={() => setHoveredNode(node.id)}
                      onMouseLeave={() => setHoveredNode(null)}
                      onClick={() => setSelectedNode(node)}
                    >
                      <div
                        className={`w-14 h-14 rounded-full flex flex-col items-center justify-center cursor-pointer transition-all ${
                          hoveredNode === node.id ? 'scale-110' : ''
                        }`}
                        style={{
                          backgroundColor: `${nodeTypeColors[node.type] || '#71717a'}20`,
                          border: `2px solid ${nodeTypeColors[node.type] || '#71717a'}`,
                        }}
                      >
                        <span className="text-white font-medium text-sm">
                          {node.name.charAt(0)}
                        </span>
                      </div>
                      <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 whitespace-nowrap">
                        <span className="text-zinc-400 text-xs">{node.name}</span>
                      </div>
                    </div>
                  )
                })}
            </div>
          </div>

          <div className="absolute bottom-4 left-4 flex items-center gap-3">
            {Object.entries(nodeTypeColors).slice(0, 4).map(([type, color]) => (
              <div key={type} className="flex items-center gap-1">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <span className="text-zinc-500 text-xs capitalize">{type}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-white/[0.02] rounded-xl p-4">
            <h4 className="text-sm font-medium text-white mb-3">关联实体</h4>
            <div className="space-y-2 max-h-[200px] overflow-y-auto">
              {graphData.nodes
                .filter((n) => n.id !== graphData.center)
                .map((node) => {
                  const Icon = nodeTypeIcons[node.type] || Network
                  return (
                    <div
                      key={node.id}
                      className={`p-2 rounded-lg cursor-pointer transition-all ${
                        selectedNode?.id === node.id
                          ? 'bg-violet-500/20 border border-violet-500/40'
                          : 'bg-white/[0.02] hover:bg-white/[0.05]'
                      }`}
                      onClick={() => setSelectedNode(node)}
                    >
                      <div className="flex items-center gap-2">
                        <Icon
                          className="w-4 h-4"
                          style={{ color: nodeTypeColors[node.type] }}
                        />
                        <div>
                          <p className="text-white text-sm font-medium">{node.name}</p>
                          <p className="text-zinc-500 text-xs capitalize">{node.type}</p>
                        </div>
                      </div>
                    </div>
                  )
                })}
            </div>
          </div>

          <div className="bg-white/[0.02] rounded-xl p-4">
            <h4 className="text-sm font-medium text-white mb-3">关系类型</h4>
            <div className="space-y-2">
              {Array.from(new Set(graphData.edges.map((e) => e.type))).map((type) => {
                const count = graphData.edges.filter((e) => e.type === type).length
                return (
                  <div
                    key={type}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="text-zinc-400">
                      {relationTypeLabels[type] || type}
                    </span>
                    <Badge variant="secondary" className="bg-zinc-500/20 text-zinc-400">
                      {count}
                    </Badge>
                  </div>
                )
              })}
            </div>
          </div>

          {selectedNode && (
            <div className="bg-white/[0.02] rounded-xl p-4">
              <h4 className="text-sm font-medium text-white mb-3">节点详情</h4>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500">名称</span>
                  <span className="text-white">{selectedNode.name}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-500">类型</span>
                  <span className="text-white capitalize">{selectedNode.type}</span>
                </div>
                {selectedNode.code && (
                  <div className="flex justify-between text-sm">
                    <span className="text-zinc-500">代码</span>
                    <span className="text-white">{selectedNode.code}</span>
                  </div>
                )}
                {selectedNode.industry && (
                  <div className="flex justify-between text-sm">
                    <span className="text-zinc-500">行业</span>
                    <span className="text-white">{selectedNode.industry}</span>
                  </div>
                )}
                <div className="pt-2 border-t border-white/[0.05]">
                  <p className="text-zinc-500 text-xs mb-2">关联关系</p>
                  {getRelatedEdges(selectedNode.id).map((edge) => {
                    const isSource = edge.source === selectedNode.id
                    const otherNodeId = isSource ? edge.target : edge.source
                    const otherNode = graphData.nodes.find((n) => n.id === otherNodeId)
                    return (
                      <div key={edge.id} className="text-xs text-zinc-400 py-1">
                        {isSource ? '→' : '←'} {relationTypeLabels[edge.type] || edge.type} {otherNode?.name}
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
