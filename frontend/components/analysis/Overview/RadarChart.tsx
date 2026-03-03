'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false });

interface RadarChartProps {
  dimensions: Array<{
    name: string;
    score: number;
    previousScore?: number;
  }>;
  height?: number;
}

const DIMENSION_NAMES: Record<string, string> = {
  global_macro: '全球宏观',
  china_macro: '中国宏观',
  market: '股市大盘',
  industry: '行业情况',
  stock: '个股情况',
};

export default function RadarChart({ dimensions, height = 280 }: RadarChartProps) {
  const [chartData, setChartData] = useState<any>(null);

  useEffect(() => {
    if (!dimensions || dimensions.length === 0) return;

    const option = {
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          const values = params.value;
          const names = params.name;
          let html = '<div style="font-weight:bold;margin-bottom:8px">评分概览</div>';
          dimensions.forEach((dim, idx) => {
            const name = DIMENSION_NAMES[dim.name] || dim.name;
            html += `<div>${name}: <span style="color:#1890ff;font-weight:bold">${values[idx]}</span>分</div>`;
          });
          return html;
        }
      },
      radar: {
        indicator: dimensions.map(dim => ({
          name: DIMENSION_NAMES[dim.name] || dim.name,
          max: 100,
        })),
        center: ['50%', '50%'],
        radius: '65%',
        axisName: {
          color: '#666',
          fontSize: 12,
        },
        splitArea: {
          areaStyle: {
            color: ['rgba(24,144,255,0.02)', 'rgba(24,144,255,0.05)', 'rgba(24,144,255,0.08)', 'rgba(24,144,255,0.11)', 'rgba(24,144,255,0.14)']
          }
        },
        axisLine: {
          lineStyle: { color: 'rgba(0,0,0,0.1)' }
        },
        splitLine: {
          lineStyle: { color: 'rgba(0,0,0,0.1)' }
        }
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: dimensions.map(d => d.score),
              name: '当前评分',
              symbol: 'circle',
              symbolSize: 6,
              lineStyle: {
                width: 2,
                color: '#1890ff'
              },
              areaStyle: {
                color: 'rgba(24,144,255,0.3)'
              },
              itemStyle: {
                color: '#1890ff'
              }
            }
          ]
        }
      ]
    };

    if (dimensions.some(d => d.previousScore !== undefined)) {
      option.series[0].data.push({
        value: dimensions.map(d => d.previousScore ?? d.score),
        name: '上期评分',
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: {
          width: 1,
          type: 'dashed',
          color: '#999'
        },
        areaStyle: {
          color: 'rgba(153,153,153,0.1)'
        },
        itemStyle: {
          color: '#999'
        }
      });
    }

    setChartData(option);
  }, [dimensions]);

  if (!chartData) {
    return (
      <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span className="text-gray-400">加载中...</span>
      </div>
    );
  }

  return (
    <ReactECharts
      option={chartData}
      style={{ height }}
      opts={{ renderer: 'canvas' }}
    />
  );
}
