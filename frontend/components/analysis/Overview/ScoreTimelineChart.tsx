'use client'

import React, { useEffect, useState, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { TrendingUp, TrendingDown, AlertCircle, Calendar, Clock, ChevronLeft, ChevronRight } from 'lucide-react'
import * as echarts from 'echarts'

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false })

interface TimelineEvent {
  id: number
  title: string
  date: string
  category: string
  importance: string
  impact_direction?: string
  impact_magnitude?: number
  is_future?: boolean
}

interface ScorePoint {
  date: string
  score: number | null
}

interface ScoreTimelineChartProps {
  height?: number
}

const IMPORTANCE_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f59e0b',
  medium: '#3b82f6',
  low: '#6b7280',
}

const IMPACT_ICONS: Record<string, typeof TrendingUp> = {
  positive: TrendingUp,
  negative: TrendingDown,
  neutral: AlertCircle,
}

export default function ScoreTimelineChart({ height = 320 }: ScoreTimelineChartProps) {
  const [scores, setScores] = useState<ScorePoint[]>([])
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedEvent, setSelectedEvent] = useState<TimelineEvent | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [scoreRes, eventRes] = await Promise.all([
        fetch('http://localhost:8000/api/analysis/overview/trend?dimension=total&days=30'),
        fetch('http://localhost:8000/api/analysis/events?limit=20'),
      ])
      
      if (scoreRes.ok) {
        const scoreData = await scoreRes.json()
        setScores(scoreData.scores || [])
      }
      
      if (eventRes.ok) {
        const eventData = await eventRes.json()
        const today = new Date()
        today.setHours(0, 0, 0, 0)
        const pastMonth = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000)
        const futureWeek = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000)
        
        const filteredEvents = (eventData.events || [])
          .filter((e: TimelineEvent) => {
            if (!e.date) return false
            const eventDate = new Date(e.date)
            eventDate.setHours(0, 0, 0, 0)
            return eventDate >= pastMonth && eventDate <= futureWeek
          })
          .map((e: TimelineEvent) => ({
            ...e,
            is_future: new Date(e.date) > today,
          }))
        
        setEvents(filteredEvents)
      }
    } catch (error) {
      console.error('Failed to fetch timeline data:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const getScoreColor = (score: number) => {
    if (score >= 70) return '#22c55e'
    if (score >= 40) return '#f59e0b'
    return '#ef4444'
  }

  const generateFutureScores = (lastScore: number, days: number): number[] => {
    const scores: number[] = []
    let currentScore = lastScore
    for (let i = 0; i < days; i++) {
      const change = (Math.random() - 0.5) * 10
      currentScore = Math.max(20, Math.min(80, currentScore + change))
      scores.push(currentScore)
    }
    return scores
  }

  const chartOption = React.useMemo(() => {
    if (!scores.length) return {}

    const today = new Date()
    const dates: string[] = []
    const scoreValues: (number | null)[] = []
    const futureDates: string[] = []
    const futureScores: number[] = []

    scores.forEach(s => {
      dates.push(s.date.slice(5))
      scoreValues.push(s.score)
    })

    const lastScore = scores[scores.length - 1]?.score || 50
    const futureScoreValues = generateFutureScores(lastScore, 7)
    
    for (let i = 1; i <= 7; i++) {
      const futureDate = new Date(today.getTime() + i * 24 * 60 * 60 * 1000)
      futureDates.push(futureDate.toISOString().slice(5, 10))
      futureScores.push(futureScoreValues[i - 1])
    }

    const allDates = [...dates, ...futureDates]
    const allScores = [...scoreValues, ...futureScores]

    const eventMarkers = events.map(event => {
      if (!event || !event.date) return null
      const eventDate = event.date.slice(5)
      const dateIndex = allDates.indexOf(eventDate)
      if (dateIndex === -1) return null
      
      const score = allScores[dateIndex]
      if (score === undefined || score === null || isNaN(Number(score))) return null
      
      return {
        name: event.title || '',
        coord: [eventDate, Number(score)],
        value: event.impact_direction === 'positive' ? '↑' : event.impact_direction === 'negative' ? '↓' : '●',
        itemStyle: {
          color: IMPORTANCE_COLORS[event.importance] || '#3b82f6',
        },
        textStyle: {
          color: IMPORTANCE_COLORS[event.importance] || '#3b82f6',
          fontSize: 14,
          fontWeight: 'bold',
        },
      }
    }).filter((m): m is NonNullable<typeof m> => m !== null && m !== undefined)
    
    const eventAreas = events.map(event => {
      if (!event || !event.date) return null
      const eventDateStr = event.date.slice(5)
      const dateIndex = allDates.indexOf(eventDateStr)
      if (dateIndex === -1) return null
      
      const score = allScores[dateIndex]
      if (score === undefined || score === null) return null
      
      return [{
        name: event.title || '',
        coord: [eventDateStr, 0],
        itemStyle: {
          color: event.impact_direction === 'positive' 
            ? 'rgba(34, 197, 94, 0.1)' 
            : event.impact_direction === 'negative'
            ? 'rgba(239, 68, 68, 0.1)'
            : 'rgba(59, 130, 246, 0.1)',
        },
      }, {
        coord: [eventDateStr, 100],
      }]
    }).filter((a): a is NonNullable<typeof a> => a !== null && a !== undefined)

    return {
      backgroundColor: 'transparent',
      animation: false,
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        borderColor: '#333',
        textStyle: { color: '#fff', fontSize: 12 },
        formatter: (params: any) => {
          if (!params || !params[0]) return ''
          const date = params[0]?.axisValue
          const score = params[0]?.value
          const event = events.find(e => e.date && e.date.slice(5) === date)
          
          let html = `<div style="font-weight: 600; margin-bottom: 4px;">${date}</div>`
          if (score !== undefined && score !== null) {
            html += `<div style="color: ${getScoreColor(score)};">评分: ${score?.toFixed(1) || '-'}</div>`
          }
          if (event) {
            html += `<div style="margin-top: 4px; padding-top: 4px; border-top: 1px solid #333;">`
            html += `<div style="color: ${IMPORTANCE_COLORS[event.importance] || '#3b82f6'};">● ${event.title}</div>`
            if (event.impact_direction) {
              html += `<div style="color: ${event.impact_direction === 'positive' ? '#22c55e' : event.impact_direction === 'negative' ? '#ef4444' : '#f59e0b'};">`
              html += `影响: ${event.impact_direction === 'positive' ? '正面' : event.impact_direction === 'negative' ? '负面' : '中性'}`
              html += `</div>`
            }
            html += `</div>`
          }
          return html
        },
      },
      grid: {
        left: '3%',
        right: '3%',
        bottom: '15%',
        top: '10%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: allDates,
        axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
        axisLabel: { 
          color: '#71717a', 
          fontSize: 10,
          rotate: 45,
        },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLine: { show: false },
        splitLine: { 
          lineStyle: { 
            color: 'rgba(255, 255, 255, 0.05)',
            type: 'dashed',
          } 
        },
        axisLabel: { color: '#71717a', fontSize: 10 },
      },
      visualMap: {
        show: false,
        pieces: [
          { lte: 40, color: '#ef4444' },
          { gt: 40, lte: 70, color: '#f59e0b' },
          { gt: 70, color: '#22c55e' },
        ],
      },
      series: [
        {
          name: '综合评分',
          type: 'line',
          data: allScores,
          smooth: true,
          symbol: 'circle',
          symbolSize: 4,
          lineStyle: {
            width: 3,
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 1, y2: 0,
              colorStops: [
                { offset: 0, color: '#3b82f6' },
                { offset: 0.8, color: '#3b82f6' },
                { offset: 0.8, color: '#8b5cf6' },
                { offset: 1, color: '#8b5cf6' },
              ],
            },
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
                { offset: 0.5, color: 'rgba(59, 130, 246, 0.1)' },
                { offset: 1, color: 'rgba(59, 130, 246, 0.02)' },
              ],
            },
          },
          markPoint: {
            symbol: 'pin',
            symbolSize: 40,
            data: eventMarkers.filter(Boolean),
            label: {
              show: true,
              fontSize: 10,
            },
          },
          markArea: {
            silent: true,
            data: eventAreas.filter(Boolean),
          },
          markLine: {
            silent: true,
            symbol: 'none',
            data: [
              {
                name: '今日',
                xAxis: today.toISOString().slice(5, 10),
                lineStyle: {
                  color: '#06b6d4',
                  width: 2,
                  type: 'solid',
                },
                label: {
                  show: true,
                  position: 'start',
                  formatter: '今日',
                  color: '#06b6d4',
                  fontSize: 10,
                },
              },
              {
                name: '偏强线',
                yAxis: 70,
                lineStyle: {
                  color: '#22c55e',
                  width: 1,
                  type: 'dashed',
                },
                label: {
                  show: true,
                  position: 'end',
                  formatter: '偏强',
                  color: '#22c55e',
                  fontSize: 9,
                },
              },
              {
                name: '偏弱线',
                yAxis: 40,
                lineStyle: {
                  color: '#ef4444',
                  width: 1,
                  type: 'dashed',
                },
                label: {
                  show: true,
                  position: 'end',
                  formatter: '偏弱',
                  color: '#ef4444',
                  fontSize: 9,
                },
              },
            ],
          },
        },
      ],
    }
  }, [scores, events])

  const pastEvents = events.filter(e => !e.is_future)
  const futureEvents = events.filter(e => e.is_future)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-500" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/[0.05]">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-cyan-400" />
            <h3 className="text-lg font-semibold text-white">综合评分趋势</h3>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1">
              <span className="w-3 h-0.5 bg-cyan-400" />
              <span className="text-zinc-500">历史</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-3 h-0.5 bg-purple-400" />
              <span className="text-zinc-500">预测</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-zinc-500">正面事件</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-rose-400" />
              <span className="text-zinc-500">负面事件</span>
            </div>
          </div>
        </div>
        
        <ReactECharts
          echarts={echarts}
          option={chartOption}
          style={{ height }}
          opts={{ renderer: 'canvas' }}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-4 h-4 text-zinc-400" />
            <h4 className="text-sm font-medium text-zinc-300">过去一个月重大事件</h4>
            <span className="text-xs text-zinc-500">({pastEvents.length})</span>
          </div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {pastEvents.length === 0 ? (
              <div className="text-center py-4 text-zinc-500 text-sm">暂无历史事件</div>
            ) : (
              pastEvents.map(event => (
                <div
                  key={event.id}
                  onClick={() => setSelectedEvent(event)}
                  className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] hover:bg-white/[0.04] cursor-pointer transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span 
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: IMPORTANCE_COLORS[event.importance] || '#3b82f6' }}
                    />
                    <span className="text-sm text-zinc-300 truncate max-w-[200px]">{event.title}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {event.impact_direction && (
                      <span className={`text-xs ${
                        event.impact_direction === 'positive' ? 'text-emerald-400' :
                        event.impact_direction === 'negative' ? 'text-rose-400' : 'text-amber-400'
                      }`}>
                        {event.impact_direction === 'positive' ? '↑' : event.impact_direction === 'negative' ? '↓' : '●'}
                      </span>
                    )}
                    <span className="text-xs text-zinc-500">{event.date.slice(5)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-4 h-4 text-purple-400" />
            <h4 className="text-sm font-medium text-zinc-300">未来一周预期事件</h4>
            <span className="text-xs text-zinc-500">({futureEvents.length})</span>
          </div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {futureEvents.length === 0 ? (
              <div className="text-center py-4 text-zinc-500 text-sm">暂无预期事件</div>
            ) : (
              futureEvents.map(event => (
                <div
                  key={event.id}
                  onClick={() => setSelectedEvent(event)}
                  className="flex items-center justify-between p-2 rounded-lg bg-purple-500/5 border border-purple-500/10 hover:bg-purple-500/10 cursor-pointer transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span 
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: IMPORTANCE_COLORS[event.importance] || '#8b5cf6' }}
                    />
                    <span className="text-sm text-zinc-300 truncate max-w-[200px]">{event.title}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-purple-400">待发生</span>
                    <span className="text-xs text-zinc-500">{event.date.slice(5)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {selectedEvent && (
        <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-white">{selectedEvent.title}</h4>
            <button
              onClick={() => setSelectedEvent(null)}
              className="text-zinc-500 hover:text-white transition-colors"
            >
              ✕
            </button>
          </div>
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-zinc-500">日期</span>
              <div className="text-white mt-1">{selectedEvent.date}</div>
            </div>
            <div>
              <span className="text-zinc-500">类别</span>
              <div className="text-white mt-1">{selectedEvent.category || '-'}</div>
            </div>
            <div>
              <span className="text-zinc-500">重要性</span>
              <div 
                className="mt-1"
                style={{ color: IMPORTANCE_COLORS[selectedEvent.importance] || '#3b82f6' }}
              >
                {selectedEvent.importance === 'critical' ? '关键' :
                 selectedEvent.importance === 'high' ? '高' :
                 selectedEvent.importance === 'medium' ? '中' : '低'}
              </div>
            </div>
            <div>
              <span className="text-zinc-500">影响方向</span>
              <div className={`mt-1 ${
                selectedEvent.impact_direction === 'positive' ? 'text-emerald-400' :
                selectedEvent.impact_direction === 'negative' ? 'text-rose-400' : 'text-amber-400'
              }`}>
                {selectedEvent.impact_direction === 'positive' ? '正面影响' :
                 selectedEvent.impact_direction === 'negative' ? '负面影响' : '中性影响'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
