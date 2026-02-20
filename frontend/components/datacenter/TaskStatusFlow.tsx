'use client';

import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';

interface TaskStatusData {
  pending: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  paused: number;
}

interface StatusFlowProps {
  data?: TaskStatusData;
  autoRefresh?: boolean;
  refreshInterval?: number;
  onStatusClick?: (status: string) => void;
}

const statusConfig: Record<string, { label: string; color: string; bgColor: string }> = {
  pending: { label: '待执行', color: '#6b7280', bgColor: 'bg-gray-500' },
  running: { label: '执行中', color: '#3b82f6', bgColor: 'bg-blue-500' },
  completed: { label: '已完成', color: '#22c55e', bgColor: 'bg-green-500' },
  failed: { label: '失败', color: '#ef4444', bgColor: 'bg-red-500' },
  cancelled: { label: '已取消', color: '#f59e0b', bgColor: 'bg-yellow-500' },
  paused: { label: '已暂停', color: '#f97316', bgColor: 'bg-orange-500' },
};

const TaskStatusFlow: React.FC<StatusFlowProps> = ({
  data,
  autoRefresh = true,
  refreshInterval = 10000,
  onStatusClick,
}) => {
  const [statusData, setStatusData] = useState<TaskStatusData>(
    data || { pending: 0, running: 0, completed: 0, failed: 0, cancelled: 0, paused: 0 }
  );
  const [loading, setLoading] = useState(true);

  const fetchStatusData = async () => {
    try {
      const response = await fetch('/api/datacenter/monitoring/summary');
      if (response.ok) {
        const result = await response.json();
        setStatusData({
          pending: result.pending_tasks || 0,
          running: result.running_tasks || 0,
          completed: result.total_success || 0,
          failed: result.total_failures || 0,
          cancelled: 0,
          paused: 0,
        });
      }
    } catch (error) {
      console.error('Failed to fetch status data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (data) {
      setStatusData(data);
      setLoading(false);
    } else {
      fetchStatusData();
    }

    if (autoRefresh && !data) {
      const interval = setInterval(fetchStatusData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [data, autoRefresh, refreshInterval]);

  const total = Object.values(statusData).reduce((a, b) => a + b, 0);

  const pieOption = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: {
        fontSize: 12,
      },
    },
    series: [
      {
        name: '任务状态',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['40%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: false,
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold',
          },
        },
        labelLine: {
          show: false,
        },
        data: Object.entries(statusConfig).map(([key, config]) => ({
          value: statusData[key as keyof TaskStatusData] || 0,
          name: config.label,
          itemStyle: { color: config.color },
        })),
      },
    ],
  };

  const flowStates = [
    { key: 'pending', icon: '⏳', arrow: true },
    { key: 'running', icon: '▶️', arrow: true },
    { key: 'completed', icon: '✅', arrow: false },
  ];

  const errorStates = [
    { key: 'failed', icon: '❌' },
    { key: 'cancelled', icon: '⚠️' },
    { key: 'paused', icon: '⏸️' },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">任务状态流转</h3>
        <Badge variant="outline">总计: {total}</Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="p-4">
          <div className="text-sm text-gray-500 mb-2">状态分布</div>
          <ReactECharts
            option={pieOption}
            style={{ height: '200px' }}
            opts={{ renderer: 'canvas' }}
          />
        </Card>

        <Card className="p-4">
          <div className="text-sm text-gray-500 mb-4">状态流转图</div>
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              {flowStates.map((state, index) => {
                const config = statusConfig[state.key];
                const count = statusData[state.key as keyof TaskStatusData] || 0;
                
                return (
                  <React.Fragment key={state.key}>
                    <button
                      className="flex flex-col items-center p-3 rounded-lg border-2 transition-all hover:shadow-md cursor-pointer"
                      style={{ borderColor: config.color }}
                      onClick={() => onStatusClick?.(state.key)}
                    >
                      <span className="text-2xl">{state.icon}</span>
                      <span className="text-sm font-medium mt-1">{config.label}</span>
                      <Badge className={`${config.bgColor} text-white mt-1`}>
                        {count}
                      </Badge>
                    </button>
                    {state.arrow && index < flowStates.length - 1 && (
                      <div className="flex-1 flex items-center justify-center">
                        <svg width="40" height="20" viewBox="0 0 40 20">
                          <path
                            d="M0 10 L30 10 M25 5 L30 10 L25 15"
                            stroke="#9ca3af"
                            strokeWidth="2"
                            fill="none"
                          />
                        </svg>
                      </div>
                    )}
                  </React.Fragment>
                );
              })}
            </div>

            <div className="border-t pt-4">
              <div className="text-xs text-gray-400 mb-2">异常状态</div>
              <div className="flex gap-2">
                {errorStates.map((state) => {
                  const config = statusConfig[state.key];
                  const count = statusData[state.key as keyof TaskStatusData] || 0;
                  
                  return (
                    <button
                      key={state.key}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg border transition-all hover:shadow-sm cursor-pointer"
                      style={{ borderColor: config.color }}
                      onClick={() => onStatusClick?.(state.key)}
                    >
                      <span>{state.icon}</span>
                      <span className="text-sm">{config.label}</span>
                      <Badge className={`${config.bgColor} text-white`}>
                        {count}
                      </Badge>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </Card>
      </div>

      <Card className="p-4">
        <div className="text-sm text-gray-500 mb-2">执行进度</div>
        {total > 0 ? (
          <div className="space-y-2">
            <Progress 
              value={(statusData.completed / total) * 100} 
              className="h-3"
            />
            <div className="flex justify-between text-xs text-gray-500">
              <span>已完成: {statusData.completed}</span>
              <span>成功率: {((statusData.completed / total) * 100).toFixed(1)}%</span>
            </div>
          </div>
        ) : (
          <div className="text-center text-gray-400 py-4">暂无任务数据</div>
        )}
      </Card>
    </div>
  );
};

export default TaskStatusFlow;
