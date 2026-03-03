'use client'

import { useEffect, useState } from 'react'
import { TrendingUp, TrendingDown, Minus, Loader2 } from 'lucide-react'
import { Badge } from '@/components/ui'

interface NewsItem {
  news_id: string
  title: string
  content: string | null
  source: string | null
  published_at: string | null
  sentiment: number | null
  related_codes: string[]
}

interface NewsPanelProps {
  stockCode: string
  limit?: number
}

export default function NewsPanel({ stockCode, limit = 10 }: NewsPanelProps) {
  const [loading, setLoading] = useState(true)
  const [newsData, setNewsData] = useState<NewsItem[]>([])

  useEffect(() => {
    loadNewsData()
  }, [stockCode, limit])

  const loadNewsData = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/analysis/company/${stockCode}/news?limit=${limit}`)
      const data = await response.json()
      setNewsData(data.news || [])
    } catch (error) {
      console.error('Failed to load news data:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatTime = (dateStr: string | null) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`
    
    return date.toLocaleDateString('zh-CN')
  }

  const getSentimentIcon = (sentiment: number | null) => {
    if (sentiment === null || sentiment === undefined) return <Minus className="w-3 h-3 text-zinc-500" />
    if (sentiment > 0.3) return <TrendingUp className="w-3 h-3 text-emerald-400" />
    if (sentiment < -0.3) return <TrendingDown className="w-3 h-3 text-rose-400" />
    return <Minus className="w-3 h-3 text-zinc-500" />
  }

  const getSentimentColor = (sentiment: number | null) => {
    if (sentiment === null || sentiment === undefined) return 'text-zinc-400'
    if (sentiment > 0.3) return 'text-emerald-400'
    if (sentiment < -0.3) return 'text-rose-400'
    return 'text-zinc-400'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
      </div>
    )
  }

  if (!newsData.length) {
    return (
      <div className="text-center py-12 text-zinc-500">
        暂无相关新闻
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {newsData.map((news) => (
        <div
          key={news.news_id}
          className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05] hover:border-cyan-500/20 transition-all cursor-pointer"
        >
          <div className="flex items-start justify-between mb-2">
            <h4 className="text-sm font-medium text-white line-clamp-2 flex-1">{news.title}</h4>
            <div className="flex items-center gap-1 ml-2">
              {getSentimentIcon(news.sentiment)}
            </div>
          </div>
          
          {news.content && (
            <p className="text-xs text-zinc-500 line-clamp-2 mb-3">{news.content}</p>
          )}
          
          <div className="flex items-center justify-between text-xs text-zinc-600">
            <div className="flex items-center gap-2">
              {news.source && (
                <>
                  <span>{news.source}</span>
                  <span>·</span>
                </>
              )}
              <span>{formatTime(news.published_at)}</span>
            </div>
            
            {news.sentiment !== null && news.sentiment !== undefined && (
              <Badge 
                variant="secondary" 
                size="sm"
                className={getSentimentColor(news.sentiment)}
              >
                {news.sentiment > 0.3 ? '利好' : news.sentiment < -0.3 ? '利空' : '中性'}
              </Badge>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
