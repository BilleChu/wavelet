import apiClient from './apiConfig'

export interface APIParameter {
  name: string
  type: string
  required: boolean
  description: string
  default?: string
  enum?: string[]
}

export interface APIEndpoint {
  path: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  description: string
  parameters: Record<string, { type?: string; description?: string }>
  response_schema: Record<string, unknown>
  response_example: Record<string, unknown>
  error_codes: Array<{ code: string; message: string; description: string }>
  requires_auth: boolean
  deprecated: boolean
  deprecation_message?: string
  cache_ttl_seconds: number
}

export interface APIService {
  service_id: string
  name: string
  description: string
  category: string
  version: string
  status: string
  endpoints: APIEndpoint[]
  tags: string[]
  documentation_url?: string
  rate_limit: {
    requests_per_minute: number
    requests_per_hour: number
  }
}

export interface APIDocumentation {
  services: APIService[]
  total: number
  categories: Array<{ id: string; name: string; count: number }>
  version: string
  last_updated: string
}

export interface APIResponse<T> {
  success: boolean
  data: T
  error?: string
  error_code?: string
  request_id: string
  timestamp: string
}

export const dataserviceDocService = {
  async getDocumentation(): Promise<APIDocumentation> {
    const response = await apiClient.get<APIResponse<APIDocumentation>>('/api/dataservice/v1/docs')
    if (response.data.success && response.data.data) {
      return response.data.data
    }
    throw new Error(response.data.error || 'Failed to fetch documentation')
  },

  async getServices(category?: string): Promise<{ services: APIService[]; total: number }> {
    const params = category ? { category } : {}
    const response = await apiClient.get<APIResponse<{ services: APIService[]; total: number }>>(
      '/api/dataservice/v1/services',
      { params }
    )
    if (response.data.success && response.data.data) {
      return response.data.data
    }
    throw new Error(response.data.error || 'Failed to fetch services')
  },

  async getService(serviceId: string): Promise<APIService> {
    const response = await apiClient.get<APIResponse<APIService>>(
      `/api/dataservice/v1/services/${serviceId}`
    )
    if (response.data.success && response.data.data) {
      return response.data.data
    }
    throw new Error(response.data.error || 'Failed to fetch service')
  },

  async searchEndpoints(query: string): Promise<{
    results: Array<{ service: Partial<APIService>; endpoint: Partial<APIEndpoint> }>
    total: number
  }> {
    const response = await apiClient.get<APIResponse<{
      results: Array<{ service: Partial<APIService>; endpoint: Partial<APIEndpoint> }>
      total: number
    }>>('/api/dataservice/v1/search', {
      params: { q: query },
    })
    if (response.data.success && response.data.data) {
      return response.data.data
    }
    throw new Error(response.data.error || 'Failed to search endpoints')
  },
}

export const categoryLabels: Record<string, string> = {
  analysis: '智能分析',
  graph: '知识图谱',
  quant: '量化分析',
  market: '市场数据',
  fundamental: '基本面数据',
  alternative: '另类数据',
}

export const methodColors: Record<string, string> = {
  GET: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  POST: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  PUT: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  DELETE: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
}

export const statusColors: Record<string, string> = {
  active: 'text-emerald-400',
  inactive: 'text-zinc-400',
  deprecated: 'text-amber-400',
  maintenance: 'text-blue-400',
}

export const categoryIcons: Record<string, string> = {
  analysis: '🧠',
  graph: '🕸️',
  quant: '📊',
  market: '📈',
  fundamental: '💼',
  alternative: '🔍',
}
