'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { 
  graphService, 
  entityService,
  type GraphNode, 
  type GraphData,
  type GraphEdge,
  type Entity,
  type EntityNews,
  type EntitySource,
  type EntityType,
  type RelationType,
  type Industry,
  type DataQualityReport,
} from '@/services/graphService'
import apiClient from '@/services/apiConfig'
import { 
  Search, ZoomIn, ZoomOut, RotateCcw, Loader2, Maximize2, ArrowLeft, 
  Network, Info, BarChart3, Plus, Trash2, Edit2, 
  ChevronRight, Newspaper, Database, Layers,
  X, Filter, Eye, EyeOff, Link2, Save, AlertTriangle,
  AlertCircle, Shield, Users, GitBranch, Move, Expand, Compass,
} from 'lucide-react'
import Link from 'next/link'
import { Button, Badge } from '@/components/ui'

const nodeColors: Record<string, string> = {
  company: '#f59e0b',
  industry: '#10b981',
  concept: '#8b5cf6',
  person: '#06b6d4',
  stock: '#f43f5e',
  fund: '#64748b',
  event: '#ec4899',
  sector: '#14b8a6',
  index: '#3b82f6',
  investor: '#84cc16',
}

const nodeLabels: Record<string, string> = {
  company: '公司',
  industry: '行业',
  concept: '概念',
  person: '人物',
  stock: '股票',
  fund: '基金',
  event: '事件',
  sector: '板块',
  index: '指数',
  investor: '投资者',
}

const relationLabels: Record<string, string> = {
  belongs_to: '属于',
  has_concept: '具有概念',
  competes_with: '竞争',
  supplies_to: '供应',
  invests_in: '投资',
  affects: '影响',
  works_for: '任职',
  manages: '管理',
  owns: '拥有',
  parent_of: '母公司',
  subsidiary_of: '子公司',
  ceo_of: 'CEO',
  director_of: '董事',
  founded: '创立',
  acquired: '收购',
  merged_with: '合并',
  operates_in: '运营于',
  regulated_by: '受监管',
  related_to: '相关',
  listed_on: '上市于',
}

interface SimNode extends GraphNode {
  x: number
  y: number
  vx: number
  vy: number
  fx: number | null
  fy: number | null
  depth: number
  connections: number
}

interface SimEdge extends GraphEdge {
  sourceNode: SimNode
  targetNode: SimNode
}

export default function KnowledgeGraphPage() {
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchKeyword, setSearchKeyword] = useState('')
  const [selectedNode, setSelectedNode] = useState<SimNode | null>(null)
  const [hoveredNode, setHoveredNode] = useState<SimNode | null>(null)
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null)
  const [entityNews, setEntityNews] = useState<EntityNews[]>([])
  const [entitySources, setEntitySources] = useState<EntitySource[]>([])
  const [zoom, setZoom] = useState(1)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [draggingNode, setDraggingNode] = useState<SimNode | null>(null)
  const [depth, setDepth] = useState(2)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showRelationModal, setShowRelationModal] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [showQualityPanel, setShowQualityPanel] = useState(false)
  const [activeTab, setActiveTab] = useState<'info' | 'relations' | 'news' | 'sources'>('info')
  const [stats, setStats] = useState<{
    total_entities: number
    total_relations: number
    entity_types: Record<string, number>
    relation_types: Record<string, number>
  } | null>(null)
  const [qualityReport, setQualityReport] = useState<DataQualityReport | null>(null)
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set())
  const [entityTypes, setEntityTypes] = useState<EntityType[]>([])
  const [relationTypes, setRelationTypes] = useState<RelationType[]>([])
  const [industries, setIndustries] = useState<Industry[]>([])
  const [formData, setFormData] = useState({
    entity_type: 'stock',
    name: '',
    code: '',
    description: '',
    industry: '',
    aliases: '',
  })
  const [relationFormData, setRelationFormData] = useState({
    target_entity_id: '',
    relation_type: 'belongs_to',
    weight: 1.0,
    evidence: '',
  })
  const [targetSearchKeyword, setTargetSearchKeyword] = useState('')
  const [targetSearchResults, setTargetSearchResults] = useState<Entity[]>([])
  const [saving, setSaving] = useState(false)
  const [showLabels, setShowLabels] = useState(true)
  const [centerNodeId, setCenterNodeId] = useState<string | null>(null)
  
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const nodesRef = useRef<SimNode[]>([])
  const edgesRef = useRef<SimEdge[]>([])
  const animationRef = useRef<number>(0)
  const dprRef = useRef<number>(1)
  const canvasSizeRef = useRef({ width: 800, height: 600 })
  const isInitializedRef = useRef(false)

  useEffect(() => {
    loadDefaultGraph()
    loadStats()
    loadEntityTypes()
    loadRelationTypes()
    loadIndustries()
  }, [])

  const loadEntityTypes = async () => {
    try {
      const data = await entityService.getEntityTypes()
      setEntityTypes(data.types)
    } catch (error) {
      console.error('Failed to load entity types:', error)
    }
  }

  const loadRelationTypes = async () => {
    try {
      const data = await entityService.getRelationTypes()
      setRelationTypes(data.types)
    } catch (error) {
      console.error('Failed to load relation types:', error)
    }
  }

  const loadIndustries = async () => {
    try {
      const data = await entityService.getIndustries()
      setIndustries(data.industries)
    } catch (error) {
      console.error('Failed to load industries:', error)
    }
  }

  const loadStats = async () => {
    try {
      const data = await graphService.getStats()
      setStats(data)
    } catch (error) {
      console.error('Failed to load stats:', error)
    }
  }

  const loadQualityReport = async () => {
    try {
      const data = await graphService.getQuality()
      setQualityReport(data)
    } catch (error) {
      console.error('Failed to load quality report:', error)
    }
  }

  const calculateNodeDepths = useCallback((nodes: GraphNode[], edges: GraphEdge[], centerId: string | null) => {
    const depths = new Map<string, number>()
    const connectionCounts = new Map<string, number>()
    
    nodes.forEach(n => {
      depths.set(n.id, 999)
      connectionCounts.set(n.id, 0)
    })
    
    edges.forEach(e => {
      connectionCounts.set(e.source, (connectionCounts.get(e.source) || 0) + 1)
      connectionCounts.set(e.target, (connectionCounts.get(e.target) || 0) + 1)
    })

    if (centerId && depths.has(centerId)) {
      depths.set(centerId, 0)
    } else if (nodes.length > 0) {
      const maxConnections = Math.max(...nodes.map(n => connectionCounts.get(n.id) || 0))
      const centerNode = nodes.find(n => connectionCounts.get(n.id) === maxConnections)
      if (centerNode) depths.set(centerNode.id, 0)
    }

    for (let iter = 0; iter < 20; iter++) {
      let changed = false
      edges.forEach(e => {
        const sourceDepth = depths.get(e.source)
        const targetDepth = depths.get(e.target)
        if (sourceDepth !== undefined && targetDepth !== undefined) {
          if (sourceDepth < 999 && targetDepth > sourceDepth + 1) {
            depths.set(e.target, sourceDepth + 1)
            changed = true
          }
          if (targetDepth < 999 && sourceDepth > targetDepth + 1) {
            depths.set(e.source, targetDepth + 1)
            changed = true
          }
        }
      })
      if (!changed) break
    }

    nodes.forEach(n => {
      if (depths.get(n.id) === 999) {
        depths.set(n.id, 0)
      }
    })

    return { depths, connectionCounts }
  }, [])

  const initializeSimulation = useCallback((data: GraphData, centerId: string | null = null) => {
    const { width, height } = canvasSizeRef.current
    const centerX = width / 2
    const centerY = height / 2

    const { depths, connectionCounts } = calculateNodeDepths(data.nodes, data.edges, centerId)

    const nodesByDepth = new Map<number, GraphNode[]>()
    data.nodes.forEach(node => {
      const d = depths.get(node.id) ?? 0
      if (!nodesByDepth.has(d)) nodesByDepth.set(d, [])
      nodesByDepth.get(d)!.push(node)
    })

    const simNodes: SimNode[] = data.nodes.map((node) => {
      const nodeDepth = depths.get(node.id) ?? 0
      const connections = connectionCounts.get(node.id) ?? 0
      const nodesAtDepth = nodesByDepth.get(nodeDepth) || [node]
      const indexAtDepth = nodesAtDepth.indexOf(node)
      const totalAtDepth = nodesAtDepth.length
      
      const baseRadius = 100 + nodeDepth * 160
      const angleSpread = totalAtDepth <= 1 ? 0 : Math.min(2 * Math.PI, (2 * Math.PI * totalAtDepth) / Math.max(6, totalAtDepth))
      const angleOffset = nodeDepth === 0 ? 0 : -angleSpread / 2
      const angle = totalAtDepth <= 1 ? 0 : angleOffset + (angleSpread * indexAtDepth) / (totalAtDepth - 1)
      
      const x = centerX + baseRadius * Math.cos(angle)
      const y = centerY + baseRadius * Math.sin(angle)
      
      return {
        ...node,
        x: Number.isFinite(x) ? x : centerX,
        y: Number.isFinite(y) ? y : centerY,
        vx: 0,
        vy: 0,
        fx: null,
        fy: null,
        depth: nodeDepth,
        connections,
      }
    })

    const nodeMap = new Map(simNodes.map(n => [n.id, n]))
    const simEdges: SimEdge[] = data.edges.map(edge => ({
      ...edge,
      sourceNode: nodeMap.get(edge.source)!,
      targetNode: nodeMap.get(edge.target)!,
    })).filter(e => e.sourceNode && e.targetNode)

    nodesRef.current = simNodes
    edgesRef.current = simEdges
    isInitializedRef.current = true
  }, [calculateNodeDepths])

  const applyForces = useCallback(() => {
    const nodes = nodesRef.current
    const edges = edgesRef.current
    if (nodes.length === 0) return false

    const { width, height } = canvasSizeRef.current
    const centerX = width / 2
    const centerY = height / 2

    let totalMovement = 0
    const alpha = 0.12

    nodes.forEach(node => {
      if (!Number.isFinite(node.x)) node.x = centerX
      if (!Number.isFinite(node.y)) node.y = centerY
      
      if (node.fx !== null) {
        node.x = node.fx
        node.vx = 0
      }
      if (node.fy !== null) {
        node.y = node.fy
        node.vy = 0
      }
    })

    for (let i = 0; i < nodes.length; i++) {
      const nodeA = nodes[i]
      for (let j = i + 1; j < nodes.length; j++) {
        const nodeB = nodes[j]
        
        const dx = nodeB.x - nodeA.x
        const dy = nodeB.y - nodeA.y
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
        
        const minDist = nodeA.depth === nodeB.depth ? 70 : 90
        
        if (dist < minDist) {
          const force = ((minDist - dist) / dist) * alpha * 1.2
          const fx = dx * force
          const fy = dy * force
          
          if (nodeA.fx === null) {
            nodeA.vx -= fx
            nodeA.vy -= fy
          }
          if (nodeB.fx === null) {
            nodeB.vx += fx
            nodeB.vy += fy
          }
        }
      }
    }

    edges.forEach(edge => {
      const source = edge.sourceNode
      const target = edge.targetNode
      
      if (!source || !target) return
      
      const dx = target.x - source.x
      const dy = target.y - source.y
      const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
      
      const idealDist = 120 + Math.abs(target.depth - source.depth) * 60
      const force = ((dist - idealDist) / dist) * alpha * 0.03
      
      if (source.fx === null && Number.isFinite(force)) {
        source.vx += dx * force
        source.vy += dy * force
      }
      if (target.fx === null && Number.isFinite(force)) {
        target.vx -= dx * force
        target.vy -= dy * force
      }
    })

    nodes.forEach(node => {
      if (node.fx !== null && node.fy !== null) return
      
      const dx = node.x - centerX
      const dy = node.y - centerY
      const dist = Math.sqrt(dx * dx + dy * dy) || 1
      
      const targetRadius = 100 + node.depth * 160
      const radialForce = (dist - targetRadius) * 0.008
      
      if (dist > targetRadius + 40) {
        node.vx -= (dx / dist) * radialForce
        node.vy -= (dy / dist) * radialForce
      } else if (dist < targetRadius - 40) {
        node.vx += (dx / dist) * Math.abs(radialForce) * 0.3
        node.vy += (dy / dist) * Math.abs(radialForce) * 0.3
      }
    })

    nodes.forEach(node => {
      if (node.fx !== null) {
        node.x = node.fx
        node.vx = 0
      } else {
        node.vx *= 0.82
        node.x += node.vx
      }
      
      if (node.fy !== null) {
        node.y = node.fy
        node.vy = 0
      } else {
        node.vy *= 0.82
        node.y += node.vy
      }

      const padding = 50
      node.x = Math.max(padding, Math.min(width - padding, node.x))
      node.y = Math.max(padding, Math.min(height - padding, node.y))
      
      if (!Number.isFinite(node.x)) node.x = width / 2
      if (!Number.isFinite(node.y)) node.y = height / 2
      
      totalMovement += Math.abs(node.vx) + Math.abs(node.vy)
    })

    return totalMovement < 0.05
  }, [])

  const drawGraph = useCallback(() => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d', { alpha: false })
    if (!canvas || !ctx) return

    const dpr = dprRef.current
    const { width, height } = canvasSizeRef.current
    const nodes = nodesRef.current
    const edges = edgesRef.current

    if (!isInitializedRef.current || nodes.length === 0) return

    ctx.save()
    ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.scale(dpr, dpr)
    
    ctx.fillStyle = '#0a0a0f'
    ctx.fillRect(0, 0, width, height)

    ctx.translate(offset.x, offset.y)
    ctx.scale(zoom, zoom)

    const highlightedNodes = new Set<string>()
    const connectedEdges = new Set<string>()
    if (hoveredNode || selectedNode) {
      const focusNode = hoveredNode || selectedNode
      highlightedNodes.add(focusNode!.id)
      edges.forEach(edge => {
        if (edge.source === focusNode!.id) {
          highlightedNodes.add(edge.target)
          connectedEdges.add(`${edge.source}-${edge.target}`)
        }
        if (edge.target === focusNode!.id) {
          highlightedNodes.add(edge.source)
          connectedEdges.add(`${edge.source}-${edge.target}`)
        }
      })
    }

    ctx.lineWidth = 1 / zoom
    edges.forEach(edge => {
      const sourceNode = edge.sourceNode
      const targetNode = edge.targetNode
      
      if (!sourceNode || !targetNode) return
      if (hiddenTypes.has(sourceNode.type) || hiddenTypes.has(targetNode.type)) return
      if (!Number.isFinite(sourceNode.x) || !Number.isFinite(sourceNode.y)) return
      if (!Number.isFinite(targetNode.x) || !Number.isFinite(targetNode.y)) return

      const isHighlighted = connectedEdges.has(`${edge.source}-${edge.target}`)
      const isSelected = selectedNode && (edge.source === selectedNode.id || edge.target === selectedNode.id)
      const isHovered = hoveredNode && (edge.source === hoveredNode.id || edge.target === hoveredNode.id)
      
      ctx.beginPath()
      ctx.moveTo(sourceNode.x, sourceNode.y)
      
      const midX = (sourceNode.x + targetNode.x) / 2
      const midY = (sourceNode.y + targetNode.y) / 2
      const dx = targetNode.x - sourceNode.x
      const dy = targetNode.y - sourceNode.y
      const perpX = -dy * 0.06
      const perpY = dx * 0.06
      const ctrlX = midX + perpX
      const ctrlY = midY + perpY
      
      ctx.quadraticCurveTo(ctrlX, ctrlY, targetNode.x, targetNode.y)
      
      if (isSelected || isHovered) {
        ctx.strokeStyle = 'rgba(139, 92, 246, 0.7)'
        ctx.lineWidth = 2.5 / zoom
      } else if (isHighlighted) {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)'
        ctx.lineWidth = 1.5 / zoom
      } else {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)'
        ctx.lineWidth = 1 / zoom
      }
      ctx.stroke()

      if (showLabels && (isSelected || isHovered)) {
        const labelX = midX + perpX * 0.5
        const labelY = midY + perpY * 0.5
        const relLabel = relationLabels[edge.type] || edge.type
        
        ctx.save()
        ctx.font = `500 ${11 / zoom}px Inter, system-ui, sans-serif`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        
        const textWidth = ctx.measureText(relLabel).width
        ctx.fillStyle = 'rgba(20, 20, 25, 0.9)'
        ctx.beginPath()
        ctx.roundRect(labelX - textWidth / 2 - 6, labelY - 9, textWidth + 12, 18, 4)
        ctx.fill()
        
        ctx.fillStyle = 'rgba(255, 255, 255, 0.95)'
        ctx.fillText(relLabel, labelX, labelY)
        ctx.restore()
      }
    })

    const sortedNodes = [...nodes].sort((a, b) => {
      const aHighlight = highlightedNodes.has(a.id)
      const bHighlight = highlightedNodes.has(b.id)
      if (aHighlight && !bHighlight) return 1
      if (!aHighlight && bHighlight) return -1
      return a.depth - b.depth
    })

    sortedNodes.forEach(node => {
      if (hiddenTypes.has(node.type)) return
      if (!Number.isFinite(node.x) || !Number.isFinite(node.y)) return

      const isSelected = selectedNode?.id === node.id
      const isHovered = hoveredNode?.id === node.id
      const isHighlighted = highlightedNodes.has(node.id)
      const nodeColor = nodeColors[node.type] || '#64748b'
      
      const baseRadius = 20 + Math.min(node.connections * 1.5, 12)
      const nodeRadius = Math.max(10, isSelected ? baseRadius + 5 : isHovered ? baseRadius + 3 : baseRadius)

      if (isSelected || isHovered) {
        ctx.beginPath()
        ctx.arc(node.x, node.y, nodeRadius + 12, 0, 2 * Math.PI)
        const gradient = ctx.createRadialGradient(
          node.x, node.y, nodeRadius,
          node.x, node.y, nodeRadius + 12
        )
        gradient.addColorStop(0, `${nodeColor}50`)
        gradient.addColorStop(1, `${nodeColor}00`)
        ctx.fillStyle = gradient
        ctx.fill()
      }

      ctx.beginPath()
      ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI)
      
      const nodeGradient = ctx.createRadialGradient(
        node.x - nodeRadius * 0.3,
        node.y - nodeRadius * 0.3,
        0,
        node.x,
        node.y,
        nodeRadius
      )
      
      if (isHighlighted) {
        nodeGradient.addColorStop(0, nodeColor)
        nodeGradient.addColorStop(1, `${nodeColor}dd`)
      } else {
        nodeGradient.addColorStop(0, `${nodeColor}aa`)
        nodeGradient.addColorStop(1, `${nodeColor}66`)
      }
      
      ctx.fillStyle = nodeGradient
      ctx.fill()

      if (isSelected) {
        ctx.strokeStyle = '#ffffff'
        ctx.lineWidth = 2.5 / zoom
        ctx.stroke()
      } else if (isHovered) {
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)'
        ctx.lineWidth = 2 / zoom
        ctx.stroke()
      }

      if (showLabels || isHighlighted) {
        ctx.fillStyle = '#ffffff'
        ctx.font = `${isSelected || isHovered ? '600 ' : ''}${11 / zoom}px Inter, system-ui, sans-serif`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        
        const maxWidth = nodeRadius * 1.8
        let displayName = node.name
        if (ctx.measureText(displayName).width > maxWidth) {
          while (ctx.measureText(displayName + '…').width > maxWidth && displayName.length > 1) {
            displayName = displayName.slice(0, -1)
          }
          displayName += '…'
        }
        
        ctx.fillText(displayName, node.x, node.y)
      }

      if (isHighlighted && node.depth > 0) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.6)'
        ctx.font = `${9 / zoom}px Inter, system-ui, sans-serif`
        ctx.textAlign = 'center'
        ctx.fillText(`${node.depth}跳`, node.x, node.y + nodeRadius + 12)
      }
    })

    ctx.restore()
  }, [zoom, offset, selectedNode, hoveredNode, hiddenTypes, showLabels])

  const animate = useCallback(() => {
    const settled = applyForces()
    drawGraph()
    
    if (!settled) {
      animationRef.current = requestAnimationFrame(animate)
    }
  }, [applyForces, drawGraph])

  useEffect(() => {
    if (graphData && isInitializedRef.current) {
      initializeSimulation(graphData, centerNodeId)
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
      animationRef.current = requestAnimationFrame(animate)
    }
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [graphData, centerNodeId, initializeSimulation, animate])

  const loadDefaultGraph = async () => {
    setLoading(true)
    try {
      const maotaiCode = '600519'
      console.log('Loading default graph with 贵州茅台 (600519)')
      
      let entityId: string | null = null
      try {
        const response = await apiClient.get('/api/entities', { 
          params: { keyword: maotaiCode, page: 1, page_size: 1 } 
        })
        const searchResult = response.data
        if (searchResult.entities && searchResult.entities.length > 0) {
          entityId = searchResult.entities[0].id
          console.log('Found 贵州茅台 entity:', entityId)
        }
      } catch (searchError) {
        console.warn('Failed to search for 贵州茅台，falling back to default graph:', searchError)
      }
      
      let data: GraphData
      if (entityId) {
        data = await graphService.getEntityGraph(entityId, 2)
        setCenterNodeId(entityId)
      } else {
        data = await graphService.getDefaultGraph(100)
        setCenterNodeId(null)
      }
      
      setGraphData(data)
    } catch (error) {
      console.error('Failed to load default graph:', error)
      setGraphData({ nodes: [], edges: [], total_nodes: 0, total_edges: 0 })
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchKeyword.trim()) {
      loadDefaultGraph()
      return
    }

    setLoading(true)
    try {
      const data = await graphService.searchGraph(searchKeyword)
      setGraphData(data)
      setSelectedNode(null)
      setSelectedEntity(null)
      setCenterNodeId(null)
      setZoom(1)
      setOffset({ x: 0, y: 0 })
    } catch (error) {
      console.error('Failed to search graph:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadEntityDetails = async (node: SimNode) => {
    try {
      const entity = await entityService.getEntity(node.id)
      setSelectedEntity(entity)
      
      const [newsData, sourcesData] = await Promise.all([
        entityService.getEntityNews(node.id, 5),
        entityService.getEntitySources(node.id),
      ])
      
      setEntityNews(newsData.news)
      setEntitySources(sourcesData.sources)
    } catch (error) {
      console.error('Failed to load entity details:', error)
    }
  }

  const handleNodeClick = async (node: SimNode) => {
    setSelectedNode(node)
    setActiveTab('info')
    setCenterNodeId(node.id)
    await loadEntityDetails(node)
  }

  const handleExpandNode = async (newDepth: number) => {
    if (!selectedNode) return
    
    setLoading(true)
    try {
      const data = await graphService.getEntityGraph(selectedNode.id, newDepth)
      setGraphData(data)
      setDepth(newDepth)
      setCenterNodeId(selectedNode.id)
    } catch (error) {
      console.error('Failed to expand node:', error)
    } finally {
      setLoading(false)
    }
  }

  const findNodeAtPosition = useCallback((x: number, y: number): SimNode | null => {
    const nodes = nodesRef.current
    if (!nodes || nodes.length === 0) return null
    
    for (let i = nodes.length - 1; i >= 0; i--) {
      const node = nodes[i]
      if (hiddenTypes.has(node.type)) continue
      if (!Number.isFinite(node.x) || !Number.isFinite(node.y)) continue
      
      const baseRadius = 20 + Math.min(node.connections * 1.5, 12)
      const distance = Math.sqrt((x - node.x) ** 2 + (y - node.y) ** 2)
      if (Number.isFinite(distance) && distance < baseRadius + 10) {
        return node
      }
    }
    return null
  }, [hiddenTypes])

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!canvasRef.current || draggingNode) return

    const canvas = canvasRef.current
    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left - offset.x) / zoom
    const y = (e.clientY - rect.top - offset.y) / zoom

    const clickedNode = findNodeAtPosition(x, y)
    if (clickedNode) {
      handleNodeClick(clickedNode)
    } else {
      setSelectedNode(null)
      setSelectedEntity(null)
    }
  }

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!canvasRef.current) return

    const canvas = canvasRef.current
    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left - offset.x) / zoom
    const y = (e.clientY - rect.top - offset.y) / zoom

    const clickedNode = findNodeAtPosition(x, y)
    if (clickedNode) {
      setDraggingNode(clickedNode)
      clickedNode.fx = clickedNode.x
      clickedNode.fy = clickedNode.y
    } else {
      setIsDragging(true)
      setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y })
    }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!canvasRef.current) return

    const canvas = canvasRef.current
    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left - offset.x) / zoom
    const y = (e.clientY - rect.top - offset.y) / zoom

    if (draggingNode) {
      // Only move node when explicitly dragging it
      draggingNode.fx = x
      draggingNode.fy = y
      draggingNode.x = x
      draggingNode.y = y
      drawGraph()
    } else if (isDragging) {
      // Move the canvas view (pan)
      setOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      })
    } else {
      // Just hover - don't move anything, just update cursor and highlight
      const hovered = findNodeAtPosition(x, y)
      setHoveredNode(hovered)
      canvas.style.cursor = hovered ? 'pointer' : 'grab'
    }
  }

  const handleMouseUp = () => {
    if (draggingNode) {
      draggingNode.fx = null
      draggingNode.fy = null
      setDraggingNode(null)
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
      animationRef.current = requestAnimationFrame(animate)
    }
    setIsDragging(false)
  }

  const handleMouseLeave = () => {
    setHoveredNode(null)
    handleMouseUp()
  }

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? 0.9 : 1.1
    setZoom((z) => Math.max(0.2, Math.min(5, z * delta)))
  }

  const handleDoubleClick = async (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!canvasRef.current) return

    const canvas = canvasRef.current
    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left - offset.x) / zoom
    const y = (e.clientY - rect.top - offset.y) / zoom

    const clickedNode = findNodeAtPosition(x, y)
    if (clickedNode) {
      setLoading(true)
      try {
        const data = await graphService.getEntityGraph(clickedNode.id, depth)
        setGraphData(data)
        setSelectedNode(clickedNode)
        setCenterNodeId(clickedNode.id)
        await loadEntityDetails(clickedNode)
      } catch (error) {
        console.error('Failed to expand node:', error)
      } finally {
        setLoading(false)
      }
    }
  }

  const resetView = () => {
    setZoom(1)
    setOffset({ x: 0, y: 0 })
    setCenterNodeId(null)
    if (graphData) {
      initializeSimulation(graphData, null)
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
      animationRef.current = requestAnimationFrame(animate)
    }
  }

  const toggleTypeVisibility = (type: string) => {
    setHiddenTypes(prev => {
      const newSet = new Set(prev)
      if (newSet.has(type)) {
        newSet.delete(type)
      } else {
        newSet.add(type)
      }
      return newSet
    })
  }

  const handleCreateEntity = async () => {
    if (!formData.name.trim()) return
    
    setSaving(true)
    try {
      await entityService.createEntity({
        entity_type: formData.entity_type,
        name: formData.name,
        code: formData.code || undefined,
        description: formData.description || undefined,
        industry: formData.industry || undefined,
        aliases: formData.aliases ? formData.aliases.split(',').map(a => a.trim()) : [],
      })
      setShowCreateModal(false)
      setFormData({
        entity_type: 'stock',
        name: '',
        code: '',
        description: '',
        industry: '',
        aliases: '',
      })
      await loadDefaultGraph()
      await loadStats()
    } catch (error) {
      console.error('Failed to create entity:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleEditEntity = async () => {
    if (!selectedEntity || !formData.name.trim()) return
    
    setSaving(true)
    try {
      await entityService.updateEntity(selectedEntity.id, {
        name: formData.name,
        description: formData.description || undefined,
        industry: formData.industry || undefined,
        aliases: formData.aliases ? formData.aliases.split(',').map(a => a.trim()) : [],
      })
      setShowEditModal(false)
      if (selectedNode) {
        await loadEntityDetails(selectedNode)
      }
      await loadDefaultGraph()
    } catch (error) {
      console.error('Failed to update entity:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteEntity = async () => {
    if (!selectedEntity) return
    
    setSaving(true)
    try {
      await entityService.deleteEntity(selectedEntity.id)
      setShowDeleteConfirm(false)
      setSelectedNode(null)
      setSelectedEntity(null)
      await loadDefaultGraph()
      await loadStats()
    } catch (error) {
      console.error('Failed to delete entity:', error)
    } finally {
      setSaving(false)
    }
  }

  const searchTargetEntities = async (keyword: string) => {
    if (!keyword.trim()) {
      setTargetSearchResults([])
      return
    }
    try {
      const result = await entityService.listEntities({ keyword, limit: 10 })
      setTargetSearchResults(result.entities)
    } catch (error) {
      console.error('Failed to search entities:', error)
    }
  }

  const handleCreateRelation = async () => {
    if (!selectedEntity || !relationFormData.target_entity_id) return
    
    setSaving(true)
    try {
      await entityService.createRelation({
        source_entity_id: selectedEntity.id,
        target_entity_id: relationFormData.target_entity_id,
        relation_type: relationFormData.relation_type,
        weight: relationFormData.weight,
        evidence: relationFormData.evidence || undefined,
      })
      setShowRelationModal(false)
      setRelationFormData({
        target_entity_id: '',
        relation_type: 'belongs_to',
        weight: 1.0,
        evidence: '',
      })
      setTargetSearchKeyword('')
      setTargetSearchResults([])
      if (selectedNode) {
        await loadEntityDetails(selectedNode)
      }
      await loadDefaultGraph()
    } catch (error) {
      console.error('Failed to create relation:', error)
    } finally {
      setSaving(false)
    }
  }

  const openEditModal = () => {
    if (selectedEntity) {
      setFormData({
        entity_type: selectedEntity.type,
        name: selectedEntity.name,
        code: selectedEntity.code || '',
        description: selectedEntity.description || '',
        industry: selectedEntity.industry || '',
        aliases: selectedEntity.aliases?.join(', ') || '',
      })
      setShowEditModal(true)
    }
  }

  useEffect(() => {
    const setupCanvas = () => {
      if (!canvasRef.current || !containerRef.current) return
      
      const container = containerRef.current
      const dpr = window.devicePixelRatio || 1
      dprRef.current = dpr
      
      const width = container.clientWidth
      const height = container.clientHeight
      canvasSizeRef.current = { width, height }
      
      const canvas = canvasRef.current
      canvas.width = width * dpr
      canvas.height = height * dpr
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      
      if (isInitializedRef.current) {
        drawGraph()
      }
    }

    setupCanvas()
    window.addEventListener('resize', setupCanvas)
    return () => window.removeEventListener('resize', setupCanvas)
  }, [drawGraph])

  useEffect(() => {
    if (graphData && canvasRef.current && containerRef.current) {
      const container = containerRef.current
      const dpr = window.devicePixelRatio || 1
      dprRef.current = dpr
      
      const width = container.clientWidth
      const height = container.clientHeight
      canvasSizeRef.current = { width, height }
      
      const canvas = canvasRef.current
      canvas.width = width * dpr
      canvas.height = height * dpr
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      
      initializeSimulation(graphData, centerNodeId)
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
      animationRef.current = requestAnimationFrame(animate)
    }
  }, [graphData])

  useEffect(() => {
    if (showQualityPanel && !qualityReport) {
      loadQualityReport()
    }
  }, [showQualityPanel, qualityReport])

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-400" />
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-amber-400" />
      default:
        return <Info className="w-4 h-4 text-blue-400" />
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'error':
        return 'border-red-500/30 bg-red-500/10'
      case 'warning':
        return 'border-amber-500/30 bg-amber-500/10'
      default:
        return 'border-blue-500/30 bg-blue-500/10'
    }
  }

  return (
    <div className="h-screen flex flex-col bg-[#0a0a0f]">
      {/* Header */}
      <header className="relative z-10 border-b border-white/[0.05] bg-[#0a0a0f]/90 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="w-10 h-10 rounded-xl bg-white/[0.03] border border-white/[0.05] flex items-center justify-center text-zinc-400 hover:text-white hover:bg-white/[0.06] hover:border-white/[0.1] transition-all"
              >
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
                  <Network className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-white">知识图谱</h1>
                  <p className="text-xs text-zinc-500">实体关系可视化与智能关联分析</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                <input
                  type="text"
                  value={searchKeyword}
                  onChange={(e) => setSearchKeyword(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="搜索实体..."
                  className="pl-10 pr-4 py-2.5 w-64 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/40 text-sm transition-all"
                />
              </div>
              <Button onClick={handleSearch} size="sm">
                搜索
              </Button>
              <Button 
                onClick={() => setShowCreateModal(true)} 
                size="sm" 
                variant="secondary"
                className="flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                创建实体
              </Button>
              <Button 
                onClick={() => {
                  setShowQualityPanel(!showQualityPanel)
                  if (!showQualityPanel) loadQualityReport()
                }} 
                size="sm" 
                variant={showQualityPanel ? "default" : "secondary"}
                className="flex items-center gap-2"
              >
                <Shield className="w-4 h-4" />
                数据质量
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex relative z-10">
        {/* Canvas Area */}
        <div ref={containerRef} className="flex-1 relative">
          {loading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-[#0a0a0f]">
              <div className="flex flex-col items-center gap-4">
                <Loader2 className="w-8 h-8 animate-spin text-violet-400" />
                <span className="text-zinc-400 text-sm">加载图谱中...</span>
              </div>
            </div>
          ) : !graphData || graphData.nodes.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center bg-[#0a0a0f]">
              <div className="flex flex-col items-center gap-4">
                <div className="w-16 h-16 rounded-2xl bg-white/[0.03] border border-white/[0.05] flex items-center justify-center">
                  <Network className="w-8 h-8 text-zinc-600" />
                </div>
                <p className="text-zinc-500 text-sm">暂无图谱数据</p>
              </div>
            </div>
          ) : (
            <canvas
              ref={canvasRef}
              onClick={handleCanvasClick}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseLeave}
              onDoubleClick={handleDoubleClick}
              onWheel={handleWheel}
              className="w-full h-full cursor-grab active:cursor-grabbing"
            />
          )}

          {/* Zoom Controls */}
          <div className="absolute bottom-6 left-6 flex items-center gap-2">
            <button
              onClick={() => setZoom((z) => Math.min(5, z * 1.2))}
              className="w-10 h-10 rounded-xl bg-white/[0.05] border border-white/[0.08] flex items-center justify-center text-zinc-400 hover:text-white hover:bg-white/[0.08] hover:border-white/[0.12] transition-all"
              title="放大"
            >
              <ZoomIn className="w-5 h-5" />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.2, z * 0.8))}
              className="w-10 h-10 rounded-xl bg-white/[0.05] border border-white/[0.08] flex items-center justify-center text-zinc-400 hover:text-white hover:bg-white/[0.08] hover:border-white/[0.12] transition-all"
              title="缩小"
            >
              <ZoomOut className="w-5 h-5" />
            </button>
            <button
              onClick={resetView}
              className="w-10 h-10 rounded-xl bg-white/[0.05] border border-white/[0.08] flex items-center justify-center text-zinc-400 hover:text-white hover:bg-white/[0.08] hover:border-white/[0.12] transition-all"
              title="重置视图"
            >
              <RotateCcw className="w-5 h-5" />
            </button>
            <div className="ml-2 px-3 py-2 rounded-lg bg-white/[0.03] border border-white/[0.05] text-xs text-zinc-500">
              {Math.round(zoom * 100)}%
            </div>
          </div>

          {/* Depth & Display Controls */}
          <div className="absolute bottom-6 left-52 flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-500">展开深度:</span>
              {[1, 2, 3].map((d) => (
                <button
                  key={d}
                  onClick={() => handleExpandNode(d)}
                  disabled={!selectedNode}
                  className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-medium transition-all ${
                    depth === d
                      ? 'bg-violet-500/20 border border-violet-500/40 text-violet-400'
                      : 'bg-white/[0.03] border border-white/[0.05] text-zinc-400 hover:text-white hover:bg-white/[0.06]'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {d}跳
                </button>
              ))}
            </div>
            
            <div className="w-px h-6 bg-white/[0.08]" />
            
            <button
              onClick={() => setShowLabels(!showLabels)}
              className={`px-3 py-2 rounded-lg flex items-center gap-2 text-xs transition-all ${
                showLabels
                  ? 'bg-violet-500/20 border border-violet-500/40 text-violet-400'
                  : 'bg-white/[0.03] border border-white/[0.05] text-zinc-400 hover:text-white'
              }`}
            >
              {showLabels ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
              标签
            </button>
          </div>

          {/* Help Tooltip */}
          <div className="absolute top-6 left-6 p-4 rounded-xl bg-white/[0.03] border border-white/[0.05] backdrop-blur-sm">
            <div className="text-xs text-zinc-500 space-y-1">
              <p className="flex items-center gap-2"><Move className="w-3 h-3" /> 拖拽画布平移</p>
              <p className="flex items-center gap-2"><Compass className="w-3 h-3" /> 滚轮缩放</p>
              <p className="flex items-center gap-2"><Expand className="w-3 h-3" /> 双击节点展开</p>
              <p className="flex items-center gap-2"><Move className="w-3 h-3" /> 拖拽节点移动</p>
            </div>
          </div>
        </div>

        {/* Quality Panel */}
        {showQualityPanel && qualityReport && (
          <div className="w-80 border-l border-white/[0.05] bg-[#0d0d12]/90 backdrop-blur-xl flex flex-col overflow-y-auto">
            <div className="p-6 border-b border-white/[0.05]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Shield className="w-5 h-5 text-violet-400" />
                  <h3 className="text-lg font-semibold text-white">数据质量报告</h3>
                </div>
                <button
                  onClick={() => setShowQualityPanel(false)}
                  className="text-zinc-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
            
            <div className="p-6 space-y-4">
              <div className="p-4 rounded-xl bg-gradient-to-br from-violet-500/20 to-purple-500/10 border border-violet-500/20">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-zinc-400">一致性评分</span>
                  <span className="text-2xl font-bold text-white">
                    {(qualityReport.consistency_score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="w-full h-2 bg-white/[0.1] rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-violet-500 to-purple-500 rounded-full transition-all"
                    style={{ width: `${qualityReport.consistency_score * 100}%` }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-2 mb-1">
                    <Users className="w-4 h-4 text-blue-400" />
                    <span className="text-xs text-zinc-500">实体总数</span>
                  </div>
                  <p className="text-xl font-bold text-white">{qualityReport.total_entities}</p>
                </div>
                <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <div className="flex items-center gap-2 mb-1">
                    <GitBranch className="w-4 h-4 text-green-400" />
                    <span className="text-xs text-zinc-500">关系总数</span>
                  </div>
                  <p className="text-xl font-bold text-white">{qualityReport.total_relations}</p>
                </div>
              </div>

              {qualityReport.issues.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-white mb-3">发现问题</h4>
                  <div className="space-y-2">
                    {qualityReport.issues.map((issue, i) => (
                      <div
                        key={i}
                        className={`p-3 rounded-lg border ${getSeverityColor(issue.severity)}`}
                      >
                        <div className="flex items-start gap-2">
                          {getSeverityIcon(issue.severity)}
                          <div className="flex-1">
                            <p className="text-sm text-white">{issue.message}</p>
                            <p className="text-xs text-zinc-500 mt-1">数量: {issue.count}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <h4 className="text-sm font-medium text-white mb-3">质量指标</h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                    <span className="text-sm text-zinc-400">孤立实体</span>
                    <span className={`text-sm font-medium ${qualityReport.isolated_entities > 0 ? 'text-amber-400' : 'text-green-400'}`}>
                      {qualityReport.isolated_entities}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                    <span className="text-sm text-zinc-400">缺少行业</span>
                    <span className={`text-sm font-medium ${qualityReport.entities_without_industry > 0 ? 'text-amber-400' : 'text-green-400'}`}>
                      {qualityReport.entities_without_industry}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                    <span className="text-sm text-zinc-400">缺少代码</span>
                    <span className={`text-sm font-medium ${qualityReport.entities_without_code > 0 ? 'text-amber-400' : 'text-green-400'}`}>
                      {qualityReport.entities_without_code}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                    <span className="text-sm text-zinc-400">悬空关系</span>
                    <span className={`text-sm font-medium ${qualityReport.dangling_relations > 0 ? 'text-red-400' : 'text-green-400'}`}>
                      {qualityReport.dangling_relations}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Sidebar */}
        <div className="w-96 border-l border-white/[0.05] bg-[#0d0d12]/90 backdrop-blur-xl flex flex-col">
          <div className="flex-1 overflow-y-auto">
            {selectedNode && selectedEntity ? (
              <div className="animate-fade-in">
                <div className="p-6 border-b border-white/[0.05]">
                  <div className="flex items-center gap-4">
                    <div
                      className="w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg"
                      style={{ backgroundColor: nodeColors[selectedNode.type] || '#64748b' }}
                    >
                      <span className="text-white text-xl font-semibold">
                        {selectedNode.name.charAt(0)}
                      </span>
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-white">{selectedNode.name}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="secondary" size="sm">
                          {nodeLabels[selectedNode.type] || selectedNode.type}
                        </Badge>
                        {selectedEntity.code && (
                          <span className="text-xs text-zinc-500">{selectedEntity.code}</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={openEditModal}
                        className="w-8 h-8 rounded-lg bg-white/[0.03] border border-white/[0.05] flex items-center justify-center text-zinc-400 hover:text-white hover:bg-white/[0.06] transition-all"
                        title="编辑"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setShowRelationModal(true)}
                        className="w-8 h-8 rounded-lg bg-white/[0.03] border border-white/[0.05] flex items-center justify-center text-zinc-400 hover:text-white hover:bg-white/[0.06] transition-all"
                        title="添加关系"
                      >
                        <Link2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setShowDeleteConfirm(true)}
                        className="w-8 h-8 rounded-lg bg-white/[0.03] border border-white/[0.05] flex items-center justify-center text-zinc-400 hover:text-red-400 hover:bg-red-500/10 transition-all"
                        title="删除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>

                <div className="flex border-b border-white/[0.05]">
                  {[
                    { id: 'info', label: '基本信息', icon: Info },
                    { id: 'relations', label: '关系', icon: Layers },
                    { id: 'news', label: '新闻', icon: Newspaper },
                    { id: 'sources', label: '来源', icon: Database },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as typeof activeTab)}
                      className={`flex-1 py-3 text-xs font-medium flex items-center justify-center gap-1.5 transition-all ${
                        activeTab === tab.id
                          ? 'text-violet-400 border-b-2 border-violet-400'
                          : 'text-zinc-500 hover:text-white'
                      }`}
                    >
                      <tab.icon className="w-3.5 h-3.5" />
                      {tab.label}
                    </button>
                  ))}
                </div>

                <div className="p-6">
                  {activeTab === 'info' && (
                    <div className="space-y-3">
                      {selectedEntity.description && (
                        <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                          <p className="text-xs text-zinc-500 mb-1">描述</p>
                          <p className="text-white text-sm">{selectedEntity.description}</p>
                        </div>
                      )}
                      {selectedEntity.industry && (
                        <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                          <p className="text-xs text-zinc-500 mb-1">所属行业</p>
                          <p className="text-white font-medium">{selectedEntity.industry}</p>
                        </div>
                      )}
                      {selectedEntity.aliases && selectedEntity.aliases.length > 0 && (
                        <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                          <p className="text-xs text-zinc-500 mb-2">别名</p>
                          <div className="flex flex-wrap gap-2">
                            {selectedEntity.aliases.map((alias, i) => (
                              <Badge key={i} variant="secondary" size="sm">{alias}</Badge>
                            ))}
                          </div>
                        </div>
                      )}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                          <p className="text-xs text-zinc-500 mb-1">置信度</p>
                          <p className="text-white font-medium">{(selectedEntity.confidence * 100).toFixed(0)}%</p>
                        </div>
                        <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                          <p className="text-xs text-zinc-500 mb-1">数据来源</p>
                          <p className="text-white font-medium">{selectedEntity.source || '手动创建'}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {activeTab === 'relations' && selectedEntity.relations && (
                    <div className="space-y-4">
                      {selectedEntity.relations.outgoing.length > 0 && (
                        <div>
                          <p className="text-xs text-zinc-500 mb-2">出边关系 ({selectedEntity.relations.outgoing.length})</p>
                          <div className="space-y-2">
                            {selectedEntity.relations.outgoing.slice(0, 10).map((rel, i) => (
                              <div key={i} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05] flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <Badge variant="secondary" size="sm">
                                    {relationLabels[rel.type] || rel.type}
                                  </Badge>
                                  {rel.target && (
                                    <span className="text-sm text-white">{rel.target.name}</span>
                                  )}
                                </div>
                                <ChevronRight className="w-4 h-4 text-zinc-500" />
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {selectedEntity.relations.incoming.length > 0 && (
                        <div>
                          <p className="text-xs text-zinc-500 mb-2">入边关系 ({selectedEntity.relations.incoming.length})</p>
                          <div className="space-y-2">
                            {selectedEntity.relations.incoming.slice(0, 10).map((rel, i) => (
                              <div key={i} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05] flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  {rel.source && (
                                    <span className="text-sm text-white">{rel.source.name}</span>
                                  )}
                                  <Badge variant="secondary" size="sm">
                                    {relationLabels[rel.type] || rel.type}
                                  </Badge>
                                </div>
                                <ChevronRight className="w-4 h-4 text-zinc-500" />
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {selectedEntity.relations.total === 0 && (
                        <div className="text-center py-8 text-zinc-500 text-sm">
                          暂无关系数据
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === 'news' && (
                    <div className="space-y-3">
                      {entityNews.length > 0 ? (
                        entityNews.map((news, i) => (
                          <div key={i} className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                            <div className="flex items-start justify-between gap-2">
                              <h4 className="text-sm font-medium text-white line-clamp-2">{news.title}</h4>
                              <Badge 
                                variant={news.sentiment === 'positive' ? 'success' : news.sentiment === 'negative' ? 'danger' : 'secondary'} 
                                size="sm"
                              >
                                {news.sentiment === 'positive' ? '利好' : news.sentiment === 'negative' ? '利空' : '中性'}
                              </Badge>
                            </div>
                            <p className="text-xs text-zinc-500 mt-2 line-clamp-2">{news.summary}</p>
                            <div className="flex items-center justify-between mt-3">
                              <span className="text-xs text-zinc-600">{news.source}</span>
                              <span className="text-xs text-zinc-600">{news.published_at}</span>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-center py-8 text-zinc-500 text-sm">
                          暂无相关新闻
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === 'sources' && (
                    <div className="space-y-3">
                      {entitySources.length > 0 ? (
                        entitySources.map((source, i) => (
                          <div key={i} className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                            <div className="flex items-center gap-2">
                              <Database className="w-4 h-4 text-zinc-500" />
                              <span className="text-sm text-white">
                                {source.type === 'primary' ? '主要数据源' : source.type === 'created' ? '创建时间' : '更新时间'}
                              </span>
                            </div>
                            {source.name && (
                              <p className="text-sm text-zinc-400 mt-2">{source.name}</p>
                            )}
                            {source.confidence && (
                              <p className="text-xs text-zinc-500 mt-1">置信度: {(source.confidence * 100).toFixed(0)}%</p>
                            )}
                            {source.timestamp && (
                              <p className="text-xs text-zinc-600 mt-1">{source.timestamp}</p>
                            )}
                          </div>
                        ))
                      ) : (
                        <div className="text-center py-8 text-zinc-500 text-sm">
                          暂无来源信息
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center p-6">
                <div className="w-16 h-16 rounded-2xl bg-white/[0.03] border border-white/[0.05] flex items-center justify-center mb-4">
                  <Maximize2 className="w-8 h-8 text-zinc-600" />
                </div>
                <p className="text-zinc-500 text-sm">点击图谱中的节点查看详情</p>
                <p className="text-zinc-600 text-xs mt-2">双击节点展开更多关系</p>
              </div>
            )}
          </div>

          {stats && (
            <div className="p-6 border-t border-white/[0.05]">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="w-4 h-4 text-zinc-500" />
                <h4 className="text-sm font-medium text-white">图谱统计</h4>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <p className="text-2xl font-bold text-white">{stats.total_entities}</p>
                  <p className="text-xs text-zinc-500">实体数量</p>
                </div>
                <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                  <p className="text-2xl font-bold text-white">{stats.total_relations}</p>
                  <p className="text-xs text-zinc-500">关系数量</p>
                </div>
              </div>
            </div>
          )}

          <div className="p-6 border-t border-white/[0.05]">
            <div className="flex items-center gap-2 mb-4">
              <Filter className="w-4 h-4 text-zinc-500" />
              <h4 className="text-sm font-medium text-white">类型筛选</h4>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(nodeLabels).map(([type, label]) => (
                <button
                  key={type}
                  onClick={() => toggleTypeVisibility(type)}
                  className={`flex items-center gap-2 p-2 rounded-lg transition-all ${
                    hiddenTypes.has(type)
                      ? 'bg-white/[0.01] border border-white/[0.03] opacity-50'
                      : 'bg-white/[0.03] border border-white/[0.05]'
                  }`}
                >
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: nodeColors[type] || '#64748b' }}
                  />
                  <span className="text-xs text-zinc-400">{label}</span>
                  {hiddenTypes.has(type) ? (
                    <EyeOff className="w-3 h-3 text-zinc-600 ml-auto" />
                  ) : (
                    <Eye className="w-3 h-3 text-zinc-500 ml-auto" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Modals - keeping them for brevity */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowCreateModal(false)} />
          <div className="relative w-full max-w-lg bg-[#0d0d12] border border-white/[0.08] rounded-2xl shadow-2xl">
            <div className="flex items-center justify-between p-6 border-b border-white/[0.05]">
              <h3 className="text-lg font-semibold text-white">创建实体</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">实体类型</label>
                <select
                  value={formData.entity_type}
                  onChange={(e) => setFormData({ ...formData, entity_type: e.target.value })}
                  className="w-full px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:border-violet-500/40"
                >
                  {entityTypes.map((t) => (
                    <option key={t.type} value={t.type} className="bg-zinc-900">
                      {t.display_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">名称 *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="输入实体名称"
                  className="w-full px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/40"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">代码</label>
                <input
                  type="text"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  placeholder="如股票代码"
                  className="w-full px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/40"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">所属行业</label>
                <select
                  value={formData.industry}
                  onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                  className="w-full px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:border-violet-500/40"
                >
                  <option value="" className="bg-zinc-900">选择行业</option>
                  {industries.map((ind) => (
                    <option key={ind.name} value={ind.name} className="bg-zinc-900">
                      {ind.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">描述</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="输入实体描述"
                  rows={3}
                  className="w-full px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/40 resize-none"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">别名 (逗号分隔)</label>
                <input
                  type="text"
                  value={formData.aliases}
                  onChange={(e) => setFormData({ ...formData, aliases: e.target.value })}
                  placeholder="别名1, 别名2"
                  className="w-full px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/40"
                />
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 p-6 border-t border-white/[0.05]">
              <Button variant="secondary" onClick={() => setShowCreateModal(false)}>取消</Button>
              <Button onClick={handleCreateEntity} disabled={saving || !formData.name.trim()}>
                {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
                创建
              </Button>
            </div>
          </div>
        </div>
      )}

      {showEditModal && selectedEntity && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowEditModal(false)} />
          <div className="relative w-full max-w-lg bg-[#0d0d12] border border-white/[0.08] rounded-2xl shadow-2xl">
            <div className="flex items-center justify-between p-6 border-b border-white/[0.05]">
              <h3 className="text-lg font-semibold text-white">编辑实体</h3>
              <button onClick={() => setShowEditModal(false)} className="text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">名称 *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="输入实体名称"
                  className="w-full px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/40"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">所属行业</label>
                <select
                  value={formData.industry}
                  onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                  className="w-full px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:border-violet-500/40"
                >
                  <option value="" className="bg-zinc-900">选择行业</option>
                  {industries.map((ind) => (
                    <option key={ind.name} value={ind.name} className="bg-zinc-900">
                      {ind.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">描述</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="输入实体描述"
                  rows={3}
                  className="w-full px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/40 resize-none"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">别名 (逗号分隔)</label>
                <input
                  type="text"
                  value={formData.aliases}
                  onChange={(e) => setFormData({ ...formData, aliases: e.target.value })}
                  placeholder="别名1, 别名2"
                  className="w-full px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/40"
                />
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 p-6 border-t border-white/[0.05]">
              <Button variant="secondary" onClick={() => setShowEditModal(false)}>取消</Button>
              <Button onClick={handleEditEntity} disabled={saving || !formData.name.trim()}>
                {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
                保存
              </Button>
            </div>
          </div>
        </div>
      )}

      {showRelationModal && selectedEntity && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowRelationModal(false)} />
          <div className="relative w-full max-w-lg bg-[#0d0d12] border border-white/[0.08] rounded-2xl shadow-2xl">
            <div className="flex items-center justify-between p-6 border-b border-white/[0.05]">
              <h3 className="text-lg font-semibold text-white">创建关系</h3>
              <button onClick={() => setShowRelationModal(false)} className="text-zinc-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                <p className="text-xs text-zinc-500 mb-1">源实体</p>
                <p className="text-white font-medium">{selectedEntity.name}</p>
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">关系类型</label>
                <select
                  value={relationFormData.relation_type}
                  onChange={(e) => setRelationFormData({ ...relationFormData, relation_type: e.target.value })}
                  className="w-full px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:border-violet-500/40"
                >
                  {relationTypes.map((t) => (
                    <option key={t.type} value={t.type} className="bg-zinc-900">
                      {t.display_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">目标实体</label>
                <div className="relative">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                  <input
                    type="text"
                    value={targetSearchKeyword}
                    onChange={(e) => {
                      setTargetSearchKeyword(e.target.value)
                      searchTargetEntities(e.target.value)
                    }}
                    placeholder="搜索目标实体..."
                    className="w-full pl-10 pr-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/40"
                  />
                  {targetSearchResults.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-2 bg-zinc-900 border border-white/[0.08] rounded-xl overflow-hidden z-10 max-h-48 overflow-y-auto">
                      {targetSearchResults
                        .filter(e => e.id !== selectedEntity.id)
                        .map((entity) => (
                          <button
                            key={entity.id}
                            onClick={() => {
                              setRelationFormData({ ...relationFormData, target_entity_id: entity.id })
                              setTargetSearchKeyword(entity.name)
                              setTargetSearchResults([])
                            }}
                            className="w-full px-4 py-3 text-left hover:bg-white/[0.05] flex items-center gap-3"
                          >
                            <div
                              className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm"
                              style={{ backgroundColor: nodeColors[entity.type] || '#64748b' }}
                            >
                              {entity.name.charAt(0)}
                            </div>
                            <div>
                              <p className="text-white text-sm">{entity.name}</p>
                              <p className="text-zinc-500 text-xs">{nodeLabels[entity.type] || entity.type}</p>
                            </div>
                          </button>
                        ))}
                    </div>
                  )}
                </div>
                {relationFormData.target_entity_id && (
                  <p className="text-xs text-green-400 mt-2">已选择: {targetSearchKeyword}</p>
                )}
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">权重 (0-1)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={relationFormData.weight}
                  onChange={(e) => setRelationFormData({ ...relationFormData, weight: parseFloat(e.target.value) || 1 })}
                  className="w-full px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white focus:outline-none focus:border-violet-500/40"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1.5">证据/来源</label>
                <textarea
                  value={relationFormData.evidence}
                  onChange={(e) => setRelationFormData({ ...relationFormData, evidence: e.target.value })}
                  placeholder="输入关系证据或来源"
                  rows={2}
                  className="w-full px-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/40 resize-none"
                />
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 p-6 border-t border-white/[0.05]">
              <Button variant="secondary" onClick={() => setShowRelationModal(false)}>取消</Button>
              <Button onClick={handleCreateRelation} disabled={saving || !relationFormData.target_entity_id}>
                {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Link2 className="w-4 h-4 mr-2" />}
                创建关系
              </Button>
            </div>
          </div>
        </div>
      )}

      {showDeleteConfirm && selectedEntity && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowDeleteConfirm(false)} />
          <div className="relative w-full max-w-md bg-[#0d0d12] border border-white/[0.08] rounded-2xl shadow-2xl">
            <div className="p-6">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-12 h-12 rounded-xl bg-red-500/20 flex items-center justify-center">
                  <Trash2 className="w-6 h-6 text-red-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">确认删除</h3>
                  <p className="text-sm text-zinc-500">此操作不可撤销</p>
                </div>
              </div>
              <p className="text-zinc-400 text-sm">
                确定要删除实体 <span className="text-white font-medium">{selectedEntity.name}</span> 吗？删除后相关关系也会被移除。
              </p>
            </div>
            <div className="flex items-center justify-end gap-3 p-6 border-t border-white/[0.05]">
              <Button variant="secondary" onClick={() => setShowDeleteConfirm(false)}>取消</Button>
              <Button variant="danger" onClick={handleDeleteEntity} disabled={saving}>
                {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Trash2 className="w-4 h-4 mr-2" />}
                删除
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
