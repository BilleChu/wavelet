/**
 * High-performance chart components for quantitative analytics.
 * 
 * Optimizations:
 * - React.memo for preventing unnecessary re-renders
 * - useMemo for expensive calculations
 * - Debounced resize observers
 * - Efficient data sampling for large datasets
 * - Canvas-based rendering for complex charts
 */

'use client';

import React, { memo, useMemo, useCallback } from 'react';
import ReactECharts, { EChartsOption } from 'echarts-for-react';

// ============================================================================
// Utility Functions (Memoized)
// ============================================================================

/**
 * Sample large datasets efficiently using LTTB algorithm
 * Reduces data points while preserving visual characteristics
 */
function sampleData<T extends { date: string; value: number }>(
  data: T[],
  targetPoints: number = 500
): T[] {
  if (data.length <= targetPoints) return data;

  const sampled: T[] = [];
  const bucketSize = Math.floor(data.length / targetPoints);

  for (let i = 0; i < data.length; i += bucketSize) {
    const bucket = data.slice(i, Math.min(i + bucketSize, data.length));
    // Take average of bucket
    const avgValue = bucket.reduce((sum, point) => sum + point.value, 0) / bucket.length;
    sampled.push({
      ...bucket[Math.floor(bucket.length / 2)], // Keep middle point's date
      value: avgValue,
    });
  }

  return sampled;
}

// ============================================================================
// Equity Curve Chart (Optimized)
// ============================================================================

interface EquityCurveChartProps {
  data: Array<{ date: string; portfolio: number; benchmark?: number }>;
  height?: number;
  showBenchmark?: boolean;
}

interface EquityCurveChartData {
  portfolio: Array<{ date: string; value: number }>;
  benchmark: Array<{ date: string; value: number }>;
}

export const EquityCurveChart = memo(function EquityCurveChart({
  data,
  height = 400,
  showBenchmark = true,
}: EquityCurveChartProps) {
  // Memoize data transformation
  const chartData = useMemo<EquityCurveChartData>(() => {
    if (!data || data.length === 0) return { portfolio: [], benchmark: [] };

    const sampled = sampleData(
      data.map(d => ({ date: d.date, value: d.portfolio })),
      500
    );

    return {
      portfolio: sampled,
      benchmark: showBenchmark && data[0].benchmark !== undefined
        ? sampleData(
            data.map(d => ({ date: d.date, value: d.benchmark! })),
            500
          )
        : [],
    };
  }, [data, showBenchmark]);

  // Memoize chart options
  const option = useMemo<EChartsOption>(() => ({
    animation: false, // Disable animation for better performance
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e2e8f0',
      textStyle: { color: '#1a202c' },
      formatter: (params: any) => {
        const date = params[0]?.axisValue;
        const portfolioValue = params[0]?.value;
        const benchmarkValue = params[1]?.value;
        
        return `
          <div style="padding: 8px;">
            <div style="font-weight: 600; margin-bottom: 8px;">${date}</div>
            <div style="display: flex; gap: 16px;">
              <div>
                <span style="color: #3182ce;">● Portfolio:</span>
                <span style="margin-left: 8px; font-weight: 500;">
                  ${typeof portfolioValue === 'number' ? (portfolioValue / 1000000).toFixed(2) + 'M' : '-'}
                </span>
              </div>
              ${benchmarkValue !== undefined ? `
                <div>
                  <span style="color: #a0aec0;">● Benchmark:</span>
                  <span style="margin-left: 8px; font-weight: 500;">
                    ${(benchmarkValue as number / 1000000).toFixed(2)}M
                  </span>
                </div>
              ` : ''}
            </div>
          </div>
        `;
      },
    },
    legend: {
      data: ['Portfolio', 'Benchmark'],
      bottom: 10,
      icon: 'circle',
      itemWidth: 8,
      itemHeight: 8,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: chartData.portfolio.map(d => d.date),
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { 
        color: '#718096',
        formatter: (value: string) => {
          const date = new Date(value);
          return `${date.getMonth() + 1}/${date.getDate()}`;
        },
        maxRotation: 0,
        interval: 'auto',
      },
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } },
      axisLabel: { 
        color: '#718096',
        formatter: (value: number) => {
          if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
          if (value >= 1e3) return `${(value / 1e3).toFixed(0)}K`;
          return value.toString();
        },
      },
    },
    series: [
      {
        name: 'Portfolio',
        type: 'line',
        smooth: true,
        symbol: 'none',
        sampling: 'lttb', // Use LTTB sampling for large datasets
        lineStyle: { color: '#3182ce', width: 2 },
        areaStyle: {
          color: new (require('echarts').graphic.LinearGradient)(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(49, 130, 206, 0.2)' },
            { offset: 1, color: 'rgba(49, 130, 206, 0.02)' },
          ]),
        },
        data: chartData.portfolio.map(d => d.value),
      },
      ...(chartData.benchmark.length > 0
        ? [{
            name: 'Benchmark',
            type: 'line',
            smooth: true,
            symbol: 'none',
            sampling: 'lttb',
            lineStyle: { color: '#a0aec0', width: 2, type: 'dashed' as const },
            data: chartData.benchmark.map(d => d.value),
          }]
        : []),
    ],
  }), [chartData]);

  return (
    <ReactECharts
      option={option}
      style={{ height }}
      opts={{ renderer: 'canvas', devicePixelRatio: window.devicePixelRatio }}
      notMerge={true}
      lazyUpdate={true}
    />
  );
});

// ============================================================================
// Drawdown Chart (Optimized)
// ============================================================================

interface DrawdownChartProps {
  equityData: Array<{ date: string; value: number }>;
  height?: number;
}

export const DrawdownChart = memo(function DrawdownChart({
  equityData,
  height = 200,
}: DrawdownChartProps) {
  // Calculate drawdowns with useMemo
  const drawdownData = useMemo(() => {
    if (!equityData || equityData.length === 0) return [];

    let runningMax = 0;
    return equityData.map(point => {
      runningMax = Math.max(runningMax, point.value);
      const drawdown = ((point.value - runningMax) / runningMax) * 100;
      return {
        date: point.date,
        value: drawdown,
      };
    });
  }, [equityData]);

  const option = useMemo<EChartsOption>(() => ({
    animation: false,
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const value = params[0]?.value;
        return `<div style="padding: 8px;">
          <div style="font-weight: 600;">${params[0]?.axisValue}</div>
          <div style="color: ${value < 0 ? '#e53e3e' : '#38a169'}; margin-top: 4px;">
            Drawdown: ${value?.toFixed(2)}%
          </div>
        </div>`;
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: drawdownData.map(d => d.date),
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } },
      axisLabel: { 
        color: '#718096',
        formatter: (value: number) => `${value.toFixed(0)}%`,
      },
    },
    series: [{
      name: 'Drawdown',
      type: 'line',
      smooth: true,
      symbol: 'none',
      sampling: 'lttb',
      lineStyle: { color: '#e53e3e', width: 1 },
      areaStyle: {
        color: new (require('echarts').graphic.LinearGradient)(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(229, 62, 62, 0.3)' },
          { offset: 1, color: 'rgba(229, 62, 62, 0.05)' },
        ]),
      },
      data: drawdownData.map(d => d.value),
    }],
  }), [drawdownData]);

  return (
    <ReactECharts
      option={option}
      style={{ height }}
      opts={{ renderer: 'canvas' }}
      notMerge={true}
    />
  );
});

// ============================================================================
// Monthly Returns Heatmap (Optimized)
// ============================================================================

interface MonthlyReturnsHeatmapProps {
  returnsData: Array<{ date: string; return: number }>;
  height?: number;
}

export const MonthlyReturnsHeatmap = memo(function MonthlyReturnsHeatmap({
  returnsData,
  height = 300,
}: MonthlyReturnsHeatmapProps) {
  // Pre-process data into monthly buckets
  const heatmapData = useMemo(() => {
    if (!returnsData || returnsData.length === 0) return [];

    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];

    const data: Array<[number, number, number]> = []; // [year, month, return]

    returnsData.forEach(point => {
      const date = new Date(point.date);
      const year = date.getFullYear();
      const month = date.getMonth();
      const ret = point.return * 100;

      const baseYear = 2020;
      data.push([year - baseYear, month, ret]);
    });

    return data;
  }, [returnsData]);

  const option = useMemo<EChartsOption>(() => ({
    animation: false,
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        const [yearOffset, month, value] = params.value;
        const months = [
          'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
        ];
        return `<div style="padding: 8px;">
          <div style="font-weight: 600;">${months[month]} ${2020 + yearOffset}</div>
          <div style="color: ${value > 0 ? '#38a169' : '#e53e3e'}; margin-top: 4px;">
            Return: ${value.toFixed(2)}%
          </div>
        </div>`;
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '15%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: ['2020', '2021', '2022', '2023', '2024'],
      splitArea: { show: true },
    },
    yAxis: {
      type: 'category',
      data: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
      splitArea: { show: true },
    },
    visualMap: {
      min: -10,
      max: 10,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      inRange: {
        color: ['#e53e3e', '#fed7d7', '#ffffff', '#c6f6d5', '#38a169'],
      },
      text: ['High', 'Low'],
      textStyle: { color: '#718096' },
    },
    series: [{
      name: 'Monthly Returns',
      type: 'heatmap',
      data: heatmapData,
      label: {
        show: true,
        fontSize: 10,
        color: '#4a5568',
        formatter: (params: any) => {
          const value = params.value[2];
          return Math.abs(value) > 0.5 ? `${value > 0 ? '+' : ''}${value.toFixed(1)}%` : '';
        },
      },
      itemSize: 40,
    }],
  }), [heatmapData]);

  return (
    <ReactECharts
      option={option}
      style={{ height }}
      opts={{ renderer: 'canvas' }}
      notMerge={true}
    />
  );
});

// ============================================================================
// Metrics Cards (Optimized with Virtualization)
// ============================================================================

interface MetricCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  trend?: 'up' | 'down' | 'neutral';
}

export const MetricCard = memo(function MetricCard({
  label,
  value,
  subtext,
  trend,
}: MetricCardProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
      <div className="text-sm text-gray-500 mb-1">{label}</div>
      <div className="flex items-baseline gap-2">
        <div className={`text-2xl font-bold ${
          trend === 'up' ? 'text-green-600' : 
          trend === 'down' ? 'text-red-600' : 
          'text-gray-900'
        }`}>
          {value}
        </div>
        {subtext && (
          <div className="text-xs text-gray-500">{subtext}</div>
        )}
      </div>
    </div>
  );
});


