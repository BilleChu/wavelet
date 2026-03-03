'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  BarChart3,
  Calculator,
  ChevronRight,
  Code,
  Copy,
  Check,
  Cpu,
  Database,
  LineChart,
  Play,
  Plus,
  RefreshCw,
  Settings,
  TrendingUp,
  Zap,
  FileCode,
  Info,
  Sliders,
  Search,
  X,
  Sparkles,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';

import FactorCreator from '@/components/quant/FactorCreator';
import StrategyCreator from '@/components/quant/StrategyCreator';

import {
  quantService,
  Factor,
  Strategy,
  BacktestResult,
  FactorValidationResult,
  FactorTestResult,
  FactorDataResponse,
  StrategyRunResponse,
  BacktestConfigOptions,
  BacktestStatusResponse,
  BacktestReportResponse,
} from '@/services/quantService';
import { API_BASE_URL } from '@/services/apiConfig';
import { factorTypeLabels, categoryLabels, formatPercent, formatNumber } from '@/constants/quant';
import ReactECharts from 'echarts-for-react';

interface FactorCode {
  factor_id: string;
  name: string;
  code: string;
  language: string;
  file_path?: string;
}

export default function QuantPage() {
  const [mounted, setMounted] = useState(false);
  const [activeTab, setActiveTab] = useState('factors');
  const [factors, setFactors] = useState<Factor[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(false);

  const [selectedFactor, setSelectedFactor] = useState<Factor | null>(null);
  const [selectedFactorCode, setSelectedFactorCode] = useState<FactorCode | null>(null);
  const [codeLoading, setCodeLoading] = useState(false);
  const [codeCopied, setCodeCopied] = useState(false);
  const [factorDetailTab, setFactorDetailTab] = useState('info');
  
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);

  const [customCode, setCustomCode] = useState(`def factor(df, period=20):
    """Custom factor calculation"""
    close = df['close']
    return close.pct_change(period).iloc[-1]
`);
  const [validationResult, setValidationResult] = useState<FactorValidationResult | null>(null);
  const [testResult, setTestResult] = useState<FactorTestResult | null>(null);
  
  const [stockCode, setStockCode] = useState('600000.SH');
  const [dataFrequency, setDataFrequency] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [lookbackDays, setLookbackDays] = useState(120);
  const [factorData, setFactorData] = useState<FactorDataResponse | null>(null);
  const [dataLoading, setDataLoading] = useState(false);
  
  const [strategyTopN, setStrategyTopN] = useState(20);
  const [strategyMinScore, setStrategyMinScore] = useState<number | undefined>(undefined);
  const [strategyResult, setStrategyResult] = useState<StrategyRunResponse | null>(null);
  const [strategyRunning, setStrategyRunning] = useState(false);
  const [strategyMaxPositions, setStrategyMaxPositions] = useState(50);
  const [strategyRebalanceFreq, setStrategyRebalanceFreq] = useState('monthly');
  
  const [showNewStrategyDialog, setShowNewStrategyDialog] = useState(false);
  const [showFactorCreator, setShowFactorCreator] = useState(false);
  const [showStrategyCreator, setShowStrategyCreator] = useState(false);
  const [newStrategyName, setNewStrategyName] = useState('');
  const [newStrategyCode, setNewStrategyCode] = useState('');
  const [newStrategyDescription, setNewStrategyDescription] = useState('');
  const [newStrategyFactors, setNewStrategyFactors] = useState<string[]>([]);
  const [newStrategyFactorWeights, setNewStrategyFactorWeights] = useState<Record<string, number>>({});
  const [newStrategyWeightMethod, setNewStrategyWeightMethod] = useState('equal');
  const [newStrategyMaxPositions, setNewStrategyMaxPositions] = useState(30);
  const [newStrategyRebalanceFreq, setNewStrategyRebalanceFreq] = useState('monthly');
  const [newStrategyCreating, setNewStrategyCreating] = useState(false);
  const [deletingFactor, setDeletingFactor] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const [backtestConfigs, setBacktestConfigs] = useState<BacktestConfigOptions | null>(null);
  const [backtestStrategyId, setBacktestStrategyId] = useState<string>('');
  const [backtestStartDate, setBacktestStartDate] = useState<string>('');
  const [backtestEndDate, setBacktestEndDate] = useState<string>('');
  const [backtestInitialCapital, setBacktestInitialCapital] = useState<number>(1000000);
  const [backtestBenchmark, setBacktestBenchmark] = useState<string>('000300');
  const [backtestCommissionRate, setBacktestCommissionRate] = useState<number>(0.0003);
  const [backtestSlippage, setBacktestSlippage] = useState<number>(0.001);
  const [backtestRunning, setBacktestRunning] = useState(false);
  const [backtestProgress, setBacktestProgress] = useState<BacktestStatusResponse | null>(null);
  const [backtestReport, setBacktestReport] = useState<BacktestReportResponse | null>(null);
  const [backtestHistory, setBacktestHistory] = useState<{ total: number; backtests: any[] } | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  const loadFactors = useCallback(async () => {
    setLoading(true);
    try {
      const response = await quantService.getFactors();
      setFactors(response.factors);
    } catch (error) {
      console.error('Failed to load factors:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadStrategies = useCallback(async () => {
    setLoading(true);
    try {
      const response = await quantService.getStrategies();
      setStrategies(response.strategies);
    } catch (error) {
      console.error('Failed to load strategies:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (mounted) {
      loadFactors();
      loadStrategies();
      loadBacktestConfigs();
    }
  }, [mounted, loadFactors, loadStrategies]);

  const loadBacktestConfigs = useCallback(async () => {
    try {
      const configs = await quantService.getBacktestConfigs();
      setBacktestConfigs(configs);
      setBacktestStartDate(configs.default_params.start_date);
      setBacktestEndDate(configs.default_params.end_date);
      setBacktestInitialCapital(configs.default_params.initial_capital);
      setBacktestCommissionRate(configs.default_params.commission_rate);
      setBacktestSlippage(configs.default_params.slippage);
    } catch (error) {
      console.error('Failed to load backtest configs:', error);
    }
  }, []);

  const loadFactorCode = useCallback(async (factorId: string) => {
    setCodeLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/quant/factors/${factorId}/code`);
      if (response.ok) {
        const data = await response.json();
        setSelectedFactorCode(data);
      }
    } catch (error) {
      console.error('Failed to load factor code:', error);
    } finally {
      setCodeLoading(false);
    }
  }, []);

  const handleSelectFactor = useCallback((factor: Factor) => {
    setSelectedFactor(factor);
    setFactorDetailTab('info');
    loadFactorCode(factor.factor_id);
  }, [loadFactorCode]);

  const copyCode = useCallback(async () => {
    if (selectedFactorCode?.code) {
      await navigator.clipboard.writeText(selectedFactorCode.code);
      setCodeCopied(true);
      setTimeout(() => setCodeCopied(false), 2000);
    }
  }, [selectedFactorCode]);

  const handleDeleteFactor = useCallback(async () => {
    if (!selectedFactor) return;
    
    setDeletingFactor(selectedFactor.factor_id);
    try {
      await quantService.deleteFactor(selectedFactor.factor_id);
      setSelectedFactor(null);
      setSelectedFactorCode(null);
      loadFactors();
    } catch (error) {
      console.error('Failed to delete factor:', error);
    } finally {
      setDeletingFactor(null);
      setShowDeleteConfirm(false);
    }
  }, [selectedFactor, loadFactors]);

  const handleRunBacktest = async () => {
    if (!backtestStrategyId) return;

    setBacktestRunning(true);
    setBacktestProgress(null);
    setBacktestReport(null);
    
    try {
      const { backtest_id } = await quantService.runBacktestAsync({
        strategy_id: backtestStrategyId,
        start_date: backtestStartDate,
        end_date: backtestEndDate,
        initial_capital: backtestInitialCapital,
        benchmark: backtestBenchmark,
        commission_rate: backtestCommissionRate,
        slippage: backtestSlippage,
      });

      await quantService.pollBacktestStatus(
        backtest_id,
        (status) => setBacktestProgress(status),
        2000,
        120
      );

      const report = await quantService.getBacktestReport(backtest_id);
      setBacktestReport(report);
      
      loadBacktestHistory();
    } catch (error) {
      console.error('Backtest failed:', error);
    } finally {
      setBacktestRunning(false);
    }
  };

  const loadBacktestHistory = useCallback(async () => {
    try {
      const history = await quantService.getBacktestHistory(10);
      setBacktestHistory(history);
    } catch (error) {
      console.error('Failed to load backtest history:', error);
    }
  }, []);

  const handleDatePreset = (days: number) => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);
    
    setBacktestEndDate(end.toISOString().split('T')[0]);
    setBacktestStartDate(start.toISOString().split('T')[0]);
  };

  const handleValidateCode = async () => {
    setLoading(true);
    try {
      const result = await quantService.validateCustomFactor({
        python_code: customCode,
      });
      setValidationResult(result);
    } catch (error) {
      console.error('Validation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTestFactor = async () => {
    setLoading(true);
    try {
      const result = await quantService.testCustomFactor({
        python_code: customCode,
        start_date: '2023-01-01',
        end_date: '2024-01-01',
      });
      setTestResult(result);
    } catch (error) {
      console.error('Test failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleQueryFactorData = async () => {
    if (!selectedFactor) return;
    setDataLoading(true);
    try {
      const result = await quantService.queryFactorData({
        factor_id: selectedFactor.factor_id,
        stock_code: stockCode,
        frequency: dataFrequency,
        lookback_days: lookbackDays,
      });
      setFactorData(result);
      setFactorDetailTab('data');
    } catch (error) {
      console.error('Failed to query factor data:', error);
    } finally {
      setDataLoading(false);
    }
  };

  const handleRunStrategy = async () => {
    if (!selectedStrategy) return;
    setStrategyRunning(true);
    try {
      const result = await quantService.runStrategy({
        strategy_id: selectedStrategy.strategy_id,
        parameters: {
          top_n: strategyTopN,
          min_score: strategyMinScore,
        },
      });
      
      // Validate result structure before setting state
      if (result && typeof result === 'object') {
        setStrategyResult(result);
      } else {
        console.warn('Invalid strategy result received:', result);
        setStrategyResult(null);
      }
    } catch (error) {
      console.error('Failed to run strategy:', error);
      setStrategyResult(null); // Reset on error to prevent showing stale data
    } finally {
      setStrategyRunning(false);
    }
  };

  const handleToggleFactor = (factorId: string) => {
    const newFactors = [...newStrategyFactors];
    const newWeights = { ...newStrategyFactorWeights };
    
    if (newFactors.includes(factorId)) {
      const index = newFactors.indexOf(factorId);
      newFactors.splice(index, 1);
      delete newWeights[factorId];
    } else {
      newFactors.push(factorId);
      newWeights[factorId] = 1 / (newFactors.length);
    }
    
    if (newStrategyWeightMethod === 'equal' && newFactors.length > 0) {
      const equalWeight = 1 / newFactors.length;
      newFactors.forEach(f => {
        newWeights[f] = equalWeight;
      });
    }
    
    setNewStrategyFactors(newFactors);
    setNewStrategyFactorWeights(newWeights);
  };

  const handleFactorWeightChange = (factorId: string, weight: number) => {
    setNewStrategyFactorWeights(prev => ({
      ...prev,
      [factorId]: weight,
    }));
  };

  const handleNormalizeWeights = () => {
    if (!newStrategyFactorWeights) {
      return;
    }
    const values = Object.values(newStrategyFactorWeights);
    const total = values.reduce((sum, w) => sum + w, 0);
    if (total > 0) {
      const normalized: Record<string, number> = {};
      Object.entries(newStrategyFactorWeights).forEach(([id, w]) => {
        normalized[id] = w / total;
      });
      setNewStrategyFactorWeights(normalized);
    }
  };

  const handleCreateStrategy = async () => {
    if (!newStrategyName || !newStrategyCode || newStrategyFactors.length === 0) {
      return;
    }
    
    setNewStrategyCreating(true);
    try {
      await quantService.createStrategy({
        name: newStrategyName || '',
        code: newStrategyCode || `strategy_${Date.now()}`,
        factors: newStrategyFactors || [],
        factor_weights: newStrategyFactorWeights || {},
        weight_method: newStrategyWeightMethod || 'equal',
        max_positions: newStrategyMaxPositions || 30,
        rebalance_freq: newStrategyRebalanceFreq || 'monthly',
        description: newStrategyDescription || '',
      });
      
      setShowNewStrategyDialog(false);
      resetNewStrategyForm();
      loadStrategies();
    } catch (error) {
      console.error('Failed to create strategy:', error);
    } finally {
      setNewStrategyCreating(false);
    }
  };

  const resetNewStrategyForm = () => {
    setNewStrategyName('');
    setNewStrategyCode('');
    setNewStrategyDescription('');
    setNewStrategyFactors([]);
    setNewStrategyFactorWeights({});
    setNewStrategyWeightMethod('equal');
    setNewStrategyMaxPositions(30);
    setNewStrategyRebalanceFreq('monthly');
  };

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
      axisLabel: { color: '#999', fontSize: 10, rotate: 45 },
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
      { type: 'inside', start: 0, end: 100 },
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
    series: factorData.chart_data.datasets.map((dataset: any) => ({
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

  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(2)}%`;
  };

  const formatNumber = (value: number, decimals: number = 2) => {
    return value.toFixed(decimals);
  };

  if (!mounted) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-950 via-zinc-900 to-zinc-950 text-white">
      <div className="container mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">量化分析</h1>
              <p className="text-xs text-zinc-500">因子管理 · 策略开发 · 回测评测 · 自定义因子</p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              loadFactors();
              loadStrategies();
            }}
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            刷新数据
          </Button>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid grid-cols-4 w-full max-w-2xl mx-auto bg-zinc-900/50 border border-zinc-800">
            <TabsTrigger value="factors" data-testid="factors-tab" className="data-[state=active]:bg-amber-500/20">
              <Database className="w-4 h-4 mr-2" />
              因子管理
            </TabsTrigger>
            <TabsTrigger value="strategy" data-testid="strategies-tab" className="data-[state=active]:bg-amber-500/20">
              <Settings className="w-4 h-4 mr-2" />
              策略开发
            </TabsTrigger>
            <TabsTrigger value="backtest" data-testid="backtest-tab" className="data-[state=active]:bg-amber-500/20">
              <LineChart className="w-4 h-4 mr-2" />
              回测评测
            </TabsTrigger>
            <TabsTrigger value="custom" data-testid="custom-factor-tab" className="data-[state=active]:bg-amber-500/20">
              <Code className="w-4 h-4 mr-2" />
              自定义因子
            </TabsTrigger>
          </TabsList>

          <TabsContent value="factors" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <Card className="bg-zinc-900/50 border-zinc-800 shadow-lg" data-testid="factor-list">
                  <CardHeader className="border-b border-zinc-800">
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2">
                        <Database className="w-5 h-5 text-amber-400" />
                        因子库
                      </CardTitle>
                      <Button 
                        size="sm" 
                        className="bg-amber-500 hover:bg-amber-600"
                        onClick={() => setShowFactorCreator(true)}
                      >
                        <Sparkles className="w-4 h-4 mr-2" />
                        新建因子
                      </Button>
                    </div>
                    <CardDescription>
                      共 {factors.length} 个因子可用
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {factors.map((factor) => (
                        <div
                          key={factor.factor_id}
                          data-testid="factor-item"
                          className={`p-4 rounded-lg border cursor-pointer transition-all ${
                            selectedFactor?.factor_id === factor.factor_id
                              ? 'border-amber-500 bg-amber-500/10'
                              : 'border-zinc-700 hover:border-zinc-600'
                          }`}
                          onClick={() => handleSelectFactor(factor)}
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div>
                              <h4 className="font-medium" data-testid="factor-name">{factor.name}</h4>
                              <p className="text-sm text-zinc-400">{factor.code}</p>
                            </div>
                            <Badge variant="secondary" size="sm">
                              {factorTypeLabels[factor.factor_type] || factor.factor_type}
                            </Badge>
                          </div>
                          <p className="text-sm text-zinc-500 line-clamp-2">
                            {factor.description}
                          </p>
                          <div className="flex items-center gap-2 mt-3">
                            <Badge variant="outline" size="sm" data-testid="factor-category">
                              {categoryLabels[factor.category] || factor.category}
                            </Badge>
                            {factor.tags?.slice(0, 2).map((tag) => (
                              <Badge key={tag} variant="outline" size="sm">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="space-y-6">
                <Card className="bg-zinc-900/50 border-zinc-800 shadow-lg" data-testid="factor-detail-panel">
                  <CardHeader className="border-b border-zinc-800">
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2 text-base">
                        <Info className="w-4 h-4 text-amber-400" />
                        因子详情
                      </CardTitle>
                      {selectedFactor && !selectedFactor.factor_id.startsWith('factor_builtin_') && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setShowDeleteConfirm(true)}
                          disabled={deletingFactor === selectedFactor.factor_id}
                          className="text-red-400 hover:text-red-300 hover:bg-red-900/20 h-7 text-xs"
                        >
                          {deletingFactor === selectedFactor.factor_id ? (
                            <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                          ) : (
                            <X className="w-3 h-3 mr-1" />
                          )}
                          删除
                        </Button>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="p-4">
                    {!selectedFactor ? (
                      <div className="text-center py-8 text-zinc-500">
                        <Info className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p>请从因子库中选择一个因子查看详情</p>
                      </div>
                    ) : (
                      <Tabs value={factorDetailTab} onValueChange={setFactorDetailTab} className="space-y-3">
                        <TabsList className="grid grid-cols-3 w-full bg-zinc-800/50 h-8">
                          <TabsTrigger value="info" data-testid="factor-info-tab" className="text-xs">
                            <Info className="w-3 h-3 mr-1" />
                            信息
                          </TabsTrigger>
                          <TabsTrigger value="code" data-testid="factor-code-tab" className="text-xs">
                            <FileCode className="w-3 h-3 mr-1" />
                            代码
                          </TabsTrigger>
                          <TabsTrigger value="params" data-testid="factor-data-tab" className="text-xs">
                            <Sliders className="w-3 h-3 mr-1" />
                            参数
                          </TabsTrigger>
                        </TabsList>

                        <TabsContent value="info" className="space-y-3">
                          <div>
                            <Label className="text-zinc-400 text-xs">因子名称</Label>
                            <p className="font-medium text-sm" data-testid="detail-factor-name">{selectedFactor.name}</p>
                          </div>
                          <div>
                            <Label className="text-zinc-400 text-xs">因子代码</Label>
                            <code className="block p-2 bg-zinc-800 rounded text-xs mt-1">
                              {selectedFactor.code}
                            </code>
                          </div>
                          <div>
                            <Label className="text-zinc-400 text-xs">描述</Label>
                            <p className="text-xs text-zinc-300 mt-1">
                              {selectedFactor.description}
                            </p>
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                            <Label className="text-zinc-400 text-xs">回看周期</Label>
                            <p className="text-sm" data-testid="detail-factor-lookback">{selectedFactor.lookback_period} 天</p>
                          </div>
                            <div>
                              <Label className="text-zinc-400 text-xs">版本</Label>
                              <p className="text-sm">v{selectedFactor.version}</p>
                            </div>
                          </div>
                          <div>
                            <Label className="text-zinc-400 text-xs">类别</Label>
                            <p className="text-sm" data-testid="detail-factor-category">{categoryLabels[selectedFactor.category] || selectedFactor.category}</p>
                          </div>
                          <div>
                            <Label className="text-zinc-400 text-xs">标签</Label>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {selectedFactor.tags?.map((tag) => (
                                <Badge key={tag} variant="outline" size="sm" className="text-xs">
                                  {tag}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        </TabsContent>

                        <TabsContent value="code" className="space-y-3">
                          {selectedFactorCode ? (
                            <div className="relative">
                              {selectedFactorCode.file_path && !selectedFactorCode.file_path.startsWith('factor://') && (
                                <div className="mb-2 text-xs text-zinc-500 flex items-center gap-1">
                                  <FileCode className="w-3 h-3" />
                                  <span className="font-mono truncate">{selectedFactorCode.file_path.split('/').slice(-3).join('/')}</span>
                                </div>
                              )}
                              <Button
                                variant="ghost"
                                size="sm"
                                className="absolute top-2 right-2 h-6 w-6 p-0 z-10"
                                onClick={copyCode}
                              >
                                {codeCopied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                              </Button>
                              <pre className="p-3 bg-zinc-800 rounded text-xs overflow-auto max-h-96 border border-zinc-700">
                                <code className="text-zinc-300">{selectedFactorCode.code}</code>
                              </pre>
                            </div>
                          ) : (
                            <div className="text-center py-6 text-zinc-500">
                              <FileCode className="w-10 h-10 mx-auto mb-2 opacity-50" />
                              <p className="text-sm">无法加载因子代码</p>
                            </div>
                          )}
                        </TabsContent>

                        <TabsContent value="params" className="space-y-3">
                          <div>
                            <Label className="text-zinc-400 text-xs">计算公式</Label>
                            <code className="block p-2 bg-zinc-800 rounded text-xs mt-1">
                              {selectedFactor.formula || '内置因子'}
                            </code>
                          </div>
                          <div>
                            <Label className="text-zinc-400 text-xs">默认参数</Label>
                            <pre className="p-2 bg-zinc-800 rounded text-xs mt-1 overflow-auto max-h-32">
                              {JSON.stringify(selectedFactor.default_params, null, 2)}
                            </pre>
                          </div>
                        </TabsContent>
                      </Tabs>
                    )}
                  </CardContent>
                </Card>

                <Card className="bg-zinc-900/50 border-zinc-800 shadow-lg">
                  <CardHeader className="border-b border-zinc-800">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Search className="w-4 h-4 text-amber-400" />
                      标的查询
                    </CardTitle>
                    <CardDescription className="text-xs">
                      查询指定股票的因子数据
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-4">
                    {!selectedFactor ? (
                      <div className="text-center py-6 text-zinc-500">
                        <TrendingUp className="w-10 h-10 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">请先选择一个因子</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-2">
                          <div className="space-y-1">
                            <Label className="text-zinc-400 text-xs">股票代码</Label>
                            <Input
                              value={stockCode}
                              onChange={(e) => setStockCode(e.target.value.toUpperCase())}
                              className="bg-zinc-800 border-zinc-700 h-8 text-xs"
                              placeholder="600000.SH"
                              data-testid="stock-code-input"
                            />
                          </div>
                          <div className="space-y-1">
                            <Label className="text-zinc-400 text-xs">数据频率</Label>
                            <Select value={dataFrequency} onValueChange={(v: any) => setDataFrequency(v)}>
                              <SelectTrigger className="bg-zinc-800 border-zinc-700 h-8 text-xs">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="daily">日线</SelectItem>
                                <SelectItem value="weekly">周线</SelectItem>
                                <SelectItem value="monthly">月线</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div className="space-y-1">
                            <Label className="text-zinc-400 text-xs">回看天数</Label>
                            <Input
                              type="number"
                              value={lookbackDays}
                              onChange={(e) => setLookbackDays(Number(e.target.value))}
                              className="bg-zinc-800 border-zinc-700 h-8 text-xs"
                              min={30}
                              max={720}
                            />
                          </div>
                          <div className="flex items-end">
                            <Button
                              onClick={handleQueryFactorData}
                              disabled={dataLoading}
                              className="w-full bg-amber-500 hover:bg-amber-600 h-8 text-xs"
                              size="sm"
                              data-testid="query-data-button"
                            >
                              {dataLoading ? (
                                <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                              ) : (
                                <Search className="w-3 h-3 mr-1" />
                              )}
                              查询
                            </Button>
                          </div>
                        </div>

                        {!factorData ? (
                          <div className="text-center py-4 text-zinc-500 border-t border-zinc-800 mt-3">
                            <p className="text-xs">输入股票代码后点击查询</p>
                          </div>
                        ) : (
                          <div className="space-y-3 border-t border-zinc-800 pt-3 mt-3">
                            <div className="grid grid-cols-3 gap-2">
                              <div className="bg-zinc-800/50 rounded p-2 text-center">
                                <div className="text-xs text-zinc-400">均值</div>
                                <div className="text-sm font-semibold text-white">
                                  {factorData.statistics?.mean?.toFixed(2) ?? '-'}
                                </div>
                              </div>
                              <div className="bg-zinc-800/50 rounded p-2 text-center">
                                <div className="text-xs text-zinc-400">标准差</div>
                                <div className="text-sm font-semibold text-white">
                                  {factorData.statistics?.std?.toFixed(2) ?? '-'}
                                </div>
                              </div>
                              <div className="bg-zinc-800/50 rounded p-2 text-center">
                                <div className="text-xs text-zinc-400">数据点</div>
                                <div className="text-sm font-semibold text-white">{factorData.data.length}</div>
                              </div>
                            </div>
                            
                            {factorData.chart_data && (
                              <div className="bg-zinc-800/30 rounded p-2" data-testid="factor-chart">
                                <ReactECharts option={factorDataChartOption} style={{ height: '120px' }} />
                              </div>
                            )}

                            <div className="bg-zinc-800/30 rounded overflow-hidden max-h-32 overflow-y-auto" data-testid="factor-data-table">
                              <table className="w-full text-xs">
                                <thead className="bg-zinc-900 sticky top-0">
                                  <tr>
                                    <th className="px-2 py-1 text-left text-zinc-400">日期</th>
                                    <th className="px-2 py-1 text-right text-zinc-400">因子值</th>
                                    <th className="px-2 py-1 text-right text-zinc-400">标准化</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {factorData.data.slice(-8).reverse().map((row, idx) => (
                                    <tr key={idx} data-testid="factor-data-row" className="border-t border-zinc-700">
                                      <td className="px-2 py-1 text-zinc-300" data-testid="trade-date">{row.trade_date}</td>
                                      <td className="px-2 py-1 text-right text-blue-400 font-mono" data-testid="factor-value">
                                        {row.value?.toFixed(2) ?? '-'}
                                      </td>
                                      <td className="px-2 py-1 text-right text-green-400 font-mono">
                                        {row.value_normalized?.toFixed(2) ?? '-'}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="strategy" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <Card className="bg-zinc-900/50 border-zinc-800 shadow-lg" data-testid="strategy-list">
                  <CardHeader className="border-b border-zinc-800">
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2">
                        <Settings className="w-5 h-5 text-amber-400" />
                        策略列表
                      </CardTitle>
                      <Button size="sm" className="bg-amber-500 hover:bg-amber-600" onClick={() => setShowStrategyCreator(true)}>
                        <Plus className="w-4 h-4 mr-2" />
                        新建策略
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="p-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {strategies.length > 0 ? (
                        strategies.map((strategy) => (
                          <div
                            key={strategy.strategy_id}
                            data-testid="strategy-item"
                            className={`p-4 rounded-lg border cursor-pointer transition-all ${
                              selectedStrategy?.strategy_id === strategy.strategy_id
                                ? 'border-amber-500 bg-amber-500/10'
                                : 'border-zinc-700 hover:border-zinc-600'
                            }`}
                            onClick={() => {
                              setSelectedStrategy(strategy);
                              setStrategyResult(null);
                              setStrategyMaxPositions(strategy.max_positions || 50);
                              setStrategyRebalanceFreq(strategy.rebalance_freq || 'monthly');
                            }}
                          >
                            <div className="flex items-start justify-between mb-2">
                              <div>
                                <h4 className="font-medium" data-testid="strategy-name">{strategy.name}</h4>
                                <p className="text-xs text-zinc-400">{strategy.code}</p>
                              </div>
                              <Badge variant="secondary" size="sm">
                                {strategy.strategy_type === 'single_factor' ? '单因子' : '多因子'}
                              </Badge>
                            </div>
                            <p className="text-sm text-zinc-500 line-clamp-2 mb-2">
                              {strategy.description}
                            </p>
                            <div className="flex items-center gap-3 text-xs text-zinc-500" data-testid="strategy-factors">
                              <span>因子: {strategy.factors.length}</span>
                              <span>持仓: {strategy.max_positions}</span>
                              <span>调仓: {strategy.rebalance_freq}</span>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="col-span-2 text-center py-8 text-zinc-500">
                          <Settings className="w-12 h-12 mx-auto mb-4 opacity-50" />
                          <p>暂无策略，点击上方按钮创建</p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>

                {strategyResult && strategyResult.statistics && (
                  <Card className="bg-zinc-900/50 border-zinc-800 shadow-lg mt-6" data-testid="strategy-results">
                    <CardHeader className="border-b border-zinc-800">
                      <CardTitle className="flex items-center gap-2 text-base">
                        <TrendingUp className="w-4 h-4 text-amber-400" />
                        选股结果 - {strategyResult.run_date}
                      </CardTitle>
                      <CardDescription className="text-xs">
                        策略: {strategyResult.strategy_name || 'N/A'} | 
                        分析股票: {strategyResult.statistics.total_stocks || 0}只
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="p-4">
                      <div className="grid grid-cols-4 gap-2 mb-4">
                        <div className="bg-zinc-800/50 rounded p-2 text-center">
                          <div className="text-xs text-zinc-400">平均得分</div>
                          <div className="text-sm font-semibold text-white">
                            {(strategyResult.statistics.avg_score || 0).toFixed(2)}
                          </div>
                        </div>
                        <div className="bg-zinc-800/50 rounded p-2 text-center">
                          <div className="text-xs text-zinc-400">最高分</div>
                          <div className="text-sm font-semibold text-green-400">
                            {(strategyResult.statistics.max_score || 0).toFixed(2)}
                          </div>
                        </div>
                        <div className="bg-zinc-800/50 rounded p-2 text-center">
                          <div className="text-xs text-zinc-400">最低分</div>
                          <div className="text-sm font-semibold text-red-400">
                            {(strategyResult.statistics.min_score || 0).toFixed(2)}
                          </div>
                        </div>
                        <div className="bg-zinc-800/50 rounded p-2 text-center">
                          <div className="text-xs text-zinc-400">选股数量</div>
                          <div className="text-sm font-semibold text-amber-400">
                            {strategyResult.top_picks?.length || 0}只
                          </div>
                        </div>
                      </div>

                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead className="bg-zinc-900">
                            <tr>
                              <th className="px-3 py-2 text-left text-zinc-400">排名</th>
                              <th className="px-3 py-2 text-left text-zinc-400">股票代码</th>
                              <th className="px-3 py-2 text-left text-zinc-400">股票名称</th>
                              <th className="px-3 py-2 text-right text-zinc-400">得分</th>
                              <th className="px-3 py-2 text-left text-zinc-400">因子详情</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-zinc-700">
                            {strategyResult.top_picks?.map((signal) => (
                              <tr key={signal.code} data-testid="stock-recommendation" className="hover:bg-zinc-700/50">
                                <td className="px-3 py-2 text-amber-400 font-medium" data-testid="stock-rank">#{signal.rank}</td>
                                <td className="px-3 py-2 text-white font-mono" data-testid="stock-code">{signal.code}</td>
                                <td className="px-3 py-2 text-zinc-300">{signal.name || '-'}</td>
                                <td className="px-3 py-2 text-right">
                                  <span data-testid="stock-score" className={`font-mono ${
                                    signal.score > 0.5 ? 'text-green-400' : 
                                    signal.score > 0 ? 'text-blue-400' : 
                                    signal.score > -0.5 ? 'text-zinc-400' : 'text-red-400'
                                  }`}>
                                    {signal.score.toFixed(2)}
                                  </span>
                                </td>
                                <td className="px-3 py-2 text-xs text-zinc-400">
                                  {signal.factor_scores && Object.entries(signal.factor_scores).map(([factorId, data]) => (
                                    <span key={factorId} className="mr-2">
                                      {factorId.split('_').pop()}: {data.value?.toFixed(1)}
                                    </span>
                                  ))}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>

              <div className="space-y-6">
                <Card className="bg-zinc-900/50 border-zinc-800 shadow-lg">
                  <CardHeader className="border-b border-zinc-800">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Cpu className="w-4 h-4 text-amber-400" />
                      策略配置
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4">
                    {selectedStrategy ? (
                      <div className="space-y-4">
                        <div>
                          <Label className="text-zinc-400 text-xs">策略名称</Label>
                          <Input
                            value={selectedStrategy.name}
                            className="bg-zinc-800 border-zinc-700 h-8 text-sm mt-1"
                            readOnly
                          />
                        </div>
                        <div>
                          <Label className="text-zinc-400 text-xs">因子权重</Label>
                          <div className="space-y-1 mt-1">
                            {selectedStrategy.factor_weights && Object.entries(selectedStrategy.factor_weights).length > 0 ? (
                              Object.entries(selectedStrategy.factor_weights).map(
                                ([factor, weight]) => (
                                  <div key={factor} className="flex items-center justify-between text-xs">
                                    <span className="text-zinc-300">{factor}</span>
                                    <span className="text-amber-400 font-mono">
                                      {(weight * 100).toFixed(1)}%
                                    </span>
                                  </div>
                                )
                              )
                            ) : (
                              <div className="text-xs text-zinc-500">暂无因子权重配置</div>
                            )}
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <Label className="text-zinc-400 text-xs">最大持仓</Label>
                            <Input
                              type="number"
                              value={strategyMaxPositions}
                              onChange={(e) => setStrategyMaxPositions(Number(e.target.value))}
                              className="bg-zinc-800 border-zinc-700 h-8 text-sm mt-1"
                              min={1}
                              max={100}
                            />
                          </div>
                          <div>
                            <Label className="text-zinc-400 text-xs">调仓频率</Label>
                            <Select value={strategyRebalanceFreq} onValueChange={setStrategyRebalanceFreq}>
                              <SelectTrigger className="bg-zinc-800 border-zinc-700 h-8 text-sm mt-1">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="daily">每日</SelectItem>
                                <SelectItem value="weekly">每周</SelectItem>
                                <SelectItem value="monthly">每月</SelectItem>
                                <SelectItem value="quarterly">每季度</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-6 text-zinc-500">
                        <Settings className="w-10 h-10 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">选择一个策略</p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card className="bg-zinc-900/50 border-zinc-800 shadow-lg">
                  <CardHeader className="border-b border-zinc-800">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Play className="w-4 h-4 text-amber-400" />
                      运行策略
                    </CardTitle>
                    <CardDescription className="text-xs">
                      运行策略获取选股建议
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-4">
                    {!selectedStrategy ? (
                      <div className="text-center py-4 text-zinc-500">
                        <p className="text-sm">请先选择一个策略</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-2">
                          <div className="space-y-1">
                            <Label className="text-zinc-400 text-xs">选股数量</Label>
                            <Input
                              type="number"
                              value={strategyTopN}
                              onChange={(e) => setStrategyTopN(Number(e.target.value))}
                              className="bg-zinc-800 border-zinc-700 h-8 text-sm"
                              min={5}
                              max={50}
                            />
                          </div>
                          <div className="space-y-1">
                            <Label className="text-zinc-400 text-xs">最低得分</Label>
                            <Input
                              type="number"
                              value={strategyMinScore ?? ''}
                              onChange={(e) => setStrategyMinScore(e.target.value ? Number(e.target.value) : undefined)}
                              className="bg-zinc-800 border-zinc-700 h-8 text-sm"
                              placeholder="可选"
                            />
                          </div>
                        </div>
                        <Button
                          className="w-full bg-amber-500 hover:bg-amber-600"
                          onClick={handleRunStrategy}
                          disabled={strategyRunning}
                          data-testid="run-strategy-button"
                        >
                          {strategyRunning ? (
                            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                          ) : (
                            <Play className="w-4 h-4 mr-2" />
                          )}
                          {strategyRunning ? '运行中...' : '运行策略'}
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="backtest" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <Card className="bg-zinc-900/50 border-zinc-800">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Settings className="w-5 h-5 text-amber-400" />
                      回测配置
                    </CardTitle>
                    <CardDescription>配置回测参数并运行策略回测</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label className="text-zinc-400">选择策略 *</Label>
                          <Select value={backtestStrategyId} onValueChange={setBacktestStrategyId}>
                            <SelectTrigger className="bg-zinc-800 border-zinc-700">
                              <SelectValue placeholder="选择要回测的策略" />
                            </SelectTrigger>
                            <SelectContent>
                              {strategies.map((strategy) => (
                                <SelectItem key={strategy.strategy_id} value={strategy.strategy_id}>
                                  {strategy.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-2">
                          <Label className="text-zinc-400">基准指数</Label>
                          <Select value={backtestBenchmark} onValueChange={setBacktestBenchmark}>
                            <SelectTrigger className="bg-zinc-800 border-zinc-700">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {backtestConfigs?.benchmarks.map((b) => (
                                <SelectItem key={b.code} value={b.code}>
                                  {b.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label className="text-zinc-400">时间范围</Label>
                        <div className="flex flex-wrap gap-2 mb-2">
                          {backtestConfigs?.date_presets.map((preset) => (
                            <Button
                              key={preset.label}
                              variant="outline"
                              size="sm"
                              onClick={() => handleDatePreset(preset.days)}
                              className="text-xs"
                            >
                              {preset.label}
                            </Button>
                          ))}
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-1">
                            <Label className="text-zinc-500 text-xs">开始日期</Label>
                            <Input
                              type="date"
                              value={backtestStartDate}
                              onChange={(e) => setBacktestStartDate(e.target.value)}
                              className="bg-zinc-800 border-zinc-700"
                            />
                          </div>
                          <div className="space-y-1">
                            <Label className="text-zinc-500 text-xs">结束日期</Label>
                            <Input
                              type="date"
                              value={backtestEndDate}
                              onChange={(e) => setBacktestEndDate(e.target.value)}
                              className="bg-zinc-800 border-zinc-700"
                            />
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-4">
                        <div className="space-y-2">
                          <Label className="text-zinc-400">初始资金</Label>
                          <Input
                            type="number"
                            value={backtestInitialCapital}
                            onChange={(e) => setBacktestInitialCapital(Number(e.target.value))}
                            className="bg-zinc-800 border-zinc-700"
                            step={100000}
                            min={10000}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-zinc-400">手续费率</Label>
                          <Input
                            type="number"
                            value={backtestCommissionRate}
                            onChange={(e) => setBacktestCommissionRate(Number(e.target.value))}
                            className="bg-zinc-800 border-zinc-700"
                            step={0.0001}
                            min={0}
                            max={0.01}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label className="text-zinc-400">滑点</Label>
                          <Input
                            type="number"
                            value={backtestSlippage}
                            onChange={(e) => setBacktestSlippage(Number(e.target.value))}
                            className="bg-zinc-800 border-zinc-700"
                            step={0.001}
                            min={0}
                            max={0.1}
                          />
                        </div>
                      </div>

                      {backtestProgress && backtestRunning && (
                        <div className="bg-zinc-800/50 rounded-lg p-4 border border-zinc-700">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm text-zinc-400">{backtestProgress.message}</span>
                            <span className="text-sm text-amber-400">{(backtestProgress.progress * 100).toFixed(0)}%</span>
                          </div>
                          <div className="w-full bg-zinc-700 rounded-full h-2">
                            <div
                              className="bg-amber-500 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${backtestProgress.progress * 100}%` }}
                            />
                          </div>
                        </div>
                      )}

                      <Button
                        className="w-full bg-amber-500 hover:bg-amber-600"
                        onClick={handleRunBacktest}
                        disabled={backtestRunning || !backtestStrategyId || !backtestStartDate || !backtestEndDate}
                      >
                        {backtestRunning ? (
                          <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                        ) : (
                          <Play className="w-4 h-4 mr-2" />
                        )}
                        {backtestRunning ? '回测运行中...' : '开始回测'}
                      </Button>
                    </div>
                  </CardContent>
                </Card>

                {backtestReport && backtestReport.status === 'completed' && backtestReport.report && (
                  <Card className="bg-zinc-900/50 border-zinc-800 mt-6">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <LineChart className="w-5 h-5 text-amber-400" />
                        回测结果 - {backtestReport.strategy_name}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {(() => {
                        const report = backtestReport.report as any;
                        const summary = report.executive_summary || {};
                        const metrics = report.performance_metrics || {};
                        const equityCurve = report.equity_curve;
                        
                        console.log('Backtest report:', report);
                        console.log('Equity curve:', equityCurve);
                        
                        return (
                          <div className="space-y-6">
                            <div className="flex items-center justify-between p-4 bg-zinc-800/50 rounded-lg border border-zinc-700">
                              <div>
                                <div className="text-sm text-zinc-400 mb-1">策略评级</div>
                                <div className={`text-3xl font-bold ${
                                  summary.grade?.startsWith('A') ? 'text-green-400' :
                                  summary.grade?.startsWith('B') ? 'text-blue-400' :
                                  summary.grade?.startsWith('C') ? 'text-yellow-400' :
                                  'text-red-400'
                                }`}>
                                  {summary.grade || 'N/A'}
                                </div>
                              </div>
                              <div className="text-right">
                                <div className="text-sm text-zinc-400 mb-1">综合得分</div>
                                <div className="text-2xl font-bold text-amber-400">
                                  {summary.total_score?.toFixed(1) || 'N/A'}
                                </div>
                              </div>
                            </div>

                            {equityCurve && equityCurve.dates && equityCurve.dates.length > 0 ? (
                              <div className="bg-zinc-800/50 rounded-lg p-4 border border-zinc-700">
                                <h4 className="font-medium text-sm text-zinc-400 mb-4">权益曲线</h4>
                                <div className="h-64 relative">
                                  <svg className="w-full h-full" viewBox="0 0 800 200" preserveAspectRatio="none">
                                    <defs>
                                      <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="rgba(245, 158, 11, 0.3)" />
                                        <stop offset="100%" stopColor="rgba(245, 158, 11, 0)" />
                                      </linearGradient>
                                    </defs>
                                    {(() => {
                                      const ec = equityCurve;
                                      const maxEquity = Math.max(...ec.equities);
                                      const minEquity = Math.min(...ec.equities);
                                      const range = maxEquity - minEquity || 1;
                                      const points = ec.equities.map((e: number, i: number) => {
                                        const x = (i / (ec.equities.length - 1)) * 800;
                                        const y = 200 - ((e - minEquity) / range) * 180;
                                        return `${x},${y}`;
                                      }).join(' ');
                                      const areaPoints = `0,200 ${points} 800,200`;
                                      return (
                                        <>
                                          <polygon
                                            points={areaPoints}
                                            fill="url(#equityGradient)"
                                          />
                                          <polyline
                                            points={points}
                                            fill="none"
                                            stroke="#f59e0b"
                                            strokeWidth="2"
                                          />
                                        </>
                                      );
                                    })()}
                                  </svg>
                                  <div className="absolute bottom-0 left-0 right-0 flex justify-between text-xs text-zinc-500 px-2">
                                    {equityCurve.dates.filter((_: any, i: number) => i % Math.ceil(equityCurve.dates.length / 6) === 0).map((d: string, i: number) => (
                                      <span key={i}>{d}</span>
                                    ))}
                                  </div>
                                </div>
                                <div className="flex justify-between mt-4 text-sm">
                                  <div>
                                    <span className="text-zinc-500">初始资金: </span>
                                    <span className="text-zinc-300">¥{equityCurve.initial_capital?.toLocaleString()}</span>
                                  </div>
                                  <div>
                                    <span className="text-zinc-500">最终权益: </span>
                                    <span className="text-zinc-300">¥{equityCurve.final_equity?.toLocaleString()}</span>
                                  </div>
                                  <div>
                                    <span className="text-zinc-500">总收益: </span>
                                    <span className={equityCurve.total_return >= 0 ? 'text-green-400' : 'text-red-400'}>
                                      {formatPercent(equityCurve.total_return)}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            ) : (
                              <div className="bg-zinc-800/50 rounded-lg p-4 border border-zinc-700">
                                <h4 className="font-medium text-sm text-zinc-400 mb-4">权益曲线</h4>
                                <div className="h-32 flex items-center justify-center text-zinc-500">
                                  <div className="text-center">
                                    <LineChart className="w-12 h-12 mx-auto opacity-50 mb-2" />
                                    <p className="text-sm">暂无权益曲线数据</p>
                                    <p className="text-xs mt-1">dates: {equityCurve?.dates?.length || 0}, equities: {equityCurve?.equities?.length || 0}</p>
                                  </div>
                                </div>
                              </div>
                            )}

                            {equityCurve && equityCurve.drawdowns && equityCurve.drawdowns.length > 0 && (
                              <div className="bg-zinc-800/50 rounded-lg p-4 border border-zinc-700">
                                <h4 className="font-medium text-sm text-zinc-400 mb-4">回撤曲线</h4>
                                <div className="h-32 relative">
                                  <svg className="w-full h-full" viewBox="0 0 800 100" preserveAspectRatio="none">
                                    {(() => {
                                      const dd = equityCurve.drawdowns;
                                      const maxDd = Math.min(...dd);
                                      const points = dd.map((d: number, i: number) => {
                                        const x = (i / (dd.length - 1)) * 800;
                                        const y = 100 - (d / maxDd) * 80;
                                        return `${x},${y}`;
                                      }).join(' ');
                                      return (
                                        <polyline
                                          points={points}
                                          fill="none"
                                          stroke="#ef4444"
                                          strokeWidth="1.5"
                                        />
                                      );
                                    })()}
                                  </svg>
                                </div>
                              </div>
                            )}

                            <div className="grid grid-cols-4 gap-4">
                              <MetricCard
                                label="总收益"
                                value={summary.total_return ? formatPercent(summary.total_return) : 'N/A'}
                                icon={<BarChart3 className="w-4 h-4" />}
                              />
                              <MetricCard
                                label="年化收益"
                                value={summary.annual_return ? formatPercent(summary.annual_return) : 'N/A'}
                                icon={<TrendingUp className="w-4 h-4" />}
                              />
                              <MetricCard
                                label="夏普比率"
                                value={summary.sharpe_ratio?.toFixed(2) || 'N/A'}
                                icon={<Activity className="w-4 h-4" />}
                              />
                              <MetricCard
                                label="最大回撤"
                                value={summary.max_drawdown ? formatPercent(summary.max_drawdown) : 'N/A'}
                                icon={<TrendingUp className="w-4 h-4 rotate-180" />}
                              />
                            </div>

                            {metrics.returns && (
                              <div className="space-y-3">
                                <h4 className="font-medium text-sm text-zinc-400">收益指标</h4>
                                <div className="grid grid-cols-3 gap-3">
                                  <MetricRow label="累计收益" value={metrics.returns.cumulative_return ? formatPercent(metrics.returns.cumulative_return) : 'N/A'} />
                                  <MetricRow label="超额收益" value={metrics.returns.excess_return ? formatPercent(metrics.returns.excess_return) : 'N/A'} />
                                  <MetricRow label="CAGR" value={metrics.returns.cagr ? formatPercent(metrics.returns.cagr) : 'N/A'} />
                                </div>
                              </div>
                            )}

                            {metrics.risk && (
                              <div className="space-y-3">
                                <h4 className="font-medium text-sm text-zinc-400">风险指标</h4>
                                <div className="grid grid-cols-3 gap-3">
                                  <MetricRow label="年化波动率" value={metrics.risk.volatility ? formatPercent(metrics.risk.volatility) : 'N/A'} />
                                  <MetricRow label="VaR(95%)" value={metrics.risk.var_95 ? formatPercent(metrics.risk.var_95) : 'N/A'} />
                                  <MetricRow label="CVaR(95%)" value={metrics.risk.cvar_95 ? formatPercent(metrics.risk.cvar_95) : 'N/A'} />
                                </div>
                              </div>
                            )}

                            {metrics.risk_adjusted && (
                              <div className="space-y-3">
                                <h4 className="font-medium text-sm text-zinc-400">风险调整收益</h4>
                                <div className="grid grid-cols-3 gap-3">
                                  <MetricRow label="Sortino比率" value={metrics.risk_adjusted.sortino_ratio?.toFixed(2) || 'N/A'} />
                                  <MetricRow label="Calmar比率" value={metrics.risk_adjusted.calmar_ratio?.toFixed(2) || 'N/A'} />
                                  <MetricRow label="Omega比率" value={metrics.risk_adjusted.omega_ratio?.toFixed(2) || 'N/A'} />
                                </div>
                              </div>
                            )}

                            {metrics.trading && (
                              <div className="space-y-3">
                                <h4 className="font-medium text-sm text-zinc-400">交易统计</h4>
                                <div className="grid grid-cols-3 gap-3">
                                  <MetricRow label="胜率" value={metrics.trading.win_rate ? formatPercent(metrics.trading.win_rate) : 'N/A'} />
                                  <MetricRow label="盈亏比" value={metrics.trading.profit_loss_ratio?.toFixed(2) || 'N/A'} />
                                  <MetricRow label="换手率" value={metrics.trading.turnover_rate ? formatPercent(metrics.trading.turnover_rate) : 'N/A'} />
                                </div>
                              </div>
                            )}

                            {report.recommendations && report.recommendations.length > 0 && (
                              <div className="space-y-3">
                                <h4 className="font-medium text-sm text-zinc-400">优化建议</h4>
                                <div className="space-y-2">
                                  {report.recommendations.map((rec: string, i: number) => (
                                    <div key={i} className="flex items-start gap-2 text-sm">
                                      <Info className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                                      <span className="text-zinc-300">{rec}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })()}
                    </CardContent>
                  </Card>
                )}
              </div>

              <div className="space-y-6">
                <Card className="bg-zinc-900/50 border-zinc-800">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BarChart3 className="w-5 h-5 text-amber-400" />
                      回测历史
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {backtestHistory && backtestHistory.backtests.length > 0 ? (
                      <div className="space-y-3">
                        {backtestHistory.backtests.map((bt: any) => (
                          <div
                            key={bt.backtest_id}
                            className="p-3 bg-zinc-800/50 rounded-lg border border-zinc-700"
                          >
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs text-zinc-500">{bt.backtest_id}</span>
                              <Badge
                                variant={bt.status === 'completed' ? 'default' : 'secondary'}
                                size="sm"
                              >
                                {bt.status === 'completed' ? '已完成' : bt.status}
                              </Badge>
                            </div>
                            {bt.summary && (
                              <div className="grid grid-cols-2 gap-2 text-xs">
                                <div>
                                  <span className="text-zinc-500">收益: </span>
                                  <span className={bt.summary.total_return >= 0 ? 'text-green-400' : 'text-red-400'}>
                                    {formatPercent(bt.summary.total_return)}
                                  </span>
                                </div>
                                <div>
                                  <span className="text-zinc-500">夏普: </span>
                                  <span className="text-zinc-300">{bt.summary.sharpe_ratio?.toFixed(2)}</span>
                                </div>
                              </div>
                            )}
                            <div className="text-xs text-zinc-500 mt-1">
                              {new Date(bt.created_at).toLocaleString()}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-zinc-500">
                        <BarChart3 className="w-12 h-12 mx-auto opacity-50 mb-4" />
                        <p>暂无回测历史</p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card className="bg-zinc-900/50 border-zinc-800">
                  <CardHeader>
                    <CardTitle className="text-sm">配置说明</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 text-xs text-zinc-400">
                      <p><strong>初始资金:</strong> 回测起始资金金额</p>
                      <p><strong>手续费率:</strong> 每笔交易的手续费比例</p>
                      <p><strong>滑点:</strong> 交易执行时的价格滑点</p>
                      <p><strong>基准指数:</strong> 用于计算超额收益的基准</p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="custom" className="space-y-6">
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Code className="w-5 h-5 text-amber-400" />
                  自定义因子开发
                </CardTitle>
                <CardDescription>
                  编写 Python 代码创建自定义因子
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div>
                      <Label className="text-zinc-400">Python 代码</Label>
                      <Textarea
                        value={customCode}
                        onChange={(e) => setCustomCode(e.target.value)}
                        className="mt-2 font-mono text-sm bg-zinc-800 border-zinc-700 min-h-[300px]"
                        placeholder="def factor(df, period=20): ..."
                        data-testid="code-editor"
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        onClick={handleValidateCode}
                        disabled={loading}
                        data-testid="validate-button"
                      >
                        验证代码
                      </Button>
                      <Button
                        className="bg-amber-500 hover:bg-amber-600"
                        onClick={handleTestFactor}
                        disabled={loading}
                        data-testid="test-factor-button"
                      >
                        测试因子
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-4">
                    {validationResult && (
                      <Card className="bg-zinc-800/50 border-zinc-700" data-testid="validation-result">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm">验证结果</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant={validationResult.is_valid ? 'default' : 'danger'}>
                              {validationResult.is_valid ? '有效' : '无效'}
                            </Badge>
                          </div>
                          {validationResult.errors.length > 0 && (
                            <ul className="text-sm text-red-400">
                              {validationResult.errors.map((error, i) => (
                                <li key={i}>• {error}</li>
                              ))}
                            </ul>
                          )}
                        </CardContent>
                      </Card>
                    )}

                    {testResult && (
                      <Card className="bg-zinc-800/50 border-zinc-700">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm">测试结果</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <span className="text-zinc-400">测试股票数:</span>
                              <span className="ml-2">{testResult.stocks_tested ?? '-'}</span>
                            </div>
                            <div>
                              <span className="text-zinc-400">成功率:</span>
                              <span className="ml-2">{testResult.success_rate != null ? formatPercent(testResult.success_rate) : '-'}</span>
                            </div>
                            <div>
                              <span className="text-zinc-400">IC均值:</span>
                              <span className="ml-2" data-testid="ic-mean">{testResult.ic_mean != null ? testResult.ic_mean.toFixed(4) : '-'}</span>
                            </div>
                            <div>
                              <span className="text-zinc-400">ICIR:</span>
                              <span className="ml-2" data-testid="ic-ir">{testResult.ic_ir != null ? testResult.ic_ir.toFixed(4) : '-'}</span>
                            </div>
                            <div>
                              <span className="text-zinc-400">平均执行时间:</span>
                              <span className="ml-2">{testResult.avg_execution_time != null ? `${testResult.avg_execution_time.toFixed(2)}ms` : '-'}</span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {showNewStrategyDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-zinc-700">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold">新建策略</h2>
                <Button variant="ghost" size="sm" onClick={() => setShowNewStrategyDialog(false)}>
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>

            <div className="p-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>策略名称 *</Label>
                  <Input
                    value={newStrategyName}
                    onChange={(e) => setNewStrategyName(e.target.value)}
                    className="bg-zinc-800 border-zinc-700"
                    placeholder="输入策略名称"
                  />
                </div>
                <div className="space-y-2">
                  <Label>策略代码 *</Label>
                  <Input
                    value={newStrategyCode}
                    onChange={(e) => setNewStrategyCode(e.target.value)}
                    className="bg-zinc-800 border-zinc-700"
                    placeholder="strategy_custom_001"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>策略描述</Label>
                <Textarea
                  value={newStrategyDescription}
                  onChange={(e) => setNewStrategyDescription(e.target.value)}
                  className="bg-zinc-800 border-zinc-700"
                  placeholder="描述策略的投资逻辑和特点"
                  rows={3}
                />
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label className="text-base font-medium">选择因子</Label>
                  <span className="text-sm text-zinc-400">已选择 {newStrategyFactors.length} 个因子</span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2 max-h-48 overflow-y-auto p-2 bg-zinc-800/50 rounded border border-zinc-700">
                  {factors.map((factor) => (
                    <button
                      key={factor.factor_id}
                      onClick={() => handleToggleFactor(factor.factor_id)}
                      className={`p-3 rounded-lg border text-left transition-all ${
                        newStrategyFactors.includes(factor.factor_id)
                          ? 'border-amber-500 bg-amber-500/10 text-amber-400'
                          : 'border-zinc-700 hover:border-zinc-600 text-zinc-400'
                      }`}
                    >
                      <div className="text-xs font-medium mb-1">{factor.name}</div>
                      <div className="text-xs text-zinc-500">{factor.code}</div>
                    </button>
                  ))}
                </div>
              </div>

              {newStrategyFactors.length > 0 && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <Label className="text-base font-medium">因子权重</Label>
                    <div className="flex items-center gap-2">
                      <Select value={newStrategyWeightMethod} onValueChange={(v: any) => {
                        setNewStrategyWeightMethod(v);
                        if (v === 'equal') {
                          const equalWeight = 1 / newStrategyFactors.length;
                          const weights: Record<string, number> = {};
                          newStrategyFactors.forEach(f => {
                            weights[f] = equalWeight;
                          });
                          setNewStrategyFactorWeights(weights);
                        }
                      }}>
                        <SelectTrigger className="w-40 bg-zinc-800 border-zinc-700">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="equal">等权</SelectItem>
                          <SelectItem value="custom">自定义</SelectItem>
                        </SelectContent>
                      </Select>
                      {newStrategyWeightMethod === 'custom' && (
                        <Button variant="outline" size="sm" onClick={handleNormalizeWeights}>
                          <RefreshCw className="w-3 h-3 mr-1" />
                          归一化
                        </Button>
                      )}
                    </div>
                  </div>
                  <div className="space-y-2">
                    {newStrategyFactors.map((factorId) => {
                      const factor = factors.find(f => f.factor_id === factorId);
                      return (
                        <div key={factorId} className="flex items-center gap-3 p-3 bg-zinc-800/50 rounded border border-zinc-700">
                          <div className="flex-1">
                            <div className="text-sm font-medium">{factor?.name || factorId}</div>
                            <div className="text-xs text-zinc-500">{factor?.code}</div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-zinc-400 w-12">
                              {newStrategyWeightMethod === 'equal' ? '等权' : '权重:'}
                            </span>
                            {newStrategyWeightMethod === 'custom' && (
                              <Input
                                type="number"
                                step="0.01"
                                min="0"
                                max="1"
                                value={newStrategyFactorWeights[factorId] || 0}
                                onChange={(e) => handleFactorWeightChange(factorId, Number(e.target.value))}
                                className="w-24 bg-zinc-700 border-zinc-600 h-8 text-sm"
                              />
                            )}
                            <span className="text-xs text-zinc-400 w-16 text-right">
                              {((newStrategyFactorWeights[factorId] || 0) * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>权重方法</Label>
                  <Select value={newStrategyWeightMethod} onValueChange={(v: any) => setNewStrategyWeightMethod(v)}>
                    <SelectTrigger className="bg-zinc-800 border-zinc-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="equal">等权</SelectItem>
                      <SelectItem value="market_cap">市值加权</SelectItem>
                      <SelectItem value="risk_parity">风险平价</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>最大持仓数</Label>
                  <Input
                    type="number"
                    value={newStrategyMaxPositions}
                    onChange={(e) => setNewStrategyMaxPositions(Number(e.target.value))}
                    className="bg-zinc-800 border-zinc-700"
                    min={1}
                    max={100}
                  />
                </div>
                <div className="space-y-2">
                  <Label>调仓频率</Label>
                  <Select value={newStrategyRebalanceFreq} onValueChange={(v: any) => setNewStrategyRebalanceFreq(v)}>
                    <SelectTrigger className="bg-zinc-800 border-zinc-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="daily">每日</SelectItem>
                      <SelectItem value="weekly">每周</SelectItem>
                      <SelectItem value="monthly">每月</SelectItem>
                      <SelectItem value="quarterly">每季度</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-zinc-700">
                <Button variant="outline" onClick={() => setShowNewStrategyDialog(false)}>
                  取消
                </Button>
                <Button
                  className="bg-amber-500 hover:bg-amber-600"
                  onClick={handleCreateStrategy}
                  disabled={newStrategyCreating || !newStrategyName || !newStrategyCode || newStrategyFactors.length === 0}
                >
                  {newStrategyCreating ? (
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Plus className="w-4 h-4 mr-2" />
                  )}
                  创建策略
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showDeleteConfirm && selectedFactor && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="bg-zinc-900 border-zinc-700 max-w-md w-full">
            <CardHeader>
              <CardTitle className="text-lg text-white">确认删除因子</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-zinc-300">
                确定要删除因子 <span className="text-amber-400 font-medium">{selectedFactor.name}</span> 吗？
              </p>
              <p className="text-zinc-400 text-sm">
                此操作无法撤销，删除后因子将从系统中移除。
              </p>
              <div className="flex justify-end gap-3 pt-2">
                <Button
                  variant="outline"
                  onClick={() => setShowDeleteConfirm(false)}
                  className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                >
                  取消
                </Button>
                <Button
                  onClick={handleDeleteFactor}
                  disabled={deletingFactor === selectedFactor.factor_id}
                  className="bg-red-600 hover:bg-red-500 text-white"
                >
                  {deletingFactor === selectedFactor.factor_id ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      删除中...
                    </>
                  ) : (
                    '确认删除'
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {showFactorCreator && (
        <FactorCreator
          onFactorCreated={(factorId) => {
            setShowFactorCreator(false);
            loadFactors();
          }}
          onCancel={() => setShowFactorCreator(false)}
        />
      )}

      {showStrategyCreator && (
        <StrategyCreator
          onStrategyCreated={(strategyId) => {
            setShowStrategyCreator(false);
            loadStrategies();
          }}
          onCancel={() => setShowStrategyCreator(false)}
        />
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon?: React.ReactNode;
}) {
  return (
    <div className="p-4 bg-zinc-800/50 rounded-lg border border-zinc-700">
      <div className="flex items-center gap-2 text-zinc-400 text-sm mb-1">
        {icon}
        {label}
      </div>
      <div className="text-xl font-bold">{value}</div>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-zinc-800">
      <span className="text-zinc-400">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
