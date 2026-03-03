'use client'

import React, { useEffect, useState, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { Newspaper, TrendingUp, TrendingDown, Minus, ExternalLink } from 'lucide-react'

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false })

interface SentimentCardProps {
  code: string
}

interface NewsItem {
  news_id: string
  title: string
  content: string
  source: string
  published_at: string
  sentiment: number
  related_codes: string[]
}

export default function SentimentCard({ code }: SentimentCardProps) {
  const [news, setNews] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/analysis/company/${code}/news?limit=20`)
      if (res.ok) {
        const json = await res.json()
        setNews(json.news || [])
      }
    } catch (error) {
      console.error('Failed to fetch news:', error)
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

  const sentiments = news.map(n => n.sentiment).filter(Boolean)
  const avgSentiment = sentiments.length > 0 ? sentiments.reduce((a, b) => a + b, 0) / sentiments.length : 0

  const positiveCount = sentiments.filter(s => s > 0.3).length
  const neutralCount = sentiments.filter(s => s >= -0.3 && s <= 0.3).length
  const negativeCount = sentiments.filter(s => s < -0.3).length

  const getSentimentConfig = (sentiment: number) => {
    if (sentiment > 0.3) return { label: '正面', color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' }
    if (sentiment < -0.3) return { label: '负面', color: 'text-rose-400', bg: 'bg-rose-500/10', border: 'border-rose-500/30' }
    return { label: '中性', color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' }
  }

  const overallConfig = getSentimentConfig(avgSentiment)

  const pieOption = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)', backgroundColor: 'rgba(0, 0, 0, 0.8)', borderColor: '#333', textStyle: { color: '#fff' } },
    legend: { bottom: 0, textStyle: { color: '#71717a', fontSize: 10 } },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      label: { show: false },
      data: [
        { value: positiveCount, name: '正面', itemStyle: { color: '#22c55e' } },
        { value: neutralCount, name: '中性', itemStyle: { color: '#f59e0b' } },
        { value: negativeCount, name: '负面', itemStyle: { color: '#ef4444' } },
      ],
    }],
  }

  const getSentimentIcon = (sentiment: number) => {
    if (sentiment > 0.3) return <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
    if (sentiment < -0.3) return <TrendingDown className="w-3.5 h-3.5 text-rose-400" />
    return <Minus className="w-3.5 h-3.5 text-amber-400" />
  }

  return (
    <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-orange-500/20 flex items-center justify-center">
            <Newspaper className="w-4 h-4 text-orange-400" />
          </div>
          情绪面分析
        </h3>
        <span className={`px-3 py-1 rounded-lg text-sm font-medium ${overallConfig.bg} ${overallConfig.border} border ${overallConfig.color}`}>
          整体{overallConfig.label}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <ReactECharts option={pieOption} style={{ height: 180 }} opts={{ renderer: 'canvas' }} />
          
          <div className="grid grid-cols-3 gap-2 mt-4">
            <div className="text-center p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
              <div className="text-2xl font-bold text-emerald-400">{positiveCount}</div>
              <div className="text-xs text-zinc-500">正面</div>
            </div>
            <div className="text-center p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <div className="text-2xl font-bold text-amber-400">{neutralCount}</div>
              <div className="text-xs text-zinc-500">中性</div>
            </div>
            <div className="text-center p-2 rounded-lg bg-rose-500/10 border border-rose-500/20">
              <div className="text-2xl font-bold text-rose-400">{negativeCount}</div>
              <div className="text-xs text-zinc-500">负面</div>
            </div>
          </div>
        </div>

        <div>
          <div className="text-sm font-medium text-zinc-400 mb-3">近期新闻</div>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {news.slice(0, 5).map((item, idx) => {
              const config = getSentimentConfig(item.sentiment)
              return (
                <div
                  key={item.news_id || idx}
                  className="p-3 bg-white/[0.02] rounded-lg hover:bg-white/[0.04] cursor-pointer transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        {getSentimentIcon(item.sentiment)}
                        <span className="text-sm text-zinc-300 line-clamp-1">{item.title}</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-zinc-500">
                        <span>{item.source}</span>
                        <span>•</span>
                        <span>{item.published_at?.slice(0, 10)}</span>
                      </div>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-xs ${config.bg} ${config.border} border ${config.color}`}>
                      {config.label}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
