'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { Button } from '@/components/ui'
import {
  Database,
  Activity,
  Server,
  Wifi,
  WifiOff,
  ArrowLeft,
} from 'lucide-react'

const subTabs = [
  { key: 'collection', label: '数据采集', icon: Activity, path: '/datacenter' },
  { key: 'service', label: '数据服务', icon: Server, path: '/datacenter/service' },
]

export default function DataCenterLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const router = useRouter()
  const [dbConnected, setDbConnected] = useState(true)

  useEffect(() => {
    const checkConnection = async () => {
      try {
        const response = await fetch('/api/datacenter/overview')
        setDbConnected(response.ok)
      } catch {
        setDbConnected(false)
      }
    }
    checkConnection()
    const interval = setInterval(checkConnection, 30000)
    return () => clearInterval(interval)
  }, [])

  const activeTab = pathname === '/datacenter' ? 'collection' : 'service'

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-amber-500/10 rounded-full blur-[100px]" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-[100px]" />
      </div>

      <div className="relative z-10 border-b border-white/[0.05] bg-[var(--bg-primary)]/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/" className="text-zinc-500 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
                  <Database className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-white">数据中心</h1>
                  <p className="text-xs text-zinc-500">数据采集、处理与服务管理</p>
                </div>
              </div>
              <div className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs ${
                dbConnected 
                  ? 'bg-emerald-500/10 text-emerald-400' 
                  : 'bg-rose-500/10 text-rose-400'
              }`}>
                {dbConnected ? (
                  <>
                    <Wifi className="w-3.5 h-3.5" />
                    <span>数据库已连接</span>
                  </>
                ) : (
                  <>
                    <WifiOff className="w-3.5 h-3.5" />
                    <span>数据库断开</span>
                  </>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              {subTabs.map((tab) => {
                const Icon = tab.icon
                const isActive = activeTab === tab.key
                return (
                  <Button
                    key={tab.key}
                    variant={isActive ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => router.push(tab.path)}
                    className={isActive 
                      ? 'bg-[var(--accent-gold)] text-black gap-2' 
                      : 'text-zinc-400 hover:text-white gap-2'
                    }
                  >
                    <Icon className="w-4 h-4" />
                    {tab.label}
                  </Button>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-6">
        {children}
      </div>
    </div>
  )
}
