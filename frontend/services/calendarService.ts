/**
 * Economic Calendar Service
 * 
 * Provides API methods for fetching economic calendar events
 */

import { apiClient } from '@/lib/apiClient';

export interface CalendarEvent {
  event_id: string;
  date: string;
  time: string | null;
  country: string | null;
  currency: string | null;
  importance: 'high' | 'medium' | 'low';
  event: string;
  actual: string | null;
  forecast: string | null;
  previous: string | null;
  source: string;
}

export interface CalendarEventsResponse {
  total: number;
  past_events: CalendarEvent[];
  future_events: CalendarEvent[];
  source: string;
  fetched_at: string;
}

export interface TodayEventsResponse {
  date: string;
  total: number;
  events: CalendarEvent[];
  source: string;
  fetched_at: string;
}

export interface ImportantEventsResponse {
  period: string;
  total: number;
  events: CalendarEvent[];
  source: string;
  fetched_at: string;
}

export interface CountryInfo {
  code: string;
  name: string;
  currency: string;
}

export interface ImportanceLevel {
  code: string;
  name: string;
  description: string;
  emoji: string;
}

export interface CalendarStats {
  total_events: number;
  by_importance: Record<string, number>;
  by_country: Record<string, number>;
  date_range: {
    start: string | null;
    end: string | null;
  };
  fetched_at: string;
}

const BASE_URL = '/api/datacenter/calendar';

export const calendarService = {
  async getEvents(params?: {
    countries?: string;
    importances?: string;
    past_days?: number;
    future_days?: number;
    source?: 'db' | 'scraper';
  }): Promise<CalendarEventsResponse> {
    const response = await apiClient.get<CalendarEventsResponse>(BASE_URL + '/events', { params });
    return response.data;
  },

  async getTodayEvents(params?: {
    countries?: string;
    importances?: string;
  }): Promise<TodayEventsResponse> {
    const response = await apiClient.get<TodayEventsResponse>(BASE_URL + '/events/today', { params });
    return response.data;
  },

  async getImportantEvents(days: number = 7): Promise<ImportantEventsResponse> {
    const response = await apiClient.get<ImportantEventsResponse>(BASE_URL + '/events/important', {
      params: { days },
    });
    return response.data;
  },

  async getEventsByDate(date: string, params?: {
    countries?: string;
    importances?: string;
  }): Promise<TodayEventsResponse> {
    const response = await apiClient.get<TodayEventsResponse>(`${BASE_URL}/events/date/${date}`, { params });
    return response.data;
  },

  async getEventsByRange(startDate: string, endDate: string, params?: {
    countries?: string;
    importances?: string;
  }): Promise<CalendarEventsResponse> {
    const response = await apiClient.get<CalendarEventsResponse>(BASE_URL + '/events/range', {
      params: { start_date: startDate, end_date: endDate, ...params },
    });
    return response.data;
  },

  async fetchAndSave(params?: {
    past_days?: number;
    future_days?: number;
    countries?: string;
    importances?: string;
  }): Promise<{ message: string; date_range: { from: string; to: string } }> {
    const response = await apiClient.post(BASE_URL + '/fetch', null, { params });
    return response.data;
  },

  async getCountries(): Promise<{ countries: CountryInfo[] }> {
    const response = await apiClient.get<{ countries: CountryInfo[] }>(BASE_URL + '/countries');
    return response.data;
  },

  async getImportanceLevels(): Promise<{ levels: ImportanceLevel[] }> {
    const response = await apiClient.get<{ levels: ImportanceLevel[] }>(BASE_URL + '/importance-levels');
    return response.data;
  },

  async getStats(): Promise<CalendarStats> {
    const response = await apiClient.get<CalendarStats>(BASE_URL + '/stats');
    return response.data;
  },

  async refreshCache(): Promise<{ message: string }> {
    const response = await apiClient.post(BASE_URL + '/refresh-cache');
    return response.data;
  },
};
