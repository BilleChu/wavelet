/**
 * Quant Module Store using Zustand.
 *
 * Provides state management for:
 * - Factor selection and caching
 * - Strategy configuration
 * - Backtest results
 * - Analysis state
 */

import { create } from 'zustand'

export interface Factor {
  id: string
  name: string
  category: string
  description?: string
  formula?: string
}

export interface Strategy {
  id: string
  name: string
  factors: string[]
  weights: Record<string, number>
  rebalanceFrequency: string
  status: 'draft' | 'running' | 'completed' | 'failed'
}

export interface BacktestResult {
  id: string
  strategyId: string
  startDate: string
  endDate: string
  totalReturn: number
  annualReturn: number
  maxDrawdown: number
  sharpeRatio: number
  winRate: number
  trades: number
}

interface QuantState {
  selectedFactors: Factor[]
  strategies: Strategy[]
  backtestResults: BacktestResult[]
  currentStrategy: Strategy | null
  isLoading: boolean
  error: string | null
  
  setSelectedFactors: (factors: Factor[]) => void
  addFactor: (factor: Factor) => void
  removeFactor: (factorId: string) => void
  clearFactors: () => void
  
  setStrategies: (strategies: Strategy[]) => void
  setCurrentStrategy: (strategy: Strategy | null) => void
  updateStrategy: (id: string, updates: Partial<Strategy>) => void
  
  setBacktestResults: (results: BacktestResult[]) => void
  addBacktestResult: (result: BacktestResult) => void
  
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  reset: () => void
}

const initialState = {
  selectedFactors: [],
  strategies: [],
  backtestResults: [],
  currentStrategy: null,
  isLoading: false,
  error: null,
}

export const useQuantStore = create<QuantState>((set, get) => ({
  ...initialState,
  
  setSelectedFactors: (factors) => set({ selectedFactors: factors }),
  
  addFactor: (factor) => set((state) => {
    if (state.selectedFactors.some(f => f.id === factor.id)) {
      return state
    }
    return { selectedFactors: [...state.selectedFactors, factor] }
  }),
  
  removeFactor: (factorId) => set((state) => ({
    selectedFactors: state.selectedFactors.filter(f => f.id !== factorId),
  })),
  
  clearFactors: () => set({ selectedFactors: [] }),
  
  setStrategies: (strategies) => set({ strategies }),
  
  setCurrentStrategy: (strategy) => set({ currentStrategy: strategy }),
  
  updateStrategy: (id, updates) => set((state) => ({
    strategies: state.strategies.map(s =>
      s.id === id ? { ...s, ...updates } : s
    ),
    currentStrategy: state.currentStrategy?.id === id
      ? { ...state.currentStrategy, ...updates }
      : state.currentStrategy,
  })),
  
  setBacktestResults: (results) => set({ backtestResults: results }),
  
  addBacktestResult: (result) => set((state) => ({
    backtestResults: [result, ...state.backtestResults],
  })),
  
  setLoading: (loading) => set({ isLoading: loading }),
  
  setError: (error) => set({ error }),
  
  reset: () => set(initialState),
}))
