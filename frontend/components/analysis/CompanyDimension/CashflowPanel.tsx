'use client'

import { useEffect, useState, useRef } from 'react'
import { Loader2, TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import { Badge } from '@/components/ui'

interface CashFlowData {
  report_date: string
  operating_cash_flow: number | null
  investing_cash_flow: number | null
  financing_cash_flow: number | null
  free_cash_flow: number | null
}

interface CashflowPanelProps {
  stockCode: string
}

export default function CashflowPanel({ stockCode }: CashflowPanelProps) {
  const [loading, setLoading] = useState(true)
  const [cashflowData, setCashflowData] = useState<CashFlowData[]>([])
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadCashflowData()
  }, [stockCode])

  const loadCashflowData = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/analysis/company/${stockCode}/cashflow?years=3`)
      const data = await response.json()
      setCashflowData(data.data || [])
    } catch (error) {
      console.error('Failed to load cashflow data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!chartRef.current || !cashflowData.length || loading) return

    const renderChart = async () => {
      const echarts = await import('echarts')
      const chart = echarts.init(chartRef.current!)

      const dates = cashflowData.map(d => d.report_date).reverse()

      const option = {
        backgroundColor: 'transparent',
        animation: false,
        legend: {
          data: ['经营现金流', '投资现金流', '筹资现金流', '自由现金流'],
          top: 10,
          textStyle: { color: '#a1a1aa', fontSize: 11 }
        },
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          borderColor: '#333',
          textStyle: { color: '#fff' },
          formatter: function (params: any) {
            let result = `<div style="font-weight: bold; margin-bottom: 8px;">${params[0].axisValue}</div>`
            params.forEach((item: any) => {
              const value = item.value / 1e8
              result += `
                <div style="display: flex; justify-content: space-between; gap: 20px; margin: 4px 0;">
                  <span>${item.marker} ${item.seriesName}</span>
                  <span style="font-weight: bold;">${value.toFixed(2)}亿</span>
                </div>
              `
            })
            return result
          }
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
          data: dates,
          axisLine: { lineStyle: { color: '#333' } },
          axisLabel: { color: '#a1a1aa', fontSize: 10 },
          splitLine: { show: false }
        },
        yAxis: {
          type: 'value',
          axisLine: { lineStyle: { color: '#333' } },
          axisLabel: { 
            color: '#a1a1aa', 
            fontSize: 10,
            formatter: (value: number) => `${(value / 1e8).toFixed(0)}亿`
          },
          splitLine: { lineStyle: { color: '#222' } }
        },
        series: [
          {
            name: '经营现金流',
            type: 'bar',
            stack: 'total',
            data: cashflowData.map(d => d.operating_cash_flow).reverse(),
            itemStyle: { color: '#10b981' }
          },
          {
            name: '投资现金流',
            type: 'bar',
            stack: 'total',
            data: cashflowData.map(d => d.investing_cash_flow).reverse(),
            itemStyle: { color: '#f59e0b' }
          },
          {
            name: '筹资现金流',
            type: 'bar',
            stack: 'total',
            data: cashflowData.map(d => d.financing_cash_flow).reverse(),
            itemStyle: { color: '#8b5cf6' }
          },
          {
            name: '自由现金流',
            type: 'line',
            smooth: true,
            symbol: 'circle',
            symbolSize: 6,
            data: cashflowData.map(d => d.free_cash_flow).reverse(),
            lineStyle: { color: '#06b6d4', width: 2 },
            itemStyle: { color: '#06b6d4' }
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
  }, [cashflowData, loading])

  const formatNumber = (num: number | null) => {
    if (num === null || num === undefined) return '-'
    if (num >= 1e12) return `${(num / 1e12).toFixed(2)}万亿`
    if (num >= 1e8) return `${(num / 1e8).toFixed(2)}亿`
    if (num >= 1e4) return `${(num / 1e4).toFixed(2)}万`
    return num.toFixed(2)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
      </div>
    )
  }

  if (!cashflowData.length) {
    return (
      <div className="text-center py-12 text-zinc-500">
        暂无现金流数据
      </div>
    )
  }

  const latest = cashflowData[0]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-zinc-500">经营活动现金流</span>
            {latest.operating_cash_flow && latest.operating_cash_flow >= 0 ? (
              <ArrowUpRight className="w-4 h-4 text-emerald-400" />
            ) : (
              <ArrowDownRight className="w-4 h-4 text-rose-400" />
            )}
          </div>
          <div className={`text-lg font-semibold ${latest.operating_cash_flow && latest.operating_cash_flow >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {formatNumber(latest.operating_cash_flow)}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-zinc-500">投资活动现金流</span>
            {latest.investing_cash_flow && latest.investing_cash_flow >= 0 ? (
              <ArrowUpRight className="w-4 h-4 text-emerald-400" />
            ) : (
              <ArrowDownRight className="w-4 h-4 text-rose-400" />
            )}
          </div>
          <div className={`text-lg font-semibold ${latest.investing_cash_flow && latest.investing_cash_flow >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {formatNumber(latest.investing_cash_flow)}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-zinc-500">筹资活动现金流</span>
            {latest.financing_cash_flow && latest.financing_cash_flow >= 0 ? (
              <ArrowUpRight className="w-4 h-4 text-emerald-400" />
            ) : (
              <ArrowDownRight className="w-4 h-4 text-rose-400" />
            )}
          </div>
          <div className={`text-lg font-semibold ${latest.financing_cash_flow && latest.financing_cash_flow >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {formatNumber(latest.financing_cash_flow)}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-zinc-500">自由现金流</span>
            {latest.free_cash_flow && latest.free_cash_flow >= 0 ? (
              <ArrowUpRight className="w-4 h-4 text-emerald-400" />
            ) : (
              <ArrowDownRight className="w-4 h-4 text-rose-400" />
            )}
          </div>
          <div className={`text-lg font-semibold ${latest.free_cash_flow && latest.free_cash_flow >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {formatNumber(latest.free_cash_flow)}
          </div>
        </div>
      </div>

      <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
        <h4 className="text-sm font-medium text-white mb-3">现金流趋势</h4>
        <div ref={chartRef} style={{ width: '100%', height: '300px' }} />
      </div>

      <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
        <h4 className="text-sm font-medium text-white mb-3">现金流分析</h4>
        <div className="space-y-2 text-sm text-zinc-400">
          {latest.operating_cash_flow && latest.operating_cash_flow > 0 ? (
            <div className="flex items-start gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-2" />
              <span>经营活动现金流为正，说明公司主营业务造血能力良好</span>
            </div>
          ) : (
            <div className="flex items-start gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-2" />
              <span>经营活动现金流为负，需关注主营业务盈利能力</span>
            </div>
          )}
          
          {latest.free_cash_flow && latest.free_cash_flow > 0 ? (
            <div className="flex items-start gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-2" />
              <span>自由现金流为正，公司有充足的资金用于分红或扩张</span>
            </div>
          ) : (
            <div className="flex items-start gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-2" />
              <span>自由现金流为负，公司可能需要外部融资支持</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
