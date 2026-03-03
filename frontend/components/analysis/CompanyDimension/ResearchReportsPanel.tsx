'use client'

import { useEffect, useState } from 'react'
import { FileText, Loader2, Database, RefreshCw, AlertCircle } from 'lucide-react'
import { Badge, Button } from '@/components/ui'

interface ResearchReport {
  report_id: string
  title: string
  summary: string | null
  analyst: string | null
  institution: string | null
  publish_date: string | null
  rating: string | null
  target_price: number | null
}

interface ResearchReportsPanelProps {
  stockCode: string
  limit?: number
}

export default function ResearchReportsPanel({ stockCode, limit = 5 }: ResearchReportsPanelProps) {
  const [loading, setLoading] = useState(true)
  const [reports, setReports] = useState<ResearchReport[]>([])
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    loadReports()
  }, [stockCode, limit])

  const loadReports = async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    
    try {
      const response = await fetch(`/api/analysis/company/${stockCode}/reports?limit=${limit}`)
      const data = await response.json()
      setReports(data.reports || [])
    } catch (error) {
      console.error('Failed to load research reports:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN')
  }

  const getRatingColor = (rating: string | null) => {
    if (!rating) return 'text-zinc-400'
    if (rating.includes('买入') || rating.includes('增持')) return 'text-emerald-400'
    if (rating.includes('卖出') || rating.includes('减持')) return 'text-rose-400'
    return 'text-amber-400'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
      </div>
    )
  }

  if (!reports.length) {
    return (
      <div className="space-y-4">
        <div className="text-center py-12">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-violet-500/20 to-purple-500/20 flex items-center justify-center mb-4">
            <Database className="w-8 h-8 text-violet-400" />
          </div>
          <h3 className="text-lg font-medium text-white mb-2">暂无研报数据</h3>
          <p className="text-sm text-zinc-500 mb-6 max-w-md mx-auto">
            当前股票的研究报告数据尚未采集，您可以尝试其他股票或等待数据更新
          </p>
          
          <div className="flex items-center justify-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => loadReports(true)}
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
              <h4 className="text-sm font-medium text-white mb-1">关于研报数据</h4>
              <p className="text-xs text-zinc-500">
                研究报告由券商分析师撰写，包含公司分析、行业研究、投资评级等内容。
                数据通常来自Wind、东方财富等数据源，需要单独采集。
              </p>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]"
            >
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-violet-500/20 to-purple-500/20 flex items-center justify-center flex-shrink-0">
                  <FileText className="w-5 h-5 text-violet-400" />
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="h-4 bg-white/[0.05] rounded w-3/4 mb-2" />
                  <div className="h-3 bg-white/[0.03] rounded w-full mb-1" />
                  <div className="h-3 bg-white/[0.03] rounded w-2/3" />
                </div>
              </div>
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
          共 {reports.length} 份研报
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => loadReports(true)}
          disabled={refreshing}
          className="gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      <div className="space-y-3">
        {reports.map((report) => (
          <div
            key={report.report_id}
            className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05] hover:border-violet-500/20 transition-all cursor-pointer"
          >
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                <FileText className="w-5 h-5 text-white" />
              </div>
              
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-white line-clamp-2 mb-2">{report.title}</h4>
                
                {report.summary && (
                  <p className="text-xs text-zinc-500 line-clamp-2 mb-3">{report.summary}</p>
                )}
                
                <div className="flex items-center justify-between text-xs text-zinc-600">
                  <div className="flex items-center gap-3">
                    {report.institution && (
                      <span className="text-zinc-400">{report.institution}</span>
                    )}
                    {report.analyst && (
                      <>
                        <span>·</span>
                        <span className="text-zinc-400">{report.analyst}</span>
                      </>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {report.rating && (
                      <Badge 
                        variant="secondary" 
                        size="sm"
                        className={getRatingColor(report.rating)}
                      >
                        {report.rating}
                      </Badge>
                    )}
                    {report.target_price && (
                      <span className="text-zinc-400">目标价: {report.target_price.toFixed(2)}</span>
                    )}
                  </div>
                </div>
                
                {report.publish_date && (
                  <div className="text-xs text-zinc-600 mt-2">
                    {formatDate(report.publish_date)}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
