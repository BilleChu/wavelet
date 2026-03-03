'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Button, Badge } from '@/components/ui'
import {
  Search,
  RefreshCw,
  Users,
  Building2,
  TrendingUp,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Star,
  Filter,
  Award,
  Eye,
} from 'lucide-react'

interface Person {
  entity_id: string
  name: string
  person_type: string | null
  person_type_label: string | null
  title: string | null
  company: string | null
  industry: string | null
  avatar_url: string | null
  verified: boolean
  total_score: number
  influence_score: number
  activity_score: number
  accuracy_score: number
  network_score: number
  followers_count: number
  news_mentions: number
  report_count: number
  industry_scores: Record<string, any>
}

interface PersonListResponse {
  persons: Person[]
  total: number
  page: number
  page_size: number
}

interface PersonStats {
  total_persons: number
  by_type: Record<string, number>
  by_industry: Record<string, number>
  avg_score: number
  top_scored_count: number
}

const personTypeLabels: Record<string, string> = {
  investment_manager: '投资经理',
  kol: 'KOL',
  entrepreneur: '企业家',
  analyst: '分析师',
  executive: '企业高管',
  investor: '投资人',
}

const personTypeColors: Record<string, string> = {
  investment_manager: 'bg-blue-500/20 text-blue-400',
  kol: 'bg-pink-500/20 text-pink-400',
  entrepreneur: 'bg-amber-500/20 text-amber-400',
  analyst: 'bg-violet-500/20 text-violet-400',
  executive: 'bg-emerald-500/20 text-emerald-400',
  investor: 'bg-cyan-500/20 text-cyan-400',
}

export default function PersonsPage() {
  const router = useRouter()
  const [persons, setPersons] = useState<Person[]>([])
  const [stats, setStats] = useState<PersonStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [pageSize] = useState(12)
  const [selectedType, setSelectedType] = useState<string | null>(null)
  const [selectedIndustry, setSelectedIndustry] = useState<string | null>(null)

  const fetchPersons = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('page', page.toString())
      params.set('page_size', pageSize.toString())
      if (selectedType) params.set('person_type', selectedType)
      if (selectedIndustry) params.set('industry', selectedIndustry)
      if (searchQuery) params.set('keyword', searchQuery)

      const response = await fetch(`/api/persons?${params}`)
      if (response.ok) {
        const data: PersonListResponse = await response.json()
        setPersons(data.persons)
        setTotal(data.total)
      }
    } catch (err) {
      console.error('Failed to fetch persons:', err)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, selectedType, selectedIndustry, searchQuery])

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch('/api/persons/stats')
      if (response.ok) {
        const data: PersonStats = await response.json()
        setStats(data)
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }, [])

  useEffect(() => {
    fetchPersons()
    fetchStats()
  }, [fetchPersons, fetchStats])

  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1)
      fetchPersons()
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400'
    if (score >= 60) return 'text-amber-400'
    if (score >= 40) return 'text-orange-400'
    return 'text-zinc-400'
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white flex items-center gap-2">
          <Users className="w-6 h-6 text-[var(--accent-gold)]" />
          人物档案
        </h1>
        <Button variant="outline" size="sm" onClick={() => { fetchPersons(); fetchStats(); }}>
          <RefreshCw className="w-4 h-4 mr-2" />
          刷新
        </Button>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <div className="glass-panel p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center">
              <Users className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs">人物总数</p>
              <p className="text-2xl font-semibold text-white">{stats?.total_persons || 0}</p>
            </div>
          </div>
        </div>
        <div className="glass-panel p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
              <Award className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs">高评分人物</p>
              <p className="text-2xl font-semibold text-white">{stats?.top_scored_count || 0}</p>
            </div>
          </div>
        </div>
        <div className="glass-panel p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-violet-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs">平均评分</p>
              <p className="text-2xl font-semibold text-white">{stats?.avg_score?.toFixed(1) || 0}</p>
            </div>
          </div>
        </div>
        <div className="glass-panel p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <p className="text-zinc-500 text-xs">覆盖行业</p>
              <p className="text-2xl font-semibold text-white">{Object.keys(stats?.by_industry || {}).length}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-6 gap-4">
        <div className="col-span-2 glass-panel p-4">
          <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
            <Users className="w-4 h-4 text-zinc-500" />
            人物类型分布
          </h3>
          <div className="space-y-2">
            {Object.entries(stats?.by_type || {}).map(([type, count]) => (
              <button
                key={type}
                onClick={() => setSelectedType(selectedType === type ? null : type)}
                className={`w-full flex items-center justify-between p-2 rounded-lg transition-all ${
                  selectedType === type 
                    ? 'bg-violet-500/20 border border-violet-500/40' 
                    : 'bg-white/[0.02] border border-white/[0.05] hover:bg-white/[0.05]'
                }`}
              >
                <Badge variant="secondary" className={personTypeColors[type] || 'bg-zinc-500/20 text-zinc-400'}>
                  {personTypeLabels[type] || type}
                </Badge>
                <span className="text-zinc-400 text-sm">{count}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="col-span-4 glass-panel p-4">
          <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-zinc-500" />
            行业分布（可下钻）
          </h3>
          <div className="grid grid-cols-4 gap-2">
            {Object.entries(stats?.by_industry || {}).slice(0, 12).map(([industry, count]) => (
              <button
                key={industry}
                onClick={() => setSelectedIndustry(selectedIndustry === industry ? null : industry)}
                className={`flex flex-col items-center justify-center p-3 rounded-lg transition-all ${
                  selectedIndustry === industry 
                    ? 'bg-amber-500/20 border border-amber-500/40' 
                    : 'bg-white/[0.02] border border-white/[0.05] hover:bg-white/[0.05]'
                }`}
              >
                <span className="text-white text-sm font-medium truncate max-w-full">{industry}</span>
                <span className="text-zinc-500 text-xs mt-1">{count}人</span>
              </button>
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
                placeholder="搜索人物..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-4 py-2 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500/40 w-64"
              />
            </div>
            {(selectedType || selectedIndustry) && (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => { setSelectedType(null); setSelectedIndustry(null); }}
              >
                清除筛选
              </Button>
            )}
          </div>
          <div className="text-zinc-500 text-sm">
            共 {total} 位人物
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="w-8 h-8 animate-spin text-[var(--accent-gold)]" />
          </div>
        ) : persons.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-zinc-500">
            <Users className="w-12 h-12 mb-4" />
            <p>暂无人物数据</p>
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-4 p-4">
            {persons.map((person) => (
              <div
                key={person.entity_id}
                onClick={() => router.push(`/datacenter/persons/${person.entity_id}`)}
                className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05] hover:bg-white/[0.04] hover:border-violet-500/30 cursor-pointer transition-all"
              >
                <div className="flex items-start gap-3">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white font-semibold text-lg">
                    {person.name.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-white font-medium truncate">{person.name}</h3>
                      {person.verified && (
                        <Badge variant="secondary" className="bg-blue-500/20 text-blue-400 text-xs">
                          已认证
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      {person.person_type && (
                        <Badge variant="secondary" className={(personTypeColors[person.person_type] || 'bg-zinc-500/20 text-zinc-400') + ' text-xs'}>
                          {person.person_type_label || personTypeLabels[person.person_type]}
                        </Badge>
                      )}
                    </div>
                    {person.title && (
                      <p className="text-zinc-500 text-sm truncate mt-1">{person.title}</p>
                    )}
                    {person.company && (
                      <p className="text-zinc-600 text-xs truncate">{person.company}</p>
                    )}
                  </div>
                  <div className="text-right">
                    <div className={`text-2xl font-bold ${getScoreColor(person.total_score)}`}>
                      {person.total_score.toFixed(1)}
                    </div>
                    <div className="text-zinc-500 text-xs">综合评分</div>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-4 gap-2">
                  <div className="text-center p-2 rounded-lg bg-white/[0.02]">
                    <div className="text-blue-400 text-sm font-medium">{person.influence_score.toFixed(0)}</div>
                    <div className="text-zinc-600 text-xs">影响力</div>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-white/[0.02]">
                    <div className="text-emerald-400 text-sm font-medium">{person.activity_score.toFixed(0)}</div>
                    <div className="text-zinc-600 text-xs">活跃度</div>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-white/[0.02]">
                    <div className="text-amber-400 text-sm font-medium">{person.accuracy_score.toFixed(0)}</div>
                    <div className="text-zinc-600 text-xs">准确度</div>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-white/[0.02]">
                    <div className="text-violet-400 text-sm font-medium">{person.network_score.toFixed(0)}</div>
                    <div className="text-zinc-600 text-xs">网络值</div>
                  </div>
                </div>

                {Object.keys(person.industry_scores || {}).length > 0 && (
                  <div className="mt-3 flex items-center gap-2 flex-wrap">
                    <span className="text-zinc-600 text-xs">行业评分:</span>
                    {Object.entries(person.industry_scores).slice(0, 3).map(([industry, data]: [string, any]) => (
                      <Badge key={industry} variant="secondary" className="bg-zinc-500/20 text-zinc-400 text-xs">
                        {industry}: {data.total_score?.toFixed(0) || 0}
                      </Badge>
                    ))}
                  </div>
                )}

                <div className="mt-3 flex items-center justify-between text-xs text-zinc-600">
                  <div className="flex items-center gap-3">
                    <span>粉丝: {person.followers_count}</span>
                    <span>新闻: {person.news_mentions}</span>
                    <span>研报: {person.report_count}</span>
                  </div>
                  <Eye className="w-4 h-4" />
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
