'use client'

import { useEffect, useState, useRef } from 'react'
import Link from 'next/link'
import dynamic from 'next/dynamic'
import { 
  Bot, Network, Database, ArrowRight, Sparkles, Zap, Shield,
  ChevronRight, TrendingUp, Users, BarChart3
} from 'lucide-react'
import { Button, Badge } from '@/components/ui'

const HeroGlobe = dynamic(
  () => import('@/components/visualization/HeroGlobe'),
  { ssr: false }
)

const features = [
  { icon: BarChart3, title: '智能分析', description: '实时交互画布，整合宏观、政策、财务、技术分析', href: '/analysis', gradient: 'from-cyan-500 to-blue-600', color: '#06b6d4', stats: '实时更新' },
  { icon: TrendingUp, title: '量化分析', description: '因子管理、策略开发、回测评测、自定义因子', href: '/quant', gradient: 'from-rose-500 to-pink-600', color: '#f43f5e', stats: '生产级' },
  { icon: Bot, title: '智能问答', description: '自然语言交互，即时获得专业金融分析', href: '/finchat', gradient: 'from-amber-500 to-orange-600', color: '#f59e0b', stats: '24/7 在线' },
  { icon: Network, title: '知识图谱', description: '实体关系可视化，发现隐藏的投资机会', href: '/knowledge-graph', gradient: 'from-violet-500 to-purple-600', color: '#8b5cf6', stats: '10万+ 实体' },
]

const quickQuestions = [
  { text: '浦发银行的市盈率是多少', category: '估值查询', color: '#f59e0b' },
  { text: '分析一下贵州茅台的投资价值', category: '深度分析', color: '#8b5cf6' },
  { text: '银行业的发展趋势如何', category: '行业研究', color: '#10b981' },
  { text: '巴菲特怎么看比亚迪', category: '投资观点', color: '#ec4899' },
]

const stats = [
  { label: '数据覆盖', value: '5000+', suffix: '只股票', icon: TrendingUp },
  { label: '分析维度', value: '100+', suffix: '个指标', icon: Database },
  { label: '响应速度', value: '<1', suffix: '秒', icon: Zap },
  { label: '用户信赖', value: '10万+', suffix: '次查询', icon: Users },
]

const trustItems = [
  { icon: Shield, title: '安全可靠', description: '企业级数据安全，多重加密保护', color: '#10b981' },
  { icon: Zap, title: '实时响应', description: '毫秒级响应速度，即时获取分析结果', color: '#f59e0b' },
  { icon: Sparkles, title: '持续进化', description: '模型持续优化，分析能力不断提升', color: '#8b5cf6' },
]

export default function HomePage() {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      <HeroGlobe />

      <div className="relative z-20 bg-[var(--bg-primary)]">
        <section className="relative py-20 px-6">
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-12">
              <Badge variant="secondary" className="mb-4">核心功能</Badge>
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">一站式金融分析平台</h2>
              <p className="text-zinc-400 max-w-xl mx-auto">整合多种数据源与分析工具，为您提供全方位的金融分析能力</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
              {features.map((feature, index) => {
                const Icon = feature.icon
                return (
                  <Link key={feature.title} href={feature.href} className="group relative p-6 rounded-3xl bg-white/[0.02] border border-white/[0.05] hover:border-white/10 overflow-hidden transition-all duration-500 hover:-translate-y-1">
                    <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500" style={{ background: `radial-gradient(circle at 50% 0%, ${feature.color}12, transparent 60%)` }} />
                    <div className="relative z-10">
                      <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300 mb-4`}>
                        <Icon className="w-6 h-6 text-white" />
                      </div>
                      <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-amber-400 transition-colors">{feature.title}</h3>
                      <p className="text-zinc-400 mb-4 leading-relaxed text-sm">{feature.description}</p>
                      <div className="flex items-center justify-between">
                        <Badge variant="secondary" size="sm">{feature.stats}</Badge>
                        <ChevronRight className="w-4 h-4 text-zinc-600 group-hover:text-amber-400 transition-colors" />
                      </div>
                    </div>
                  </Link>
                )
              })}
            </div>
          </div>
        </section>

        <section className="relative py-20 px-6">
          <div className="max-w-6xl mx-auto">
            <div className="relative p-8 md:p-10 rounded-3xl bg-gradient-to-br from-amber-500/5 via-orange-500/3 to-transparent border border-amber-500/10 overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/10 rounded-full blur-[80px]" />
              <div className="absolute bottom-0 left-0 w-48 h-48 bg-orange-500/10 rounded-full blur-[60px]" />
              
              <div className="relative z-10">
                <div className="flex flex-col md:flex-row md:items-center gap-4 mb-8">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/20 flex-shrink-0">
                    <Bot className="w-7 h-7 text-white" />
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold text-white">快速开始</h3>
                    <p className="text-zinc-400">尝试以下问题，体验智能问答的强大功能</p>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {quickQuestions.map((question, index) => (
                    <Link key={index} href={`/finchat?q=${encodeURIComponent(question.text)}`} className="group flex items-center gap-4 p-4 rounded-2xl bg-white/[0.03] border border-white/[0.05] hover:border-white/10 hover:bg-white/[0.05] transition-all duration-300">
                      <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ backgroundColor: `${question.color}15` }}>
                        <Sparkles className="w-5 h-5" style={{ color: question.color }} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <span className="text-sm text-zinc-300 group-hover:text-white transition-colors block truncate">{question.text}</span>
                        <span className="text-xs text-zinc-600">{question.category}</span>
                      </div>
                      <ChevronRight className="w-5 h-5 text-zinc-600 group-hover:text-amber-400 transition-colors flex-shrink-0" />
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="relative py-20 px-6">
          <div className="max-w-6xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {trustItems.map((item, index) => {
                const Icon = item.icon
                return (
                  <div key={item.title} className="flex items-start gap-4 p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:border-white/10 transition-all duration-300">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0" style={{ backgroundColor: `${item.color}15` }}>
                      <Icon className="w-6 h-6" style={{ color: item.color }} />
                    </div>
                    <div>
                      <h4 className="text-lg font-semibold text-white mb-1">{item.title}</h4>
                      <p className="text-sm text-zinc-500 leading-relaxed">{item.description}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        <footer className="relative border-t border-white/[0.05] py-8 px-6">
          <div className="max-w-6xl mx-auto">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <span className="text-sm text-zinc-500">© 2024 OpenFinance. All rights reserved.</span>
              </div>
              <div className="flex items-center gap-8">
                <Link href="/docs" className="text-sm text-zinc-500 hover:text-white transition-colors">文档</Link>
                <Link href="/api" className="text-sm text-zinc-500 hover:text-white transition-colors">API</Link>
                <Link href="/about" className="text-sm text-zinc-500 hover:text-white transition-colors">关于</Link>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  )
}
