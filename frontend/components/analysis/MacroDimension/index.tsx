'use client'

import { useEffect, useState, useRef } from 'react'
import { TrendingUp, TrendingDown, Minus, Loader2, Activity, DollarSign, BarChart3, PieChart, RefreshCw } from 'lucide-react'
import { Badge, Button } from '@/components/ui'

interface MacroIndicator {
  indicator_code: string
  indicator_name: string
  value: number
  unit: string
  period: string
  country: string
  yoy_change: number | null
  mom_change: number | null
  trend: string
}

const DEFAULT_INDICATORS = ['GDP', 'CPI', 'PMI', 'M2', 'PPI', 'UNEMPLOYMENT']

const INDICATOR_CATEGORIES = {
  '经济增长': ['GDP', 'PMI', '工业增加值'],
  '物价水平': ['CPI', 'PPI', '核心CPI'],
  '货币金融': ['M2', 'M1', '社会融资规模'],
  '就业市场': ['失业率', '新增就业'],
}

export default function MacroDimension() {
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [indicators, setIndicators] = useState<MacroIndicator[]>([])
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadMacroData()
  }, [])

  const loadMacroData = async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    
    try {
      const response = await fetch(`/api/analysis/macro/indicators?indicator_codes=${DEFAULT_INDICATORS.join(',')}`)
      const data = await response.json()
      setIndicators(data.indicators || [])
    } catch (error) {
      console.error('Failed to load macro data:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    if (!chartRef.current || !indicators.length || loading) return

    const renderChart = async () => {
      const echarts = await import('echarts')
      const chart = echarts.init(chartRef.current!)

      const categories = Object.keys(INDICATOR_CATEGORIES)
      const seriesData = categories.map(category => {
        const categoryIndicators = INDICATOR_CATEGORIES[category as keyof typeof INDICATOR_CATEGORIES]
        const matchingIndicators = indicators.filter(ind => 
          categoryIndicators.some(ci => ind.indicator_name.includes(ci) || ind.indicator_code.includes(ci))
        )
        return {
          name: category,
          value: matchingIndicators.length
        }
      })

      const option = {
        backgroundColor: 'transparent',
        animation: false,
        tooltip: {
          trigger: 'item',
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          borderColor: '#333',
          textStyle: { color: '#fff' }
        },
        legend: {
          orient: 'vertical',
          right: '5%',
          top: 'center',
          textStyle: { color: '#a1a1aa', fontSize: 11 }
        },
        series: [
          {
            name: '指标分类',
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['40%', '50%'],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 10,
              borderColor: '#111',
              borderWidth: 2
            },
            label: {
              show: false,
              position: 'center'
            },
            emphasis: {
              label: {
                show: true,
                fontSize: 14,
                fontWeight: 'bold',
                color: '#fff'
              }
            },
            labelLine: {
              show: false
            },
            data: seriesData
          }
        ]
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
  }, [indicators, loading])

  const getTrendIcon = (trend: string) => {
    if (trend === 'up') return <TrendingUp className="w-4 h-4 text-emerald-400" />
    if (trend === 'down') return <TrendingDown className="w-4 h-4 text-rose-400" />
    return <Minus className="w-4 h-4 text-zinc-500" />
  }

  const formatValue = (value: number, unit: string) => {
    if (unit === '%') return `${value.toFixed(2)}%`
    if (unit === '万亿元') return `${value.toFixed(2)}万亿`
    if (unit === '亿元') return `${value.toFixed(2)}亿`
    return value.toLocaleString()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">宏观经济概览</h2>
          <p className="text-sm text-zinc-500 mt-1">
            实时追踪GDP、CPI、PMI等核心宏观经济指标，把握经济走势
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => loadMacroData(true)}
          disabled={refreshing}
          className="gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          {refreshing ? '刷新中...' : '刷新数据'}
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {indicators.map((indicator) => (
          <div
            key={indicator.indicator_code}
            className="p-5 rounded-2xl bg-gradient-to-br from-cyan-500/5 to-blue-500/5 border border-cyan-500/20 hover:border-cyan-500/40 transition-all"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                {getTrendIcon(indicator.trend)}
                <span className="text-sm text-white font-medium">{indicator.indicator_name}</span>
              </div>
              <Badge variant="secondary" size="sm">{indicator.period}</Badge>
            </div>
            
            <div className="mb-3">
              <span className="text-3xl font-bold text-white">
                {formatValue(indicator.value, indicator.unit)}
              </span>
              <span className="text-sm text-zinc-500 ml-2">{indicator.unit}</span>
            </div>
            
            <div className="flex items-center gap-4 text-xs">
              {indicator.yoy_change !== null && (
                <div>
                  <span className="text-zinc-500">同比: </span>
                  <span className={indicator.yoy_change >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                    {indicator.yoy_change >= 0 ? '+' : ''}{indicator.yoy_change.toFixed(2)}%
                  </span>
                </div>
              )}
              {indicator.mom_change !== null && (
                <div>
                  <span className="text-zinc-500">环比: </span>
                  <span className={indicator.mom_change >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                    {indicator.mom_change >= 0 ? '+' : ''}{indicator.mom_change.toFixed(2)}%
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-cyan-400" />
            <h4 className="text-base font-semibold text-white">经济增长</h4>
          </div>
          <div className="space-y-3">
            {indicators.filter(i => ['GDP', 'PMI'].includes(i.indicator_code)).map((ind) => (
              <div key={ind.indicator_code} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02]">
                <span className="text-sm text-zinc-400">{ind.indicator_name}</span>
                <span className="text-sm font-medium text-white">{formatValue(ind.value, ind.unit)}</span>
              </div>
            ))}
            {indicators.filter(i => ['GDP', 'PMI'].includes(i.indicator_code)).length === 0 && (
              <div className="text-center py-8 text-zinc-500 text-sm">
                暂无经济增长数据
              </div>
            )}
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
          <div className="flex items-center gap-2 mb-4">
            <DollarSign className="w-5 h-5 text-cyan-400" />
            <h4 className="text-base font-semibold text-white">物价水平</h4>
          </div>
          <div className="space-y-3">
            {indicators.filter(i => ['CPI', 'PPI'].includes(i.indicator_code)).map((ind) => (
              <div key={ind.indicator_code} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02]">
                <span className="text-sm text-zinc-400">{ind.indicator_name}</span>
                <span className="text-sm font-medium text-white">{formatValue(ind.value, ind.unit)}</span>
              </div>
            ))}
            {indicators.filter(i => ['CPI', 'PPI'].includes(i.indicator_code)).length === 0 && (
              <div className="text-center py-8 text-zinc-500 text-sm">
                暂无物价水平数据
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
        <div className="flex items-center gap-2 mb-4">
          <PieChart className="w-5 h-5 text-cyan-400" />
          <h4 className="text-base font-semibold text-white">指标分类</h4>
        </div>
        <div ref={chartRef} style={{ width: '100%', height: '280px' }} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { icon: BarChart3, title: '数据来源', description: '国家统计局、央行等官方数据', color: '#06b6d4' },
          { icon: Activity, title: '更新频率', description: '月度/季度更新', color: '#f59e0b' },
          { icon: DollarSign, title: '数据质量', description: '权威可靠，实时同步', color: '#8b5cf6' },
        ].map((item) => {
          const Icon = item.icon
          return (
            <div
              key={item.title}
              className="flex items-center gap-4 p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]"
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ backgroundColor: `${item.color}15` }}
              >
                <Icon className="w-5 h-5" style={{ color: item.color }} />
              </div>
              <div>
                <h4 className="text-sm font-medium text-white">{item.title}</h4>
                <p className="text-xs text-zinc-500">{item.description}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
