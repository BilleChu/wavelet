'use client'

import { useState, useEffect, useCallback } from 'react'
import { Button, Badge } from '@/components/ui'
import {
  Search,
  RefreshCw,
  FileText,
  Building2,
  TrendingUp,
  Calendar,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  BarChart3,
  Filter,
} from 'lucide-react'

interface ResearchReport {
  report_id: string
  title: string
  summary: string | null
  source: string
  institution: string | null
  analyst: string | null
  rating: string | null
  target_price: number | null
  related_codes: string[]
  related_names: string[]
  industry: string | null
  sentiment_score: number | null
  sentiment_label: string | null
  publish_date: string | null
  report_type: string | null
  source_url: string | null
}

interface ResearchReportStats {
  total_reports: number
  by_source: Record<string, number>
  by_rating: Record<string, number>
  by_institution: Record<string, number>
  recent_count: number
}

interface ResearchReportListResponse {
  reports: ResearchReport[]
  total: number
  page: number
  page_size: number
}

const ratingColors: Record<string, string> = {
  '买入': 'bg-emerald-500/20 text-emerald-400',
  '增持': 'bg-blue-500/20 text-blue-400',
  '持有': 'bg-amber-500/20 text-amber-400',
  '减持': 'bg-orange-500/20 text-orange-400',
  '卖出': 'bg-rose-500/20 text-rose-400',
}

const sourceLabels: Record<string, string> = {
  'eastmoney': '东方财富',
  'thshy': '同花顺',
  'sina': '新浪财经',
}

export default function ResearchReportPage() {
  const [reports, setReports] = useState<ResearchReport[]>([])
  const [stats, setStats] = useState<ResearchReportStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [pageSize] = useState(10)
  const [selectedRating, setSelectedRating] = useState<string | null>(null)
  const [selectedInstitution, setSelectedInstitution] = useState<string | null>(null)

  const fetchReports = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('page', page.toString())
      params.set('page_size', pageSize.toString())
      if (selectedRating) params.set('rating', selectedRating)
      if (selectedInstitution) params.set('institution', selectedInstitution)

      const response = await fetch(`/api/research-reports?${params}`)
      if (response.ok) {
        const data: ResearchReportListResponse = await response.json()
        setReports(data.reports)
        setTotal(data.total)
      }
    } catch (err) {
      console.error('Failed to fetch reports:', err)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, selectedRating, selectedInstitution])

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch('/api/research-reports/stats')
      if (response.ok) {
        const data: ResearchReportStats = await response.json()
        setStats(data)
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }, [])

  const searchReports = useCallback(async (query: string) => {
    if (!query.trim()) {
      fetchReports()
      return
    }
    
    setLoading(true)
    try {
      const response = await fetch(`/api/research-reports/search?q=${encodeURIComponent(query)}&page=${page}&page_size=${pageSize}`)
      if (response.ok) {
        const data = await response.json()
        setReports(data.reports)
        setTotal(data.total)
      }
    } catch (err) {
      console.error('Failed to search reports:', err)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize])

  useEffect(() => {
    fetchReports()
    fetchStats()
  }, [fetchReports, fetchStats])

  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchQuery.trim()) {
        setPage(1)
        searchReports(searchQuery)
      } else {
        fetchReports()
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery, searchReports, fetchReports])

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white flex items-center gap-2">
          <FileText className="w-6 h-6 text-[var(--accent-gold)]" />
          研报数据服务
        </h1>
        <Button variant="outline" size="sm" onClick={() => { fetchReports(); fetchStats(); }}>
          <RefreshCw className="w-4 h-4 mr-2" />
          刷新
        </Button>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="glass-panel p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center">
              <FileText className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs">研报总数</p>
              <p className="text-2xl font-semibold text-white">{stats?.total_reports || 0}</p>
            </div>
          </div>
        </div>
        <div className="glass-panel p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
              <Calendar className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs">近7日新增</p>
              <p className="text-2xl font-semibold text-white">{stats?.recent_count || 0}</p>
            </div>
          </div>
        </div>
        <div className="glass-panel p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-violet-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs">研究机构</p>
              <p className="text-2xl font-semibold text-white">{Object.keys(stats?.by_institution || {}).length}</p>
            </div>
          </div>
        </div>
        <div className="glass-panel p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs">买入评级</p>
              <p className="text-2xl font-semibold text-white">{stats?.by_rating?.['买入'] || 0}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="glass-panel p-4">
          <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-zinc-500" />
            数据来源分布
          </h3>
          <div className="space-y-2">
            {Object.entries(stats?.by_source || {}).map(([source, count]) => (
              <div key={source} className="flex items-center justify-between">
                <span className="text-zinc-400 text-sm">{sourceLabels[source] || source}</span>
                <Badge variant="secondary" className="bg-blue-500/20 text-blue-400">
                  {count}
                </Badge>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel p-4">
          <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-zinc-500" />
            评级分布
          </h3>
          <div className="space-y-2">
            {Object.entries(stats?.by_rating || {}).map(([rating, count]) => (
              <div key={rating} className="flex items-center justify-between">
                <Badge variant="secondary" className={ratingColors[rating] || 'bg-zinc-500/20 text-zinc-400'}>
                  {rating}
                </Badge>
                <span className="text-zinc-400 text-sm">{count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel p-4">
          <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-zinc-500" />
            热门机构
          </h3>
          <div className="space-y-2">
            {Object.entries(stats?.by_institution || {}).slice(0, 5).map(([institution, count]) => (
              <div key={institution} className="flex items-center justify-between">
                <span className="text-zinc-400 text-sm truncate max-w-[150px]">{institution}</span>
                <Badge variant="secondary" className="bg-violet-500/20 text-violet-400">
                  {count}
                </Badge>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="glass-panel overflow-hidden">
        <div className="p-4 border-b border-white/[0.05] flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                type="text"
                placeholder="搜索研报..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-4 py-2 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/40 w-64"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-zinc-500" />
              <select
                value={selectedRating || ''}
                onChange={(e) => setSelectedRating(e.target.value || null)}
                className="bg-white/[0.03] border border-white/[0.08] rounded-lg px-3 py-1.5 text-sm text-zinc-300 focus:outline-none"
              >
                <option value="">全部评级</option>
                <option value="买入">买入</option>
                <option value="增持">增持</option>
                <option value="持有">持有</option>
                <option value="减持">减持</option>
                <option value="卖出">卖出</option>
              </select>
            </div>
          </div>
          <div className="text-zinc-500 text-sm">
            共 {total} 条研报
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="w-8 h-8 animate-spin text-[var(--accent-gold)]" />
          </div>
        ) : reports.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-zinc-500">
            <FileText className="w-12 h-12 mb-4" />
            <p>暂无研报数据</p>
          </div>
        ) : (
          <div className="divide-y divide-white/[0.05]">
            {reports.map((report) => (
              <div key={report.report_id} className="p-4 hover:bg-white/[0.02]">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-white font-medium mb-2 line-clamp-2">
                      {report.title}
                    </h3>
                    <div className="flex items-center gap-3 text-sm text-zinc-500 mb-2">
                      {report.institution && (
                        <span className="flex items-center gap-1">
                          <Building2 className="w-3 h-3" />
                          {report.institution}
                        </span>
                      )}
                      {report.analyst && (
                        <span>{report.analyst}</span>
                      )}
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {formatDate(report.publish_date)}
                      </span>
                    </div>
                    {report.summary && (
                      <p className="text-zinc-400 text-sm line-clamp-2">{report.summary}</p>
                    )}
                    {report.related_names && report.related_names.length > 0 && (
                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        {report.related_names.slice(0, 3).map((name, idx) => (
                          <Badge key={idx} variant="secondary" className="bg-zinc-500/20 text-zinc-400">
                            {name}
                          </Badge>
                        ))}
                        {report.related_names.length > 3 && (
                          <span className="text-zinc-500 text-xs">+{report.related_names.length - 3}</span>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    {report.rating && (
                      <Badge variant="secondary" className={ratingColors[report.rating] || 'bg-zinc-500/20 text-zinc-400'}>
                        {report.rating}
                      </Badge>
                    )}
                    {report.target_price && (
                      <span className="text-emerald-400 text-sm">
                        目标价: ¥{report.target_price.toFixed(2)}
                      </span>
                    )}
                    {report.source_url && (
                      <a
                        href={report.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-violet-400 text-xs flex items-center gap-1 hover:underline"
                      >
                        查看原文
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {totalPages > 1 && (
          <div className="p-4 border-t border-white/[0.05] flex items-center justify-between">
            <div className="text-zinc-500 text-sm">
              第 {page} / {totalPages} 页
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
