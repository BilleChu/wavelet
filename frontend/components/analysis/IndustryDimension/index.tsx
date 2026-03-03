'use client'

import { useState, useEffect, useRef } from 'react'
import { Factory, TrendingUp, BarChart3, Loader2, Users } from 'lucide-react'
import { Badge } from '@/components/ui'

const INDUSTRIES = [
  { code: 'banking', name: '银行', description: '银行业金融机构' },
  { code: 'realestate', name: '房地产', description: '房地产开发与经营' },
  { code: 'medicine', name: '医药生物', description: '医药制造与生物技术' },
  { code: 'electronics', name: '电子', description: '电子元器件制造' },
  { code: 'computer', name: '计算机', description: '计算机软硬件' },
  { code: 'machinery', name: '机械设备', description: '专用设备制造' },
  { code: 'chemical', name: '化工', description: '化学原料制品' },
  { code: 'auto', name: '汽车', description: '汽车整车制造' },
]

const INDUSTRY_LEADERS: Record<string, Array<{ code: string; name: string }>> = {
  'banking': [
    { code: '601398', name: '工商银行' },
    { code: '601288', name: '农业银行' },
    { code: '601939', name: '建设银行' },
    { code: '600036', name: '招商银行' },
  ],
  'realestate': [
    { code: '000002', name: '万科A' },
    { code: '600048', name: '保利发展' },
    { code: '001979', name: '招商蛇口' },
  ],
  'medicine': [
    { code: '600276', name: '恒瑞医药' },
    { code: '000538', name: '云南白药' },
    { code: '300760', name: '迈瑞医疗' },
  ],
  'electronics': [
    { code: '000725', name: '京东方A' },
    { code: '002475', name: '立讯精密' },
    { code: '600584', name: '长电科技' },
  ],
  'computer': [
    { code: '002415', name: '海康威视' },
    { code: '300033', name: '同花顺' },
    { code: '002230', name: '科大讯飞' },
  ],
  'machinery': [
    { code: '600031', name: '三一重工' },
    { code: '000333', name: '美的集团' },
    { code: '000651', name: '格力电器' },
  ],
  'chemical': [
    { code: '600309', name: '万华化学' },
    { code: '002493', name: '荣盛石化' },
  ],
  'auto': [
    { code: '002594', name: '比亚迪' },
    { code: '601238', name: '广汽集团' },
    { code: '000625', name: '长安汽车' },
  ],
}

export default function IndustryDimension() {
  const [selectedIndustry, setSelectedIndustry] = useState(INDUSTRIES[0])
  const [loading, setLoading] = useState(false)
  const [industryData, setIndustryData] = useState<any>(null)
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadIndustryData()
  }, [selectedIndustry])

  const loadIndustryData = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/analysis/industry/${selectedIndustry.code}`)
      const data = await response.json()
      setIndustryData(data)
    } catch (error) {
      console.error('Failed to load industry data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!chartRef.current || !industryData) return

    const renderChart = async () => {
      const echarts = await import('echarts')
      const chart = echarts.init(chartRef.current!)

      const leaders = INDUSTRY_LEADERS[selectedIndustry.code] || []
      
      const option = {
        backgroundColor: 'transparent',
        animation: false,
        tooltip: {
          trigger: 'item',
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          borderColor: '#333',
          textStyle: { color: '#fff' }
        },
        legend: {
          orient: 'vertical',
          right: '5%',
          top: 'center',
          textStyle: { color: '#a1a1aa', fontSize: 11 }
        },
        series: [
          {
            name: '市值占比',
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['40%', '50%'],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 10,
              borderColor: '#111',
              borderWidth: 2
            },
            label: {
              show: false,
              position: 'center'
            },
            emphasis: {
              label: {
                show: true,
                fontSize: 14,
                fontWeight: 'bold',
                color: '#fff'
              }
            },
            labelLine: {
              show: false
            },
            data: leaders.map((leader, index) => ({
              value: 100 / leaders.length + Math.random() * 20,
              name: leader.name
            }))
          }
        ]
      }

      chart.setOption(option)

      const handleResize = () => chart.resize()
      window.addEventListener('resize', handleResize)

      return () => {
        window.removeEventListener('resize', handleResize)
        chart.dispose()
      }
    }

    renderChart()
  }, [industryData, selectedIndustry.code])

  const leaders = INDUSTRY_LEADERS[selectedIndustry.code] || []

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 overflow-x-auto pb-2">
        {INDUSTRIES.map((industry) => (
          <button
            key={industry.code}
            onClick={() => setSelectedIndustry(industry)}
            className={`
              flex items-center gap-2 px-4 py-2.5 rounded-xl transition-all whitespace-nowrap
              ${selectedIndustry.code === industry.code
                ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-lg'
                : 'bg-white/[0.03] text-zinc-400 hover:text-white hover:bg-white/[0.06] border border-white/[0.05]'
              }
            `}
          >
            <Factory className="w-4 h-4" />
            <span className="text-sm font-medium">{industry.name}</span>
          </button>
        ))}
      </div>

      <div className="p-6 rounded-2xl bg-gradient-to-br from-emerald-500/5 to-teal-500/5 border border-emerald-500/20">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
            <BarChart3 className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">{selectedIndustry.name}</h3>
            <p className="text-xs text-zinc-500">{selectedIndustry.description}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
            <div className="text-xs text-zinc-500 mb-1">行业指数</div>
            <div className="text-xl font-bold text-white">
              {industryData?.index_value?.toFixed(2) || '-'}
            </div>
          </div>
          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
            <div className="text-xs text-zinc-500 mb-1">涨跌幅</div>
            <div className={`text-xl font-bold ${industryData?.change_pct && industryData.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {industryData?.change_pct ? `${industryData.change_pct >= 0 ? '+' : ''}${industryData.change_pct.toFixed(2)}%` : '-'}
            </div>
          </div>
          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
            <div className="text-xs text-zinc-500 mb-1">市盈率</div>
            <div className="text-xl font-bold text-white">
              {industryData?.pe_ratio?.toFixed(2) || '-'}
            </div>
          </div>
          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
            <div className="text-xs text-zinc-500 mb-1">市净率</div>
            <div className="text-xl font-bold text-white">
              {industryData?.pb_ratio?.toFixed(2) || '-'}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-emerald-400" />
            <h4 className="text-base font-semibold text-white">行业龙头</h4>
          </div>
          
          <div className="space-y-3">
            {leaders.map((leader, index) => (
              <div
                key={leader.code}
                className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.05] hover:border-emerald-500/20 transition-all cursor-pointer"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500/20 to-teal-500/20 flex items-center justify-center text-xs font-bold text-emerald-400">
                    {index + 1}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-white">{leader.name}</div>
                    <Badge variant="secondary" size="sm">{leader.code}</Badge>
                  </div>
                </div>
                <TrendingUp className="w-4 h-4 text-emerald-400" />
              </div>
            ))}
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-emerald-400" />
            <h4 className="text-base font-semibold text-white">市值分布</h4>
          </div>
          
          <div ref={chartRef} style={{ width: '100%', height: '280px' }} />
        </div>
      </div>

      <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
        <h4 className="text-base font-semibold text-white mb-4">行业对比</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {INDUSTRIES.slice(0, 4).map((industry) => (
            <div
              key={industry.code}
              className={`p-4 rounded-xl border transition-all cursor-pointer ${
                selectedIndustry.code === industry.code
                  ? 'bg-emerald-500/10 border-emerald-500/30'
                  : 'bg-white/[0.02] border-white/[0.05] hover:border-emerald-500/20'
              }`}
              onClick={() => setSelectedIndustry(industry)}
            >
              <div className="text-sm font-medium text-white mb-2">{industry.name}</div>
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-zinc-500">PE</span>
                  <span className="text-white">-</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-zinc-500">PB</span>
                  <span className="text-white">-</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-zinc-500">涨跌</span>
                  <span className="text-white">-</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
