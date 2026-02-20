'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import {
  RefreshCw, TrendingUp, FileText, Building2, BarChart3,
  Sparkles, Send, Loader2, ChevronRight, Clock, Globe, Shield, Zap,
  Package, Store
} from 'lucide-react'
import { Button, Badge } from '@/components/ui'
import {
  analysisService,
  type CanvasData,
  type MacroIndicator,
  type PolicyItem,
  type CompanyFinancial,
  type TechIndicator,
  type AnalysisResponse,
} from '@/services/analysisService'

const REFRESH_INTERVAL = 5 * 60 * 1000

export default function AnalysisPage() {
  const [canvasData, setCanvasData] = useState<CanvasData | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [aiQuery, setAiQuery] = useState('')
  const [aiResponse, setAiResponse] = useState<AnalysisResponse | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [selectedPanel, setSelectedPanel] = useState<string | null>(null)

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }

    try {
      const data = await analysisService.getCanvasData()
      setCanvasData(data)
    } catch (error) {
      console.error('Failed to load canvas data:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    loadData()

    const interval = setInterval(() => {
      loadData(true)
    }, REFRESH_INTERVAL)

    return () => clearInterval(interval)
  }, [loadData])

  const handleAiAnalyze = async () => {
    if (!aiQuery.trim() || aiLoading) return

    setAiLoading(true)
    try {
      const response = await analysisService.analyze({
        query: aiQuery,
        panels: selectedPanel ? [selectedPanel] : undefined,
      })
      setAiResponse(response)
    } catch (error) {
      console.error('AI analysis failed:', error)
    } finally {
      setAiLoading(false)
    }
  }

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  const formatNumber = (num: number, decimals = 2) => {
    if (num >= 1e12) return `${(num / 1e12).toFixed(decimals)}万亿`
    if (num >= 1e8) return `${(num / 1e8).toFixed(decimals)}亿`
    if (num >= 1e4) return `${(num / 1e4).toFixed(decimals)}万`
    return num.toFixed(decimals)
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-emerald-400" />
      case 'down':
        return <TrendingUp className="w-4 h-4 text-rose-400 rotate-180" />
      default:
        return <div className="w-4 h-0.5 bg-zinc-500" />
    }
  }

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return 'text-emerald-400'
      case 'negative':
        return 'text-rose-400'
      default:
        return 'text-zinc-400'
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      {/* Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-[100px]" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-amber-500/10 rounded-full blur-[100px]" />
      </div>

      {/* Page Header */}
      <div className="relative z-10 border-b border-white/[0.05] bg-[var(--bg-primary)]/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                <BarChart3 className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-white">智能分析</h1>
                <p className="text-xs text-zinc-500">实时交互分析画布</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <Link href="/skills/marketplace">
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-2 bg-purple-500/10 border-purple-500/30 hover:bg-purple-500/20"
                >
                  <Store className="w-4 h-4" />
                  技能市场
                </Button>
              </Link>
              {canvasData && (
                <div className="flex items-center gap-2 text-xs text-zinc-500">
                  <Clock className="w-3.5 h-3.5" />
                  <span>更新于 {formatTime(canvasData.last_updated)}</span>
                </div>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => loadData(true)}
                disabled={refreshing}
                className="gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                刷新数据
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="relative z-10 max-w-7xl mx-auto px-6 py-6">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Macro Panel */}
            <div
              className={`p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:border-cyan-500/20 transition-all ${selectedPanel === 'macro' ? 'ring-2 ring-cyan-500/30' : ''}`}
              onClick={() => setSelectedPanel(selectedPanel === 'macro' ? null : 'macro')}
            >
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
                    <Globe className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">宏观经济</h3>
                    <p className="text-xs text-zinc-500">全球宏观经济数据与趋势</p>
                  </div>
                </div>
                <Badge variant="secondary">{canvasData?.macro.indicators.length || 0} 指标</Badge>
              </div>

              <div className="space-y-3">
                {canvasData?.macro.indicators.slice(0, 4).map((indicator: MacroIndicator) => (
                  <div
                    key={indicator.code}
                    className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/[0.03]"
                  >
                    <div className="flex items-center gap-3">
                      {getTrendIcon(indicator.trend)}
                      <div>
                        <span className="text-sm text-white">{indicator.name}</span>
                        <span className="text-xs text-zinc-500 ml-2">({indicator.unit})</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-white font-medium">
                        {indicator.current_value.value.toLocaleString()}
                      </span>
                      {indicator.yoy_change !== null && indicator.yoy_change !== undefined && (
                        <span className={`text-xs ml-2 ${indicator.yoy_change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {indicator.yoy_change >= 0 ? '+' : ''}{indicator.yoy_change}%
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Policy Panel */}
            <div
              className={`p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:border-violet-500/20 transition-all ${selectedPanel === 'policy' ? 'ring-2 ring-violet-500/30' : ''}`}
              onClick={() => setSelectedPanel(selectedPanel === 'policy' ? null : 'policy')}
            >
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
                    <FileText className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">政策动态</h3>
                    <p className="text-xs text-zinc-500">国家政策与关键经济指标</p>
                  </div>
                </div>
                <Badge variant="secondary">{canvasData?.policy.policies.length || 0} 条</Badge>
              </div>

              <div className="space-y-3">
                {canvasData?.policy.policies.slice(0, 3).map((policy: PolicyItem) => (
                  <div
                    key={policy.policy_id}
                    className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.03]"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <span className="text-sm text-white font-medium line-clamp-1">{policy.title}</span>
                      <Badge
                        size="sm"
                        className={policy.impact_level === 'high' ? 'bg-rose-500/20 text-rose-400' : 'bg-amber-500/20 text-amber-400'}
                      >
                        {policy.impact_level === 'high' ? '高影响' : '中影响'}
                      </Badge>
                    </div>
                    <p className="text-xs text-zinc-500 line-clamp-2 mb-2">{policy.summary}</p>
                    <div className="flex items-center gap-2 text-xs text-zinc-600">
                      <span>{policy.issuer}</span>
                      <span>·</span>
                      <span>{formatTime(policy.publish_date)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Company Panel */}
            <div
              className={`p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:border-amber-500/20 transition-all ${selectedPanel === 'company' ? 'ring-2 ring-amber-500/30' : ''}`}
              onClick={() => setSelectedPanel(selectedPanel === 'company' ? null : 'company')}
            >
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
                    <Building2 className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">公司财务</h3>
                    <p className="text-xs text-zinc-500">财务指标与新闻资讯</p>
                  </div>
                </div>
                <Badge variant="secondary">{canvasData?.company.companies.length || 0} 家</Badge>
              </div>

              <div className="space-y-3">
                {canvasData?.company.companies.slice(0, 3).map((company: CompanyFinancial) => (
                  <div
                    key={company.stock_code}
                    className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.03]"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-white font-medium">{company.stock_name}</span>
                        <Badge variant="secondary" size="sm">{company.stock_code}</Badge>
                      </div>
                      <span className="text-xs text-zinc-500">PE: {company.pe_ratio}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <span className="text-zinc-500">营收</span>
                        <p className="text-white font-medium">
                          {company.revenue ? formatNumber(company.revenue.value) : '-'}
                        </p>
                      </div>
                      <div>
                        <span className="text-zinc-500">净利润</span>
                        <p className="text-white font-medium">
                          {company.net_profit ? formatNumber(company.net_profit.value) : '-'}
                        </p>
                      </div>
                      <div>
                        <span className="text-zinc-500">ROE</span>
                        <p className="text-white font-medium">
                          {company.roe ? `${company.roe.value.toFixed(1)}%` : '-'}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Tech Panel */}
            <div
              className={`p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:border-emerald-500/20 transition-all ${selectedPanel === 'tech' ? 'ring-2 ring-emerald-500/30' : ''}`}
              onClick={() => setSelectedPanel(selectedPanel === 'tech' ? null : 'tech')}
            >
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
                    <BarChart3 className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">技术指标</h3>
                    <p className="text-xs text-zinc-500">实时监控与分析</p>
                  </div>
                </div>
                <Badge variant="secondary">{canvasData?.tech.indicators.length || 0} 只</Badge>
              </div>

              <div className="space-y-3">
                {canvasData?.tech.indicators.slice(0, 4).map((tech: TechIndicator) => (
                  <div
                    key={tech.stock_code}
                    className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/[0.03]"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-white/[0.05] flex items-center justify-center text-xs text-white font-medium">
                        {tech.stock_name.charAt(0)}
                      </div>
                      <div>
                        <span className="text-sm text-white">{tech.stock_name}</span>
                        <div className="flex items-center gap-2 text-xs text-zinc-500">
                          <span>RSI: {tech.rsi_14?.toFixed(1)}</span>
                          <span>MACD: {tech.macd?.toFixed(2)}</span>
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-white font-medium">{tech.price.toFixed(2)}</span>
                      <span className={`text-xs ml-1 ${tech.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {tech.change_pct >= 0 ? '+' : ''}{tech.change_pct.toFixed(2)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* AI Analysis Section */}
        <div className="mt-8 p-6 rounded-2xl bg-gradient-to-br from-cyan-500/5 via-violet-500/5 to-transparent border border-white/[0.05]">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-violet-600 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-white">AI 智能分析</h3>
              <p className="text-xs text-zinc-500">基于画布数据进行智能分析</p>
            </div>
          </div>

          <div className="flex gap-3 mb-5">
            <input
              type="text"
              value={aiQuery}
              onChange={(e) => setAiQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAiAnalyze()}
              placeholder="输入您的问题，例如：分析当前银行板块的投资机会..."
              className="flex-1 px-4 py-3 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-cyan-500/40 transition-all"
            />
            <Button onClick={handleAiAnalyze} disabled={aiLoading || !aiQuery.trim()} className="px-6">
              {aiLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </Button>
          </div>

          {selectedPanel && (
            <div className="mb-4 flex items-center gap-2 text-sm text-zinc-400">
              <span>已选择面板:</span>
              <Badge variant="default">{selectedPanel}</Badge>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setSelectedPanel(null)
                }}
                className="text-zinc-500 hover:text-white"
              >
                清除
              </button>
            </div>
          )}

          {aiResponse && (
            <div className="p-5 rounded-xl bg-white/[0.02] border border-white/[0.05] animate-fade-in">
              <div className="prose prose-invert prose-sm max-w-none">
                <div className="whitespace-pre-wrap text-zinc-300 leading-relaxed">
                  {aiResponse.content}
                </div>
              </div>

              <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/[0.05]">
                <div className="flex items-center gap-4 text-xs text-zinc-500">
                  <span>响应时间: {aiResponse.duration_ms.toFixed(0)}ms</span>
                  <span>置信度: {aiResponse.confidence}</span>
                </div>
                <div className="flex items-center gap-2">
                  {aiResponse.follow_up_suggestions.slice(0, 2).map((suggestion, i) => (
                    <button
                      key={i}
                      onClick={() => setAiQuery(suggestion)}
                      className="px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.05] text-xs text-zinc-400 hover:text-white hover:bg-white/[0.06] transition-all"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Trust Indicators */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { icon: Shield, title: '数据可信', description: '所有数据标注来源与置信度', color: '#10b981' },
            { icon: Clock, title: '实时更新', description: '每5分钟自动刷新数据', color: '#f59e0b' },
            { icon: Zap, title: '快速响应', description: 'AI分析响应时间<3秒', color: '#8b5cf6' },
          ].map((item) => {
            const Icon = item.icon
            return (
              <div
                key={item.title}
                className="flex items-center gap-4 p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]"
              >
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center"
                  style={{ backgroundColor: `${item.color}15` }}
                >
                  <Icon className="w-5 h-5" style={{ color: item.color }} />
                </div>
                <div>
                  <h4 className="text-sm font-medium text-white">{item.title}</h4>
                  <p className="text-xs text-zinc-500">{item.description}</p>
                </div>
              </div>
            )
          })}
        </div>

        {/* Available Skills */}
        <div className="mt-8 p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
                <Package className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-white">可用技能</h3>
                <p className="text-xs text-zinc-500">点击技能市场查看更多</p>
              </div>
            </div>
            <Link href="/skills/marketplace">
              <Button variant="outline" size="sm" className="gap-2">
                <Store className="w-4 h-4" />
                技能市场
              </Button>
            </Link>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { name: '财务分析', id: 'financial-analysis', color: 'from-cyan-500 to-blue-600' },
              { name: '宏观分析', id: 'macro-analysis', color: 'from-emerald-500 to-teal-600' },
              { name: '政策监控', id: 'policy-monitor', color: 'from-violet-500 to-purple-600' },
              { name: '技术指标', id: 'tech-indicator', color: 'from-amber-500 to-orange-600' },
              { name: '智能分析', id: 'intelligent-analysis', color: 'from-pink-500 to-rose-600' },
              { name: '巴菲特投资', id: 'buffett-investment', color: 'from-indigo-500 to-purple-600' },
            ].map((skill) => (
              <Link
                key={skill.id}
                href={`/skills/marketplace?skill=${skill.id}`}
                className="group"
              >
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.05] hover:border-purple-500/30 transition-all text-center">
                  <div className={`w-10 h-10 mx-auto rounded-lg bg-gradient-to-br ${skill.color} flex items-center justify-center mb-2 group-hover:scale-110 transition-transform`}>
                    <Sparkles className="w-5 h-5 text-white" />
                  </div>
                  <p className="text-xs text-white font-medium">{skill.name}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
