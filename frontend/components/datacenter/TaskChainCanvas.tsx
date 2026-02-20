'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  Edge,
  Node,
  NodeTypes,
  Position,
  useEdgesState,
  useNodesState,
  MarkerType,
  Handle,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';

const statusColors: Record<string, string> = {
  pending: 'bg-gray-500',
  running: 'bg-blue-500 animate-pulse',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
  cancelled: 'bg-yellow-500',
  paused: 'bg-orange-500',
};

const statusLabels: Record<string, string> = {
  pending: '待执行',
  running: '执行中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
  paused: '已暂停',
};

interface TaskNodeData {
  label: string;
  taskType: string;
  status: string;
  chainId?: string;
  progress?: number;
  error?: string;
  startedAt?: string;
  completedAt?: string;
}

interface DataTarget {
  target_id: string;
  target_type: string;
  target_name: string;
  target_location: string;
  status: string;
  records_synced: number;
}

interface TaskChainCanvasProps {
  chainId?: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
  onNodeClick?: (nodeId: string, data: TaskNodeData) => void;
}

const TaskNode: React.FC<{ data: TaskNodeData }> = ({ data }) => {
  const statusColor = statusColors[data.status] || statusColors.pending;
  const statusLabel = statusLabels[data.status] || data.status;

  return (
    <Card className="px-4 py-2 min-w-[180px] shadow-lg border-2 border-gray-200 hover:border-blue-400 transition-colors">
      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="font-medium text-sm truncate">{data.label}</span>
          <Badge className={`${statusColor} text-white text-xs`}>
            {statusLabel}
          </Badge>
        </div>
        
        <div className="text-xs text-gray-500">
          类型: {data.taskType || '未知'}
        </div>
        
        {data.progress !== undefined && data.progress > 0 && (
          <Progress value={data.progress} className="h-1" />
        )}
        
        {data.error && (
          <div className="text-xs text-red-500 truncate" title={data.error}>
            错误: {data.error}
          </div>
        )}
      </div>
      
      <Handle type="source" position={Position.Bottom} className="w-3 h-3" />
    </Card>
  );
};

const DataTargetNode: React.FC<{ data: DataTarget }> = ({ data }) => {
  const typeIcons: Record<string, string> = {
    postgresql: '🐘',
    neo4j: '🔗',
    redis: '⚡',
    elasticsearch: '🔍',
  };

  return (
    <Card className="px-3 py-2 min-w-[150px] bg-gradient-to-br from-purple-50 to-blue-50 border-purple-200">
      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      
      <div className="flex items-center gap-2">
        <span className="text-lg">{typeIcons[data.target_type] || '📦'}</span>
        <div className="flex flex-col">
          <span className="font-medium text-sm">{data.target_name}</span>
          <span className="text-xs text-gray-500">{data.target_location}</span>
        </div>
      </div>
      
      <div className="mt-1 flex items-center gap-2">
        <Badge variant="outline" className="text-xs">
          {data.status === 'synced' ? '✓ 已同步' : '○ 待同步'}
        </Badge>
        {data.records_synced > 0 && (
          <span className="text-xs text-gray-500">
            {data.records_synced.toLocaleString()} 条
          </span>
        )}
      </div>
    </Card>
  );
};

const nodeTypes: NodeTypes = {
  taskNode: TaskNode,
  dataTarget: DataTargetNode,
};

const TaskChainCanvas: React.FC<TaskChainCanvasProps> = ({
  chainId,
  autoRefresh = true,
  refreshInterval = 5000,
  onNodeClick,
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chainData, setChainData] = useState<any>(null);

  const fetchChainData = useCallback(async () => {
    try {
      const endpoint = chainId 
        ? `/api/datacenter/canvas/chain/${chainId}`
        : '/api/datacenter/canvas/data';
      
      const response = await fetch(endpoint);
      
      if (!response.ok) {
        throw new Error('Failed to fetch chain data');
      }
      
      const data = await response.json();
      
      const flowNodes: Node[] = [];
      const flowEdges: Edge[] = [];
      
      if (chainId && data.nodes) {
        let yOffset = 0;
        const nodeWidth = 200;
        const nodeHeight = 100;
        const xSpacing = 250;
        const ySpacing = 120;
        
        const nodePositions: Record<string, { x: number; y: number }> = {};
        const levels: Record<string, string[]> = {};
        
        const edgesList = data.edges || [];
        const nodesMap = data.nodes || {};
        
        Object.keys(nodesMap).forEach(nodeId => {
          const hasIncoming = edgesList.some((e: any) => e.target === nodeId);
          if (!hasIncoming) {
            levels[0] = levels[0] || [];
            levels[0].push(nodeId);
          }
        });
        
        let level = 0;
        while (Object.keys(levels).length > level) {
          const currentLevelNodes = levels[level] || [];
          const nextLevelNodes: string[] = [];
          
          currentLevelNodes.forEach(nodeId => {
            const outgoingEdges = edgesList.filter((e: any) => e.source === nodeId);
            outgoingEdges.forEach((edge: any) => {
              const targetId = edge.target;
              if (!Object.values(levels).flat().includes(targetId)) {
                nextLevelNodes.push(targetId);
              }
            });
          });
          
          if (nextLevelNodes.length > 0) {
            levels[level + 1] = [...new Set(nextLevelNodes)];
          }
          level++;
        }
        
        Object.entries(levels).forEach(([lvl, nodeIds]) => {
          const levelNum = parseInt(lvl);
          const nodesInLevel = nodeIds.length;
          const totalWidth = nodesInLevel * xSpacing;
          const startX = -totalWidth / 2 + xSpacing / 2;
          
          nodeIds.forEach((nodeId, index) => {
            const nodeData = nodesMap[nodeId];
            if (nodeData) {
              nodePositions[nodeId] = {
                x: startX + index * xSpacing,
                y: levelNum * ySpacing,
              };
              
              flowNodes.push({
                id: nodeId,
                type: 'taskNode',
                position: nodePositions[nodeId],
                data: {
                  label: nodeData.name || nodeId,
                  taskType: nodeData.task_type || 'unknown',
                  status: nodeData.status || 'pending',
                  progress: nodeData.progress,
                  error: nodeData.error,
                },
              });
            }
          });
        });
        
        edgesList.forEach((edge: any) => {
          flowEdges.push({
            id: edge.id || edge.edge_id || `${edge.source}-${edge.target}`,
            source: edge.source || edge.source_id,
            target: edge.target || edge.target_id,
            animated: true,
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: '#3b82f6',
            },
            style: {
              stroke: '#3b82f6',
              strokeWidth: 2,
            },
            label: edge.label,
          });
        });
        
        if (data.data_targets && data.data_targets.length > 0) {
          const targetY = (Object.keys(levels).length) * ySpacing;
          const targetsWidth = data.data_targets.length * 180;
          const startTargetX = -targetsWidth / 2 + 90;
          
          data.data_targets.forEach((target: DataTarget, index: number) => {
            const targetId = `target_${target.target_id}`;
            flowNodes.push({
              id: targetId,
              type: 'dataTarget',
              position: { x: startTargetX + index * 180, y: targetY + 50 },
              data: target,
            });
            
            const lastLevelNodes = levels[Object.keys(levels).length - 1] || [];
            lastLevelNodes.forEach(sourceId => {
              flowEdges.push({
                id: `${sourceId}-${targetId}`,
                source: sourceId,
                target: targetId,
                animated: target.status === 'synced',
                markerEnd: {
                  type: MarkerType.ArrowClosed,
                  color: '#8b5cf6',
                },
                style: {
                  stroke: '#8b5cf6',
                  strokeDasharray: '5,5',
                },
              });
            });
          });
        }
      } else if (data.nodes) {
        let yOffset = 0;
        Object.entries(data.nodes as Record<string, any>).forEach(([nodeId, nodeData]) => {
          flowNodes.push({
            id: nodeId,
            type: 'taskNode',
            position: { x: 0, y: yOffset },
            data: {
              label: nodeData.label || nodeData.name || nodeId,
              taskType: nodeData.data?.taskType || 'unknown',
              status: nodeData.data?.status || 'pending',
            },
          });
          yOffset += 100;
        });
        
        if (data.edges) {
          data.edges.forEach((edge: any) => {
            flowEdges.push({
              id: edge.id,
              source: edge.source,
              target: edge.target,
              animated: edge.animated,
              markerEnd: { type: MarkerType.ArrowClosed },
            });
          });
        }
      }
      
      setNodes(flowNodes);
      setEdges(flowEdges);
      setChainData(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [chainId, setNodes, setEdges]);

  useEffect(() => {
    fetchChainData();
    
    if (autoRefresh) {
      const interval = setInterval(fetchChainData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [fetchChainData, autoRefresh, refreshInterval]);

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (onNodeClick) {
        onNodeClick(node.id, node.data as TaskNodeData);
      }
    },
    [onNodeClick]
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        <span className="ml-2">加载任务链路...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-red-500">
        <span>错误: {error}</span>
        <Button variant="outline" className="ml-4" onClick={fetchChainData}>
          重试
        </Button>
      </div>
    );
  }

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
        defaultEdgeOptions={{
          animated: true,
        }}
      >
        <Background color="#aaa" gap={16} />
        <Controls />
      </ReactFlow>
    </div>
  );
};

export default TaskChainCanvas;
