'use client'

import React, { useEffect, useState, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { TrendingUp, TrendingDown, Minus, BarChart3, DollarSign } from 'lucide-react'

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false })

interface FinancialHealthCardProps {
  code: string
}

interface FinancialData {
  report_date: string
  revenue: number
  net_profit: number
  gross_margin: number
  net_margin: number
  roe: number
  roa: number
  debt_ratio: number
  current_ratio: number
  yoy_revenue_growth: number
  yoy_profit_growth: number
}

export default function FinancialHealthCard({ code }: FinancialHealthCardProps) {
  const [data, setData] = useState<FinancialData[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/analysis/company/${code}/financial?years=5`)
      if (res.ok) {
        const json = await res.json()
        setData(json.data || [])
      }
    } catch (error) {
      console.error('Failed to fetch financial data:', error)
    } finally {
      setLoading(false)
    }
  }, [code])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  if (loading) {
    return (
      <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-zinc-800 rounded w-1/4" />
          <div className="h-32 bg-zinc-800/50 rounded" />
        </div>
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
        <p className="text-zinc-500 text-center py-8">暂无财务数据</p>
      </div>
    )
  }

  const latest = data[0]
  const previous = data[1]

  const getChange = (current: number, prev: number) => {
    if (!prev) return 0
    return ((current - prev) / Math.abs(prev)) * 100
  }

  const getTrendIcon = (change: number) => {
    if (change > 5) return <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
    if (change < -5) return <TrendingDown className="w-3.5 h-3.5 text-rose-400" />
    return <Minus className="w-3.5 h-3.5 text-zinc-500" />
  }

  const getScoreColor = (value: number, benchmark: number, higherBetter: boolean) => {
    const isGood = higherBetter ? value >= benchmark : value <= benchmark
    return isGood ? 'text-emerald-400' : 'text-rose-400'
  }

  const indicators = [
    { name: 'ROE', value: latest.roe, unit: '%', change: previous ? getChange(latest.roe, previous.roe) : 0, benchmark: 15, higherBetter: true },
    { name: '毛利率', value: latest.gross_margin, unit: '%', change: previous ? getChange(latest.gross_margin, previous.gross_margin) : 0, benchmark: 30, higherBetter: true },
    { name: '净利率', value: latest.net_margin, unit: '%', change: previous ? getChange(latest.net_margin, previous.net_margin) : 0, benchmark: 10, higherBetter: true },
    { name: '负债率', value: latest.debt_ratio, unit: '%', change: previous ? getChange(latest.debt_ratio, previous.debt_ratio) : 0, benchmark: 60, higherBetter: false },
    { name: '流动比率', value: latest.current_ratio, unit: '', change: previous ? getChange(latest.current_ratio, previous.current_ratio) : 0, benchmark: 1.5, higherBetter: true },
    { name: '营收增长', value: latest.yoy_revenue_growth, unit: '%', change: 0, benchmark: 10, higherBetter: true },
  ]

  const chartOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(0, 0, 0, 0.8)', borderColor: '#333', textStyle: { color: '#fff' } },
    legend: { data: ['ROE', '毛利率', '净利率'], bottom: 0, textStyle: { color: '#71717a', fontSize: 10 } },
    grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: data.slice().reverse().map(d => d.report_date?.slice(0, 7) || ''), axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }, axisLabel: { color: '#71717a', fontSize: 9 } },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%', color: '#71717a', fontSize: 9 }, splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.05)' } }, axisLine: { show: false } },
    series: [
      { name: 'ROE', type: 'line', data: data.slice().reverse().map(d => d.roe), smooth: true, lineStyle: { width: 2, color: '#3b82f6' }, itemStyle: { color: '#3b82f6' } },
      { name: '毛利率', type: 'line', data: data.slice().reverse().map(d => d.gross_margin), smooth: true, lineStyle: { width: 2, color: '#22c55e' }, itemStyle: { color: '#22c55e' } },
      { name: '净利率', type: 'line', data: data.slice().reverse().map(d => d.net_margin), smooth: true, lineStyle: { width: 2, color: '#f59e0b' }, itemStyle: { color: '#f59e0b' } },
    ],
  }

  return (
    <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
            <DollarSign className="w-4 h-4 text-emerald-400" />
          </div>
          财务健康度
        </h3>
        <span className="text-xs text-zinc-500">报告期: {latest.report_date}</span>
      </div>

      <div className="grid grid-cols-3 md:grid-cols-6 gap-3 mb-6">
        {indicators.map((ind) => (
          <div key={ind.name} className="text-center p-2 rounded-lg bg-white/[0.02]">
            <div className="text-xs text-zinc-500 mb-1">{ind.name}</div>
            <div className={`text-lg font-bold ${getScoreColor(ind.value || 0, ind.benchmark, ind.higherBetter)}`}>
              {(ind.value || 0).toFixed(1)}{ind.unit}
            </div>
            <div className="flex items-center justify-center gap-1 text-xs mt-1">
              {getTrendIcon(ind.change)}
              <span className={ind.change > 0 ? 'text-emerald-400' : ind.change < 0 ? 'text-rose-400' : 'text-zinc-500'}>
                {ind.change > 0 ? '+' : ''}{ind.change.toFixed(1)}%
              </span>
            </div>
          </div>
        ))}
      </div>

      <ReactECharts option={chartOption} style={{ height: 180 }} opts={{ renderer: 'canvas' }} />
    </div>
  )
}
