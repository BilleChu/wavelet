'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { Calendar, TrendingUp, TrendingDown, Minus, ExternalLink } from 'lucide-react';

interface Event {
  id: number;
  title: string;
  summary: string;
  date: string;
  category: string;
  type: string;
  importance: string;
  impact_direction?: string;
  impact_magnitude?: number;
  entities?: Array<{
    id: string;
    type: string;
    name: string;
  }>;
  source?: string;
  ai_analysis?: string;
}

interface EventTimelineProps {
  category?: string;
  importance?: string;
  limit?: number;
  onEventClick?: (eventId: number) => void;
}

const CATEGORY_LABELS: Record<string, { label: string; color: string }> = {
  global_macro: { label: '全球宏观', color: 'bg-blue-100 text-blue-700' },
  china_macro: { label: '中国宏观', color: 'bg-green-100 text-green-700' },
  market: { label: '股市大盘', color: 'bg-purple-100 text-purple-700' },
  industry: { label: '行业动态', color: 'bg-orange-100 text-orange-700' },
  company: { label: '公司事件', color: 'bg-pink-100 text-pink-700' },
};

const IMPORTANCE_LABELS: Record<string, { label: string; icon: string }> = {
  critical: { label: '重大', icon: '🔴' },
  high: { label: '重要', icon: '🟠' },
  medium: { label: '一般', icon: '🟡' },
  low: { label: '轻微', icon: '⚪' },
};

export default function EventTimeline({
  category,
  importance,
  limit = 20,
  onEventClick,
}: EventTimelineProps) {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({
    category: category || '',
    importance: importance || '',
  });

  const fetchEvents = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      params.append('limit', String(limit));
      if (filter.category) params.append('category', filter.category);
      if (filter.importance) params.append('importance', filter.importance);

      const res = await fetch(`http://localhost:8000/api/analysis/events?${params}`);
      if (res.ok) {
        const data = await res.json();
        setEvents(data.events || []);
      }
    } catch (error) {
      console.error('Failed to fetch events:', error);
    } finally {
      setLoading(false);
    }
  }, [filter, limit]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const getImpactIcon = (direction?: string) => {
    if (direction === 'positive') return <TrendingUp className="w-4 h-4 text-green-500" />;
    if (direction === 'negative') return <TrendingDown className="w-4 h-4 text-red-500" />;
    return <Minus className="w-4 h-4 text-gray-400" />;
  };

  const groupEventsByDate = (events: Event[]) => {
    const groups: Record<string, Event[]> = {};
    events.forEach(event => {
      const dateKey = event.date?.split('T')[0] || '未知日期';
      if (!groups[dateKey]) groups[dateKey] = [];
      groups[dateKey].push(event);
    });
    return Object.entries(groups).sort((a, b) => b[0].localeCompare(a[0]));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  const groupedEvents = groupEventsByDate(events);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-700 flex items-center gap-2">
          <Calendar className="w-5 h-5" />
          事件时间线
        </h3>
        <div className="flex items-center gap-2">
          <select
            value={filter.category}
            onChange={(e) => setFilter({ ...filter, category: e.target.value })}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">全部类别</option>
            {Object.entries(CATEGORY_LABELS).map(([key, value]) => (
              <option key={key} value={key}>{value.label}</option>
            ))}
          </select>
          <select
            value={filter.importance}
            onChange={(e) => setFilter({ ...filter, importance: e.target.value })}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">全部重要性</option>
            {Object.entries(IMPORTANCE_LABELS).map(([key, value]) => (
              <option key={key} value={key}>{value.icon} {value.label}</option>
            ))}
          </select>
        </div>
      </div>

      {groupedEvents.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          暂无事件数据
        </div>
      ) : (
        <div className="relative">
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />
          
          {groupedEvents.map(([date, dateEvents]) => (
            <div key={date} className="relative pl-10 pb-6">
              <div className="absolute left-2 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center">
                <div className="w-2 h-2 bg-white rounded-full" />
              </div>
              
              <div className="text-sm font-medium text-gray-500 mb-2">
                {date}
              </div>
              
              <div className="space-y-2">
                {dateEvents.map((event) => {
                  const categoryInfo = CATEGORY_LABELS[event.category] || { label: event.category, color: 'bg-gray-100 text-gray-700' };
                  const importanceInfo = IMPORTANCE_LABELS[event.importance] || { label: event.importance, icon: '⚪' };

                  return (
                    <div
                      key={event.id}
                      onClick={() => onEventClick?.(event.id)}
                      className="bg-white rounded-lg border border-gray-100 p-4 hover:shadow-md hover:border-blue-200 cursor-pointer transition-all"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span>{importanceInfo.icon}</span>
                            <span className="font-medium text-gray-800">{event.title}</span>
                          </div>
                          
                          {event.summary && (
                            <p className="text-sm text-gray-500 line-clamp-2 mb-2">
                              {event.summary}
                            </p>
                          )}
                          
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={`px-2 py-0.5 rounded text-xs ${categoryInfo.color}`}>
                              {categoryInfo.label}
                            </span>
                            
                            {event.impact_direction && (
                              <span className={`flex items-center gap-1 text-xs ${
                                event.impact_direction === 'positive' ? 'text-green-600' :
                                event.impact_direction === 'negative' ? 'text-red-600' : 'text-gray-500'
                              }`}>
                                {getImpactIcon(event.impact_direction)}
                                {event.impact_direction === 'positive' ? '正面影响' :
                                 event.impact_direction === 'negative' ? '负面影响' : '中性'}
                              </span>
                            )}
                            
                            {event.entities && event.entities.length > 0 && (
                              <span className="text-xs text-gray-400">
                                关联: {event.entities.slice(0, 3).map(e => e.name).join(', ')}
                                {event.entities.length > 3 && ` +${event.entities.length - 3}`}
                              </span>
                            )}
                          </div>
                        </div>
                        
                        <ExternalLink className="w-4 h-4 text-gray-400 flex-shrink-0" />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
