'use client'

import { useEffect, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { analysisService } from '@/services/analysisService'

interface KLineChartProps {
  stockCode: string
  period?: 'D' | 'W' | 'M'
  height?: number
}

export default function KLineChart({ stockCode, period = 'D', height = 400 }: KLineChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const [loading, setLoading] = useState(true)
  const [klineData, setKlineData] = useState<any[]>([])

  useEffect(() => {
    loadKLineData()
  }, [stockCode, period])

  const loadKLineData = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/analysis/company/${stockCode}/kline?period=${period}&days=100`)
      const data = await response.json()
      setKlineData(data.data || [])
    } catch (error) {
      console.error('Failed to load K-line data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!chartRef.current || !klineData.length || loading) return

    const renderChart = async () => {
      const echarts = await import('echarts')
      
      const chart = echarts.init(chartRef.current!)
      
      const dates = klineData.map((d: any) => d.trade_date)
      const ohlc = klineData.map((d: any) => [d.open, d.close, d.low, d.high])
      const volumes = klineData.map((d: any) => d.volume)

      const option = {
        backgroundColor: 'transparent',
        animation: false,
        legend: {
          data: ['K线', '成交量'],
          top: 10,
          left: 'center',
          textStyle: { color: '#a1a1aa' }
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross' },
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          borderColor: '#333',
          textStyle: { color: '#fff' },
          formatter: function (params: any) {
            const data = params[0]
            const kline = klineData[data.dataIndex]
            return `
              <div style="padding: 8px;">
                <div style="font-weight: bold; margin-bottom: 8px;">${kline.trade_date}</div>
                <div>开盘: ${kline.open.toFixed(2)}</div>
                <div>收盘: ${kline.close.toFixed(2)}</div>
                <div>最高: ${kline.high.toFixed(2)}</div>
                <div>最低: ${kline.low.toFixed(2)}</div>
                <div>成交量: ${(kline.volume / 1e6).toFixed(2)}M</div>
                <div>涨跌幅: ${kline.change_pct ? kline.change_pct.toFixed(2) : 0}%</div>
              </div>
            `
          }
        },
        axisPointer: {
          link: [{ xAxisIndex: 'all' }],
          label: { backgroundColor: '#777' }
        },
        grid: [
          { left: '10%', right: '8%', top: '10%', height: '50%' },
          { left: '10%', right: '8%', top: '70%', height: '15%' }
        ],
        xAxis: [
          {
            type: 'category',
            data: dates,
            boundaryGap: false,
            axisLine: { lineStyle: { color: '#333' } },
            axisLabel: { color: '#a1a1aa', fontSize: 10 },
            splitLine: { show: false },
            min: 'dataMin',
            max: 'dataMax'
          },
          {
            type: 'category',
            gridIndex: 1,
            data: dates,
            boundaryGap: false,
            axisLine: { lineStyle: { color: '#333' } },
            axisLabel: { show: false },
            splitLine: { show: false },
            min: 'dataMin',
            max: 'dataMax'
          }
        ],
        yAxis: [
          {
            scale: true,
            axisLine: { lineStyle: { color: '#333' } },
            axisLabel: { color: '#a1a1aa', fontSize: 10 },
            splitLine: { lineStyle: { color: '#222' } }
          },
          {
            scale: true,
            gridIndex: 1,
            splitNumber: 2,
            axisLine: { lineStyle: { color: '#333' } },
            axisLabel: { color: '#a1a1aa', fontSize: 10 },
            splitLine: { lineStyle: { color: '#222' } }
          }
        ],
        dataZoom: [
          {
            type: 'inside',
            xAxisIndex: [0, 1],
            start: 50,
            end: 100
          },
          {
            show: true,
            xAxisIndex: [0, 1],
            type: 'slider',
            bottom: '2%',
            start: 50,
            end: 100,
            borderColor: '#333',
            fillerColor: 'rgba(6, 182, 212, 0.2)',
            handleStyle: { color: '#06b6d4' },
            textStyle: { color: '#a1a1aa' }
          }
        ],
        series: [
          {
            name: 'K线',
            type: 'candlestick',
            data: ohlc,
            itemStyle: {
              color: '#ef4444',
              color0: '#22c55e',
              borderColor: '#ef4444',
              borderColor0: '#22c55e'
            }
          },
          {
            name: '成交量',
            type: 'bar',
            xAxisIndex: 1,
            yAxisIndex: 1,
            data: volumes,
            itemStyle: {
              color: function (params: any) {
                const kline = klineData[params.dataIndex]
                return kline && kline.close >= kline.open ? '#ef4444' : '#22c55e'
              }
            }
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
  }, [klineData, loading])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
      </div>
    )
  }

  return (
    <div ref={chartRef} style={{ width: '100%', height: `${height}px` }} />
  )
}
