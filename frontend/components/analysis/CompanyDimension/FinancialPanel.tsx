'use client'

import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, Loader2 } from 'lucide-react'
import { Badge } from '@/components/ui'

interface FinancialData {
  report_date: string
  report_type: string
  revenue: number | null
  net_profit: number | null
  gross_margin: number | null
  net_margin: number | null
  roe: number | null
  roa: number | null
  debt_ratio: number | null
  pe_ratio: number | null
  pb_ratio: number | null
  yoy_revenue_growth: number | null
  yoy_profit_growth: number | null
}

interface FinancialPanelProps {
  stockCode: string
}

export default function FinancialPanel({ stockCode }: FinancialPanelProps) {
  const [loading, setLoading] = useState(true)
  const [financialData, setFinancialData] = useState<FinancialData[]>([])

  useEffect(() => {
    loadFinancialData()
  }, [stockCode])

  const loadFinancialData = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/analysis/company/${stockCode}/financial?years=3`)
      const data = await response.json()
      setFinancialData(data.data || [])
    } catch (error) {
      console.error('Failed to load financial data:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatNumber = (num: number | null, decimals = 2) => {
    if (num === null || num === undefined) return '-'
    if (num >= 1e12) return `${(num / 1e12).toFixed(decimals)}万亿`
    if (num >= 1e8) return `${(num / 1e8).toFixed(decimals)}亿`
    if (num >= 1e4) return `${(num / 1e4).toFixed(decimals)}万`
    return num.toFixed(decimals)
  }

  const formatPercent = (num: number | null) => {
    if (num === null || num === undefined) return '-'
    return `${num.toFixed(2)}%`
  }

  const getGrowthIcon = (value: number | null) => {
    if (value === null || value === undefined) return null
    if (value > 0) return <TrendingUp className="w-3 h-3 text-emerald-400" />
    if (value < 0) return <TrendingDown className="w-3 h-3 text-rose-400" />
    return null
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
      </div>
    )
  }

  if (!financialData.length) {
    return (
      <div className="text-center py-12 text-zinc-500">
        暂无财务数据
      </div>
    )
  }

  const latest = financialData[0]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">营业收入</div>
          <div className="text-lg font-semibold text-white">{formatNumber(latest.revenue)}</div>
          <div className="flex items-center gap-1 mt-1">
            {getGrowthIcon(latest.yoy_revenue_growth)}
            <span className={`text-xs ${latest.yoy_revenue_growth && latest.yoy_revenue_growth >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {latest.yoy_revenue_growth ? `${latest.yoy_revenue_growth >= 0 ? '+' : ''}${latest.yoy_revenue_growth.toFixed(2)}%` : '-'}
            </span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">净利润</div>
          <div className="text-lg font-semibold text-white">{formatNumber(latest.net_profit)}</div>
          <div className="flex items-center gap-1 mt-1">
            {getGrowthIcon(latest.yoy_profit_growth)}
            <span className={`text-xs ${latest.yoy_profit_growth && latest.yoy_profit_growth >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {latest.yoy_profit_growth ? `${latest.yoy_profit_growth >= 0 ? '+' : ''}${latest.yoy_profit_growth.toFixed(2)}%` : '-'}
            </span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">ROE</div>
          <div className="text-lg font-semibold text-white">{formatPercent(latest.roe)}</div>
        </div>

        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">PE</div>
          <div className="text-lg font-semibold text-white">{latest.pe_ratio?.toFixed(2) || '-'}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">毛利率</div>
          <div className="text-sm font-medium text-white">{formatPercent(latest.gross_margin)}</div>
        </div>

        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">净利率</div>
          <div className="text-sm font-medium text-white">{formatPercent(latest.net_margin)}</div>
        </div>

        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">ROA</div>
          <div className="text-sm font-medium text-white">{formatPercent(latest.roa)}</div>
        </div>

        <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
          <div className="text-xs text-zinc-500 mb-1">资产负债率</div>
          <div className="text-sm font-medium text-white">{formatPercent(latest.debt_ratio)}</div>
        </div>
      </div>

      <div className="mt-4">
        <h4 className="text-sm font-medium text-white mb-3">历史财报</h4>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {financialData.slice(0, 8).map((item, index) => (
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
                  <span className="text-white">{formatNumber(item.revenue)}</span>
                </div>
                <div>
                  <span className="text-zinc-500">净利: </span>
                  <span className="text-white">{formatNumber(item.net_profit)}</span>
                </div>
                <div>
                  <span className="text-zinc-500">ROE: </span>
                  <span className="text-white">{formatPercent(item.roe)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
