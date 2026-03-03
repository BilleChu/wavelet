'use client'

import { useEffect, useState, useRef } from 'react'
import { Loader2, TrendingUp, TrendingDown, DollarSign } from 'lucide-react'
import { Badge } from '@/components/ui'

interface ProfitData {
  code: string
  report_date: string
  report_type: string
  total_revenue: number | null
  gross_profit: number | null
  operating_profit: number | null
  total_profit: number | null
  net_profit: number | null
  net_profit_attr_parent: number | null
  eps: number | null
  basic_eps: number | null
  diluted_eps: number | null
}

interface ProfitPanelProps {
  stockCode: string
}

export default function ProfitPanel({ stockCode }: ProfitPanelProps) {
  const [loading, setLoading] = useState(true)
  const [profitData, setProfitData] = useState<ProfitData[]>([])
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadProfitData()
  }, [stockCode])

  const loadProfitData = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/analysis/company/${stockCode}/profit?years=3`)
      const data = await response.json()
      setProfitData(data.data || [])
    } catch (error) {
      console.error('Failed to load profit data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!chartRef.current || !profitData.length || loading) return

    const renderChart = async () => {
      const echarts = await import('echarts')
      const chart = echarts.init(chartRef.current!)

      const dates = profitData.map(d => d.report_date).reverse()
      
      const option = {
        backgroundColor: 'transparent',
        animation: false,
        legend: {
          data: ['营业收入', '毛利润', '营业利润', '净利润'],
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
            name: '营业收入',
            type: 'bar',
            data: profitData.map(d => d.total_revenue).reverse(),
            itemStyle: { color: '#06b6d4' }
          },
          {
            name: '毛利润',
            type: 'bar',
            data: profitData.map(d => d.gross_profit).reverse(),
            itemStyle: { color: '#f59e0b' }
          },
          {
            name: '营业利润',
            type: 'bar',
            data: profitData.map(d => d.operating_profit).reverse(),
            itemStyle: { color: '#8b5cf6' }
          },
          {
            name: '净利润',
            type: 'line',
            smooth: true,
            symbol: 'circle',
            symbolSize: 6,
            data: profitData.map(d => d.net_profit).reverse(),
            lineStyle: { color: '#10b981', width: 2 },
            itemStyle: { color: '#10b981' }
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
  }, [profitData, loading])

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

  if (!profitData.length) {
    return (
      <div className="text-center py-12 text-zinc-500">
        暂无利润数据
      </div>
    )
  }

  const latest = profitData[0]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">营业收入</div>
          <div className="text-lg font-semibold text-white">{formatNumber(latest.total_revenue)}</div>
        </div>

        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">毛利润</div>
          <div className="text-lg font-semibold text-white">{formatNumber(latest.gross_profit)}</div>
        </div>

        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">营业利润</div>
          <div className="text-lg font-semibold text-white">{formatNumber(latest.operating_profit)}</div>
        </div>

        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">净利润</div>
          <div className="text-lg font-semibold text-white">{formatNumber(latest.net_profit)}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">归母净利润</div>
          <div className="text-sm font-medium text-white">{formatNumber(latest.net_profit_attr_parent)}</div>
        </div>

        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">基本每股收益</div>
          <div className="text-sm font-medium text-white">{latest.basic_eps?.toFixed(2) || '-'}</div>
        </div>

        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">稀释每股收益</div>
          <div className="text-sm font-medium text-white">{latest.diluted_eps?.toFixed(2) || '-'}</div>
        </div>
      </div>

      <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
        <h4 className="text-sm font-medium text-white mb-3">利润趋势</h4>
        <div ref={chartRef} style={{ width: '100%', height: '300px' }} />
      </div>

      <div className="mt-4">
        <h4 className="text-sm font-medium text-white mb-3">历史利润数据</h4>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {profitData.slice(0, 8).map((item, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]"
            >
              <div className="flex items-center gap-3">
                <Badge variant="secondary" size="sm">{item.report_type}</Badge>
                <span className="text-sm text-zinc-400">{item.report_date}</span>
              </div>
              <div className="flex items-center gap-6 text-sm">
                <div>
                  <span className="text-zinc-500">营收: </span>
                  <span className="text-white">{formatNumber(item.total_revenue)}</span>
                </div>
                <div>
                  <span className="text-zinc-500">净利: </span>
                  <span className="text-white">{formatNumber(item.net_profit)}</span>
                </div>
                <div>
                  <span className="text-zinc-500">EPS: </span>
                  <span className="text-white">{item.basic_eps?.toFixed(2) || '-'}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
