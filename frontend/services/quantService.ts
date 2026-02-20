/**
 * Quant Service for OpenFinance.
 *
 * Provides API calls for quantitative analysis features.
 */

import { apiClient } from './apiConfig'

export interface Factor {
  factor_id: string
  name: string
  code: string
  description: string
  factor_type: string
  category: string
  formula?: string
  parameters: Record<string, unknown>
  default_params?: Record<string, number>
  lookback_period: number
  frequency: string
  status: string
  tags: string[]
  version?: string
  created_at: string
  updated_at: string
}

export interface FactorListResponse {
  factors: Factor[]
  total: number
  page: number
  page_size: number
}

export interface Strategy {
  strategy_id: string
  name: string
  code: string
  description: string
  strategy_type: string
  factors: string[]
  factor_weights: Record<string, number>
  weight_method: string
  rebalance_freq: string
  max_positions: number
  stop_loss?: number
  take_profit?: number
  created_at: string
  updated_at: string
}

export interface StrategyListResponse {
  strategies: Strategy[]
  total: number
  page: number
  page_size: number
}

export interface BacktestConfig {
  strategy_id: string
  start_date: string
  end_date: string
  initial_capital: number
  benchmark?: string
  commission_rate?: number
  slippage?: number
  position_size?: number
}

export interface SimplePerformanceMetrics {
  total_return: number
  annual_return: number
  benchmark_return: number
  excess_return: number
  volatility: number
  max_drawdown: number
  sharpe_ratio: number
  sortino_ratio: number
  calmar_ratio: number
  win_rate: number
  profit_loss_ratio: number
  total_trades?: number
  turnover_rate?: number
  information_ratio?: number
  alpha?: number
  beta?: number
}

export interface BacktestResult {
  backtest_id: string
  strategy_id: string
  config: BacktestConfig
  status: string
  metrics: SimplePerformanceMetrics
  equity_curve: Array<{
    date: string
    equity: number
    return: number
  }>
  trades: Array<{
    trade_id: string
    trade_date: string
    stock_code: string
    direction: string
    quantity: number
    price: number
    amount: number
  }>
  duration_ms: number
  error?: string
}

export interface FactorValidationResult {
  is_valid: boolean
  syntax_valid: boolean
  imports_valid: boolean
  logic_valid: boolean
  errors: string[]
  warnings: string[]
}

export interface FactorTestResult {
  ic_mean?: number
  ic_std?: number
  ic_ir?: number
  ic_positive_ratio?: number
  coverage_mean?: number
  monotonicity?: number
  stocks_tested?: number
  success_rate?: number
  avg_execution_time?: number
  duration_ms?: number
  error?: string
}

export interface FactorDataQueryRequest {
  factor_id: string
  stock_code: string
  start_date?: string
  end_date?: string
  frequency?: 'daily' | 'weekly' | 'monthly'
  lookback_days?: number
}

export interface FactorDataBatchQueryRequest {
  factor_id: string
  stock_codes: string[]
  start_date?: string
  end_date?: string
  frequency?: 'daily' | 'weekly' | 'monthly'
}

export interface FactorDataResponse {
  factor_id: string
  factor_name: string
  stock_code: string
  frequency: string
  data: Array<{
    trade_date: string
    value: number | null
    value_normalized: number | null
    value_rank: number | null
    value_percentile: number | null
  }>
  chart_data: {
    labels: string[]
    datasets: Array<{
      label: string
      data: (number | null)[]
      borderColor: string
      backgroundColor: string
      yAxisID?: string
    }>
  }
  statistics: Record<string, number | null>
}

export interface FactorDataBatchResponse {
  factor_id: string
  factor_name: string
  frequency: string
  data_by_stock: Record<string, Array<{
    trade_date: string
    value: number | null
    value_normalized: number | null
    value_rank: number | null
    value_percentile: number | null
  }>>
  chart_data: {
    labels: string[]
    datasets: Array<{
      label: string
      data: (number | null)[]
      borderColor: string
      backgroundColor: string
    }>
  }
  statistics: Record<string, number | null>
}

export interface FactorStocksResponse {
  factor_id: string
  total_count: number
  valid_count: number
  min_date: string | null
  max_date: string | null
}

export interface StrategyRunRequest {
  strategy_id: string
  stock_codes?: string[]
  start_date?: string
  end_date?: string
  parameters?: {
    top_n?: number
    min_score?: number
  }
}

export interface StockRecommendation {
  stock_code: string
  stock_name: string | null
  score: number
  weight: number
  rank: number
  factor_scores: Record<string, number>
  recommendation: string
  reasons: string[]
}

export interface StrategyRunResponse {
  strategy_id: string
  strategy_name: string
  run_date: string
  signals: Array<{
    code: string
    name: string
    score: number
    rank: number
    factor_scores: Record<string, { value: number; normalized: number; weight: number }>
  }>
  top_picks: Array<{
    code: string
    name: string
    score: number
    rank: number
    factor_scores: Record<string, { value: number; normalized: number; weight: number }>
  }>
  statistics: {
    total_stocks: number
    avg_score: number
    max_score: number
    min_score: number
  }
}

export interface CreateStrategyRequest {
  name: string
  code: string
  factors: string[]
  factor_weights?: Record<string, number>
  weight_method?: string
  max_positions?: number
  rebalance_freq?: string
  description?: string
  parameters?: Record<string, unknown>
}

// ============================================================================
// Enhanced Performance Metrics Types
// ============================================================================

export interface ReturnsMetrics {
  total_return: number
  annualized_return: number
  excess_return: number
  active_return: number
  cumulative_return: number
  cagr: number
}

export interface RiskMetrics {
  volatility: number
  downside_deviation: number
  var_95: number
  cvar_95: number
  max_drawdown: number
  avg_drawdown: number
  ulcer_index: number
}

export interface RiskAdjustedMetrics {
  sharpe_ratio: number
  sortino_ratio: number
  calmar_ratio: number
  information_ratio: number
  omega_ratio: number
}

export interface MarketRiskMetrics {
  beta: number
  alpha: number
  tracking_error: number
  r_squared: number
}

export interface TradingMetrics {
  win_rate: number
  profit_loss_ratio: number
  avg_win: number
  avg_loss: number
  expectancy: number
  turnover_rate: number
  avg_holding_period: number
}

export interface AdvancedMetrics {
  tail_ratio: number
  skewness: number
  kurtosis: number
}

export interface PerformanceMetrics {
  returns: ReturnsMetrics
  risk: RiskMetrics
  risk_adjusted: RiskAdjustedMetrics
  market_risk: MarketRiskMetrics
  trading: TradingMetrics
  advanced: AdvancedMetrics
  summary: Record<string, number>
}

// ============================================================================
// Attribution Analysis Types
// ============================================================================

export interface BrinsonAttribution {
  allocation_effect: number
  selection_effect: number
  interaction_effect: number
  total_active_return: number
}

export interface FactorAttribution {
  size: number
  value: number
  momentum: number
  quality: number
  volatility: number
  liquidity: number
  other: number
}

export interface SectorAttributionItem {
  sector: string
  allocation_effect: number
  selection_effect: number
  total_effect: number
}

export interface AttributionResult {
  brinson: BrinsonAttribution
  factor: FactorAttribution
  sector: SectorAttributionItem[]
}

// ============================================================================
// Risk Analysis Types
// ============================================================================

export interface StressTestResult {
  scenario: string
  portfolio_return: number
  benchmark_return: number
  relative_performance: number
  max_drawdown: number
  recovery_time: number
}

export interface SensitivityAnalysisResult {
  parameter_name: string
  results: Array<Record<string, unknown>>
  optimal_value: number
  sensitivity_score: number
}

export interface MonteCarloResult {
  expected_return: number
  return_std: number
  var_95: number
  cvar_95: number
  probability_of_loss: number
  confidence_intervals: Record<string, [number, number]>
}

// ============================================================================
// Rolling Analysis Types
// ============================================================================

export interface RollingMetricsResult {
  metric_name: string
  dates: string[]
  values: number[]
  mean: number
  std: number
  min: number
  max: number
}

// ============================================================================
// Analytics API Request/Response Types
// ============================================================================

export interface PerformanceAnalyticsRequest {
  backtest_id: string
  include_benchmark?: boolean
}

export interface PerformanceAnalyticsResponse {
  backtest_id: string
  metrics: {
    returns: ReturnsMetrics
    risk: RiskMetrics
    risk_adjusted: RiskAdjustedMetrics
    market_risk: MarketRiskMetrics
    trading: TradingMetrics
    advanced: AdvancedMetrics
    summary: Record<string, number>
  }
  cached: boolean
}

export interface RiskAnalysisRequest {
  backtest_id: string
  var_method?: 'historical' | 'parametric' | 'monte_carlo'
  confidence_level?: number
  horizon?: number
}

export interface RiskAnalysisResponse {
  backtest_id: string
  var: {
    value: number
    method: string
    confidence_level: number
    horizon_days: number
  }
  cvar: number
  stress_tests: StressTestResult[]
  rolling_metrics: Record<string, unknown>[]
  scenario_analysis: Record<string, unknown>
}

export interface AttributionAnalysisRequest {
  backtest_id: string
  method?: 'brinson' | 'factor' | 'sector'
}

export interface AttributionAnalysisResponse {
  backtest_id: string
  method: string
  attribution: AttributionResult
}

export interface RollingMetricsRequest {
  backtest_id: string
  window?: number
  step?: number
}

export interface RollingMetricsAPIResponse {
  backtest_id: string
  window_days: number
  step_days: number
  metrics: Record<string, unknown>[]
}

export interface SensitivityAnalysisAPIRequest {
  strategy_id: string
  parameter_name: string
  parameter_range: number[]
  start_date: string
  end_date: string
}

export interface MonteCarloAPIRequest {
  backtest_id: string
  num_simulations?: number
  confidence_level?: number
}

class QuantService {
  private baseUrl = '/api/quant'

  async healthCheck(): Promise<{ status: string; service: string; factors_available: number }> {
    const response = await apiClient.get(`${this.baseUrl}/health`)
    return response.data
  }

  async getFactors(params?: {
    factor_type?: string
    category?: string
    status?: string
    page?: number
    page_size?: number
  }): Promise<FactorListResponse> {
    const response = await apiClient.get<FactorListResponse>(`${this.baseUrl}/factors/list`, {
      params,
    })
    return response.data
  }

  async getFactor(factorCode: string): Promise<Factor> {
    const response = await apiClient.get<Factor>(`${this.baseUrl}/factors/${factorCode}`)
    return response.data
  }

  async getStrategies(params?: {
    strategy_type?: string
    page?: number
    page_size?: number
  }): Promise<StrategyListResponse> {
    const response = await apiClient.get<StrategyListResponse>(`${this.baseUrl}/strategies/list`, {
      params,
    })
    return response.data
  }

  async getStrategy(strategyId: string): Promise<Strategy> {
    const response = await apiClient.get<Strategy>(`${this.baseUrl}/strategies/${strategyId}`)
    return response.data
  }

  async getPresetStrategies(): Promise<Strategy[]> {
    const response = await apiClient.get<Strategy[]>(`${this.baseUrl}/strategies/presets`)
    return response.data
  }

  async runBacktest(config: BacktestConfig): Promise<BacktestResult> {
    const response = await apiClient.post<BacktestResult>(`${this.baseUrl}/backtest`, config)
    return response.data
  }

  async getBacktestResult(backtestId: string): Promise<BacktestResult> {
    const response = await apiClient.get<BacktestResult>(`${this.baseUrl}/backtest/${backtestId}`)
    return response.data
  }

  async calculateFactor(params: {
    factor_id: string
    codes?: string[]
    start_date: string
    end_date: string
  }): Promise<{ factor_id: string; values: Array<{ code: string; date: string; value: number }> }> {
    const response = await apiClient.post(`${this.baseUrl}/factors/calculate`, params)
    return response.data
  }

  async getFactorRegistry(): Promise<{ total: number; factors: Factor[] }> {
    const response = await apiClient.get(`${this.baseUrl}/factors/registry`)
    return response.data
  }

  async getStrategyRegistry(): Promise<{ total: number; strategies: Strategy[] }> {
    const response = await apiClient.get(`${this.baseUrl}/strategies/registry`)
    return response.data
  }

  async validateCustomFactor(params: {
    python_code: string
  }): Promise<FactorValidationResult> {
    const response = await apiClient.post<FactorValidationResult>(`${this.baseUrl}/custom/validate`, params)
    return response.data
  }

  async testCustomFactor(params: {
    python_code: string
    factor_id?: string
    parameters?: Record<string, unknown>
    stock_codes?: string[]
    start_date: string
    end_date: string
  }): Promise<FactorTestResult> {
    const response = await apiClient.post<FactorTestResult>(`${this.baseUrl}/custom/test`, params)
    return response.data
  }

  async queryFactorData(params: FactorDataQueryRequest): Promise<FactorDataResponse> {
    const response = await apiClient.post<FactorDataResponse>(`${this.baseUrl}/factors/data/query`, params)
    return response.data
  }

  async queryFactorDataBatch(params: FactorDataBatchQueryRequest): Promise<FactorDataBatchResponse> {
    const response = await apiClient.post<FactorDataBatchResponse>(`${this.baseUrl}/factors/data/batch`, params)
    return response.data
  }

  async getFactorStocks(factorId: string): Promise<FactorStocksResponse> {
    const response = await apiClient.get<FactorStocksResponse>(`${this.baseUrl}/factors/${factorId}/stocks`)
    return response.data
  }

  async runStrategy(params: StrategyRunRequest): Promise<StrategyRunResponse> {
    const response = await apiClient.post<StrategyRunResponse>(`${this.baseUrl}/strategies/run`, params)
    return response.data
  }

  async createStrategy(params: CreateStrategyRequest): Promise<Strategy> {
    const response = await apiClient.post<Strategy>(`${this.baseUrl}/strategies/create`, params)
    return response.data
  }

  // ============================================================================
  // Analytics API Methods
  // ============================================================================

  async getPerformanceAnalytics(params: PerformanceAnalyticsRequest): Promise<PerformanceAnalyticsResponse> {
    const response = await apiClient.get<PerformanceAnalyticsResponse>(`${this.baseUrl}/analytics/performance`, {
      params,
    })
    return response.data
  }

  async getRiskAnalysis(params: RiskAnalysisRequest): Promise<RiskAnalysisResponse> {
    const response = await apiClient.get<RiskAnalysisResponse>(`${this.baseUrl}/analytics/risk`, {
      params,
    })
    return response.data
  }

  async getAttributionAnalysis(params: AttributionAnalysisRequest): Promise<AttributionAnalysisResponse> {
    const response = await apiClient.get<AttributionAnalysisResponse>(`${this.baseUrl}/analytics/attribution`, {
      params,
    })
    return response.data
  }

  async getRollingMetrics(params: RollingMetricsRequest): Promise<RollingMetricsAPIResponse> {
    const response = await apiClient.get<RollingMetricsAPIResponse>(`${this.baseUrl}/analytics/rolling`, {
      params,
    })
    return response.data
  }

  async runSensitivityAnalysis(params: SensitivityAnalysisAPIRequest): Promise<SensitivityAnalysisResult> {
    const response = await apiClient.post<SensitivityAnalysisResult>(`${this.baseUrl}/analytics/sensitivity`, params)
    return response.data
  }

  async runMonteCarloSimulation(params: MonteCarloAPIRequest): Promise<MonteCarloResult> {
    const response = await apiClient.post<MonteCarloResult>(`${this.baseUrl}/analytics/monte-carlo`, params)
    return response.data
  }

  async deleteFactor(factorId: string): Promise<{ success: boolean; factor_id: string; message: string }> {
    const response = await apiClient.delete<{ success: boolean; factor_id: string; message: string }>(
      `${this.baseUrl}/factors/${factorId}`
    )
    return response.data
  }

  async getFactorCode(factorId: string): Promise<{
    factor_id: string
    name: string
    code: string
    file_path: string
    language: string
  }> {
    const response = await apiClient.get(`${this.baseUrl}/factors/${factorId}/code`)
    return response.data
  }
}

export const quantService = new QuantService()
