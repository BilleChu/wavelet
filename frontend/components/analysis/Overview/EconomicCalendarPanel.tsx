'use client'

import React from 'react'
import { CalendarDays, ChevronRight } from 'lucide-react'

export default function EconomicCalendarPanel() {
  return (
    <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
            <CalendarDays className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">经济日历</h3>
            <p className="text-xs text-zinc-500">全球重要经济事件</p>
          </div>
        </div>
      </div>

      <div className="flex flex-col items-center justify-center py-8 text-zinc-500">
        <CalendarDays className="w-12 h-12 mb-3 opacity-30" />
        <p className="text-sm">暂无日历数据</p>
        <p className="text-xs mt-1">请稍后再试</p>
      </div>

      <div className="mt-4 pt-4 border-t border-white/[0.05] flex items-center justify-end">
        <a 
          href="/calendar" 
          className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
        >
          查看完整日历 <ChevronRight className="w-3 h-3" />
        </a>
      </div>
    </div>
  )
}
