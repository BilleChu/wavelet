'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface ChainNode {
  node_id: string;
  name: string;
  node_type: string;
  task_type: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  result: Record<string, any> | null;
  error: string | null;
}

interface DataTarget {
  target_id: string;
  target_type: string;
  target_name: string;
  target_location: string;
  status: string;
  records_synced: number;
}

interface ChainDetail {
  chain_id: string;
  name: string;
  description: string;
  status: string;
  nodes: Record<string, ChainNode>;
  edges: Array<{ edge_id: string; source_id: string; target_id: string; label: string }>;
  data_targets: DataTarget[];
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

interface TaskChainDetailProps {
  chainId: string;
  onClose?: () => void;
  onRetry?: (nodeId: string) => void;
}

const statusColors: Record<string, string> = {
  pending: 'bg-gray-500',
  running: 'bg-blue-500',
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

const targetIcons: Record<string, string> = {
  postgresql: '🐘',
  neo4j: '🔗',
  redis: '⚡',
  elasticsearch: '🔍',
};

const TaskChainDetail: React.FC<TaskChainDetailProps> = ({
  chainId,
  onClose,
  onRetry,
}) => {
  const [chain, setChain] = useState<ChainDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<ChainNode | null>(null);

  useEffect(() => {
    const fetchChainDetail = async () => {
      try {
        const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:19100';
        const response = await fetch(`${API_BASE_URL}/api/datacenter/chains/${chainId}`);
        if (!response.ok) {
          throw new Error('Failed to fetch chain detail');
        }
        const data = await response.json();
        setChain(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchChainDetail();
  }, [chainId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error || !chain) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-red-500">
        <span>错误: {error || '未找到链路'}</span>
        {onClose && (
          <Button variant="outline" className="mt-4" onClick={onClose}>
            关闭
          </Button>
        )}
      </div>
    );
  }

  const nodes = Object.values(chain.nodes);
  const completedNodes = nodes.filter(n => n.status === 'completed').length;
  const totalNodes = nodes.length;
  const duration = chain.started_at && chain.completed_at
    ? new Date(chain.completed_at).getTime() - new Date(chain.started_at).getTime()
    : null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">{chain.name}</h2>
          <p className="text-sm text-gray-500">{chain.description}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge className={`${statusColors[chain.status]} text-white`}>
            {statusLabels[chain.status] || chain.status}
          </Badge>
          {onClose && (
            <Button variant="ghost" size="sm" onClick={onClose}>
              ✕
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <Card className="p-3">
          <div className="text-xs text-gray-500">节点总数</div>
          <div className="text-2xl font-bold">{totalNodes}</div>
        </Card>
        <Card className="p-3">
          <div className="text-xs text-gray-500">已完成</div>
          <div className="text-2xl font-bold text-green-500">{completedNodes}</div>
        </Card>
        <Card className="p-3">
          <div className="text-xs text-gray-500">失败</div>
          <div className="text-2xl font-bold text-red-500">
            {nodes.filter(n => n.status === 'failed').length}
          </div>
        </Card>
        <Card className="p-3">
          <div className="text-xs text-gray-500">执行时长</div>
          <div className="text-2xl font-bold">
            {duration ? `${(duration / 1000).toFixed(1)}s` : '-'}
          </div>
        </Card>
      </div>

      <Progress value={(completedNodes / totalNodes) * 100} className="h-2" />

      <Tabs defaultValue="timeline">
        <TabsList>
          <TabsTrigger value="timeline">执行时间线</TabsTrigger>
          <TabsTrigger value="targets">数据分发</TabsTrigger>
          <TabsTrigger value="logs">日志</TabsTrigger>
        </TabsList>

        <TabsContent value="timeline">
          <ScrollArea className="h-64">
            <div className="relative pl-6">
              <div className="absolute left-2 top-0 bottom-0 w-0.5 bg-gray-200" />
              
              {nodes
                .sort((a, b) => {
                  if (!a.started_at) return 1;
                  if (!b.started_at) return -1;
                  return new Date(a.started_at).getTime() - new Date(b.started_at).getTime();
                })
                .map((node, index) => (
                  <div
                    key={node.node_id}
                    className="relative mb-4 cursor-pointer hover:bg-gray-50 p-2 rounded-lg"
                    onClick={() => setSelectedNode(node)}
                  >
                    <div
                      className={`absolute left-[-18px] w-4 h-4 rounded-full ${
                        statusColors[node.status]
                      }`}
                    />
                    
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-medium">{node.name}</span>
                        <span className="text-xs text-gray-400 ml-2">
                          {node.task_type}
                        </span>
                      </div>
                      <Badge className={`${statusColors[node.status]} text-white text-xs`}>
                        {statusLabels[node.status]}
                      </Badge>
                    </div>
                    
                    {node.started_at && (
                      <div className="text-xs text-gray-400 mt-1">
                        开始: {new Date(node.started_at).toLocaleString()}
                        {node.completed_at && (
                          <span className="ml-2">
                            耗时: {(
                              (new Date(node.completed_at).getTime() - 
                               new Date(node.started_at).getTime()) / 1000
                            ).toFixed(1)}s
                          </span>
                        )}
                      </div>
                    )}
                    
                    {node.error && (
                      <div className="text-xs text-red-500 mt-1 truncate">
                        错误: {node.error}
                      </div>
                    )}
                  </div>
                ))}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="targets">
          <ScrollArea className="h-64">
            <div className="grid grid-cols-2 gap-4">
              {chain.data_targets.map((target) => (
                <Card key={target.target_id} className="p-4">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">
                      {targetIcons[target.target_type] || '📦'}
                    </span>
                    <div className="flex-1">
                      <div className="font-medium">{target.target_name}</div>
                      <div className="text-xs text-gray-500">
                        {target.target_location}
                      </div>
                    </div>
                    <Badge
                      className={
                        target.status === 'synced'
                          ? 'bg-green-500 text-white'
                          : 'bg-gray-500 text-white'
                      }
                    >
                      {target.status === 'synced' ? '已同步' : '待同步'}
                    </Badge>
                  </div>
                  
                  {target.records_synced > 0 && (
                    <div className="mt-2 text-xs text-gray-500">
                      同步记录: {target.records_synced.toLocaleString()} 条
                    </div>
                  )}
                </Card>
              ))}
              
              {chain.data_targets.length === 0 && (
                <div className="col-span-2 text-center text-gray-400 py-8">
                  暂无数据分发目标
                </div>
              )}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="logs">
          <ScrollArea className="h-64">
            <div className="font-mono text-xs space-y-1">
              {nodes
                .filter(n => n.error)
                .map((node) => (
                  <div key={node.node_id} className="text-red-500">
                    [{node.node_id}] {node.error}
                  </div>
                ))}
              
              {nodes.filter(n => n.error).length === 0 && (
                <div className="text-center text-gray-400 py-8">
                  暂无错误日志
                </div>
              )}
            </div>
          </ScrollArea>
        </TabsContent>
      </Tabs>

      {selectedNode && (
        <Card className="p-4 border-2 border-blue-200">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-medium">{selectedNode.name}</h4>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedNode(null)}
            >
              ✕
            </Button>
          </div>
          
          <div className="text-sm space-y-1">
            <div>
              <span className="text-gray-500">节点ID:</span> {selectedNode.node_id}
            </div>
            <div>
              <span className="text-gray-500">任务类型:</span> {selectedNode.task_type}
            </div>
            <div>
              <span className="text-gray-500">状态:</span>{' '}
              <Badge className={`${statusColors[selectedNode.status]} text-white`}>
                {statusLabels[selectedNode.status]}
              </Badge>
            </div>
            
            {selectedNode.error && (
              <div className="text-red-500 mt-2">
                <span className="text-gray-500">错误:</span> {selectedNode.error}
              </div>
            )}
            
            {selectedNode.status === 'failed' && onRetry && (
              <Button
                variant="outline"
                size="sm"
                className="mt-2"
                onClick={() => onRetry(selectedNode.node_id)}
              >
                重试
              </Button>
            )}
          </div>
        </Card>
      )}
    </div>
  );
};

export default TaskChainDetail;
