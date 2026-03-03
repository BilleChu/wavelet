'use client'

import { useEffect, useState, useRef } from 'react'
import { Loader2, TrendingUp, TrendingDown, Database, RefreshCw, AlertCircle } from 'lucide-react'
import { Badge, Button } from '@/components/ui'

interface FactorData {
  date: string
  value: number
}

interface QuantFactorsPanelProps {
  stockCode: string
}

const FACTOR_NAMES = [
  { id: 'momentum', name: '动量因子', description: '价格动量趋势' },
  { id: 'value', name: '价值因子', description: '估值水平' },
  { id: 'quality', name: '质量因子', description: '盈利质量' },
  { id: 'volatility', name: '波动率因子', description: '价格波动' },
  { id: 'rsi', name: 'RSI因子', description: '相对强弱指标' },
]

export default function QuantFactorsPanel({ stockCode }: QuantFactorsPanelProps) {
  const [loading, setLoading] = useState(true)
  const [factors, setFactors] = useState<Record<string, FactorData[]>>({})
  const [refreshing, setRefreshing] = useState(false)
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadFactorData()
  }, [stockCode])

  const loadFactorData = async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    
    try {
      const response = await fetch(`/api/analysis/company/${stockCode}/factors`)
      const data = await response.json()
      setFactors(data.factors || {})
    } catch (error) {
      console.error('Failed to load factor data:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    if (!chartRef.current || !Object.keys(factors).length || loading) return

    const renderChart = async () => {
      const echarts = await import('echarts')
      const chart = echarts.init(chartRef.current!)

      const series: any[] = []
      const dates = new Set<string>()

      Object.entries(factors).forEach(([factorName, data]) => {
        data.forEach((d: any) => dates.add(d.date))
      })

      const sortedDates = Array.from(dates).sort()

      FACTOR_NAMES.forEach(({ id, name }) => {
        if (factors[id] && factors[id].length > 0) {
          const factorMap = new Map(
            factors[id].map((d: any) => [d.date, d.value])
          )

          series.push({
            name,
            type: 'line',
            smooth: true,
            symbol: 'none',
            data: sortedDates.map(date => factorMap.get(date) || null),
            lineStyle: { width: 2 },
            emphasis: {
              focus: 'series'
            }
          })
        }
      })

      const option = {
        backgroundColor: 'transparent',
        animation: false,
        legend: {
          data: FACTOR_NAMES.filter(f => factors[f.id]?.length > 0).map(f => f.name),
          top: 10,
          textStyle: { color: '#a1a1aa', fontSize: 11 }
        },
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          borderColor: '#333',
          textStyle: { color: '#fff' }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: sortedDates,
          boundaryGap: false,
          axisLine: { lineStyle: { color: '#333' } },
          axisLabel: { color: '#a1a1aa', fontSize: 10 },
          splitLine: { show: false }
        },
        yAxis: {
          type: 'value',
          axisLine: { lineStyle: { color: '#333' } },
          axisLabel: { color: '#a1a1aa', fontSize: 10 },
          splitLine: { lineStyle: { color: '#222' } }
        },
        series
      }

      chart.setOption(option)

      const handleResize = () => chart.resize()
      window.addEventListener('resize', handleResize)

      return () => {
        window.removeEventListener('resize', handleResize)
        chart.dispose()
      }
    }

    renderChart()
  }, [factors, loading])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
      </div>
    )
  }

  const hasData = Object.keys(factors).some(key => factors[key]?.length > 0)

  if (!hasData) {
    return (
      <div className="space-y-4">
        <div className="text-center py-12">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-violet-500/20 to-purple-500/20 flex items-center justify-center mb-4">
            <Database className="w-8 h-8 text-violet-400" />
          </div>
          <h3 className="text-lg font-medium text-white mb-2">暂无量化因子数据</h3>
          <p className="text-sm text-zinc-500 mb-6 max-w-md mx-auto">
            当前股票的量化因子数据尚未采集，您可以尝试其他股票或等待数据更新
          </p>
          
          <div className="flex items-center justify-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => loadFactorData(true)}
              disabled={refreshing}
              className="gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              {refreshing ? '刷新中...' : '刷新数据'}
            </Button>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-violet-500/5 border border-violet-500/20">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-violet-400 mt-0.5" />
            <div>
              <h4 className="text-sm font-medium text-white mb-1">关于量化因子</h4>
              <p className="text-xs text-zinc-500">
                量化因子包括动量、价值、质量、成长、波动率等维度，用于评估股票的投资价值。
                数据通常来自专业数据供应商，需要单独采集。
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {FACTOR_NAMES.map(({ id, name, description }) => (
            <div
              key={id}
              className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]"
            >
              <div className="text-xs text-zinc-500 mb-1">{name}</div>
              <div className="text-lg font-semibold text-zinc-600">-</div>
              <div className="text-[10px] text-zinc-600 mt-1">{description}</div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-zinc-500">
          数据更新时间: {new Date().toLocaleString('zh-CN')}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => loadFactorData(true)}
          disabled={refreshing}
          className="gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {FACTOR_NAMES.map(({ id, name, description }) => {
          const factorData = factors[id]
          const latestValue = factorData && factorData.length > 0 
            ? factorData[factorData.length - 1].value 
            : null
          const prevValue = factorData && factorData.length > 1 
            ? factorData[factorData.length - 2].value 
            : null
          const change = latestValue && prevValue 
            ? ((latestValue - prevValue) / Math.abs(prevValue) * 100)
            : null

          return (
            <div
              key={id}
              className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]"
            >
              <div className="text-xs text-zinc-500 mb-1">{name}</div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-semibold text-white">
                  {latestValue !== null ? latestValue.toFixed(2) : '-'}
                </span>
                {change !== null && (
                  <span className={`text-xs ${change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {change >= 0 ? '+' : ''}{change.toFixed(2)}%
                  </span>
                )}
              </div>
              <div className="text-[10px] text-zinc-600 mt-1">{description}</div>
            </div>
          )
        })}
      </div>

      <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
        <h4 className="text-sm font-medium text-white mb-3">因子趋势</h4>
        <div ref={chartRef} style={{ width: '100%', height: '300px' }} />
      </div>
    </div>
  )
}
