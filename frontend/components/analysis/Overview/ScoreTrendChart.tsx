'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false });

interface ScoreTrendChartProps {
  scores: Array<{
    date: string;
    score: number | null;
    total: number | null;
  }>;
  events?: Array<{
    id: number;
    title: string;
    date: string;
    category: string;
    importance: string;
    impact_direction?: string;
  }>;
  dimension?: string;
  height?: number;
  onEventClick?: (eventId: number) => void;
}

export default function ScoreTrendChart({
  scores,
  events = [],
  dimension = 'total',
  height = 300,
  onEventClick,
}: ScoreTrendChartProps) {
  const [chartData, setChartData] = useState<any>(null);

  useEffect(() => {
    if (!scores || scores.length === 0) return;

    const dates = scores.map(s => s.date);
    const values = scores.map(s => s.score ?? s.total ?? 50);

    const eventMarkers = events
      .filter(e => dates.includes(e.date))
      .map(e => {
        const idx = dates.indexOf(e.date);
        return {
          name: e.title.slice(0, 10) + (e.title.length > 10 ? '...' : ''),
          coord: [e.date, values[idx]],
          value: e.title.slice(0, 6),
          itemStyle: {
            color: e.impact_direction === 'positive' ? '#52c41a' :
                   e.impact_direction === 'negative' ? '#ff4d4f' : '#faad14'
          }
        };
      });

    const option = {
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const date = params[0].axisValue;
          const score = params[0].value;
          const event = events.find(e => e.date === date);
          let html = `<div style="font-weight:bold">${date}</div>`;
          html += `<div>评分: <span style="color:#1890ff;font-weight:bold">${score?.toFixed(1)}</span></div>`;
          if (event) {
            html += `<div style="margin-top:4px;padding-top:4px;border-top:1px solid #eee">`;
            html += `<span style="color:${event.impact_direction === 'positive' ? '#52c41a' : event.impact_direction === 'negative' ? '#ff4d4f' : '#faad14'}">●</span> ${event.title}`;
            html += `</div>`;
          }
          return html;
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#e8e8e8' } },
        axisLabel: { 
          color: '#666',
          formatter: (value: string) => value.slice(5)
        }
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLine: { show: false },
        splitLine: { lineStyle: { color: '#f0f0f0' } },
        axisLabel: { color: '#999' }
      },
      series: [
        {
          name: '评分',
          type: 'line',
          data: values,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: {
            width: 3,
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 1, y2: 0,
              colorStops: [
                { offset: 0, color: '#1890ff' },
                { offset: 1, color: '#52c41a' }
              ]
            }
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(24,144,255,0.3)' },
                { offset: 1, color: 'rgba(24,144,255,0.05)' }
              ]
            }
          },
          markPoint: eventMarkers.length > 0 ? {
            symbol: 'pin',
            symbolSize: 40,
            label: {
              show: true,
              fontSize: 10,
              color: '#fff'
            },
            data: eventMarkers
          } : undefined
        }
      ]
    };

    setChartData(option);
  }, [scores, events, dimension]);

  if (!chartData) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span className="text-gray-400">加载中...</span>
      </div>
    );
  }

  const onEvents = {
    click: (params: any) => {
      if (params.componentType === 'markPoint' && onEventClick) {
        const event = events.find(e => e.title.includes(params.name));
        if (event) {
          onEventClick(event.id);
        }
      }
    }
  };

  return (
    <ReactECharts
      option={chartData}
      style={{ height }}
      onEvents={onEvents}
      opts={{ renderer: 'canvas' }}
    />
  );
}
