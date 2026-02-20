/**
 * Factor Creator Service
 * 
 * Provides API calls for AI-powered factor creation
 */

import { apiClient } from './apiConfig';

export interface FactorGenerateRequest {
  description: string;
  name?: string;
  context?: Record<string, unknown>;
}

export interface FactorCreateRequest {
  name: string;
  description: string;
  factor_type?: string;
  category?: string;
  lookback_period?: number;
  parameters?: Record<string, unknown>;
  data_requirements?: string[];
  tags?: string[];
}

export interface FactorSaveRequest {
  factor_id: string;
  name: string;
  code: string;
  description: string;
  factor_type?: string;
  category?: string;
  lookback_period?: number;
  parameters?: Record<string, unknown>;
  tags?: string[];
}

export interface FactorGenerateResponse {
  success: boolean;
  factor_id: string;
  name: string;
  code: string;
  description: string;
  factor_type: string;
  category: string;
  lookback_period: number;
  parameters: Record<string, unknown>;
  validation: {
    is_valid: boolean;
    syntax_valid: boolean;
    imports_valid: boolean;
    logic_valid: boolean;
    errors: string[];
    warnings: string[];
  };
  explanation: string;
  created_at: string;
}

export interface FactorTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  code: string;
}

export interface FactorSuggestion {
  recommended_parameters: Record<string, {
    type: string;
    default: unknown;
    min?: number;
    max?: number;
    options?: string[];
  }>;
  data_requirements: string[];
  description_template: string;
}

export interface StreamEvent {
  type: 'status' | 'content' | 'content_start' | 'content_end' | 'result' | 'error';
  status?: string;
  message?: string;
  content?: string;
  data?: FactorGenerateResponse;
}

class FactorCreatorService {
  private baseUrl = '/api/quant/factor-creator';

  async generateFactor(request: FactorGenerateRequest): Promise<FactorGenerateResponse> {
    const response = await apiClient.post(`${this.baseUrl}/generate`, request, {
      timeout: 120000,
    });
    return response.data;
  }

  async *generateFactorStream(
    request: FactorGenerateRequest,
    onStatus?: (status: string, message: string) => void,
    onContent?: (content: string) => void,
  ): AsyncGenerator<StreamEvent, FactorGenerateResponse | null, unknown> {
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:19100';
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
    let finalResult: FactorGenerateResponse | null = null;

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

  async createFactor(request: FactorCreateRequest): Promise<FactorGenerateResponse> {
    const response = await apiClient.post(`${this.baseUrl}/create`, request, {
      timeout: 120000,
    });
    return response.data;
  }

  async saveFactor(request: FactorSaveRequest): Promise<{ success: boolean; factor_id: string; message: string }> {
    const response = await apiClient.post(`${this.baseUrl}/save`, request);
    return response.data;
  }

  async getTemplates(): Promise<{ templates: Record<string, string>; total: number }> {
    const response = await apiClient.get(`${this.baseUrl}/templates`);
    return response.data;
  }

  async validateCode(code: string): Promise<{
    success: boolean;
    validation: {
      is_valid: boolean;
      syntax_valid: boolean;
      imports_valid: boolean;
      logic_valid: boolean;
      errors: string[];
      warnings: string[];
    };
  }> {
    const response = await apiClient.post(`${this.baseUrl}/validate`, null, {
      params: { code },
    });
    return response.data;
  }

  async getSuggestions(factorType?: string, category?: string): Promise<{
    success: boolean;
    suggestions: Record<string, FactorSuggestion> | FactorSuggestion;
    available_types?: string[];
  }> {
    const response = await apiClient.get(`${this.baseUrl}/suggestions`, {
      params: { factor_type: factorType, category },
    });
    return response.data;
  }

  async testFactor(factorId: string, symbol: string, params?: Record<string, unknown>, code?: string): Promise<{
    success: boolean;
    result: {
      value: number;
      date: string;
      symbol: string;
    };
    history?: Array<{
      date: string;
      value: number;
    }>;
    note?: string;
  }> {
    const response = await apiClient.post(`/api/quant/factors/${factorId}/test`, {
      symbol,
      params,
      code,
    });
    return response.data;
  }
}

export const factorCreatorService = new FactorCreatorService();
