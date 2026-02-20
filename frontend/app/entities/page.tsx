'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { entityService, type Entity, type EntityType, type Industry } from '@/services/entityService'
import { Search, Building2, User, Tag, Hash, ArrowRight, ChevronLeft, ChevronRight, Grid, List, SlidersHorizontal, X, Database } from 'lucide-react'
import { Button, Input, Badge, EmptyState, Skeleton } from '@/components/ui'

const entityTypeLabels: Record<string, string> = {
  company: '公司',
  industry: '行业',
  concept: '概念',
  person: '人物',
  stock: '股票',
  fund: '基金',
}

const entityTypeColors: Record<string, string> = {
  company: 'from-amber-500 to-orange-600',
  industry: 'from-emerald-500 to-teal-600',
  concept: 'from-violet-500 to-purple-600',
  person: 'from-cyan-500 to-blue-600',
  stock: 'from-rose-500 to-pink-600',
  fund: 'from-slate-400 to-slate-600',
}

const entityTypeHexColors: Record<string, string> = {
  company: '#f59e0b',
  industry: '#10b981',
  concept: '#8b5cf6',
  person: '#06b6d4',
  stock: '#f43f5e',
  fund: '#64748b',
}

export default function EntitiesPage() {
  const [entities, setEntities] = useState<Entity[]>([])
  const [types, setTypes] = useState<EntityType[]>([])
  const [industries, setIndustries] = useState<Industry[]>([])
  const [loading, setLoading] = useState(true)
  const [keyword, setKeyword] = useState('')
  const [selectedType, setSelectedType] = useState<string | null>(null)
  const [selectedIndustry, setSelectedIndustry] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [showFilters, setShowFilters] = useState(false)
  const pageSize = 20

  const loadTypes = async () => {
    try {
      const data = await entityService.getEntityTypes()
      setTypes(data.types)
    } catch (error) {
      console.error('Failed to load types:', error)
    }
  }

  const loadIndustries = async () => {
    try {
      const data = await entityService.getIndustries()
      setIndustries(data.industries)
    } catch (error) {
      console.error('Failed to load industries:', error)
    }
  }

  const loadEntities = useCallback(async () => {
    setLoading(true)
    try {
      const data = await entityService.searchEntities({
        keyword: keyword || undefined,
        entity_type: selectedType || undefined,
        industry: selectedIndustry || undefined,
        page,
        page_size: pageSize,
      })
      setEntities(data.entities)
      setTotal(data.total)
    } catch (error) {
      console.error('Failed to load entities:', error)
    } finally {
      setLoading(false)
    }
  }, [keyword, selectedType, selectedIndustry, page])

  useEffect(() => {
    loadTypes()
    loadIndustries()
  }, [])

  useEffect(() => {
    loadEntities()
  }, [loadEntities])

  const handleSearch = () => {
    setPage(1)
    loadEntities()
  }

  const clearFilters = () => {
    setSelectedType(null)
    setSelectedIndustry(null)
    setKeyword('')
    setPage(1)
  }

  const formatMarketCap = (cap: number | null) => {
    if (!cap) return '-'
    if (cap >= 1e12) return `${(cap / 1e12).toFixed(2)}万亿`
    if (cap >= 1e8) return `${(cap / 1e8).toFixed(2)}亿`
    return `${(cap / 1e4).toFixed(2)}万`
  }

  const totalPages = Math.ceil(total / pageSize)

  const renderEntityIcon = (type: string) => {
    switch (type) {
      case 'company':
        return <Building2 className="w-5 h-5" />
      case 'person':
        return <User className="w-5 h-5" />
      case 'industry':
        return <Tag className="w-5 h-5" />
      case 'concept':
        return <Hash className="w-5 h-5" />
      default:
        return <Building2 className="w-5 h-5" />
    }
  }

  const activeFiltersCount = (selectedType ? 1 : 0) + (selectedIndustry ? 1 : 0)

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      {/* Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-32 w-96 h-96 bg-emerald-500/10 rounded-full blur-[100px]" />
        <div className="absolute bottom-1/4 -right-32 w-96 h-96 bg-amber-500/10 rounded-full blur-[100px]" />
      </div>

      {/* Page Header */}
      <div className="relative z-10 border-b border-white/[0.05] bg-[var(--bg-primary)]/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
                <Database className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-white">实体管理</h1>
                <p className="text-xs text-zinc-500">金融实体数据库</p>
              </div>
              <Badge variant="secondary">{total} 条记录</Badge>
            </div>
            
            <div className="flex items-center gap-2">
              <Button
                variant={viewMode === 'grid' ? 'default' : 'outline'}
                size="icon"
                onClick={() => setViewMode('grid')}
              >
                <Grid className="w-4 h-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'default' : 'outline'}
                size="icon"
                onClick={() => setViewMode('list')}
              >
                <List className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="relative z-10 max-w-7xl mx-auto px-6 py-6">
        {/* Search & Filters */}
        <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.05] mb-6">
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
                <input
                  type="text"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="搜索实体名称、代码或描述..."
                  className="w-full pl-12 pr-4 py-3 bg-white/[0.03] border border-white/[0.08] rounded-xl text-white placeholder-zinc-500 focus:outline-none focus:border-emerald-500/40 transition-all"
                />
              </div>
            </div>
            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => setShowFilters(!showFilters)}
                className="gap-2"
              >
                <SlidersHorizontal className="w-4 h-4" />
                筛选
                {activeFiltersCount > 0 && (
                  <Badge variant="default" size="sm">{activeFiltersCount}</Badge>
                )}
              </Button>
              <Button onClick={handleSearch}>
                搜索
              </Button>
            </div>
          </div>

          {/* Filters Panel */}
          {showFilters && (
            <div className="mt-5 pt-5 border-t border-white/[0.05] animate-fade-in">
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-medium text-white">筛选条件</span>
                {activeFiltersCount > 0 && (
                  <Button variant="ghost" size="sm" onClick={clearFilters} className="gap-1.5">
                    <X className="w-3.5 h-3.5" />
                    清除筛选
                  </Button>
                )}
              </div>
              
              <div className="space-y-5">
                {/* Entity Types */}
                <div>
                  <label className="text-xs text-zinc-500 mb-2.5 block">实体类型</label>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => setSelectedType(null)}
                      className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                        selectedType === null
                          ? 'bg-emerald-500 text-white'
                          : 'bg-white/[0.03] border border-white/[0.08] text-zinc-400 hover:text-white hover:bg-white/[0.06]'
                      }`}
                    >
                      全部
                    </button>
                    {types.map((t) => (
                      <button
                        key={t.type}
                        onClick={() => setSelectedType(t.type)}
                        className={`px-4 py-2 rounded-xl text-sm font-medium transition-all flex items-center gap-2 ${
                          selectedType === t.type
                            ? 'bg-emerald-500 text-white'
                            : 'bg-white/[0.03] border border-white/[0.08] text-zinc-400 hover:text-white hover:bg-white/[0.06]'
                        }`}
                      >
                        {entityTypeLabels[t.type] || t.type}
                        <span className={`px-1.5 py-0.5 rounded text-xs ${selectedType === t.type ? 'bg-white/20' : 'bg-white/[0.05]'}`}>
                          {t.count}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Industries */}
                {industries.length > 0 && (
                  <div>
                    <label className="text-xs text-zinc-500 mb-2.5 block">所属行业</label>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => setSelectedIndustry(null)}
                        className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                          selectedIndustry === null
                            ? 'bg-emerald-500 text-white'
                            : 'bg-white/[0.03] border border-white/[0.08] text-zinc-400 hover:text-white hover:bg-white/[0.06]'
                        }`}
                      >
                        全部
                      </button>
                      {industries.slice(0, 10).map((i) => (
                        <button
                          key={i.industry}
                          onClick={() => setSelectedIndustry(i.industry)}
                          className={`px-4 py-2 rounded-xl text-sm font-medium transition-all flex items-center gap-2 ${
                            selectedIndustry === i.industry
                              ? 'bg-emerald-500 text-white'
                              : 'bg-white/[0.03] border border-white/[0.08] text-zinc-400 hover:text-white hover:bg-white/[0.06]'
                          }`}
                        >
                          {i.industry}
                          <span className={`px-1.5 py-0.5 rounded text-xs ${selectedIndustry === i.industry ? 'bg-white/20' : 'bg-white/[0.05]'}`}>
                            {i.count}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Results */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.05] animate-shimmer h-40" />
            ))}
          </div>
        ) : entities.length === 0 ? (
          <EmptyState
            icon={<Search className="w-8 h-8" />}
            title="未找到匹配的实体"
            description="尝试调整搜索条件或清除筛选"
            action={
              <Button variant="outline" onClick={clearFilters}>
                清除筛选
              </Button>
            }
          />
        ) : viewMode === 'grid' ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {entities.map((entity, index) => (
              <Link
                key={entity.entity_id}
                href={`/knowledge-graph?entity=${entity.entity_id}`}
                className="group p-5 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:border-white/[0.1] hover:bg-white/[0.04] transition-all duration-300"
                style={{ animationDelay: `${index * 0.03}s` }}
              >
                <div className="flex items-start gap-4">
                  <div 
                    className={`w-12 h-12 rounded-xl bg-gradient-to-br ${entityTypeColors[entity.entity_type] || 'from-slate-400 to-slate-600'} flex items-center justify-center flex-shrink-0 text-white shadow-lg`}
                    style={{ boxShadow: `0 8px 24px ${entityTypeHexColors[entity.entity_type] || '#64748b'}30` }}
                  >
                    {renderEntityIcon(entity.entity_type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <h3 className="text-white font-medium truncate">{entity.name}</h3>
                      {entity.code && (
                        <Badge variant="secondary" size="sm">{entity.code}</Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mb-2">
                      <Badge 
                        size="sm"
                        style={{ 
                          backgroundColor: `${entityTypeHexColors[entity.entity_type] || '#64748b'}15`,
                          color: entityTypeHexColors[entity.entity_type] || '#64748b'
                        }}
                      >
                        {entityTypeLabels[entity.entity_type] || entity.entity_type}
                      </Badge>
                      {entity.industry && (
                        <span className="text-xs text-zinc-500">{entity.industry}</span>
                      )}
                    </div>
                    {entity.description && (
                      <p className="text-sm text-zinc-500 line-clamp-2 mb-2">{entity.description}</p>
                    )}
                    {entity.market_cap && (
                      <p className="text-sm">
                        <span className="text-zinc-500">市值: </span>
                        <span className="text-amber-400 font-medium">{formatMarketCap(entity.market_cap)}</span>
                      </p>
                    )}
                  </div>
                  <ArrowRight className="w-5 h-5 text-zinc-600 group-hover:text-emerald-400 group-hover:translate-x-1 transition-all flex-shrink-0" />
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="rounded-2xl bg-white/[0.02] border border-white/[0.05] overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.05]">
                  <th className="text-left px-5 py-4 text-sm font-medium text-zinc-400">名称</th>
                  <th className="text-left px-5 py-4 text-sm font-medium text-zinc-400">代码</th>
                  <th className="text-left px-5 py-4 text-sm font-medium text-zinc-400">类型</th>
                  <th className="text-left px-5 py-4 text-sm font-medium text-zinc-400">行业</th>
                  <th className="text-right px-5 py-4 text-sm font-medium text-zinc-400">市值</th>
                  <th className="w-12 px-5 py-4"></th>
                </tr>
              </thead>
              <tbody>
                {entities.map((entity) => (
                  <tr 
                    key={entity.entity_id} 
                    className="border-b border-white/[0.03] hover:bg-white/[0.02] cursor-pointer transition-colors"
                    onClick={() => window.location.href = `/knowledge-graph?entity=${entity.entity_id}`}
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${entityTypeColors[entity.entity_type] || 'from-slate-400 to-slate-600'} flex items-center justify-center text-white`}>
                          {renderEntityIcon(entity.entity_type)}
                        </div>
                        <span className="font-medium text-white">{entity.name}</span>
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      {entity.code && (
                        <Badge variant="secondary" size="sm">{entity.code}</Badge>
                      )}
                    </td>
                    <td className="px-5 py-4">
                      <Badge 
                        size="sm"
                        style={{ 
                          backgroundColor: `${entityTypeHexColors[entity.entity_type] || '#64748b'}15`,
                          color: entityTypeHexColors[entity.entity_type] || '#64748b'
                        }}
                      >
                        {entityTypeLabels[entity.entity_type] || entity.entity_type}
                      </Badge>
                    </td>
                    <td className="px-5 py-4 text-zinc-400 text-sm">{entity.industry || '-'}</td>
                    <td className="px-5 py-4 text-right text-amber-400 font-medium">{formatMarketCap(entity.market_cap)}</td>
                    <td className="px-5 py-4">
                      <ArrowRight className="w-4 h-4 text-zinc-600" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {total > pageSize && (
          <div className="flex items-center justify-center gap-4 mt-8">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="gap-1.5"
            >
              <ChevronLeft className="w-4 h-4" />
              上一页
            </Button>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-zinc-500">第</span>
              <span className="text-white font-medium">{page}</span>
              <span className="text-zinc-500">页，共</span>
              <span className="text-white font-medium">{totalPages}</span>
              <span className="text-zinc-500">页</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={page >= totalPages}
              className="gap-1.5"
            >
              下一页
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        )}
      </main>
    </div>
  )
}
