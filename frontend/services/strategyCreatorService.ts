/**
 * Strategy Creator Service
 * 
 * Provides API calls for AI-powered strategy creation
 */

import { apiClient } from './apiConfig';

export interface StrategyGenerateRequest {
  description: string;
  name?: string;
  strategy_type?: string;
  factors?: string[];
  factor_weights?: Record<string, number>;
  weight_method?: string;
  rebalance_freq?: string;
  max_positions?: number;
  stop_loss?: number;
  take_profit?: number;
  context?: Record<string, unknown>;
}

export interface StrategySaveRequest {
  strategy_id: string;
  name: string;
  code: string;
  description: string;
  strategy_type?: string;
  factors?: string[];
  factor_weights?: Record<string, number>;
  weight_method?: string;
  rebalance_freq?: string;
  max_positions?: number;
  stop_loss?: number;
  take_profit?: number;
  tags?: string[];
}

export interface StrategyGenerateResponse {
  success: boolean;
  strategy_id: string;
  name: string;
  code: string;
  description: string;
  strategy_type: string;
  factors: string[];
  factor_weights: Record<string, number>;
  validation: {
    is_valid: boolean;
    syntax_valid: boolean;
    errors: string[];
    warnings: string[];
  };
  explanation: string;
  created_at: string;
}

export interface StreamEvent {
  type: 'status' | 'content' | 'content_start' | 'content_end' | 'result' | 'error';
  status?: string;
  message?: string;
  content?: string;
  data?: StrategyGenerateResponse;
}

export interface StrategySuggestion {
  recommended_factors: Record<string, string[]>;
  weight_methods: Record<string, string>;
  rebalance_freqs: Record<string, string>;
}

class StrategyCreatorService {
  private baseUrl = '/api/quant/strategy-creator';

  async generateStrategy(request: StrategyGenerateRequest): Promise<StrategyGenerateResponse> {
    const response = await apiClient.post(`${this.baseUrl}/generate`, request, {
      timeout: 120000,
    });
    return response.data;
  }

  async *generateStrategyStream(
    request: StrategyGenerateRequest,
    onStatus?: (status: string, message: string) => void,
    onContent?: (content: string) => void,
  ): AsyncGenerator<StreamEvent, StrategyGenerateResponse | null, unknown> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const response = await fetch(`${API_BASE_URL}${this.baseUrl}/generate/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';
    let finalResult: StrategyGenerateResponse | null = null;

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            
            if (data === '[DONE]') {
              return finalResult;
            }

            try {
              const event: StreamEvent = JSON.parse(data);
              
              if (event.type === 'status' && onStatus) {
                onStatus(event.status || '', event.message || '');
              }
              
              if (event.type === 'content' && onContent) {
                onContent(event.content || '');
              }
              
              if (event.type === 'result') {
                finalResult = event.data || null;
              }
              
              yield event;
            } catch (e) {
              console.warn('Failed to parse SSE event:', data);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

    return finalResult;
  }

  async saveStrategy(request: StrategySaveRequest): Promise<{ success: boolean; strategy_id: string; message: string; file_path?: string }> {
    const response = await apiClient.post(`${this.baseUrl}/save`, request);
    return response.data;
  }

  async getTemplates(): Promise<{ templates: Record<string, string>; total: number }> {
    const response = await apiClient.get(`${this.baseUrl}/templates`);
    return response.data;
  }

  async getSuggestions(): Promise<{ success: boolean; suggestions: StrategySuggestion }> {
    const response = await apiClient.get(`${this.baseUrl}/suggestions`);
    return response.data;
  }
}

export const strategyCreatorService = new StrategyCreatorService();
