'use client';

import React from 'react';

interface DimensionCardProps {
  name: string;
  displayName: string;
  score: number;
  trend: 'up' | 'down' | 'flat';
  change?: number;
  keyIndicators?: Array<{
    name: string;
    value: string;
    impact?: string;
    trend?: string;
  }>;
  onClick?: () => void;
  isSelected?: boolean;
}

export default function DimensionCard({
  name,
  displayName,
  score,
  trend,
  change = 0,
  keyIndicators = [],
  onClick,
  isSelected = false,
}: DimensionCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-green-500';
    if (score >= 40) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 70) return 'bg-green-50 border-green-200';
    if (score >= 40) return 'bg-yellow-50 border-yellow-200';
    return 'bg-red-50 border-red-200';
  };

  const getTrendIcon = () => {
    if (trend === 'up') return '📈';
    if (trend === 'down') return '📉';
    return '📊';
  };

  const getTrendColor = () => {
    if (change > 0) return 'text-green-500';
    if (change < 0) return 'text-red-500';
    return 'text-gray-400';
  };

  return (
    <div
      onClick={onClick}
      className={`
        relative p-4 rounded-xl border-2 cursor-pointer transition-all duration-300
        hover:shadow-lg hover:scale-[1.02]
        ${isSelected ? 'border-blue-500 shadow-lg ring-2 ring-blue-100' : 'border-gray-100'}
        ${getScoreBgColor(score)}
      `}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-lg font-medium text-gray-700">{displayName}</span>
        <span className="text-xl">{getTrendIcon()}</span>
      </div>
      
      <div className="flex items-end justify-between mb-3">
        <div>
          <span className={`text-4xl font-bold ${getScoreColor(score)}`}>
            {score.toFixed(0)}
          </span>
          <span className="text-lg text-gray-400 ml-1">分</span>
        </div>
        {change !== 0 && (
          <div className={`text-sm font-medium ${getTrendColor()}`}>
            {change > 0 ? '+' : ''}{change.toFixed(1)}
          </div>
        )}
      </div>

      <div className="w-full bg-gray-200 rounded-full h-2 mb-3">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${
            score >= 70 ? 'bg-green-500' : score >= 40 ? 'bg-yellow-500' : 'bg-red-500'
          }`}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </div>

      {keyIndicators.length > 0 && (
        <div className="space-y-1 pt-2 border-t border-gray-100">
          {keyIndicators.slice(0, 3).map((indicator, idx) => (
            <div key={idx} className="flex items-center justify-between text-xs">
              <span className="text-gray-500">{indicator.name}</span>
              <span className={`font-medium ${
                indicator.impact === 'positive' ? 'text-green-500' :
                indicator.impact === 'negative' ? 'text-red-500' : 'text-gray-600'
              }`}>
                {indicator.value}
              </span>
            </div>
          ))}
        </div>
      )}

      {isSelected && (
        <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-4 h-4 bg-blue-500 rotate-45" />
      )}
    </div>
  );
}
