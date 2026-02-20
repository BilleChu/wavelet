'use client';

import React, { useEffect, useState, useCallback } from 'react';
import ReactECharts from 'echarts-for-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import TaskStatusFlow from '@/components/datacenter/TaskStatusFlow';
import TaskChainCanvas from '@/components/datacenter/TaskChainCanvas';
import TaskChainDetail from '@/components/datacenter/TaskChainDetail';

interface MonitoringSummary {
  total_tasks_monitored: number;
  total_executions: number;
  total_success: number;
  total_failures: number;
  overall_success_rate: number;
  total_alerts: number;
  active_alerts: number;
  critical_alerts: number;
  metrics_count: number;
  rules_count: number;
}

interface Alert {
  alert_id: string;
  alert_type: string;
  severity: string;
  title: string;
  message: string;
  task_id: string | null;
  chain_id: string | null;
  status: string;
  created_at: string;
}

interface Chain {
  chain_id: string;
  name: string;
  status: string;
}

const severityColors: Record<string, string> = {
  info: 'bg-blue-500',
  warning: 'bg-yellow-500',
  error: 'bg-orange-500',
  critical: 'bg-red-500',
};

const severityLabels: Record<string, string> = {
  info: '信息',
  warning: '警告',
  error: '错误',
  critical: '严重',
};

export default function MonitoringPage() {
  const [summary, setSummary] = useState<MonitoringSummary | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [chains, setChains] = useState<Chain[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedChainId, setSelectedChainId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const fetchData = useCallback(async () => {
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:19100';
      const [summaryRes, alertsRes, chainsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/datacenter/monitoring/summary`),
        fetch(`${API_BASE_URL}/api/datacenter/monitoring/alerts?limit=20`),
        fetch(`${API_BASE_URL}/api/datacenter/chains`),
      ]);

      if (summaryRes.ok) {
        const data = await summaryRes.json();
        setSummary(data);
      }

      if (alertsRes.ok) {
        const data = await alertsRes.json();
        setAlerts(data.alerts || []);
      }

      if (chainsRes.ok) {
        const data = await chainsRes.json();
        setChains(data.chains || []);
      }
    } catch (error) {
      console.error('Failed to fetch monitoring data:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleResolveAlert = async (alertId: string) => {
    try {
      const response = await fetch(`/api/datacenter/monitoring/alerts/${alertId}/resolve`, {
        method: 'PUT',
      });
      if (response.ok) {
        fetchData();
      }
    } catch (error) {
      console.error('Failed to resolve alert:', error);
    }
  };

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
    fetchData();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    );
  }

  const successRateOption = {
    tooltip: {
      formatter: '{a}: {c}%',
    },
    series: [
      {
        name: '成功率',
        type: 'gauge',
        progress: {
          show: true,
          width: 18,
        },
        axisLine: {
          lineStyle: {
            width: 18,
          },
        },
        axisTick: {
          show: false,
        },
        splitLine: {
          length: 15,
          lineStyle: {
            width: 2,
            color: '#999',
          },
        },
        axisLabel: {
          distance: 25,
          color: '#999',
          fontSize: 12,
        },
        anchor: {
          show: true,
          showAbove: true,
          size: 25,
          itemStyle: {
            borderWidth: 10,
          },
        },
        title: {
          show: false,
        },
        detail: {
          valueAnimation: true,
          fontSize: 24,
          offsetCenter: [0, '70%'],
          formatter: '{value}%',
        },
        data: [
          {
            value: summary ? Math.round(summary.overall_success_rate * 100) : 0,
          },
        ],
      },
    ],
  };

  const executionTrendOption = {
    tooltip: {
      trigger: 'axis',
    },
    legend: {
      data: ['成功', '失败'],
      bottom: 0,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
    },
    yAxis: {
      type: 'value',
    },
    series: [
      {
        name: '成功',
        type: 'line',
        smooth: true,
        areaStyle: {
          opacity: 0.3,
        },
        lineStyle: {
          color: '#22c55e',
        },
        itemStyle: {
          color: '#22c55e',
        },
        data: [120, 132, 101, 134, 90, 230, 210],
      },
      {
        name: '失败',
        type: 'line',
        smooth: true,
        areaStyle: {
          opacity: 0.3,
        },
        lineStyle: {
          color: '#ef4444',
        },
        itemStyle: {
          color: '#ef4444',
        },
        data: [5, 8, 3, 6, 2, 12, 8],
      },
    ],
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">任务监控中心</h1>
          <p className="text-gray-500">实时监控任务执行状态和系统健康</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="animate-pulse">
            实时监控中
          </Badge>
          <Button variant="outline" onClick={handleRefresh}>
            刷新
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-500">监控任务</div>
              <div className="text-2xl font-bold">{summary?.total_tasks_monitored || 0}</div>
            </div>
            <div className="text-3xl">📊</div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-500">总执行次数</div>
              <div className="text-2xl font-bold">{summary?.total_executions || 0}</div>
            </div>
            <div className="text-3xl">⚡</div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-500">活跃告警</div>
              <div className="text-2xl font-bold text-red-500">
                {summary?.active_alerts || 0}
              </div>
            </div>
            <div className="text-3xl">🔔</div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-500">成功率</div>
              <div className="text-2xl font-bold text-green-500">
                {summary ? `${Math.round(summary.overall_success_rate * 100)}%` : '0%'}
              </div>
            </div>
            <div className="text-3xl">✅</div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-4">执行成功率</h3>
          <ReactECharts
            option={successRateOption}
            style={{ height: '250px' }}
            opts={{ renderer: 'canvas' }}
          />
        </Card>

        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-4">执行趋势</h3>
          <ReactECharts
            option={executionTrendOption}
            style={{ height: '250px' }}
            opts={{ renderer: 'canvas' }}
          />
        </Card>

        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-4">任务状态分布</h3>
          <TaskStatusFlow />
        </Card>
      </div>

      <Tabs defaultValue="canvas">
        <TabsList>
          <TabsTrigger value="canvas">任务链路画布</TabsTrigger>
          <TabsTrigger value="alerts">告警列表</TabsTrigger>
          <TabsTrigger value="chains">任务链路</TabsTrigger>
        </TabsList>

        <TabsContent value="canvas">
          <Card className="p-4 h-[500px]">
            <TaskChainCanvas
              key={refreshKey}
              autoRefresh={true}
              refreshInterval={5000}
              onNodeClick={(nodeId, data) => {
                console.log('Node clicked:', nodeId, data);
              }}
            />
          </Card>
        </TabsContent>

        <TabsContent value="alerts">
          <Card className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">告警列表</h3>
              <Badge variant="outline">
                共 {alerts.length} 条
              </Badge>
            </div>
            
            <ScrollArea className="h-[400px]">
              <div className="space-y-3">
                {alerts.map((alert) => (
                  <div
                    key={alert.alert_id}
                    className="flex items-start justify-between p-3 border rounded-lg hover:bg-gray-50"
                  >
                    <div className="flex items-start gap-3">
                      <Badge className={`${severityColors[alert.severity]} text-white`}>
                        {severityLabels[alert.severity] || alert.severity}
                      </Badge>
                      <div>
                        <div className="font-medium">{alert.title}</div>
                        <div className="text-sm text-gray-500">{alert.message}</div>
                        <div className="text-xs text-gray-400 mt-1">
                          {new Date(alert.created_at).toLocaleString()}
                        </div>
                      </div>
                    </div>
                    
                    {alert.status === 'active' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleResolveAlert(alert.alert_id)}
                      >
                        解决
                      </Button>
                    )}
                  </div>
                ))}
                
                {alerts.length === 0 && (
                  <div className="text-center text-gray-400 py-8">
                    暂无告警
                  </div>
                )}
              </div>
            </ScrollArea>
          </Card>
        </TabsContent>

        <TabsContent value="chains">
          <Card className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">任务链路列表</h3>
              <Button
                variant="outline"
                onClick={async () => {
                  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:19100';
                  await fetch(`${API_BASE_URL}/api/datacenter/chains/default`, { method: 'POST' });
                  fetchData();
                }}
              >
                创建默认链路
              </Button>
            </div>
            
            <ScrollArea className="h-[400px]">
              <div className="space-y-3">
                {chains.map((chain) => (
                  <div
                    key={chain.chain_id}
                    className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                    onClick={() => setSelectedChainId(chain.chain_id)}
                  >
                    <div>
                      <div className="font-medium">{chain.name}</div>
                      <div className="text-xs text-gray-400">{chain.chain_id}</div>
                    </div>
                    <Badge
                      className={`${
                        chain.status === 'completed'
                          ? 'bg-green-500'
                          : chain.status === 'running'
                          ? 'bg-blue-500'
                          : chain.status === 'failed'
                          ? 'bg-red-500'
                          : 'bg-gray-500'
                      } text-white`}
                    >
                      {chain.status}
                    </Badge>
                  </div>
                ))}
                
                {chains.length === 0 && (
                  <div className="text-center text-gray-400 py-8">
                    暂无任务链路
                  </div>
                )}
              </div>
            </ScrollArea>
          </Card>
        </TabsContent>
      </Tabs>

      {selectedChainId && (
        <Card className="p-4 border-2 border-blue-200">
          <TaskChainDetail
            chainId={selectedChainId}
            onClose={() => setSelectedChainId(null)}
          />
        </Card>
      )}
    </div>
  );
}
