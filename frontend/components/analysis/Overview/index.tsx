'use client'

import React, { useEffect, useState, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { TrendingUp, TrendingDown, Minus, Globe, Building2, Factory, BarChart3, RefreshCw, ChevronRight, Sparkles } from 'lucide-react'
import { Badge, Button } from '@/components/ui'
import ScoreTimelineChart from './ScoreTimelineChart'
import EconomicCalendarPanel from './EconomicCalendarPanel'

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false })

interface DimensionScore {
  score: number
  trend: string
  change: number
  key_indicators: Array<{
    name: string
    value: string
    impact?: string
  }>
}

interface OverviewData {
  date: string
  total: number
  dimensions: {
    global_macro: DimensionScore
    china_macro: DimensionScore
    market: DimensionScore
    industry: DimensionScore
    stock: DimensionScore
  }
  last_updated: string
}

interface TrendData {
  dimension: string
  scores: Array<{
    date: string
    score: number | null
    total: number | null
  }>
  events: Array<{
    id: number
    title: string
    date: string
    category: string
    importance: string
    impact_direction?: string
  }>
  statistics: {
    current: number | null
    high: number | null
    low: number | null
    avg: number | null
  }
}

const DIMENSION_CONFIG = {
  global_macro: {
    name: '全球宏观',
    icon: Globe,
    color: '#3b82f6',
    gradient: 'from-blue-500 to-cyan-500',
    description: '美联储政策、全球经济、风险偏好',
  },
  china_macro: {
    name: '中国宏观',
    icon: Building2,
    color: '#22c55e',
    gradient: 'from-green-500 to-emerald-500',
    description: 'GDP、CPI、PMI、货币政策',
  },
  market: {
    name: '股市大盘',
    icon: BarChart3,
    color: '#a855f7',
    gradient: 'from-purple-500 to-violet-500',
    description: '指数趋势、成交量、市场情绪',
  },
  industry: {
    name: '行业情况',
    icon: Factory,
    color: '#f59e0b',
    gradient: 'from-amber-500 to-orange-500',
    description: '板块轮动、资金流向、估值水平',
  },
  stock: {
    name: '个股情况',
    icon: TrendingUp,
    color: '#ec4899',
    gradient: 'from-pink-500 to-rose-500',
    description: '财务健康、技术面、情绪面',
  },
}

export default function MarketOverview() {
  const [overview, setOverview] = useState<OverviewData | null>(null)
  const [trend, setTrend] = useState<TrendData | null>(null)
  const [selectedDimension, setSelectedDimension] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const fetchOverview = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    
    try {
      const res = await fetch('http://localhost:8000/api/analysis/overview')
      if (res.ok) {
        const data = await res.json()
        setOverview(data)
      }
    } catch (error) {
      console.error('Failed to fetch overview:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  const fetchTrend = useCallback(async (dimension: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/analysis/overview/trend?dimension=${dimension}&days=30`)
      if (res.ok) {
        const data = await res.json()
        setTrend(data)
      }
    } catch (error) {
      console.error('Failed to fetch trend:', error)
    }
  }, [])

  useEffect(() => {
    fetchOverview()
  }, [fetchOverview])

  useEffect(() => {
    if (selectedDimension) {
      fetchTrend(selectedDimension)
    }
  }, [selectedDimension, fetchTrend])

  const getScoreColor = (score: number) => {
    if (score >= 70) return '#22c55e'
    if (score >= 40) return '#f59e0b'
    return '#ef4444'
  }

  const getTrendIcon = (trend: string) => {
    if (trend === 'up') return <TrendingUp className="w-4 h-4 text-emerald-400" />
    if (trend === 'down') return <TrendingDown className="w-4 h-4 text-rose-400" />
    return <Minus className="w-4 h-4 text-zinc-500" />
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500" />
      </div>
    )
  }

  if (!overview) {
    return (
      <div className="flex items-center justify-center h-96 text-zinc-400">
        暂无数据
      </div>
    )
  }

  const radarOption = {
    backgroundColor: 'transparent',
    radar: {
      indicator: Object.entries(overview.dimensions).map(([key, value]) => ({
        name: DIMENSION_CONFIG[key as keyof typeof DIMENSION_CONFIG]?.name || key,
        max: 100,
      })),
      axisName: {
        color: '#a1a1aa',
        fontSize: 11,
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(59, 130, 246, 0.02)', 'rgba(59, 130, 246, 0.05)'],
        },
      },
      axisLine: {
        lineStyle: { color: 'rgba(255, 255, 255, 0.1)' },
      },
      splitLine: {
        lineStyle: { color: 'rgba(255, 255, 255, 0.1)' },
      },
    },
    series: [{
      type: 'radar',
      data: [{
        value: Object.values(overview.dimensions).map(d => d.score),
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          width: 2,
          color: '#3b82f6',
        },
        areaStyle: {
          color: 'rgba(59, 130, 246, 0.3)',
        },
        itemStyle: {
          color: '#3b82f6',
        },
      }],
    }],
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Wavelet 市场概览</h2>
          <p className="text-sm text-zinc-500 mt-1">
            金融市场小波变换 · 多维度综合评分 · {overview.date}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-sm text-zinc-500">综合评分</div>
            <div className="text-3xl font-bold" style={{ color: getScoreColor(overview.total) }}>
              {overview.total.toFixed(0)}
              <span className="text-lg text-zinc-400 ml-1">分</span>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => fetchOverview(true)}
            disabled={refreshing}
            className="gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </div>

      {/* Score Timeline Chart with Events */}
      <ScoreTimelineChart height={280} />

      {/* Economic Calendar Panel */}
      <EconomicCalendarPanel />

      {/* Dimension Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {Object.entries(overview.dimensions).map(([key, value]) => {
          const config = DIMENSION_CONFIG[key as keyof typeof DIMENSION_CONFIG]
          const Icon = config?.icon || BarChart3
          const isSelected = selectedDimension === key

          return (
            <div
              key={key}
              onClick={() => setSelectedDimension(isSelected ? null : key)}
              className={`
                p-4 rounded-xl cursor-pointer transition-all duration-300
                border hover:shadow-lg
                ${isSelected
                  ? 'bg-white/[0.05] border-cyan-500/50 shadow-cyan-500/10'
                  : 'bg-white/[0.02] border-white/[0.05] hover:bg-white/[0.04]'
                }
              `}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${config?.gradient || 'from-gray-500 to-gray-600'} flex items-center justify-center`}>
                    <Icon className="w-4 h-4 text-white" />
                  </div>
                  <span className="text-sm text-zinc-300">{config?.name}</span>
                </div>
                {getTrendIcon(value.trend)}
              </div>

              <div className="flex items-end justify-between mb-2">
                <span
                  className="text-3xl font-bold"
                  style={{ color: getScoreColor(value.score) }}
                >
                  {value.score.toFixed(0)}
                </span>
                {value.change !== 0 && (
                  <span className={`text-sm ${value.change > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {value.change > 0 ? '+' : ''}{value.change.toFixed(1)}
                  </span>
                )}
              </div>

              <div className="w-full bg-zinc-800 rounded-full h-1.5 mb-3">
                <div
                  className="h-1.5 rounded-full transition-all duration-500"
                  style={{
                    width: `${value.score}%`,
                    backgroundColor: getScoreColor(value.score),
                  }}
                />
              </div>

              {value.key_indicators && value.key_indicators.length > 0 && (
                <div className="space-y-1 pt-2 border-t border-white/[0.05]">
                  {value.key_indicators.slice(0, 2).map((ind, idx) => (
                    <div key={idx} className="flex items-center justify-between text-xs">
                      <span className="text-zinc-500">{ind.name}</span>
                      <span className={`font-medium ${
                        ind.impact === 'positive' ? 'text-emerald-400' :
                        ind.impact === 'negative' ? 'text-rose-400' : 'text-zinc-300'
                      }`}>
                        {ind.value}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {isSelected && (
                <div className="mt-3 pt-3 border-t border-white/[0.05]">
                  <span className="text-xs text-cyan-400 flex items-center gap-1">
                    查看详情 <ChevronRight className="w-3 h-3" />
                  </span>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Detail Panel */}
      {selectedDimension && trend && (
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05] animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${DIMENSION_CONFIG[selectedDimension as keyof typeof DIMENSION_CONFIG]?.gradient} flex items-center justify-center`}>
                {React.createElement(DIMENSION_CONFIG[selectedDimension as keyof typeof DIMENSION_CONFIG]?.icon || BarChart3, { className: 'w-5 h-5 text-white' })}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">
                  {DIMENSION_CONFIG[selectedDimension as keyof typeof DIMENSION_CONFIG]?.name}详情
                </h3>
                <p className="text-xs text-zinc-500">
                  {DIMENSION_CONFIG[selectedDimension as keyof typeof DIMENSION_CONFIG]?.description}
                </p>
              </div>
            </div>
            {trend.statistics && (
              <div className="flex items-center gap-4 text-sm">
                <span className="text-zinc-500">
                  最高: <span className="text-emerald-400">{trend.statistics.high?.toFixed(1)}</span>
                </span>
                <span className="text-zinc-500">
                  最低: <span className="text-rose-400">{trend.statistics.low?.toFixed(1)}</span>
                </span>
                <span className="text-zinc-500">
                  均值: <span className="text-cyan-400">{trend.statistics.avg?.toFixed(1)}</span>
                </span>
              </div>
            )}
          </div>

          {/* Trend Chart */}
          <div className="h-64 mb-4">
            <ReactECharts
              option={{
                backgroundColor: 'transparent',
                tooltip: {
                  trigger: 'axis',
                  backgroundColor: 'rgba(0, 0, 0, 0.8)',
                  borderColor: '#333',
                  textStyle: { color: '#fff' },
                },
                grid: {
                  left: '3%',
                  right: '4%',
                  bottom: '3%',
                  top: '10%',
                  containLabel: true,
                },
                xAxis: {
                  type: 'category',
                  data: trend.scores.map(s => s.date.slice(5)),
                  axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
                  axisLabel: { color: '#71717a', fontSize: 10 },
                },
                yAxis: {
                  type: 'value',
                  min: 0,
                  max: 100,
                  axisLine: { show: false },
                  splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
                  axisLabel: { color: '#71717a', fontSize: 10 },
                },
                series: [{
                  type: 'line',
                  data: trend.scores.map(s => s.score ?? s.total),
                  smooth: true,
                  symbol: 'circle',
                  symbolSize: 6,
                  lineStyle: {
                    width: 2,
                    color: DIMENSION_CONFIG[selectedDimension as keyof typeof DIMENSION_CONFIG]?.color || '#3b82f6',
                  },
                  areaStyle: {
                    color: {
                      type: 'linear',
                      x: 0, y: 0, x2: 0, y2: 1,
                      colorStops: [
                        { offset: 0, color: `${DIMENSION_CONFIG[selectedDimension as keyof typeof DIMENSION_CONFIG]?.color || '#3b82f6'}40` },
                        { offset: 1, color: `${DIMENSION_CONFIG[selectedDimension as keyof typeof DIMENSION_CONFIG]?.color || '#3b82f6'}05` },
                      ],
                    },
                  },
                  itemStyle: {
                    color: DIMENSION_CONFIG[selectedDimension as keyof typeof DIMENSION_CONFIG]?.color || '#3b82f6',
                  },
                }],
              }}
              style={{ height: '100%' }}
              opts={{ renderer: 'canvas' }}
            />
          </div>

          {/* Events */}
          {trend.events && trend.events.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-zinc-400 mb-2">相关事件</h4>
              <div className="space-y-2">
                {trend.events.slice(0, 3).map((event) => (
                  <div
                    key={event.id}
                    className="flex items-center justify-between p-3 bg-white/[0.02] rounded-lg hover:bg-white/[0.04] cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${
                        event.impact_direction === 'positive' ? 'bg-emerald-400' :
                        event.impact_direction === 'negative' ? 'bg-rose-400' : 'bg-amber-400'
                      }`} />
                      <span className="text-sm text-zinc-300">{event.title}</span>
                    </div>
                    <span className="text-xs text-zinc-500">{event.date}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Radar Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
          <h3 className="text-lg font-semibold text-white mb-4">评分雷达图</h3>
          <ReactECharts
            option={radarOption}
            style={{ height: 280 }}
            opts={{ renderer: 'canvas' }}
          />
        </div>

        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-5 h-5 text-cyan-400" />
            <h3 className="text-lg font-semibold text-white">评分说明</h3>
          </div>
          <div className="space-y-3 text-sm text-zinc-400">
            <p>
              Wavelet评分系统基于多维度数据分析，为投资者提供市场全景视角。
              评分范围0-100分，分数越高表示该维度越乐观。
            </p>
            <div className="grid grid-cols-3 gap-2 pt-2">
              <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                <div className="text-emerald-400 font-medium">70-100分</div>
                <div className="text-xs text-zinc-500">偏强区域</div>
              </div>
              <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
                <div className="text-amber-400 font-medium">40-70分</div>
                <div className="text-xs text-zinc-500">震荡区域</div>
              </div>
              <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20">
                <div className="text-rose-400 font-medium">0-40分</div>
                <div className="text-xs text-zinc-500">偏弱区域</div>
              </div>
            </div>
            <p className="text-xs text-zinc-500 pt-2">
              * 评分仅供参考，不构成投资建议。投资有风险，入市需谨慎。
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
