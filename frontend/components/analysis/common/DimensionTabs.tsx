'use client'

import { Building2, Globe, Factory, LayoutDashboard } from 'lucide-react'

export type DimensionType = 'overview' | 'company' | 'macro' | 'industry'

interface DimensionTabsProps {
  activeDimension: DimensionType
  onDimensionChange: (dimension: DimensionType) => void
}

const dimensions = [
  {
    id: 'overview' as DimensionType,
    name: '概览',
    icon: LayoutDashboard,
    description: '市场综合评分概览',
    gradient: 'from-violet-500 to-purple-600',
  },
  {
    id: 'company' as DimensionType,
    name: '公司',
    icon: Building2,
    description: '公司财务与技术分析',
    gradient: 'from-amber-500 to-orange-600',
  },
  {
    id: 'macro' as DimensionType,
    name: '宏观',
    icon: Globe,
    description: '宏观经济与政策动态',
    gradient: 'from-cyan-500 to-blue-600',
  },
  {
    id: 'industry' as DimensionType,
    name: '行业',
    icon: Factory,
    description: '行业指数与对比分析',
    gradient: 'from-emerald-500 to-teal-600',
  },
]

export default function DimensionTabs({ activeDimension, onDimensionChange }: DimensionTabsProps) {
  return (
    <div className="flex items-center gap-2 p-1 bg-white/[0.02] rounded-xl border border-white/[0.05]">
      {dimensions.map((dim) => {
        const Icon = dim.icon
        const isActive = activeDimension === dim.id

        return (
          <button
            key={dim.id}
            onClick={() => onDimensionChange(dim.id)}
            className={`
              flex items-center gap-2 px-4 py-2.5 rounded-lg transition-all
              ${isActive
                ? `bg-gradient-to-r ${dim.gradient} text-white shadow-lg`
                : 'text-zinc-400 hover:text-white hover:bg-white/[0.05]'
              }
            `}
          >
            <Icon className="w-4 h-4" />
            <span className="text-sm font-medium">{dim.name}</span>
          </button>
        )
      })}
    </div>
  )
}
