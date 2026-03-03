'use client'

import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, Minus, Loader2 } from 'lucide-react'
import { Badge } from '@/components/ui'

interface TechData {
  code: string
  name: string
  price: number
  change: number
  change_pct: number
  volume: number
  amount: number
  ma5?: number
  ma10?: number
  ma20?: number
  ma60?: number
  rsi_14?: number
  macd?: number
  macd_signal?: number
  macd_hist?: number
  kdj_k?: number
  kdj_d?: number
  kdj_j?: number
  boll_upper?: number
  boll_mid?: number
  boll_lower?: number
  trend_signal: string
  support_level?: number
  resistance_level?: number
}

interface TechIndicatorsPanelProps {
  stockCode: string
}

export default function TechIndicatorsPanel({ stockCode }: TechIndicatorsPanelProps) {
  const [loading, setLoading] = useState(true)
  const [techData, setTechData] = useState<TechData | null>(null)

  useEffect(() => {
    loadTechData()
  }, [stockCode])

  const loadTechData = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/analysis/company/${stockCode}/tech?limit=60`)
      const data = await response.json()
      setTechData(data.tech || null)
    } catch (error) {
      console.error('Failed to load tech data:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatNumber = (num: number | undefined, decimals = 2) => {
    if (num === undefined || num === null) return '-'
    return num.toFixed(decimals)
  }

  const getTrendIcon = (signal: string) => {
    if (signal === 'bullish') return <TrendingUp className="w-4 h-4 text-emerald-400" />
    if (signal === 'bearish') return <TrendingDown className="w-4 h-4 text-rose-400" />
    return <Minus className="w-4 h-4 text-zinc-500" />
  }

  const getTrendText = (signal: string) => {
    if (signal === 'bullish') return '看涨'
    if (signal === 'bearish') return '看跌'
    return '中性'
  }

  const getTrendColor = (signal: string) => {
    if (signal === 'bullish') return 'text-emerald-400'
    if (signal === 'bearish') return 'text-rose-400'
    return 'text-zinc-400'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
      </div>
    )
  }

  if (!techData) {
    return (
      <div className="text-center py-12 text-zinc-500">
        暂无技术指标数据
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-2xl font-bold text-white">{techData.price.toFixed(2)}</div>
            <div className="flex items-center gap-2 mt-1">
              <span className={`text-sm ${techData.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {techData.change_pct >= 0 ? '+' : ''}{techData.change.toFixed(2)} ({techData.change_pct.toFixed(2)}%)
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {getTrendIcon(techData.trend_signal)}
            <span className={`text-sm font-medium ${getTrendColor(techData.trend_signal)}`}>
              {getTrendText(techData.trend_signal)}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-zinc-500">成交量: </span>
            <span className="text-white">{(techData.volume / 1e6).toFixed(2)}M</span>
          </div>
          <div>
            <span className="text-zinc-500">成交额: </span>
            <span className="text-white">{(techData.amount / 1e8).toFixed(2)}亿</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">MA5</div>
          <div className="text-sm font-medium text-white">{formatNumber(techData.ma5)}</div>
        </div>
        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">MA10</div>
          <div className="text-sm font-medium text-white">{formatNumber(techData.ma10)}</div>
        </div>
        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">MA20</div>
          <div className="text-sm font-medium text-white">{formatNumber(techData.ma20)}</div>
        </div>
        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">MA60</div>
          <div className="text-sm font-medium text-white">{formatNumber(techData.ma60)}</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">RSI(14)</div>
          <div className="text-sm font-medium text-white">{formatNumber(techData.rsi_14)}</div>
        </div>
        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">MACD</div>
          <div className="text-sm font-medium text-white">{formatNumber(techData.macd)}</div>
        </div>
        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">KDJ K</div>
          <div className="text-sm font-medium text-white">{formatNumber(techData.kdj_k)}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">支撑位</div>
          <div className="text-sm font-medium text-white">{formatNumber(techData.support_level)}</div>
        </div>
        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">阻力位</div>
          <div className="text-sm font-medium text-white">{formatNumber(techData.resistance_level)}</div>
        </div>
      </div>
    </div>
  )
}
