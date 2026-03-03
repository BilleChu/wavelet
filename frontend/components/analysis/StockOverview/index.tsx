'use client'

import React, { useEffect, useState, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { TrendingUp, TrendingDown, Minus, DollarSign, Activity, Newspaper, Wallet, PieChart, RefreshCw } from 'lucide-react'
import { Badge, Button } from '@/components/ui'

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false })

interface StockScoreData {
  code: string
  name: string
  date: string
  total_score: number
  recommendation: string
  dimensions: {
    financial: { score: number; weight: number; name: string }
    profit: { score: number; weight: number; name: string }
    cashflow: { score: number; weight: number; name: string }
    tech: { score: number; weight: number; name: string }
    sentiment: { score: number; weight: number; name: string }
  }
  details: Record<string, any>
  last_updated: string
}

interface StockScoreTrend {
  code: string
  history: Array<{
    date: string
    total: number | null
    financial: number | null
    profit: number | null
    cashflow: number | null
    tech: number | null
    sentiment: number | null
    recommendation: string | null
  }>
  events: Array<{
    id: number
    title: string
    date: string
    category: string
    importance: string
  }>
}

const RECOMMENDATION_CONFIG = {
  strong_buy: { label: '强烈推荐', color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
  buy: { label: '推荐买入', color: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/30' },
  hold: { label: '持有观望', color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' },
  sell: { label: '建议卖出', color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/30' },
  strong_sell: { label: '强烈卖出', color: 'text-rose-400', bg: 'bg-rose-500/10', border: 'border-rose-500/30' },
}

const DIMENSION_ICONS = {
  financial: DollarSign,
  profit: PieChart,
  cashflow: Wallet,
  tech: Activity,
  sentiment: Newspaper,
}

const DIMENSION_COLORS = {
  financial: '#22c55e',
  profit: '#f59e0b',
  cashflow: '#06b6d4',
  tech: '#a855f7',
  sentiment: '#ec4899',
}

export default function StockOverview({ code }: { code: string }) {
  const [score, setScore] = useState<StockScoreData | null>(null)
  const [trend, setTrend] = useState<StockScoreTrend | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const fetchData = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }

    try {
      const [scoreRes, trendRes] = await Promise.all([
        fetch(`http://localhost:8000/api/analysis/stock/${code}/score`),
        fetch(`http://localhost:8000/api/analysis/stock/${code}/score/trend?days=90`),
      ])

      if (scoreRes.ok) {
        const data = await scoreRes.json()
        setScore(data)
      }
      if (trendRes.ok) {
        const data = await trendRes.json()
        setTrend(data)
      }
    } catch (error) {
      console.error('Failed to fetch stock data:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [code])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const getScoreColor = (score: number) => {
    if (score >= 70) return '#22c55e'
    if (score >= 40) return '#f59e0b'
    return '#ef4444'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-500" />
      </div>
    )
  }

  if (!score) {
    return (
      <div className="flex items-center justify-center h-64 text-zinc-400">
        暂无评分数据
      </div>
    )
  }

  const recommendation = RECOMMENDATION_CONFIG[score.recommendation as keyof typeof RECOMMENDATION_CONFIG] ||
    { label: '中性', color: 'text-zinc-400', bg: 'bg-zinc-500/10', border: 'border-zinc-500/30' }

  const dimensions = Object.entries(score.dimensions).map(([key, value]) => ({
    key,
    ...value,
    icon: DIMENSION_ICONS[key as keyof typeof DIMENSION_ICONS] || Activity,
    color: DIMENSION_COLORS[key as keyof typeof DIMENSION_COLORS] || '#71717a',
  }))

  const trendChartOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      borderColor: '#333',
      textStyle: { color: '#fff' },
    },
    legend: {
      data: ['综合', '财务', '利润', '现金流', '技术', '情绪'],
      bottom: 0,
      textStyle: { color: '#71717a', fontSize: 10 },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: trend?.history.map(h => h.date.slice(5)) || [],
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
      axisLabel: { color: '#71717a', fontSize: 9 },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } },
      axisLabel: { color: '#71717a', fontSize: 9 },
    },
    series: [
      {
        name: '综合',
        type: 'line',
        data: trend?.history.map(h => h.total) || [],
        smooth: true,
        lineStyle: { width: 2, color: '#3b82f6' },
        itemStyle: { color: '#3b82f6' },
      },
      {
        name: '财务',
        type: 'line',
        data: trend?.history.map(h => h.financial) || [],
        smooth: true,
        lineStyle: { width: 1, type: 'dashed', color: '#22c55e' },
        itemStyle: { color: '#22c55e' },
      },
      {
        name: '利润',
        type: 'line',
        data: trend?.history.map(h => h.profit) || [],
        smooth: true,
        lineStyle: { width: 1, type: 'dashed', color: '#f59e0b' },
        itemStyle: { color: '#f59e0b' },
      },
      {
        name: '现金流',
        type: 'line',
        data: trend?.history.map(h => h.cashflow) || [],
        smooth: true,
        lineStyle: { width: 1, type: 'dashed', color: '#06b6d4' },
        itemStyle: { color: '#06b6d4' },
      },
      {
        name: '技术',
        type: 'line',
        data: trend?.history.map(h => h.tech) || [],
        smooth: true,
        lineStyle: { width: 1, type: 'dashed', color: '#a855f7' },
        itemStyle: { color: '#a855f7' },
      },
      {
        name: '情绪',
        type: 'line',
        data: trend?.history.map(h => h.sentiment) || [],
        smooth: true,
        lineStyle: { width: 1, type: 'dashed', color: '#ec4899' },
        itemStyle: { color: '#ec4899' },
      },
    ],
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">
            {score.name} <span className="text-zinc-500 text-lg">({score.code})</span>
          </h2>
          <p className="text-sm text-zinc-500 mt-1">评分日期: {score.date}</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`px-4 py-2 rounded-lg ${recommendation.bg} ${recommendation.border} border`}>
            <span className={`font-medium ${recommendation.color}`}>{recommendation.label}</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => fetchData(true)}
            disabled={refreshing}
            className="gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            刷新
          </Button>
        </div>
      </div>

      {/* Score Gauge */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
          <div className="text-center">
            <div className="relative inline-block">
              <svg className="w-40 h-40 transform -rotate-90">
                <circle
                  cx="80"
                  cy="80"
                  r="70"
                  stroke="rgba(255,255,255,0.1)"
                  strokeWidth="12"
                  fill="none"
                />
                <circle
                  cx="80"
                  cy="80"
                  r="70"
                  stroke={getScoreColor(score.total_score)}
                  strokeWidth="12"
                  fill="none"
                  strokeDasharray={`${score.total_score * 4.4} 440`}
                  strokeLinecap="round"
                  style={{ transition: 'stroke-dasharray 0.5s ease' }}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <div>
                  <div className="text-4xl font-bold" style={{ color: getScoreColor(score.total_score) }}>
                    {score.total_score.toFixed(0)}
                  </div>
                  <div className="text-zinc-500 text-sm">综合评分</div>
                </div>
              </div>
            </div>
          </div>

          {/* Dimension Bars */}
          <div className="space-y-3 mt-4">
            {dimensions.map((dim) => {
              const Icon = dim.icon
              return (
                <div key={dim.key} className="flex items-center gap-3">
                  <div className="w-6 h-6 rounded flex items-center justify-center" style={{ backgroundColor: `${dim.color}20` }}>
                    <Icon className="w-3.5 h-3.5" style={{ color: dim.color }} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-zinc-400">{dim.name}</span>
                      <span className="font-medium" style={{ color: getScoreColor(dim.score) }}>
                        {dim.score.toFixed(0)}
                      </span>
                    </div>
                    <div className="w-full bg-zinc-800 rounded-full h-1.5">
                      <div
                        className="h-1.5 rounded-full transition-all duration-500"
                        style={{ width: `${dim.score}%`, backgroundColor: dim.color }}
                      />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Trend Chart */}
        <div className="lg:col-span-2 p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
          <h3 className="text-lg font-semibold text-white mb-4">评分趋势</h3>
          <ReactECharts
            option={trendChartOption}
            style={{ height: 280 }}
            opts={{ renderer: 'canvas' }}
          />
        </div>
      </div>

      {/* Dimension Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {dimensions.map((dim) => {
          const Icon = dim.icon
          return (
            <div
              key={dim.key}
              className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05] hover:bg-white/[0.04] transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${dim.color}20` }}>
                    <Icon className="w-4 h-4" style={{ color: dim.color }} />
                  </div>
                  <span className="text-sm text-zinc-400">{dim.name}</span>
                </div>
              </div>
              <div className="text-3xl font-bold mb-2" style={{ color: getScoreColor(dim.score) }}>
                {dim.score.toFixed(0)}
              </div>
              <div className="w-full bg-zinc-800 rounded-full h-1.5">
                <div
                  className="h-1.5 rounded-full transition-all duration-500"
                  style={{ width: `${dim.score}%`, backgroundColor: dim.color }}
                />
              </div>
              <div className="text-xs text-zinc-500 mt-2">
                权重: {(dim.weight * 100).toFixed(0)}%
              </div>
            </div>
          )
        })}
      </div>

      {/* Events */}
      {trend?.events && trend.events.length > 0 && (
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
          <h3 className="text-lg font-semibold text-white mb-4">📅 相关事件</h3>
          <div className="space-y-2">
            {trend.events.slice(0, 5).map((event) => (
              <div
                key={event.id}
                className="flex items-center justify-between p-3 bg-white/[0.02] rounded-lg hover:bg-white/[0.04] cursor-pointer transition-colors"
              >
                <span className="text-sm text-zinc-300">{event.title}</span>
                <span className="text-xs text-zinc-500">{event.date}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
