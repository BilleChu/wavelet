/**
 * Analysis Service for OpenFinance.
 *
 * Provides API calls for the intelligent analysis canvas.
 */

import { apiClient } from './apiConfig'

export interface DataPoint {
  value: number
  timestamp: string
  source: string
  confidence: 'high' | 'medium' | 'low'
  metadata?: Record<string, unknown>
}

export interface MacroIndicator {
  code: string
  name: string
  name_en?: string
  category: string
  unit: string
  current_value: DataPoint
  previous_value?: DataPoint
  yoy_change?: number
  mom_change?: number
  trend: string
  historical_data?: DataPoint[]
}

export interface MacroPanelData {
  indicators: MacroIndicator[]
  last_updated: string
  next_update?: string
}

export interface PolicyItem {
  policy_id: string
  title: string
  summary: string
  source: string
  publish_date: string
  effective_date?: string
  issuer: string
  category: string
  impact_level: string
  affected_sectors: string[]
  affected_stocks: string[]
  sentiment: string
  relevance_score: number
  url?: string
}

export interface PolicyPanelData {
  policies: PolicyItem[]
  hot_topics: string[]
  last_updated: string
}

export interface CompanyFinancial {
  stock_code: string
  stock_name: string
  report_date: string
  report_type: string
  revenue?: DataPoint
  net_profit?: DataPoint
  gross_margin?: DataPoint
  net_margin?: DataPoint
  roe?: DataPoint
  roa?: DataPoint
  debt_ratio?: DataPoint
  current_ratio?: DataPoint
  pe_ratio?: number
  pb_ratio?: number
  yoy_revenue_growth?: number
  yoy_profit_growth?: number
  news?: Array<{
    title: string
    source: string
    time: string
    sentiment: string
    related_stocks: string[]
  }>
  ai_insight?: string
}

export interface CompanyPanelData {
  companies: CompanyFinancial[]
  news: Array<{
    title: string
    source: string
    time: string
    sentiment: string
    related_stocks: string[]
  }>
  last_updated: string
}

export interface TechIndicator {
  stock_code: string
  stock_name: string
  timestamp: string
  price: number
  change: number
  change_pct: number
  volume: number
  amount: number
  ma5?: number
  ma10?: number
  ma20?: number
  ma60?: number
  rsi_14?: number
  macd?: number
  macd_signal?: number
  macd_hist?: number
  kdj_k?: number
  kdj_d?: number
  kdj_j?: number
  boll_upper?: number
  boll_mid?: number
  boll_lower?: number
  trend_signal: string
  support_level?: number
  resistance_level?: number
}

export interface TechPanelData {
  indicators: TechIndicator[]
  signals: Array<{
    stock_code: string
    stock_name: string
    signal: string
    reason: string
    confidence: number
  }>
  last_updated: string
}

export interface CanvasData {
  macro: MacroPanelData
  policy: PolicyPanelData
  company: CompanyPanelData
  tech: TechPanelData
  last_updated: string
}

export interface AnalysisRequest {
  query: string
  context?: Record<string, unknown>
  panels?: string[]
  include_historical?: boolean
}

export interface AnalysisResponse {
  analysis_id: string
  query: string
  content: string
  data_sources: string[]
  confidence: 'high' | 'medium' | 'low'
  related_entities: string[]
  follow_up_suggestions: string[]
  duration_ms: number
}

class AnalysisService {
  private baseUrl = '/api/analysis'

  async getCanvasData(): Promise<CanvasData> {
    const response = await apiClient.get<CanvasData>(`${this.baseUrl}/canvas`)
    return response.data
  }

  async getMacroData(): Promise<MacroPanelData> {
    const response = await apiClient.get<MacroPanelData>(`${this.baseUrl}/macro`)
    return response.data
  }

  async getPolicyData(): Promise<PolicyPanelData> {
    const response = await apiClient.get<PolicyPanelData>(`${this.baseUrl}/policy`)
    return response.data
  }

  async getCompanyData(): Promise<CompanyPanelData> {
    const response = await apiClient.get<CompanyPanelData>(`${this.baseUrl}/company`)
    return response.data
  }

  async getTechData(): Promise<TechPanelData> {
    const response = await apiClient.get<TechPanelData>(`${this.baseUrl}/tech`)
    return response.data
  }

  async analyze(request: AnalysisRequest): Promise<AnalysisResponse> {
    const response = await apiClient.post<AnalysisResponse>(
      `${this.baseUrl}/ai/analyze`,
      request
    )
    return response.data
  }

  async healthCheck(): Promise<{ status: string; service: string }> {
    const response = await apiClient.get<{ status: string; service: string }>(
      `${this.baseUrl}/health`
    )
    return response.data
  }
}

export const analysisService = new AnalysisService()
