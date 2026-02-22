'use client'

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import dynamic from 'next/dynamic'
import { ChevronDown, Activity, Globe2, TrendingUp, Zap, Sparkles } from 'lucide-react'

const Globe = dynamic(() => import('react-globe.gl'), { 
  ssr: false,
  loading: () => null
})

interface GlobalEvent {
  id: string
  title: string
  description: string
  type: 'market' | 'policy' | 'economic' | 'geopolitical' | 'technology'
  lat: number
  lng: number
  time: string
  impact: 'high' | 'medium' | 'low'
}

const mockEvents: GlobalEvent[] = [
  { id: '1', title: '美联储利率决议', description: '美联储宣布维持利率不变', type: 'policy', lat: 38.8977, lng: -77.0365, time: '2小时前', impact: 'high' },
  { id: '2', title: 'A股市场大涨', description: '沪深300指数上涨2.5%', type: 'market', lat: 31.2304, lng: 121.4737, time: '3小时前', impact: 'high' },
  { id: '3', title: '欧洲央行会议', description: '欧洲央行讨论货币政策', type: 'policy', lat: 50.1109, lng: 8.6821, time: '5小时前', impact: 'medium' },
  { id: '4', title: '日本GDP数据', description: '日本第四季度GDP增长1.2%', type: 'economic', lat: 35.6762, lng: 139.6503, time: '6小时前', impact: 'medium' },
  { id: '5', title: '科技股反弹', description: '纳斯达克指数上涨1.8%', type: 'market', lat: 37.7749, lng: -122.4194, time: '8小时前', impact: 'medium' },
  { id: '6', title: '原油价格波动', description: '布伦特原油突破85美元', type: 'market', lat: 25.2048, lng: 55.2708, time: '10小时前', impact: 'medium' },
  { id: '7', title: '人民币汇率', description: '人民币兑美元汇率稳定', type: 'economic', lat: 39.9042, lng: 116.4074, time: '12小时前', impact: 'low' },
  { id: '8', title: '英国通胀数据', description: '英国CPI同比上涨4.0%', type: 'economic', lat: 51.5074, lng: -0.1278, time: '1天前', impact: 'medium' },
]

const eventTypeColors: Record<string, string> = {
  market: '#f59e0b',
  policy: '#8b5cf6',
  economic: '#10b981',
  geopolitical: '#ef4444',
  technology: '#06b6d4',
}

const arcData = [
  { startLat: 31.2304, startLng: 121.4737, endLat: 37.7749, endLng: -122.4194, color: '#f59e0b' },
  { startLat: 35.6762, startLng: 139.6503, endLat: 37.7749, endLng: -122.4194, color: '#10b981' },
  { startLat: 51.5074, startLng: -0.1278, endLat: 38.8977, endLng: -77.0365, color: '#8b5cf6' },
  { startLat: 50.1109, startLng: 8.6821, endLat: 51.5074, endLng: -0.1278, color: '#06b6d4' },
  { startLat: 25.2048, startLng: 55.2708, endLat: 31.2304, endLng: 121.4737, color: '#f59e0b' },
  { startLat: 39.9042, startLng: 116.4074, endLat: 35.6762, endLng: 139.6503, color: '#10b981' },
]

export default function HeroGlobe() {
  const [mounted, setMounted] = useState(false)
  const [globeReady, setGlobeReady] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState<GlobalEvent | null>(null)
  const [scrollProgress, setScrollProgress] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const globeRef = useRef<any>(null)
  const rotationRef = useRef<number>(0)
  const animationFrameRef = useRef<number | null>(null)
  
  useEffect(() => {
    setMounted(true)
  }, [])
  
  useEffect(() => {
    const handleScroll = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        const progress = Math.max(0, Math.min(1, -rect.top / (rect.height - window.innerHeight)))
        setScrollProgress(progress)
      }
    }
    
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])
  
  useEffect(() => {
    if (!globeReady || !globeRef.current) return
    
    const animate = () => {
      rotationRef.current += 0.15
      if (globeRef.current) {
        globeRef.current.pointOfView({ lat: 20, lng: rotationRef.current, altitude: 2.5 }, 0)
      }
      animationFrameRef.current = requestAnimationFrame(animate)
    }
    
    animationFrameRef.current = requestAnimationFrame(animate)
    
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
    }
  }, [globeReady])
  
  const pointsData = useMemo(() => {
    return mockEvents.map(event => ({
      lat: event.lat,
      lng: event.lng,
      size: event.impact === 'high' ? 0.8 : event.impact === 'medium' ? 0.5 : 0.3,
      color: eventTypeColors[event.type],
      event,
    }))
  }, [])
  
  const handlePointClick = useCallback((point: any) => {
    if (point?.event) {
      setSelectedEvent(point.event)
    }
  }, [])
  
  const handleGlobeReady = useCallback(() => {
    setGlobeReady(true)
  }, [])
  
  const opacity = Math.max(0, 1 - scrollProgress * 2)
  const scale = Math.max(0.5, 1 - scrollProgress * 0.3)
  
  return (
    <div 
      ref={containerRef}
      className="relative min-h-[200vh]"
    >
      <div 
        className="fixed inset-0 z-0"
        style={{ opacity: globeReady ? opacity : 1 }}
      >
        <Globe
          ref={globeRef}
          globeImageUrl="//unpkg.com/three-globe/example/img/earth-dark.jpg"
          bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
          backgroundImageUrl="//unpkg.com/three-globe/example/img/night-sky.png"
          pointsData={pointsData}
          pointAltitude={0.02}
          pointLabel={({ event }: any) => `
            <div style="background: rgba(0,0,0,0.9); padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); min-width: 200px;">
              <div style="color: ${eventTypeColors[event.type]}; font-size: 12px; margin-bottom: 4px;">${event.type.toUpperCase()}</div>
              <div style="color: white; font-weight: 600; margin-bottom: 4px;">${event.title}</div>
              <div style="color: #a1a1aa; font-size: 12px;">${event.description}</div>
              <div style="color: #71717a; font-size: 11px; margin-top: 8px;">${event.time}</div>
            </div>
          `}
          pointsMerge={true}
          pointColor={({ color }: any) => color}
          pointRadius={({ size }: any) => size}
          arcsData={arcData}
          arcColor={'color'}
          arcDashLength={0.4}
          arcDashGap={0.2}
          arcDashAnimateTime={1500}
          arcStroke={0.5}
          atmosphereColor="#3b82f6"
          atmosphereAltitude={0.15}
          width={typeof window !== 'undefined' ? window.innerWidth : 1920}
          height={typeof window !== 'undefined' ? window.innerHeight : 1080}
          backgroundColor="rgba(3, 7, 18, 1)"
          enablePointerInteraction={true}
          onPointClick={handlePointClick}
          onGlobeReady={handleGlobeReady}
        />
        
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[#030712]" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#030712]/50 via-transparent to-[#030712]/50" />
        </div>
        
        <div className="absolute top-0 left-0 right-0 z-10 pointer-events-auto">
          <div className="max-w-7xl mx-auto px-6 pt-8">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <span className="text-xl font-bold text-white">OpenFinance</span>
              </div>
              
              <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 backdrop-blur-sm border border-white/10">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-sm text-zinc-300">实时监控中</span>
              </div>
            </div>
          </div>
        </div>
        
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10 pointer-events-auto text-center" style={{ transform: `translate(-50%, -50%) scale(${scale})` }}>
          <div className="mb-6">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 backdrop-blur-sm border border-white/10 mb-8">
              <Activity className="w-4 h-4 text-amber-500" />
              <span className="text-sm text-zinc-300">全球金融市场实时监控</span>
            </div>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight">
            <span className="block">基于大语言模型的</span>
            <span className="block bg-gradient-to-r from-amber-400 via-orange-500 to-red-500 bg-clip-text text-transparent">
              智能分析引擎
            </span>
          </h1>
          
          <p className="text-xl text-zinc-400 max-w-2xl mx-auto mb-12 leading-relaxed">
            融合人工智能与金融专业知识，为您提供实时、精准、个性化的投资决策支持
          </p>
          
          <div className="flex flex-wrap justify-center gap-4 mb-16">
            <button className="px-8 py-4 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 text-white font-semibold shadow-lg shadow-amber-500/25 hover:shadow-amber-500/40 transition-all hover:-translate-y-0.5">
              开始智能问答
            </button>
            <button className="px-8 py-4 rounded-xl bg-white/5 border border-white/10 text-white font-semibold hover:bg-white/10 transition-all">
              探索知识图谱
            </button>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto">
            {[
              { icon: Activity, label: '实时事件', value: '128', color: '#f59e0b' },
              { icon: Globe2, label: '覆盖地区', value: '45+', color: '#10b981' },
              { icon: TrendingUp, label: '数据源', value: '12', color: '#8b5cf6' },
              { icon: Zap, label: '更新延迟', value: '<1s', color: '#06b6d4' },
            ].map((stat) => {
              const Icon = stat.icon
              return (
                <div key={stat.label} className="p-4 rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10">
                  <Icon className="w-5 h-5 mb-2 mx-auto" style={{ color: stat.color }} />
                  <div className="text-2xl font-bold text-white">{stat.value}</div>
                  <div className="text-xs text-zinc-500">{stat.label}</div>
                </div>
              )
            })}
          </div>
        </div>
        
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10 pointer-events-auto">
          <div className="flex flex-col items-center gap-2 animate-bounce">
            <span className="text-xs text-zinc-500">向下滚动探索更多</span>
            <ChevronDown className="w-5 h-5 text-zinc-400" />
          </div>
        </div>
        
        <div className="absolute bottom-8 right-8 z-10 pointer-events-auto">
          <div className="flex flex-col gap-2">
            <div className="px-4 py-3 rounded-xl bg-black/50 backdrop-blur-sm border border-white/10">
              <div className="text-xs text-zinc-500 mb-2">事件类型</div>
              <div className="flex flex-wrap gap-2">
                {[
                  { label: '市场', color: '#f59e0b' },
                  { label: '政策', color: '#8b5cf6' },
                  { label: '经济', color: '#10b981' },
                  { label: '科技', color: '#06b6d4' },
                ].map((type) => (
                  <span 
                    key={type.label}
                    className="px-2 py-1 rounded text-xs"
                    style={{ backgroundColor: `${type.color}20`, color: type.color }}
                  >
                    {type.label}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
        
        {selectedEvent && (
          <div className="fixed right-8 top-1/2 -translate-y-1/2 z-50 pointer-events-auto">
            <div className="w-80 bg-[#0a0f1a]/95 backdrop-blur-md rounded-2xl border border-white/10 shadow-2xl overflow-hidden">
              <div className="p-4 border-b border-white/5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div 
                      className="w-3 h-3 rounded-full animate-pulse"
                      style={{ backgroundColor: eventTypeColors[selectedEvent.type] }}
                    />
                    <span className="text-sm text-zinc-400">{selectedEvent.type}</span>
                  </div>
                  <button 
                    onClick={() => setSelectedEvent(null)}
                    className="text-zinc-500 hover:text-white"
                  >
                    ✕
                  </button>
                </div>
              </div>
              <div className="p-4">
                <h3 className="text-lg font-semibold text-white mb-2">{selectedEvent.title}</h3>
                <p className="text-sm text-zinc-400 mb-4">{selectedEvent.description}</p>
                <div className="flex items-center gap-4 text-xs text-zinc-500">
                  <span>{selectedEvent.time}</span>
                  <span className={`px-2 py-1 rounded ${
                    selectedEvent.impact === 'high' ? 'bg-red-500/20 text-red-400' :
                    selectedEvent.impact === 'medium' ? 'bg-amber-500/20 text-amber-400' :
                    'bg-emerald-500/20 text-emerald-400'
                  }`}>
                    {selectedEvent.impact === 'high' ? '高影响' : selectedEvent.impact === 'medium' ? '中等影响' : '低影响'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
