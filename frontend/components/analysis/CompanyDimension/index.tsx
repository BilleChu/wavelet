'use client'

import { useState } from 'react'
import { Search, TrendingUp, BarChart3, DollarSign, Newspaper, FileText, Activity, LineChart, Wallet, RefreshCw, PieChart, LayoutDashboard } from 'lucide-react'
import KLineChart from './KLineChart'
import FinancialPanel from './FinancialPanel'
import NewsPanel from './NewsPanel'
import TechIndicatorsPanel from './TechIndicatorsPanel'
import ResearchReportsPanel from './ResearchReportsPanel'
import QuantFactorsPanel from './QuantFactorsPanel'
import CashflowPanel from './CashflowPanel'
import ProfitPanel from './ProfitPanel'
import StockOverview from '@/components/analysis/StockOverview'
import { FinancialHealthCard, TechCard, SentimentCard } from '@/components/analysis/StockAnalysis'
import { Badge, Button } from '@/components/ui'

const HOT_STOCKS = [
  { code: '600000', name: '浦发银行' },
  { code: '000001', name: '平安银行' },
  { code: '600519', name: '贵州茅台' },
  { code: '002594', name: '比亚迪' },
  { code: '601318', name: '中国平安' },
  { code: '000858', name: '五粮液' },
]

type TabType = 'overview' | 'kline' | 'financial' | 'profit' | 'cashflow' | 'quant' | 'tech' | 'news' | 'reports'

export default function CompanyDimension() {
  const [selectedStock, setSelectedStock] = useState(HOT_STOCKS[0])
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [refreshKey, setRefreshKey] = useState(0)

  const tabs = [
    { id: 'overview' as TabType, name: '概览', icon: LayoutDashboard },
    { id: 'kline' as TabType, name: 'K线图', icon: TrendingUp },
    { id: 'financial' as TabType, name: '财务数据', icon: DollarSign },
    { id: 'profit' as TabType, name: '利润分析', icon: PieChart },
    { id: 'cashflow' as TabType, name: '现金流', icon: Wallet },
    { id: 'quant' as TabType, name: '量化因子', icon: LineChart },
    { id: 'tech' as TabType, name: '技术指标', icon: Activity },
    { id: 'news' as TabType, name: '新闻资讯', icon: Newspaper },
    { id: 'reports' as TabType, name: '研报分析', icon: FileText },
  ]

  const handleSearch = () => {
    if (searchQuery.trim()) {
      setSelectedStock({ code: searchQuery.trim(), name: searchQuery.trim() })
      setSearchQuery('')
    }
  }

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="输入股票代码或名称..."
            className="w-full pl-10 pr-4 py-2.5 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-cyan-500/40 transition-all"
          />
        </div>
        
        <Button onClick={handleSearch} size="sm">
          搜索
        </Button>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-zinc-500 mr-2">热门股票:</span>
        {HOT_STOCKS.map((stock) => (
          <button
            key={stock.code}
            onClick={() => setSelectedStock(stock)}
            className={`
              px-3 py-1.5 rounded-lg text-xs font-medium transition-all
              ${selectedStock.code === stock.code
                ? 'bg-gradient-to-r from-amber-500 to-orange-600 text-white'
                : 'bg-white/[0.03] text-zinc-400 hover:text-white hover:bg-white/[0.06] border border-white/[0.05]'
              }
            `}
          >
            {stock.name}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-3 p-4 rounded-xl bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/20">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
          <BarChart3 className="w-6 h-6 text-white" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-white">{selectedStock.name}</h3>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant="secondary">{selectedStock.code}</Badge>
            <span className="text-xs text-zinc-500">点击上方标签查看详细数据</span>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleRefresh}
          className="gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          刷新
        </Button>
      </div>

      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-lg transition-all whitespace-nowrap
                ${isActive
                  ? 'bg-white/[0.08] text-white border border-white/[0.1]'
                  : 'text-zinc-400 hover:text-white hover:bg-white/[0.03]'
                }
              `}
            >
              <Icon className="w-4 h-4" />
              <span className="text-sm font-medium">{tab.name}</span>
            </button>
          )
        })}
      </div>

      <div className="min-h-[500px]" key={refreshKey}>
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <StockOverview code={selectedStock.code} />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <FinancialHealthCard code={selectedStock.code} />
              <TechCard code={selectedStock.code} />
            </div>
            <SentimentCard code={selectedStock.code} />
          </div>
        )}
        
        {activeTab === 'kline' && (
          <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
            <KLineChart stockCode={selectedStock.code} />
          </div>
        )}
        
        {activeTab === 'financial' && (
          <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
            <h3 className="text-lg font-semibold text-white mb-4">财务数据</h3>
            <FinancialPanel stockCode={selectedStock.code} />
          </div>
        )}
        
        {activeTab === 'profit' && (
          <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
            <h3 className="text-lg font-semibold text-white mb-4">利润分析</h3>
            <ProfitPanel stockCode={selectedStock.code} />
          </div>
        )}
        
        {activeTab === 'cashflow' && (
          <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
            <h3 className="text-lg font-semibold text-white mb-4">现金流分析</h3>
            <CashflowPanel stockCode={selectedStock.code} />
          </div>
        )}
        
        {activeTab === 'quant' && (
          <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
            <h3 className="text-lg font-semibold text-white mb-4">量化因子</h3>
            <QuantFactorsPanel stockCode={selectedStock.code} />
          </div>
        )}
        
        {activeTab === 'tech' && (
          <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
            <h3 className="text-lg font-semibold text-white mb-4">技术指标</h3>
            <TechIndicatorsPanel stockCode={selectedStock.code} />
          </div>
        )}
        
        {activeTab === 'news' && (
          <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
            <h3 className="text-lg font-semibold text-white mb-4">新闻资讯</h3>
            <NewsPanel stockCode={selectedStock.code} limit={10} />
          </div>
        )}
        
        {activeTab === 'reports' && (
          <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
            <h3 className="text-lg font-semibold text-white mb-4">研报分析</h3>
            <ResearchReportsPanel stockCode={selectedStock.code} limit={5} />
          </div>
        )}
      </div>
    </div>
  )
}
