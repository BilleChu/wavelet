'use client'

import React, { useEffect, useState, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { Activity, TrendingUp, TrendingDown, Minus } from 'lucide-react'

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false })

interface TechCardProps {
  code: string
}

interface TechData {
  price: number
  change: number
  change_pct: number
  ma5: number
  ma10: number
  ma20: number
  ma60: number
  rsi_14: number
  macd: number
  macd_signal: number
  macd_hist: number
  kdj_k: number
  kdj_d: number
  kdj_j: number
  boll_upper: number
  boll_mid: number
  boll_lower: number
  trend_signal: string
  support_level: number
  resistance_level: number
}

export default function TechCard({ code }: TechCardProps) {
  const [data, setData] = useState<TechData | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/analysis/company/${code}/tech?limit=100`)
      if (res.ok) {
        const json = await res.json()
        setData(json.tech || null)
      }
    } catch (error) {
      console.error('Failed to fetch tech data:', error)
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
          <div className="h-48 bg-zinc-800/50 rounded" />
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
        <p className="text-zinc-500 text-center py-8">暂无技术指标数据</p>
      </div>
    )
  }

  const getSignalConfig = (signal: string) => {
    if (signal === 'bullish' || signal === 'buy') return { label: '看涨', color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' }
    if (signal === 'bearish' || signal === 'sell') return { label: '看跌', color: 'text-rose-400', bg: 'bg-rose-500/10', border: 'border-rose-500/30' }
    return { label: '中性', color: 'text-zinc-400', bg: 'bg-zinc-500/10', border: 'border-zinc-500/30' }
  }

  const getRSILevel = (rsi: number) => {
    if (rsi > 70) return { label: '超买', color: 'text-rose-400' }
    if (rsi < 30) return { label: '超卖', color: 'text-emerald-400' }
    return { label: '正常', color: 'text-zinc-400' }
  }

  const getMACDSignal = (macd: number, signal: number) => {
    if (macd > signal) return { label: '金叉', color: 'text-emerald-400' }
    return { label: '死叉', color: 'text-rose-400' }
  }

  const signalConfig = getSignalConfig(data.trend_signal)
  const rsiLevel = getRSILevel(data.rsi_14 || 50)
  const macdSignal = getMACDSignal(data.macd || 0, data.macd_signal || 0)

  const gaugeOption = {
    backgroundColor: 'transparent',
    series: [{
      type: 'gauge',
      startAngle: 180,
      endAngle: 0,
      min: 0,
      max: 100,
      radius: '100%',
      center: ['50%', '70%'],
      splitNumber: 5,
      axisLine: {
        lineStyle: {
          width: 12,
          color: [
            [0.3, '#ef4444'],
            [0.5, '#f59e0b'],
            [0.7, '#22c55e'],
            [1, '#22c55e'],
          ],
        },
      },
      pointer: { icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z', length: '55%', width: 6, itemStyle: { color: 'auto' } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      title: { show: false },
      detail: { valueAnimation: true, formatter: '{value}', fontSize: 20, offsetCenter: [0, '-15%'], color: '#fff' },
      data: [{ value: data.rsi_14?.toFixed(1) || 50 }],
    }],
  }

  const indicators = [
    { name: '均线趋势', value: data.ma5 && data.ma20 ? (data.ma5 > data.ma20 ? '多头' : '空头') : '-', isGood: data.ma5 > data.ma20 },
    { name: 'RSI(14)', value: data.rsi_14?.toFixed(1) || '-', status: rsiLevel.label, statusColor: rsiLevel.color },
    { name: 'MACD', value: macdSignal.label, statusColor: macdSignal.color },
    { name: 'KDJ', value: data.kdj_j?.toFixed(1) || '-', status: data.kdj_j && data.kdj_j > 80 ? '超买' : data.kdj_j && data.kdj_j < 20 ? '超卖' : '正常' },
    { name: '支撑位', value: data.support_level?.toFixed(2) || '-' },
    { name: '压力位', value: data.resistance_level?.toFixed(2) || '-' },
  ]

  return (
    <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
            <Activity className="w-4 h-4 text-purple-400" />
          </div>
          技术面分析
        </h3>
        <span className={`px-3 py-1 rounded-lg text-sm font-medium ${signalConfig.bg} ${signalConfig.border} border ${signalConfig.color}`}>
          {signalConfig.label}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <div className="text-center mb-2">
            <span className="text-xs text-zinc-500">RSI 指标</span>
          </div>
          <ReactECharts option={gaugeOption} style={{ height: 150 }} opts={{ renderer: 'canvas' }} />
          <div className="text-center mt-1">
            <span className={`text-sm ${rsiLevel.color}`}>{rsiLevel.label}</span>
          </div>
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            {indicators.map((ind) => (
              <div key={ind.name} className="p-2 rounded-lg bg-white/[0.02]">
                <div className="text-xs text-zinc-500 mb-1">{ind.name}</div>
                <div className={`text-sm font-medium ${
                  ind.isGood !== undefined ? (ind.isGood ? 'text-emerald-400' : 'text-rose-400') : ind.statusColor || 'text-zinc-300'
                }`}>
                  {ind.value}
                </div>
                {ind.status && <div className={`text-xs ${ind.statusColor || 'text-zinc-500'}`}>{ind.status}</div>}
              </div>
            ))}
          </div>

          <div className="p-3 rounded-lg bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/20">
            <div className="text-xs font-medium text-zinc-400 mb-2">价格位置 (布林带)</div>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-zinc-500">当前价</span>
              <span className="font-bold text-white">{data.price?.toFixed(2)}</span>
            </div>
            <div className="w-full bg-zinc-800 rounded-full h-2 my-2 relative">
              {data.boll_upper && data.boll_lower && data.price && (
                <>
                  <div className="absolute h-2 bg-emerald-500/30 rounded-l-full" style={{ width: '33%' }} />
                  <div className="absolute h-2 bg-amber-500/30" style={{ left: '33%', width: '34%' }} />
                  <div className="absolute h-2 bg-rose-500/30 rounded-r-full" style={{ left: '67%', width: '33%' }} />
                  <div
                    className="absolute w-2.5 h-2.5 bg-cyan-400 rounded-full -top-px"
                    style={{
                      left: `${Math.min(100, Math.max(0, ((data.price - data.boll_lower) / (data.boll_upper - data.boll_lower)) * 100))}%`,
                      transform: 'translateX(-50%)',
                    }}
                  />
                </>
              )}
            </div>
            <div className="flex items-center justify-between text-xs text-zinc-500">
              <span>下轨: {data.boll_lower?.toFixed(2)}</span>
              <span>中轨: {data.boll_mid?.toFixed(2)}</span>
              <span>上轨: {data.boll_upper?.toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
