/**
 * Attribution Analysis Component
 * 
 * Visualizes performance attribution using:
 * - Brinson attribution (Allocation, Selection, Interaction)
 * - Factor attribution
 * - Sector attribution
 */

'use client';

import React, { memo, useMemo } from 'react';
import ReactECharts, { EChartsOption } from 'echarts-for-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { AttributionResult } from '@/services/quantService';

interface AttributionChartProps {
  attribution: AttributionResult;
}

const COLORS = ['#3182ce', '#38a169', '#d69e2e', '#e53e3e', '#805ad5', '#319795', '#dd6b20'];

export const AttributionChart = memo(function AttributionChart({ attribution }: AttributionChartProps) {
  // Prepare Brinson attribution data
  const brinsonData = useMemo(() => {
    if (!attribution?.brinson) return [];
    
    return [
      { name: '配置效应', value: attribution.brinson.allocation_effect },
      { name: '选股效应', value: attribution.brinson.selection_effect },
      { name: '交互效应', value: attribution.brinson.interaction_effect },
      { name: '总主动收益', value: attribution.brinson.total_active_return },
    ];
  }, [attribution]);

  // Prepare factor attribution data
  const factorData = useMemo(() => {
    if (!attribution?.factor) return [];
    
    return Object.entries(attribution.factor)
      .filter(([_, value]) => Math.abs(value) > 0.001)
      .map(([factor, value]) => ({
        name: factor === 'size' ? '规模因子' : 
              factor === 'value' ? '价值因子' : 
              factor === 'momentum' ? '动量因子' : 
              factor === 'quality' ? '质量因子' : 
              factor === 'volatility' ? '波动率因子' : 
              factor === 'liquidity' ? '流动性因子' : '其他因子',
        value: value * 100,
      }))
      .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
  }, [attribution]);

  // Prepare sector attribution data
  const sectorData = useMemo(() => {
    if (!attribution?.sector || attribution.sector.length === 0) return [];
    
    return attribution.sector
      .map(item => ({
        name: item.sector,
        配置效应: item.allocation_effect * 100,
        选股效应: item.selection_effect * 100,
        总效应: item.total_effect * 100,
      }))
      .sort((a, b) => Math.abs(b.总效应) - Math.abs(a.总效应));
  }, [attribution]);

  const formatPercent = (value: number): string => {
    return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  return (
    <div className="space-y-6">
      {/* Brinson Attribution */}
      {brinsonData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Brinson 归因分析</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Pie Chart */}
              <div className="h-64">
                <ReactECharts
                  option={{
                    tooltip: {
                      formatter: (params: any) => `${params.name}: ${formatPercent(params.value)}`,
                    },
                    series: [
                      {
                        name: 'Brinson 归因',
                        type: 'pie',
                        radius: '70%',
                        data: brinsonData.slice(0, 3).map((item, index) => ({
                          value: item.value * 100,
                          name: item.name,
                          itemStyle: { color: COLORS[index % COLORS.length] },
                        })),
                        label: {
                          formatter: ({ name, value }: any) => `${name}: ${formatPercent(value)}`,
                        },
                      },
                    ],
                  }}
                  style={{ height: '100%' }}
                />
              </div>

              {/* Metrics */}
              <div className="space-y-3">
                {brinsonData.map((item, index) => (
                  <div
                    key={item.name}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      />
                      <span className="text-sm font-medium">{item.name}</span>
                    </div>
                    <span
                      className={`text-sm font-bold ${
                        item.value > 0 ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      {formatPercent(item.value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Factor Attribution */}
      {factorData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">因子归因分析</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ReactECharts
                option={{
                  tooltip: {
                    trigger: 'axis',
                    axisPointer: { type: 'shadow' },
                    formatter: (params: any) => {
                      const value = params[0]?.value;
                      return `${params[0]?.name}: ${formatPercent(value)}`;
                    },
                  },
                  xAxis: {
                    type: 'value',
                    axisLabel: {
                      formatter: (value: number) => `${value}%`,
                    },
                  },
                  yAxis: {
                    type: 'category',
                    data: factorData.map((d) => d.name),
                    axisLabel: {
                      fontSize: 12,
                    },
                  },
                  series: [
                    {
                      name: '因子贡献 (%)',
                      type: 'bar',
                      data: factorData.map((d) => d.value),
                      itemStyle: {
                        color: (params: any) => {
                          return params.value > 0 ? '#38a169' : '#e53e3e';
                        },
                      },
                    },
                  ],
                }}
                style={{ height: '100%' }}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sector Attribution */}
      {sectorData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">行业归因分析</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-2 px-3 font-semibold">行业</th>
                    <th className="text-right py-2 px-3 font-semibold">配置效应</th>
                    <th className="text-right py-2 px-3 font-semibold">选股效应</th>
                    <th className="text-right py-2 px-3 font-semibold">总效应</th>
                  </tr>
                </thead>
                <tbody>
                  {sectorData.map((sector, index) => (
                    <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-2 px-3 font-medium">{sector.name}</td>
                      <td className={`text-right py-2 px-3 ${sector.配置效应 > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatPercent(sector.配置效应)}
                      </td>
                      <td className={`text-right py-2 px-3 ${sector.选股效应 > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatPercent(sector.选股效应)}
                      </td>
                      <td className={`text-right py-2 px-3 font-bold ${sector.总效应 > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatPercent(sector.总效应)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary Card */}
      <Card className="bg-gradient-to-br from-blue-50 to-indigo-50">
        <CardHeader>
          <CardTitle className="text-lg">归因总结</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {attribution?.brinson && (
            <>
              <div className="text-center p-4 bg-white rounded-lg shadow-sm">
                <div className="text-xs text-gray-500 mb-1">主要贡献来源</div>
                <div className="text-lg font-bold text-gray-900">
                  {Math.abs(attribution.brinson.selection_effect) > Math.abs(attribution.brinson.allocation_effect)
                    ? '选股能力'
                    : '资产配置'}
                </div>
              </div>
              <div className="text-center p-4 bg-white rounded-lg shadow-sm">
                <div className="text-xs text-gray-500 mb-1">总主动收益</div>
                <div
                  className={`text-lg font-bold ${
                    attribution.brinson.total_active_return > 0 ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {formatPercent(attribution.brinson.total_active_return * 100)}
                </div>
              </div>
              <div className="text-center p-4 bg-white rounded-lg shadow-sm">
                <div className="text-xs text-gray-500 mb-1">影响因子数</div>
                <div className="text-lg font-bold text-gray-900">{factorData.length}</div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
});

export default AttributionChart;
