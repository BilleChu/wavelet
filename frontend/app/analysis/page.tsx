'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  RefreshCw, Sparkles, Send, Loader2, Clock, Shield, Zap, Package, AlertCircle
} from 'lucide-react'
import { Button, Badge } from '@/components/ui'
import DimensionTabs, { DimensionType } from '@/components/analysis/common/DimensionTabs'
import SkillMarketButton, { SkillRecommendation } from '@/components/analysis/common/SkillMarketButton'
import CompanyDimension from '@/components/analysis/CompanyDimension'
import MacroDimension from '@/components/analysis/MacroDimension'
import IndustryDimension from '@/components/analysis/IndustryDimension'
import MarketOverview from '@/components/analysis/Overview'
import {
  analysisService,
  type AnalysisResponse,
} from '@/services/analysisService'

export default function AnalysisPage() {
  const [activeDimension, setActiveDimension] = useState<DimensionType>('overview')
  const [aiQuery, setAiQuery] = useState('')
  const [aiResponse, setAiResponse] = useState<AnalysisResponse | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleAiAnalyze = useCallback(async () => {
    if (!aiQuery.trim() || aiLoading) return

    setAiLoading(true)
    setError(null)
    
    try {
      const response = await analysisService.analyze({
        query: aiQuery,
      })
      setAiResponse(response)
    } catch (error) {
      console.error('AI analysis failed:', error)
      setError('AI分析失败，请稍后重试')
    } finally {
      setAiLoading(false)
    }
  }, [aiQuery, aiLoading])

  const renderDimension = () => {
    try {
      switch (activeDimension) {
        case 'overview':
          return <MarketOverview />
        case 'company':
          return <CompanyDimension />
        case 'macro':
          return <MacroDimension />
        case 'industry':
          return <IndustryDimension />
        default:
          return null
      }
    } catch (err) {
      console.error('Failed to render dimension:', err)
      return (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <AlertCircle className="w-12 h-12 text-rose-400 mx-auto mb-4" />
            <p className="text-zinc-400">加载失败，请刷新页面重试</p>
          </div>
        </div>
      )
    }
  }

  const getDimensionSkills = () => {
    switch (activeDimension) {
      case 'overview':
        return [
          { id: 'market-overview', name: '市场概览', description: '全市场综合分析' },
          { id: 'macro-analysis', name: '宏观分析', description: '宏观经济趋势分析' },
          { id: 'sector-rotation', name: '板块轮动', description: '板块轮动策略' },
        ]
      case 'company':
        return [
          { id: 'financial-analysis', name: '财务分析', description: '深度财务指标分析' },
          { id: 'tech-indicator', name: '技术分析', description: 'K线与技术指标分析' },
          { id: 'buffett-investment', name: '巴菲特投资', description: '价值投资分析' },
          { id: 'momentum-strategy', name: '动量策略', description: '量化动量策略' },
        ]
      case 'macro':
        return [
          { id: 'macro-analysis', name: '宏观分析', description: '宏观经济趋势分析' },
          { id: 'policy-monitor', name: '政策监控', description: '政策动态追踪' },
          { id: 'interest-rate', name: '利率分析', description: '利率走势预测' },
        ]
      case 'industry':
        return [
          { id: 'industry-compare', name: '行业对比', description: '多行业横向对比' },
          { id: 'sector-rotation', name: '板块轮动', description: '板块轮动策略' },
        ]
      default:
        return []
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-[100px]" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-amber-500/10 rounded-full blur-[100px]" />
      </div>

      <div className="relative z-10 border-b border-white/[0.05] bg-[var(--bg-primary)]/80 backdrop-blur-xl sticky top-0">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <DimensionTabs
                activeDimension={activeDimension}
                onDimensionChange={setActiveDimension}
              />
            </div>

            <div className="flex items-center gap-4">
              <SkillMarketButton installedCount={6} />
            </div>
          </div>
        </div>
      </div>

      <main className="relative z-10 max-w-7xl mx-auto px-6 py-6">
        <div className="mb-6">
          {renderDimension()}
        </div>

        <div className="mt-8 p-6 rounded-2xl bg-gradient-to-br from-cyan-500/5 via-violet-500/5 to-transparent border border-white/[0.05]">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-violet-600 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-white">AI 智能分析</h3>
              <p className="text-xs text-zinc-500">基于当前维度数据进行智能分析</p>
            </div>
          </div>

          <div className="flex gap-3 mb-5">
            <input
              type="text"
              value={aiQuery}
              onChange={(e) => setAiQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAiAnalyze()}
              placeholder={`输入您的问题，例如：分析${activeDimension === 'company' ? '当前股票' : activeDimension === 'macro' ? '宏观经济' : '当前行业'}的投资机会...`}
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

          {error && (
            <div className="mb-4 p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
              {error}
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

        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { icon: Shield, title: '数据可信', description: '所有数据标注来源与置信度', color: '#10b981' },
            { icon: Clock, title: '实时更新', description: '数据实时从数据库查询', color: '#f59e0b' },
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

        <div className="mt-8 p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
                <Package className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="font-semibold text-white">推荐技能</h3>
                <p className="text-xs text-zinc-500">基于当前维度推荐相关技能</p>
              </div>
            </div>
          </div>

          <SkillRecommendation skills={getDimensionSkills()} />
        </div>
      </main>
    </div>
  )
}
