'use client';

import React, { useEffect, useState } from 'react';
import { X, ExternalLink, TrendingUp, TrendingDown, Minus, Calendar, Tag, Link2, Bot } from 'lucide-react';

interface EventDetailProps {
  eventId: number;
  onClose: () => void;
}

interface EventData {
  event: {
    id: number;
    title: string;
    summary: string;
    content: string;
    date: string;
    publish_date: string;
    category: string;
    type: string;
    importance: string;
    impact_direction: string;
    impact_magnitude: number;
    affected_dimensions: string[];
    score_change: Record<string, number>;
    entities: Array<{
      id: string;
      type: string;
      name: string;
    }>;
    source: {
      name: string;
      url: string;
      confidence: number;
    };
    ai_analysis: string;
  };
  relations: Array<{
    entity_id: string;
    entity_type: string;
    entity_name: string;
    relation_type: string;
    impact_score: number;
  }>;
}

const CATEGORY_LABELS: Record<string, string> = {
  global_macro: '全球宏观',
  china_macro: '中国宏观',
  market: '股市大盘',
  industry: '行业动态',
  company: '公司事件',
};

const IMPORTANCE_LABELS: Record<string, { label: string; color: string }> = {
  critical: { label: '重大事件', color: 'bg-red-100 text-red-700 border-red-200' },
  high: { label: '重要事件', color: 'bg-orange-100 text-orange-700 border-orange-200' },
  medium: { label: '一般事件', color: 'bg-yellow-100 text-yellow-700 border-yellow-200' },
  low: { label: '轻微事件', color: 'bg-gray-100 text-gray-700 border-gray-200' },
};

const ENTITY_TYPE_LABELS: Record<string, string> = {
  stock: '股票',
  industry: '行业',
  concept: '概念',
  person: '人物',
  organization: '机构',
};

export default function EventDetail({ eventId, onClose }: EventDetailProps) {
  const [data, setData] = useState<EventData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/analysis/events/${eventId}`);
        if (res.ok) {
          const json = await res.json();
          setData(json);
        }
      } catch (error) {
        console.error('Failed to fetch event detail:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
  }, [eventId]);

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl p-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl p-8">
          <p className="text-gray-500">事件不存在</p>
          <button onClick={onClose} className="mt-4 px-4 py-2 bg-gray-100 rounded-lg">
            关闭
          </button>
        </div>
      </div>
    );
  }

  const { event, relations } = data;
  const importanceInfo = IMPORTANCE_LABELS[event.importance] || { label: event.importance, color: 'bg-gray-100 text-gray-700' };

  const getImpactIcon = () => {
    if (event.impact_direction === 'positive') return <TrendingUp className="w-5 h-5 text-green-500" />;
    if (event.impact_direction === 'negative') return <TrendingDown className="w-5 h-5 text-red-500" />;
    return <Minus className="w-5 h-5 text-gray-400" />;
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="p-6 border-b border-gray-100 flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2 py-0.5 rounded text-xs border ${importanceInfo.color}`}>
                {importanceInfo.label}
              </span>
              <span className="px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-700">
                {CATEGORY_LABELS[event.category] || event.category}
              </span>
            </div>
            <h2 className="text-xl font-bold text-gray-800">{event.title}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              {event.date}
            </span>
            {event.source?.name && (
              <span className="flex items-center gap-1">
                <Tag className="w-4 h-4" />
                {event.source.name}
              </span>
            )}
          </div>

          {event.summary && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">事件摘要</h3>
              <p className="text-gray-600 leading-relaxed">{event.summary}</p>
            </div>
          )}

          {event.content && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">详细内容</h3>
              <p className="text-gray-600 leading-relaxed whitespace-pre-wrap">{event.content}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                {getImpactIcon()}
                影响评估
              </h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">影响方向</span>
                  <span className={`font-medium ${
                    event.impact_direction === 'positive' ? 'text-green-600' :
                    event.impact_direction === 'negative' ? 'text-red-600' : 'text-gray-600'
                  }`}>
                    {event.impact_direction === 'positive' ? '正面' :
                     event.impact_direction === 'negative' ? '负面' : '中性'}
                  </span>
                </div>
                {event.impact_magnitude && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">影响程度</span>
                    <span className="font-medium text-gray-700">{event.impact_magnitude}/10</span>
                  </div>
                )}
                {event.score_change && Object.keys(event.score_change).length > 0 && (
                  <div className="pt-2 border-t border-gray-200">
                    <span className="text-xs text-gray-500">评分变化</span>
                    <div className="mt-1 space-y-1">
                      {Object.entries(event.score_change).map(([dim, change]) => (
                        <div key={dim} className="flex items-center justify-between text-sm">
                          <span className="text-gray-500">{dim}</span>
                          <span className={`font-medium ${change > 0 ? 'text-green-600' : change < 0 ? 'text-red-600' : 'text-gray-600'}`}>
                            {change > 0 ? '+' : ''}{change}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="bg-gray-50 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <Link2 className="w-4 h-4" />
                关联实体
              </h3>
              {relations.length > 0 ? (
                <div className="space-y-2">
                  {relations.slice(0, 6).map((rel, idx) => (
                    <div key={idx} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className="px-1.5 py-0.5 bg-white rounded text-xs text-gray-500">
                          {ENTITY_TYPE_LABELS[rel.entity_type] || rel.entity_type}
                        </span>
                        <span className="text-gray-700">{rel.entity_name}</span>
                      </div>
                      {rel.impact_score && (
                        <span className={`text-xs ${rel.impact_score > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {rel.impact_score > 0 ? '+' : ''}{rel.impact_score}
                        </span>
                      )}
                    </div>
                  ))}
                  {relations.length > 6 && (
                    <span className="text-xs text-gray-400">+{relations.length - 6} 更多</span>
                  )}
                </div>
              ) : (
                <p className="text-sm text-gray-400">暂无关联实体</p>
              )}
            </div>
          </div>

          {event.ai_analysis && (
            <div className="bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                <Bot className="w-4 h-4" />
                AI 分析
              </h3>
              <p className="text-gray-600 leading-relaxed">{event.ai_analysis}</p>
            </div>
          )}

          {event.entities && event.entities.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">相关标的</h3>
              <div className="flex flex-wrap gap-2">
                {event.entities.map((entity, idx) => (
                  <span
                    key={idx}
                    className="px-3 py-1 bg-gray-100 rounded-full text-sm text-gray-600 hover:bg-gray-200 cursor-pointer transition-colors"
                  >
                    {entity.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-gray-100 flex items-center justify-between">
          <div className="text-xs text-gray-400">
            {event.source?.confidence && `置信度: ${(event.source.confidence * 100).toFixed(0)}%`}
          </div>
          <div className="flex items-center gap-2">
            {event.source?.url && (
              <a
                href={event.source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg flex items-center gap-1"
              >
                <ExternalLink className="w-4 h-4" />
                查看来源
              </a>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              关闭
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
