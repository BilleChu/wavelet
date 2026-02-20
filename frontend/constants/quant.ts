export const factorTypeLabels: Record<string, string> = {
  TECHNICAL: '技术因子',
  FUNDAMENTAL: '基本面因子',
  ALTERNATIVE: '另类因子',
  MACRO: '宏观因子',
  SENTIMENT: '情绪因子',
  CUSTOM: '自定义因子',
}

export const categoryLabels: Record<string, string> = {
  MOMENTUM: '动量',
  VALUE: '价值',
  QUALITY: '质量',
  GROWTH: '成长',
  VOLATILITY: '波动率',
  LIQUIDITY: '流动性',
  SIZE: '规模',
  TECHNICAL: '技术分析',
}

export const weightMethodLabels: Record<string, string> = {
  equal: '等权重',
  ic_weighted: 'IC加权',
  icir_weighted: 'ICIR加权',
  max_sharpe: '最大夏普',
  min_variance: '最小方差',
  risk_parity: '风险平价',
  custom: '自定义',
}

export const rebalanceFreqLabels: Record<string, string> = {
  daily: '每日',
  weekly: '每周',
  biweekly: '双周',
  monthly: '每月',
  quarterly: '每季度',
}

export const statusLabels: Record<string, string> = {
  DRAFT: '草稿',
  ACTIVE: '激活',
  INACTIVE: '停用',
  ARCHIVED: '归档',
}

export const statusColors: Record<string, string> = {
  DRAFT: 'bg-zinc-500/20 text-zinc-400',
  ACTIVE: 'bg-emerald-500/20 text-emerald-400',
  INACTIVE: 'bg-amber-500/20 text-amber-400',
  ARCHIVED: 'bg-rose-500/20 text-rose-400',
}

export const methodColors: Record<string, string> = {
  GET: 'bg-emerald-500/20 text-emerald-400',
  POST: 'bg-blue-500/20 text-blue-400',
  PUT: 'bg-amber-500/20 text-amber-400',
  DELETE: 'bg-rose-500/20 text-rose-400',
  PATCH: 'bg-violet-500/20 text-violet-400',
}

export const formatPercent = (value: number | null | undefined): string => {
  if (value === null || value === undefined || isNaN(value)) return '-'
  return `${(value * 100).toFixed(2)}%`
}

export const formatNumber = (value: number | null | undefined, decimals: number = 2): string => {
  if (value === null || value === undefined || isNaN(value)) return '-'
  return value.toFixed(decimals)
}

export const formatCurrency = (value: number | null | undefined): string => {
  if (value === null || value === undefined || isNaN(value)) return '-'
  if (Math.abs(value) >= 1e8) return `${(value / 1e8).toFixed(2)}亿`
  if (Math.abs(value) >= 1e4) return `${(value / 1e4).toFixed(2)}万`
  return value.toFixed(2)
}

export const formatDateTime = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export const formatDate = (dateStr: string | null | undefined): string => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}
