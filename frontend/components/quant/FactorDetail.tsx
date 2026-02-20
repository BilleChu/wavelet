'use client';

import { useState, useEffect, useCallback } from 'react';
import { Copy, Check, Play, RefreshCw, Code2, Settings, BarChart3, Table, Search, TrendingUp } from 'lucide-react';
import * as Tabs from '@radix-ui/react-tabs';
import * as Tooltip from '@radix-ui/react-tooltip';
import ReactECharts from 'echarts-for-react';
import Editor from 'react-simple-code-editor';
import { highlight, languages } from 'prismjs/components/prism-core';
import 'prismjs/components/prism-python';
import 'prismjs/themes/prism-tomorrow.css';
import { API_BASE_URL } from '@/services/apiConfig';
import { quantService, FactorDataResponse } from '@/services/quantService';

interface ParameterDefinition {
  name: string;
  type: string;
  default: any;
  description: string;
  required: boolean;
  min?: number;
  max?: number;
  step?: number;
  options?: string[];
  input_type: 'slider' | 'number' | 'text' | 'select' | 'switch';
}

interface FactorDetailProps {
  factorId: string;
  factorName: string;
  factorCode: string;
  onClose?: () => void;
}

const highlightPython = (code: string) => {
  return highlight(code, languages.python, 'python');
};

export function FactorDetail({ factorId, factorName, factorCode, onClose }: FactorDetailProps) {
  const [activeTab, setActiveTab] = useState('code');
  const [code, setCode] = useState<string>('');
  const [parameters, setParameters] = useState<ParameterDefinition[]>([]);
  const [paramValues, setParamValues] = useState<Record<string, any>>({});
  const [previewResult, setPreviewResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  
  const [stockCode, setStockCode] = useState('600000.SH');
  const [frequency, setFrequency] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [lookbackDays, setLookbackDays] = useState(120);
  const [factorData, setFactorData] = useState<FactorDataResponse | null>(null);
  const [dataLoading, setDataLoading] = useState(false);

  useEffect(() => {
    loadFactorCode();
    loadFactorParameters();
  }, [factorId]);

  const loadFactorCode = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/quant/factors/${factorId}/code`);
      if (response.ok) {
        const data = await response.json();
        setCode(data.code);
      }
    } catch (error) {
      console.error('Failed to load factor code:', error);
    }
  };

  const loadFactorParameters = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/quant/factors/${factorId}/parameters`);
      if (response.ok) {
        const data = await response.json();
        setParameters(data.parameters);
        
        const defaults: Record<string, any> = {};
        data.parameters.forEach((p: ParameterDefinition) => {
          defaults[p.name] = p.default;
        });
        setParamValues(defaults);
      }
    } catch (error) {
      console.error('Failed to load parameters:', error);
    }
  };

  const handlePreview = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/quant/factors/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          factor_id: factorId,
          stock_codes: ['600000.SH', '600036.SH', '000001.SZ'],
          parameters: paramValues,
          lookback_days: 60,
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        setPreviewResult(data);
        setActiveTab('result');
      }
    } catch (error) {
      console.error('Failed to preview:', error);
    } finally {
      setLoading(false);
    }
  }, [factorId, paramValues]);

  const copyCode = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleQueryFactorData = useCallback(async () => {
    setDataLoading(true);
    try {
      const result = await quantService.queryFactorData({
        factor_id: factorId,
        stock_code: stockCode,
        frequency: frequency,
        lookback_days: lookbackDays,
      });
      setFactorData(result);
      setActiveTab('data');
    } catch (error) {
      console.error('Failed to query factor data:', error);
    } finally {
      setDataLoading(false);
    }
  }, [factorId, stockCode, frequency, lookbackDays]);

  const renderParameterInput = (param: ParameterDefinition) => {
    const value = paramValues[param.name] ?? param.default;

    switch (param.input_type) {
      case 'slider':
        return (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">{param.min}</span>
              <span className="text-blue-400 font-medium">{value}</span>
              <span className="text-gray-400">{param.max}</span>
            </div>
            <input
              type="range"
              min={param.min}
              max={param.max}
              step={param.step || 1}
              value={value}
              onChange={(e) => setParamValues(prev => ({ ...prev, [param.name]: Number(e.target.value) }))}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
          </div>
        );
      
      case 'number':
        return (
          <input
            type="number"
            value={value ?? ''}
            onChange={(e) => setParamValues(prev => ({ ...prev, [param.name]: Number(e.target.value) }))}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
            placeholder={`默认: ${param.default}`}
          />
        );
      
      case 'text':
        return (
          <input
            type="text"
            value={value ?? ''}
            onChange={(e) => setParamValues(prev => ({ ...prev, [param.name]: e.target.value }))}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
            placeholder={`默认: ${param.default}`}
          />
        );
      
      case 'select':
        return (
          <select
            value={value ?? ''}
            onChange={(e) => setParamValues(prev => ({ ...prev, [param.name]: e.target.value }))}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
          >
            {param.options?.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        );
      
      case 'switch':
        return (
          <label className="flex items-center cursor-pointer">
            <div className="relative">
              <input
                type="checkbox"
                checked={value ?? false}
                onChange={(e) => setParamValues(prev => ({ ...prev, [param.name]: e.target.checked }))}
                className="sr-only"
              />
              <div className={`w-10 h-6 rounded-full transition-colors ${value ? 'bg-blue-500' : 'bg-gray-600'}`}>
                <div className={`absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform ${value ? 'translate-x-4' : ''}`} />
              </div>
            </div>
            <span className="ml-3 text-sm text-gray-300">{value ? '开启' : '关闭'}</span>
          </label>
        );
      
      default:
        return null;
    }
  };

  const chartOption = previewResult?.chart_data ? {
    title: {
      text: `${factorName} 因子值趋势`,
      textStyle: { color: '#fff', fontSize: 14 },
      left: 'center',
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(0,0,0,0.8)',
      borderColor: '#333',
      textStyle: { color: '#fff' },
    },
    legend: {
      data: previewResult.chart_data.datasets.map((d: any) => d.label),
      textStyle: { color: '#999' },
      bottom: 0,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '15%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: previewResult.chart_data.labels,
      axisLine: { lineStyle: { color: '#333' } },
      axisLabel: { color: '#999', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#333' } },
      axisLabel: { color: '#999' },
      splitLine: { lineStyle: { color: '#222' } },
    },
    series: previewResult.chart_data.datasets.map((dataset: any) => ({
      name: dataset.label,
      type: 'line',
      data: dataset.data,
      smooth: true,
      lineStyle: { color: dataset.borderColor },
      itemStyle: { color: dataset.borderColor },
      areaStyle: { color: dataset.backgroundColor },
    })),
  } : {};

  const factorDataChartOption = factorData?.chart_data ? {
    title: {
      text: `${factorData.factor_name} - ${factorData.stock_code}`,
      textStyle: { color: '#fff', fontSize: 14 },
      left: 'center',
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(0,0,0,0.8)',
      borderColor: '#333',
      textStyle: { color: '#fff' },
      formatter: (params: any) => {
        if (!params || params.length === 0) return '';
        const date = params[0].axisValue;
        let html = `<div style="font-weight:bold;margin-bottom:5px;">${date}</div>`;
        params.forEach((item: any) => {
          if (item.value !== null && item.value !== undefined) {
            html += `<div style="display:flex;justify-content:space-between;gap:20px;">
              <span>${item.marker} ${item.seriesName}</span>
              <span style="font-weight:bold;">${item.value.toFixed(4)}</span>
            </div>`;
          }
        });
        return html;
      },
    },
    legend: {
      data: factorData.chart_data.datasets.map((d: any) => d.label),
      textStyle: { color: '#999' },
      bottom: 0,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '15%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: factorData.chart_data.labels,
      axisLine: { lineStyle: { color: '#333' } },
      axisLabel: { 
        color: '#999', 
        fontSize: 10,
        rotate: 45,
      },
    },
    yAxis: factorData.chart_data.datasets.length > 1 ? [
      {
        type: 'value',
        name: '因子值',
        position: 'left',
        axisLine: { lineStyle: { color: '#3b82f6' } },
        axisLabel: { color: '#999' },
        splitLine: { lineStyle: { color: '#222' } },
      },
      {
        type: 'value',
        name: '标准化值',
        position: 'right',
        axisLine: { lineStyle: { color: '#10b981' } },
        axisLabel: { color: '#999' },
        splitLine: { show: false },
      },
    ] : {
      type: 'value',
      axisLine: { lineStyle: { color: '#333' } },
      axisLabel: { color: '#999' },
      splitLine: { lineStyle: { color: '#222' } },
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100,
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 50,
        borderColor: '#333',
        backgroundColor: '#1a1a1a',
        fillerColor: 'rgba(59, 130, 246, 0.2)',
        handleStyle: { color: '#3b82f6' },
        textStyle: { color: '#999' },
      },
    ],
    series: factorData.chart_data.datasets.map((dataset: any, index: number) => ({
      name: dataset.label,
      type: 'line',
      data: dataset.data,
      smooth: true,
      symbol: 'none',
      lineStyle: { color: dataset.borderColor, width: 2 },
      itemStyle: { color: dataset.borderColor },
      areaStyle: { color: dataset.backgroundColor },
      yAxisIndex: dataset.yAxisID === 'y1' ? 1 : 0,
    })),
  } : {};

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <div>
          <h3 className="text-lg font-semibold text-white">{factorName}</h3>
          <p className="text-sm text-gray-400">代码: {factorCode}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handlePreview}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg transition-colors"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            <span>{loading ? '计算中...' : '运行预览'}</span>
          </button>
        </div>
      </div>

      <Tabs.Root value={activeTab} onValueChange={setActiveTab}>
        <Tabs.List className="flex border-b border-gray-800">
          <Tabs.Trigger
            value="code"
            className="flex items-center gap-2 px-4 py-3 text-sm font-medium text-gray-400 hover:text-white data-[state=active]:text-blue-400 data-[state=active]:border-b-2 data-[state=active]:border-blue-400 transition-colors"
          >
            <Code2 className="w-4 h-4" />
            代码实现
          </Tabs.Trigger>
          <Tabs.Trigger
            value="params"
            className="flex items-center gap-2 px-4 py-3 text-sm font-medium text-gray-400 hover:text-white data-[state=active]:text-blue-400 data-[state=active]:border-b-2 data-[state=active]:border-blue-400 transition-colors"
          >
            <Settings className="w-4 h-4" />
            参数配置
          </Tabs.Trigger>
          <Tabs.Trigger
            value="data"
            className="flex items-center gap-2 px-4 py-3 text-sm font-medium text-gray-400 hover:text-white data-[state=active]:text-blue-400 data-[state=active]:border-b-2 data-[state=active]:border-blue-400 transition-colors"
          >
            <Search className="w-4 h-4" />
            标的查询
          </Tabs.Trigger>
          <Tabs.Trigger
            value="result"
            className="flex items-center gap-2 px-4 py-3 text-sm font-medium text-gray-400 hover:text-white data-[state=active]:text-blue-400 data-[state=active]:border-b-2 data-[state=active]:border-blue-400 transition-colors"
          >
            <BarChart3 className="w-4 h-4" />
            计算结果
          </Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="code" className="p-4">
          <div className="relative">
            <div className="absolute top-2 right-2 z-10">
              <Tooltip.Provider>
                <Tooltip.Root>
                  <Tooltip.Trigger asChild>
                    <button
                      onClick={copyCode}
                      className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
                    >
                      {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4 text-gray-400" />}
                    </button>
                  </Tooltip.Trigger>
                  <Tooltip.Portal>
                    <Tooltip.Content className="px-2 py-1 bg-gray-800 text-white text-xs rounded" sideOffset={5}>
                      {copied ? '已复制' : '复制代码'}
                    </Tooltip.Content>
                  </Tooltip.Portal>
                </Tooltip.Root>
              </Tooltip.Provider>
            </div>
            <div className="bg-[#2d2d2d] rounded-lg overflow-hidden max-h-96 overflow-auto">
              <Editor
                value={code}
                onValueChange={() => {}}
                highlight={highlightPython}
                padding={16}
                disabled
                textareaId="code-editor"
                className="font-mono text-sm"
                style={{
                  backgroundColor: '#2d2d2d',
                  fontFamily: '"Fira code", "Fira Mono", monospace',
                  fontSize: 13,
                  lineHeight: 1.5,
                }}
              />
            </div>
          </div>
        </Tabs.Content>

        <Tabs.Content value="params" className="p-4">
          {parameters.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <Settings className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>该因子没有可配置的参数</p>
            </div>
          ) : (
            <div className="space-y-6">
              {parameters.map((param) => (
                <div key={param.name} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-white">
                      {param.name}
                      {param.required && <span className="text-red-400 ml-1">*</span>}
                    </label>
                    <span className="text-xs text-gray-500">{param.type}</span>
                  </div>
                  {param.description && (
                    <p className="text-xs text-gray-400">{param.description}</p>
                  )}
                  {renderParameterInput(param)}
                </div>
              ))}
            </div>
          )}
        </Tabs.Content>

        <Tabs.Content value="data" className="p-4">
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-white">股票代码</label>
                <input
                  type="text"
                  value={stockCode}
                  onChange={(e) => setStockCode(e.target.value.toUpperCase())}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                  placeholder="例如: 600000.SH"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-white">数据频率</label>
                <select
                  value={frequency}
                  onChange={(e) => setFrequency(e.target.value as 'daily' | 'weekly' | 'monthly')}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                >
                  <option value="daily">日线</option>
                  <option value="weekly">周线</option>
                  <option value="monthly">月线</option>
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-white">回看天数</label>
                <input
                  type="number"
                  value={lookbackDays}
                  onChange={(e) => setLookbackDays(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                  min={30}
                  max={720}
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={handleQueryFactorData}
                  disabled={dataLoading}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg transition-colors"
                >
                  {dataLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                  <span>{dataLoading ? '查询中...' : '查询数据'}</span>
                </button>
              </div>
            </div>

            {!factorData ? (
              <div className="text-center py-12 text-gray-400">
                <TrendingUp className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p className="text-lg">输入股票代码查询因子数据</p>
                <p className="text-sm mt-2">支持不同周期和频率的数据展示</p>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {factorData.statistics && Object.entries(factorData.statistics).map(([key, value]) => (
                    <div key={key} className="bg-gray-800 rounded-lg p-3">
                      <div className="text-xs text-gray-400 uppercase">{key}</div>
                      <div className="text-lg font-semibold text-white mt-1">
                        {value !== null && typeof value === 'number' ? value.toFixed(4) : '-'}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="bg-gray-800 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-sm font-medium text-white">因子值趋势图</h4>
                    <div className="flex items-center gap-2 text-xs text-gray-400">
                      <span>频率: {factorData.frequency === 'daily' ? '日线' : factorData.frequency === 'weekly' ? '周线' : '月线'}</span>
                      <span>|</span>
                      <span>数据点: {factorData.data.length}</span>
                    </div>
                  </div>
                  <ReactECharts option={factorDataChartOption} style={{ height: '400px' }} />
                </div>

                <div className="bg-gray-800 rounded-lg overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700">
                    <h4 className="text-sm font-medium text-white flex items-center gap-2">
                      <Table className="w-4 h-4" />
                      数据明细
                    </h4>
                    <span className="text-xs text-gray-400">最近20条</span>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-900">
                        <tr>
                          <th className="px-4 py-2 text-left text-gray-400">交易日期</th>
                          <th className="px-4 py-2 text-right text-gray-400">因子值</th>
                          <th className="px-4 py-2 text-right text-gray-400">标准化值</th>
                          <th className="px-4 py-2 text-right text-gray-400">排名</th>
                          <th className="px-4 py-2 text-right text-gray-400">百分位</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-700">
                        {factorData.data.slice(-20).reverse().map((row, idx) => (
                          <tr key={idx} className="hover:bg-gray-700/50">
                            <td className="px-4 py-2 text-white">{row.trade_date}</td>
                            <td className="px-4 py-2 text-right text-blue-400 font-mono">
                              {row.value?.toFixed(4) ?? '-'}
                            </td>
                            <td className="px-4 py-2 text-right text-green-400 font-mono">
                              {row.value_normalized?.toFixed(4) ?? '-'}
                            </td>
                            <td className="px-4 py-2 text-right text-gray-300">
                              {row.value_rank ?? '-'}
                            </td>
                            <td className="px-4 py-2 text-right text-gray-300">
                              {row.value_percentile !== null ? `${(row.value_percentile * 100).toFixed(1)}%` : '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        </Tabs.Content>

        <Tabs.Content value="result" className="p-4">
          {!previewResult ? (
            <div className="text-center py-8 text-gray-400">
              <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>点击&ldquo;运行预览&rdquo;查看计算结果</p>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {previewResult.statistics && Object.entries(previewResult.statistics).map(([key, value]) => (
                  <div key={key} className="bg-gray-800 rounded-lg p-3">
                    <div className="text-xs text-gray-400 uppercase">{key}</div>
                    <div className="text-lg font-semibold text-white mt-1">
                      {typeof value === 'number' ? value.toFixed(4) : String(value)}
                    </div>
                  </div>
                ))}
              </div>

              <div className="bg-gray-800 rounded-lg p-4">
                <h4 className="text-sm font-medium text-white mb-4">因子值趋势图</h4>
                <ReactECharts option={chartOption} style={{ height: '300px' }} />
              </div>

              <div className="bg-gray-800 rounded-lg overflow-hidden">
                <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700">
                  <h4 className="text-sm font-medium text-white flex items-center gap-2">
                    <Table className="w-4 h-4" />
                    计算结果明细
                  </h4>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-900">
                      <tr>
                        <th className="px-4 py-2 text-left text-gray-400">股票代码</th>
                        <th className="px-4 py-2 text-left text-gray-400">交易日期</th>
                        <th className="px-4 py-2 text-right text-gray-400">因子值</th>
                        <th className="px-4 py-2 text-right text-gray-400">标准化值</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                      {previewResult.results?.slice(0, 10).map((row: any, idx: number) => (
                        <tr key={idx} className="hover:bg-gray-700/50">
                          <td className="px-4 py-2 text-white">{row.code}</td>
                          <td className="px-4 py-2 text-gray-300">{row.trade_date}</td>
                          <td className="px-4 py-2 text-right text-blue-400 font-mono">
                            {row.value?.toFixed(4) ?? '-'}
                          </td>
                          <td className="px-4 py-2 text-right text-green-400 font-mono">
                            {row.value_normalized?.toFixed(4) ?? '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
