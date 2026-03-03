'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button, Badge } from '@/components/ui'
import {
  ArrowLeft,
  RefreshCw,
  Users,
  Building2,
  MapPin,
  Award,
  Eye,
  Newspaper,
  Network,
  Calendar,
  ExternalLink,
  Briefcase,
} from 'lucide-react'
import PersonGraph from './PersonGraph'

interface PersonDetail {
  entity_id: string
  name: string
  person_type: string | null
  person_type_label: string | null
  title: string | null
  company: string | null
  industry: string | null
  avatar_url: string | null
  verified: boolean
  biography: string | null
  certifications: string[]
  social_links: Record<string, string>
  work_history: Record<string, any>[]
  education: Record<string, any>[]
  focus_industries: Record<string, any>[]
  managed_assets: number | null
  investment_style: string | null
  total_score: number
  influence_score: number
  activity_score: number
  accuracy_score: number
  network_score: number
  industry_score: number
  followers_count: number
  news_mentions: number
  report_count: number
  industry_scores: Record<string, any>
  created_at: string | null
  updated_at: string | null
}

interface Activity {
  activity_id: string
  activity_type: string
  title: string
  content: string | null
  source: string | null
  source_url: string | null
  industry: string | null
  sentiment_score: number | null
  impact_score: number | null
  related_codes: string[]
  related_entities: string[]
  activity_date: string | null
}

interface ActivityListResponse {
  activities: Activity[]
  total: number
  page: number
  page_size: number
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

const activityTypeLabels: Record<string, string> = {
  news: '新闻',
  report: '研报',
  investment: '投资',
  speech: '演讲',
  social: '社交',
}

const activityTypeColors: Record<string, string> = {
  news: 'bg-blue-500/20 text-blue-400',
  report: 'bg-violet-500/20 text-violet-400',
  investment: 'bg-emerald-500/20 text-emerald-400',
  speech: 'bg-amber-500/20 text-amber-400',
  social: 'bg-pink-500/20 text-pink-400',
}

export default function PersonDetailPage() {
  const params = useParams()
  const router = useRouter()
  const entityId = params.entity_id as string

  const [person, setPerson] = useState<PersonDetail | null>(null)
  const [activities, setActivities] = useState<Activity[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overview' | 'activities' | 'graph'>('overview')

  const fetchPerson = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/persons/${entityId}`)
      if (response.ok) {
        const data: PersonDetail = await response.json()
        setPerson(data)
      } else {
        console.error('Person not found')
      }
    } catch (err) {
      console.error('Failed to fetch person:', err)
    } finally {
      setLoading(false)
    }
  }, [entityId])

  const fetchActivities = useCallback(async () => {
    try {
      const response = await fetch(`/api/persons/${entityId}/activities?page=1&page_size=10`)
      if (response.ok) {
        const data: ActivityListResponse = await response.json()
        setActivities(data.activities)
      }
    } catch (err) {
      console.error('Failed to fetch activities:', err)
    }
  }, [entityId])

  useEffect(() => {
    fetchPerson()
    fetchActivities()
  }, [fetchPerson, fetchActivities])

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400'
    if (score >= 60) return 'text-amber-400'
    if (score >= 40) return 'text-orange-400'
    return 'text-zinc-400'
  }

  const getScoreBgColor = (score: number) => {
    if (score >= 80) return 'from-emerald-500/20 to-emerald-600/10'
    if (score >= 60) return 'from-amber-500/20 to-amber-600/10'
    if (score >= 40) return 'from-orange-500/20 to-orange-600/10'
    return 'from-zinc-500/20 to-zinc-600/10'
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-[var(--accent-gold)]" />
      </div>
    )
  }

  if (!person) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-zinc-500">
        <Users className="w-12 h-12 mb-4" />
        <p>人物不存在</p>
        <Button variant="outline" size="sm" className="mt-4" onClick={() => router.push('/datacenter/persons')}>
          返回列表
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/datacenter/persons">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回
          </Button>
        </Link>
      </div>

      <div className="glass-panel p-6">
        <div className="flex items-start gap-6">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white font-bold text-3xl shadow-lg shadow-violet-500/20">
            {person.name.charAt(0)}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold text-white">{person.name}</h1>
              {person.verified && (
                <Badge variant="secondary" className="bg-blue-500/20 text-blue-400">
                  已认证
                </Badge>
              )}
              {person.person_type && (
                <Badge variant="secondary" className={personTypeColors[person.person_type] || 'bg-zinc-500/20 text-zinc-400'}>
                  {person.person_type_label || personTypeLabels[person.person_type]}
                </Badge>
              )}
            </div>
            {person.title && (
              <p className="text-zinc-400 mt-1">{person.title}</p>
            )}
            <div className="flex items-center gap-4 mt-2 text-sm text-zinc-500">
              {person.company && (
                <span className="flex items-center gap-1">
                  <Building2 className="w-4 h-4" />
                  {person.company}
                </span>
              )}
              {person.industry && (
                <span className="flex items-center gap-1">
                  <MapPin className="w-4 h-4" />
                  {person.industry}
                </span>
              )}
            </div>
            {person.biography && (
              <p className="text-zinc-400 text-sm mt-3 line-clamp-2">{person.biography}</p>
            )}
          </div>
          <div className="text-right">
            <div className={`text-4xl font-bold ${getScoreColor(person.total_score)}`}>
              {person.total_score.toFixed(1)}
            </div>
            <div className="text-zinc-500 text-sm">综合评分</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-5 gap-4">
        <div className={`glass-panel p-4 bg-gradient-to-br ${getScoreBgColor(person.influence_score)}`}>
          <div className="text-zinc-500 text-xs mb-1">影响力</div>
          <div className={`text-2xl font-bold ${getScoreColor(person.influence_score)}`}>
            {person.influence_score.toFixed(0)}
          </div>
          <div className="text-zinc-600 text-xs mt-1">/ 30分</div>
        </div>
        <div className={`glass-panel p-4 bg-gradient-to-br ${getScoreBgColor(person.activity_score)}`}>
          <div className="text-zinc-500 text-xs mb-1">活跃度</div>
          <div className={`text-2xl font-bold ${getScoreColor(person.activity_score)}`}>
            {person.activity_score.toFixed(0)}
          </div>
          <div className="text-zinc-600 text-xs mt-1">/ 20分</div>
        </div>
        <div className={`glass-panel p-4 bg-gradient-to-br ${getScoreBgColor(person.accuracy_score)}`}>
          <div className="text-zinc-500 text-xs mb-1">准确度</div>
          <div className={`text-2xl font-bold ${getScoreColor(person.accuracy_score)}`}>
            {person.accuracy_score.toFixed(0)}
          </div>
          <div className="text-zinc-600 text-xs mt-1">/ 15分</div>
        </div>
        <div className={`glass-panel p-4 bg-gradient-to-br ${getScoreBgColor(person.network_score)}`}>
          <div className="text-zinc-500 text-xs mb-1">网络值</div>
          <div className={`text-2xl font-bold ${getScoreColor(person.network_score)}`}>
            {person.network_score.toFixed(0)}
          </div>
          <div className="text-zinc-600 text-xs mt-1">/ 10分</div>
        </div>
        <div className={`glass-panel p-4 bg-gradient-to-br ${getScoreBgColor(person.industry_score)}`}>
          <div className="text-zinc-500 text-xs mb-1">行业分</div>
          <div className={`text-2xl font-bold ${getScoreColor(person.industry_score)}`}>
            {person.industry_score.toFixed(0)}
          </div>
          <div className="text-zinc-600 text-xs mt-1">/ 25分</div>
        </div>
      </div>

      <div className="flex border-b border-white/[0.05]">
        {[
          { id: 'overview', label: '概览', icon: Eye },
          { id: 'activities', label: '动态', icon: Newspaper },
          { id: 'graph', label: '知识图谱', icon: Network },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`flex items-center gap-2 px-6 py-3 text-sm font-medium transition-all ${
              activeTab === tab.id
                ? 'text-violet-400 border-b-2 border-violet-400'
                : 'text-zinc-500 hover:text-white'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2 space-y-4">
            {Object.keys(person.industry_scores || {}).length > 0 && (
              <div className="glass-panel p-5">
                <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                  <Award className="w-4 h-4 text-zinc-500" />
                  行业评分明细
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(person.industry_scores).map(([industry, data]: [string, any]) => (
                    <div key={industry} className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-white font-medium">{industry}</span>
                        <span className={`text-lg font-bold ${getScoreColor(data.total_score || 0)}`}>
                          {data.total_score?.toFixed(0) || 0}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div>
                          <span className="text-zinc-500">专业度</span>
                          <span className="text-zinc-400 ml-1">{data.expertise_score?.toFixed(0) || '-'}</span>
                        </div>
                        <div>
                          <span className="text-zinc-500">影响力</span>
                          <span className="text-zinc-400 ml-1">{data.influence_score?.toFixed(0) || '-'}</span>
                        </div>
                        <div>
                          <span className="text-zinc-500">准确度</span>
                          <span className="text-zinc-400 ml-1">{data.accuracy_score?.toFixed(0) || '-'}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {person.work_history && person.work_history.length > 0 && (
              <div className="glass-panel p-5">
                <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                  <Briefcase className="w-4 h-4 text-zinc-500" />
                  工作经历
                </h3>
                <div className="space-y-3">
                  {person.work_history.map((work: any, idx: number) => (
                    <div key={idx} className="flex items-start gap-3 p-3 rounded-lg bg-white/[0.02]">
                      <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center">
                        <Building2 className="w-4 h-4 text-violet-400" />
                      </div>
                      <div>
                        <p className="text-white font-medium">{work.company}</p>
                        <p className="text-zinc-500 text-sm">{work.title}</p>
                        {work.period && <p className="text-zinc-600 text-xs">{work.period}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {person.certifications && person.certifications.length > 0 && (
              <div className="glass-panel p-5">
                <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                  <Award className="w-4 h-4 text-zinc-500" />
                  专业资质
                </h3>
                <div className="flex flex-wrap gap-2">
                  {person.certifications.map((cert, idx) => (
                    <Badge key={idx} variant="secondary" className="bg-emerald-500/20 text-emerald-400">
                      {cert}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="space-y-4">
            <div className="glass-panel p-5">
              <h3 className="text-sm font-medium text-white mb-4">统计数据</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-zinc-500 text-sm">粉丝数</span>
                  <span className="text-white font-medium">{person.followers_count.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-zinc-500 text-sm">新闻提及</span>
                  <span className="text-white font-medium">{person.news_mentions}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-zinc-500 text-sm">研报数量</span>
                  <span className="text-white font-medium">{person.report_count}</span>
                </div>
                {person.managed_assets && (
                  <div className="flex items-center justify-between">
                    <span className="text-zinc-500 text-sm">管理资产</span>
                    <span className="text-white font-medium">{(person.managed_assets / 1e8).toFixed(2)}亿</span>
                  </div>
                )}
              </div>
            </div>

            {person.focus_industries && person.focus_industries.length > 0 && (
              <div className="glass-panel p-5">
                <h3 className="text-sm font-medium text-white mb-4">关注领域</h3>
                <div className="flex flex-wrap gap-2">
                  {person.focus_industries.map((item: any, idx: number) => (
                    <Badge key={idx} variant="secondary" className="bg-amber-500/20 text-amber-400">
                      {item.industry}
                      {item.weight && <span className="ml-1 opacity-60">({(item.weight * 100).toFixed(0)}%)</span>}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {person.social_links && Object.keys(person.social_links).length > 0 && (
              <div className="glass-panel p-5">
                <h3 className="text-sm font-medium text-white mb-4">社交账号</h3>
                <div className="space-y-2">
                  {Object.entries(person.social_links).map(([platform, account]) => (
                    <div key={platform} className="flex items-center justify-between text-sm">
                      <span className="text-zinc-500">{platform}</span>
                      <span className="text-zinc-400">{account}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'activities' && (
        <div className="glass-panel">
          <div className="p-4 border-b border-white/[0.05]">
            <h3 className="text-sm font-medium text-white flex items-center gap-2">
              <Newspaper className="w-4 h-4 text-zinc-500" />
              最新动态
            </h3>
          </div>
          {activities.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-zinc-500">
              <Newspaper className="w-10 h-10 mb-3" />
              <p>暂无动态数据</p>
            </div>
          ) : (
            <div className="divide-y divide-white/[0.05]">
              {activities.map((activity) => (
                <div key={activity.activity_id} className="p-4 hover:bg-white/[0.02]">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="secondary" className={activityTypeColors[activity.activity_type] || 'bg-zinc-500/20 text-zinc-400'}>
                          {activityTypeLabels[activity.activity_type] || activity.activity_type}
                        </Badge>
                        {activity.industry && (
                          <Badge variant="secondary" className="bg-zinc-500/20 text-zinc-400">
                            {activity.industry}
                          </Badge>
                        )}
                      </div>
                      <h4 className="text-white font-medium mb-1">{activity.title}</h4>
                      {activity.content && (
                        <p className="text-zinc-500 text-sm line-clamp-2">{activity.content}</p>
                      )}
                      <div className="flex items-center gap-4 mt-2 text-xs text-zinc-600">
                        {activity.source && <span>来源: {activity.source}</span>}
                        {activity.activity_date && (
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {formatDate(activity.activity_date)}
                          </span>
                        )}
                      </div>
                    </div>
                    {activity.source_url && (
                      <a
                        href={activity.source_url}
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
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'graph' && (
        <PersonGraph entityId={entityId} />
      )}
    </div>
  )
}
