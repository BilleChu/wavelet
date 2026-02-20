'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Calculator,
  ChevronRight,
  Dices,
  Minus,
  Plus,
  RefreshCw,
  Save,
  Settings,
  Sliders,
  Trash2,
  TrendingUp,
  Zap,
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
import { quantService } from '@/services/quantService';
import { 
  factorTypeLabels, 
  categoryLabels, 
  weightMethodLabels, 
  rebalanceFreqLabels 
} from '@/constants/quant';

interface FactorInfo {
  factor_id: string;
  name: string;
  description: string;
  factor_type: string;
  category: string;
  tags: string[];
  lookback_period: number;
  min_value: number | null;
  max_value: number | null;
}

interface SelectedFactor {
  factor_id: string;
  name: string;
  weight: number;
  enabled: boolean;
}

interface StrategyConfig {
  name: string;
  description: string;
  factors: SelectedFactor[];
  weight_method: string;
  max_positions: number;
  rebalance_freq: string;
  stop_loss: number | null;
  take_profit: number | null;
}

export default function StrategyBuilderPage() {
  const [mounted, setMounted] = useState(false);
  const [availableFactors, setAvailableFactors] = useState<FactorInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('select');

  const [strategyConfig, setStrategyConfig] = useState<StrategyConfig>({
    name: '',
    description: '',
    factors: [],
    weight_method: 'equal',
    max_positions: 50,
    rebalance_freq: 'monthly',
    stop_loss: null,
    take_profit: null,
  });

  const [filterType, setFilterType] = useState<string>('all');
  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    setMounted(true);
  }, []);

  const loadFactors = useCallback(async () => {
    setLoading(true);
    try {
      const data = await quantService.getFactorRegistry();
      setAvailableFactors((data.factors || []).map(f => ({
        factor_id: f.factor_id,
        name: f.name,
        description: f.description || '',
        factor_type: f.factor_type,
        category: f.category,
        tags: f.tags || [],
        lookback_period: f.lookback_period || 20,
        min_value: null,
        max_value: null,
      })));
    } catch (error) {
      console.error('Failed to load factors:', error);
      setAvailableFactors([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (mounted) {
      loadFactors();
    }
  }, [mounted, loadFactors]);

  const filteredFactors = availableFactors.filter((factor) => {
    if (filterType !== 'all' && factor.factor_type !== filterType) return false;
    if (filterCategory !== 'all' && factor.category !== filterCategory) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        factor.name.toLowerCase().includes(query) ||
        factor.description.toLowerCase().includes(query) ||
        factor.factor_id.toLowerCase().includes(query)
      );
    }
    return true;
  });

  const addFactor = (factor: FactorInfo) => {
    if (strategyConfig.factors.some((f) => f.factor_id === factor.factor_id)) {
      return;
    }
    setStrategyConfig((prev) => ({
      ...prev,
      factors: [
        ...prev.factors,
        {
          factor_id: factor.factor_id,
          name: factor.name,
          weight: 1.0 / (prev.factors.length + 1),
          enabled: true,
        },
      ],
    }));
  };

  const removeFactor = (factorId: string) => {
    setStrategyConfig((prev) => ({
      ...prev,
      factors: prev.factors.filter((f) => f.factor_id !== factorId),
    }));
  };

  const updateFactorWeight = (factorId: string, weight: number) => {
    setStrategyConfig((prev) => ({
      ...prev,
      factors: prev.factors.map((f) =>
        f.factor_id === factorId ? { ...f, weight } : f
      ),
    }));
  };

  const toggleFactorEnabled = (factorId: string) => {
    setStrategyConfig((prev) => ({
      ...prev,
      factors: prev.factors.map((f) =>
        f.factor_id === factorId ? { ...f, enabled: !f.enabled } : f
      ),
    }));
  };

  const normalizeWeights = () => {
    const enabledFactors = strategyConfig.factors.filter((f) => f.enabled);
    if (enabledFactors.length === 0) return;

    const equalWeight = 1.0 / enabledFactors.length;
    setStrategyConfig((prev) => ({
      ...prev,
      factors: prev.factors.map((f) =>
        f.enabled ? { ...f, weight: equalWeight } : f
      ),
    }));
  };

  const autoBalanceWeights = () => {
    const enabledFactors = strategyConfig.factors.filter((f) => f.enabled);
    if (enabledFactors.length === 0) return;

    const totalWeight = enabledFactors.reduce((sum, f) => sum + f.weight, 0);
    if (totalWeight === 0) {
      normalizeWeights();
      return;
    }

    setStrategyConfig((prev) => ({
      ...prev,
      factors: prev.factors.map((f) =>
        f.enabled ? { ...f, weight: f.weight / totalWeight } : f
      ),
    }));
  };

  const totalWeight = strategyConfig.factors
    .filter((f) => f.enabled)
    .reduce((sum, f) => sum + f.weight, 0);

  const saveStrategy = async () => {
    setLoading(true);
    try {
      // Validate that strategyConfig and its factors exist
      if (!strategyConfig || !strategyConfig.factors || !Array.isArray(strategyConfig.factors)) {
        throw new Error('Invalid strategy configuration');
      }
      
      const enabledFactors = strategyConfig.factors.filter((f) => f.enabled);
      
      await quantService.createStrategy({
        name: strategyConfig.name || '',
        code: `strategy_${Date.now()}`,
        description: strategyConfig.description || '',
        factors: enabledFactors.map((f) => f.factor_id),
        factor_weights: Object.fromEntries(
          enabledFactors.map((f) => [f.factor_id, f.weight])
        ),
        weight_method: strategyConfig.weight_method || 'equal',
        max_positions: strategyConfig.max_positions || 50,
        rebalance_freq: strategyConfig.rebalance_freq || 'monthly',
      });
      alert('策略保存成功！');
    } catch (error) {
      console.error('Failed to save strategy:', error);
      alert('策略保存失败，请重试');
    } finally {
      setLoading(false);
    }
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
              <Settings className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">多因子策略构建器</h1>
              <p className="text-xs text-zinc-500">选择因子 · 配置权重 · 构建策略</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={loadFactors}
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              刷新因子
            </Button>
            <Button
              size="sm"
              className="bg-amber-500 hover:bg-amber-600"
              onClick={saveStrategy}
              disabled={loading || strategyConfig.factors.length === 0 || !strategyConfig.name}
            >
              <Save className="w-4 h-4 mr-2" />
              保存策略
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid grid-cols-3 w-full bg-zinc-900/50 border border-zinc-800 mb-4">
                <TabsTrigger value="select" className="data-[state=active]:bg-amber-500/20">
                  <Plus className="w-4 h-4 mr-2" />
                  选择因子
                </TabsTrigger>
                <TabsTrigger value="weights" className="data-[state=active]:bg-amber-500/20">
                  <Sliders className="w-4 h-4 mr-2" />
                  配置权重
                </TabsTrigger>
                <TabsTrigger value="params" className="data-[state=active]:bg-amber-500/20">
                  <Settings className="w-4 h-4 mr-2" />
                  策略参数
                </TabsTrigger>
              </TabsList>

              <TabsContent value="select" className="space-y-4">
                <Card className="bg-zinc-900/50 border-zinc-800">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-amber-400" />
                      因子库
                    </CardTitle>
                    <CardDescription>
                      从因子库中选择要使用的因子
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-4 mb-4">
                      <Input
                        placeholder="搜索因子..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="bg-zinc-800 border-zinc-700"
                      />
                      <Select value={filterType} onValueChange={setFilterType}>
                        <SelectTrigger className="w-32 bg-zinc-800 border-zinc-700">
                          <SelectValue placeholder="类型" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">全部类型</SelectItem>
                          <SelectItem value="technical">技术指标</SelectItem>
                          <SelectItem value="fundamental">基本面</SelectItem>
                          <SelectItem value="alternative">另类数据</SelectItem>
                        </SelectContent>
                      </Select>
                      <Select value={filterCategory} onValueChange={setFilterCategory}>
                        <SelectTrigger className="w-32 bg-zinc-800 border-zinc-700">
                          <SelectValue placeholder="类别" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">全部类别</SelectItem>
                          <SelectItem value="momentum">动量</SelectItem>
                          <SelectItem value="volatility">波动率</SelectItem>
                          <SelectItem value="value">价值</SelectItem>
                          <SelectItem value="quality">质量</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {filteredFactors.map((factor) => {
                        const isSelected = strategyConfig.factors.some(
                          (f) => f.factor_id === factor.factor_id
                        );
                        return (
                          <div
                            key={factor.factor_id}
                            className={`p-4 rounded-lg border cursor-pointer transition-all ${
                              isSelected
                                ? 'border-amber-500 bg-amber-500/10'
                                : 'border-zinc-700 hover:border-zinc-600'
                            }`}
                            onClick={() => (isSelected ? removeFactor(factor.factor_id) : addFactor(factor))}
                          >
                            <div className="flex items-start justify-between mb-2">
                              <div>
                                <h4 className="font-medium text-sm">{factor.name}</h4>
                                <p className="text-xs text-zinc-500">{factor.factor_id}</p>
                              </div>
                              <div className="flex items-center gap-2">
                                {isSelected && (
                                  <Badge variant="default" size="sm">
                                    已选择
                                  </Badge>
                                )}
                                <Badge variant="secondary" size="sm">
                                  {factorTypeLabels[factor.factor_type] || factor.factor_type}
                                </Badge>
                              </div>
                            </div>
                            <p className="text-xs text-zinc-400 line-clamp-2 mb-2">
                              {factor.description}
                            </p>
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" size="sm">
                                {categoryLabels[factor.category] || factor.category}
                              </Badge>
                              <span className="text-xs text-zinc-500">
                                回看: {factor.lookback_period}天
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="weights" className="space-y-4">
                <Card className="bg-zinc-900/50 border-zinc-800">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2">
                        <Sliders className="w-5 h-5 text-amber-400" />
                        因子权重配置
                      </CardTitle>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={normalizeWeights}
                        >
                          <Dices className="w-4 h-4 mr-2" />
                          等权分配
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={autoBalanceWeights}
                        >
                          <Zap className="w-4 h-4 mr-2" />
                          自动平衡
                        </Button>
                      </div>
                    </div>
                    <CardDescription>
                      配置每个因子的权重，总权重应接近 100%
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {strategyConfig.factors.length > 0 ? (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg">
                          <span className="text-zinc-400">总权重</span>
                          <span
                            className={`font-bold ${
                              Math.abs(totalWeight - 1.0) < 0.01
                                ? 'text-green-400'
                                : 'text-amber-400'
                            }`}
                          >
                            {(totalWeight * 100).toFixed(1)}%
                          </span>
                        </div>

                        {strategyConfig.factors.map((factor) => (
                          <div
                            key={factor.factor_id}
                            className={`p-4 rounded-lg border transition-all ${
                              factor.enabled
                                ? 'border-zinc-700 bg-zinc-800/30'
                                : 'border-zinc-800 bg-zinc-900/30 opacity-50'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-3">
                              <div className="flex items-center gap-3">
                                <input
                                  type="checkbox"
                                  checked={factor.enabled}
                                  onChange={() => toggleFactorEnabled(factor.factor_id)}
                                  className="w-4 h-4 rounded border-zinc-600 bg-zinc-800 text-amber-500 focus:ring-amber-500"
                                />
                                <div>
                                  <h4 className="font-medium text-sm">{factor.name}</h4>
                                  <p className="text-xs text-zinc-500">{factor.factor_id}</p>
                                </div>
                              </div>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => removeFactor(factor.factor_id)}
                                className="text-red-400 hover:text-red-300"
                              >
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>

                            <div className="flex items-center gap-4">
                              <input
                                type="range"
                                min="0"
                                max="100"
                                value={factor.weight * 100}
                                onChange={(e) =>
                                  updateFactorWeight(factor.factor_id, parseInt(e.target.value) / 100)
                                }
                                className="flex-1 h-2 bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-amber-500"
                                disabled={!factor.enabled}
                              />
                              <div className="flex items-center gap-2">
                                <Input
                                  type="number"
                                  min="0"
                                  max="100"
                                  value={(factor.weight * 100).toFixed(1)}
                                  onChange={(e) =>
                                    updateFactorWeight(factor.factor_id, parseFloat(e.target.value) / 100)
                                  }
                                  className="w-20 bg-zinc-800 border-zinc-700 text-center"
                                  disabled={!factor.enabled}
                                />
                                <span className="text-zinc-400">%</span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-zinc-500">
                        <Sliders className="w-12 h-12 mx-auto opacity-50 mb-4" />
                        <p>请先在&ldquo;选择因子&rdquo;页面添加因子</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="params" className="space-y-4">
                <Card className="bg-zinc-900/50 border-zinc-800">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Settings className="w-5 h-5 text-amber-400" />
                      策略参数配置
                    </CardTitle>
                    <CardDescription>
                      配置策略的基本参数和风控设置
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-6">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <Label className="text-zinc-400">策略名称 *</Label>
                          <Input
                            value={strategyConfig.name}
                            onChange={(e) =>
                              setStrategyConfig((prev) => ({ ...prev, name: e.target.value }))
                            }
                            placeholder="输入策略名称"
                            className="bg-zinc-800 border-zinc-700 mt-1"
                          />
                        </div>
                        <div>
                          <Label className="text-zinc-400">权重方法</Label>
                          <Select
                            value={strategyConfig.weight_method}
                            onValueChange={(v) =>
                              setStrategyConfig((prev) => ({ ...prev, weight_method: v }))
                            }
                          >
                            <SelectTrigger className="bg-zinc-800 border-zinc-700 mt-1">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {Object.entries(weightMethodLabels).map(([value, label]) => (
                                <SelectItem key={value} value={value}>
                                  {label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div>
                        <Label className="text-zinc-400">策略描述</Label>
                        <Input
                          value={strategyConfig.description}
                          onChange={(e) =>
                            setStrategyConfig((prev) => ({ ...prev, description: e.target.value }))
                          }
                          placeholder="输入策略描述"
                          className="bg-zinc-800 border-zinc-700 mt-1"
                        />
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                          <Label className="text-zinc-400">最大持仓数</Label>
                          <Input
                            type="number"
                            value={strategyConfig.max_positions}
                            onChange={(e) =>
                              setStrategyConfig((prev) => ({
                                ...prev,
                                max_positions: parseInt(e.target.value) || 50,
                              }))
                            }
                            className="bg-zinc-800 border-zinc-700 mt-1"
                          />
                        </div>
                        <div>
                          <Label className="text-zinc-400">调仓频率</Label>
                          <Select
                            value={strategyConfig.rebalance_freq}
                            onValueChange={(v) =>
                              setStrategyConfig((prev) => ({ ...prev, rebalance_freq: v }))
                            }
                          >
                            <SelectTrigger className="bg-zinc-800 border-zinc-700 mt-1">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {Object.entries(rebalanceFreqLabels).map(([value, label]) => (
                                <SelectItem key={value} value={value}>
                                  {label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label className="text-zinc-400">单只持仓比例</Label>
                          <Input
                            type="number"
                            step="0.01"
                            placeholder="0.02"
                            className="bg-zinc-800 border-zinc-700 mt-1"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <Label className="text-zinc-400">止损比例 (%)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={strategyConfig.stop_loss || ''}
                            onChange={(e) =>
                              setStrategyConfig((prev) => ({
                                ...prev,
                                stop_loss: e.target.value ? parseFloat(e.target.value) : null,
                              }))
                            }
                            placeholder="例如: 15"
                            className="bg-zinc-800 border-zinc-700 mt-1"
                          />
                        </div>
                        <div>
                          <Label className="text-zinc-400">止盈比例 (%)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={strategyConfig.take_profit || ''}
                            onChange={(e) =>
                              setStrategyConfig((prev) => ({
                                ...prev,
                                take_profit: e.target.value ? parseFloat(e.target.value) : null,
                              }))
                            }
                            placeholder="例如: 30"
                            className="bg-zinc-800 border-zinc-700 mt-1"
                          />
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>

          <div>
            <Card className="bg-zinc-900/50 border-zinc-800 sticky top-6">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calculator className="w-5 h-5 text-amber-400" />
                  策略预览
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <Label className="text-zinc-400">策略名称</Label>
                    <p className="font-medium mt-1">
                      {strategyConfig.name || '(未命名)'}
                    </p>
                  </div>

                  <div>
                    <Label className="text-zinc-400">策略类型</Label>
                    <p className="mt-1">
                      <Badge variant="secondary">
                        {strategyConfig.factors.length > 1 ? '多因子策略' : '单因子策略'}
                      </Badge>
                    </p>
                  </div>

                  <div>
                    <Label className="text-zinc-400">
                      已选因子 ({strategyConfig.factors.filter((f) => f.enabled).length})
                    </Label>
                    <div className="mt-2 space-y-2">
                      {strategyConfig.factors.filter((f) => f.enabled).length > 0 ? (
                        strategyConfig.factors
                          .filter((f) => f.enabled)
                          .map((factor) => (
                            <div
                              key={factor.factor_id}
                              className="flex items-center justify-between p-2 bg-zinc-800/50 rounded"
                            >
                              <span className="text-sm truncate">{factor.name}</span>
                              <span className="text-amber-400 text-sm">
                                {(factor.weight * 100).toFixed(1)}%
                              </span>
                            </div>
                          ))
                      ) : (
                        <p className="text-sm text-zinc-500">暂无选择因子</p>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-zinc-400">权重方法</Label>
                      <p className="text-sm mt-1">
                        {weightMethodLabels[strategyConfig.weight_method]}
                      </p>
                    </div>
                    <div>
                      <Label className="text-zinc-400">调仓频率</Label>
                      <p className="text-sm mt-1">
                        {rebalanceFreqLabels[strategyConfig.rebalance_freq]}
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-zinc-400">最大持仓</Label>
                      <p className="text-sm mt-1">{strategyConfig.max_positions} 只</p>
                    </div>
                    <div>
                      <Label className="text-zinc-400">止损</Label>
                      <p className="text-sm mt-1">
                        {strategyConfig.stop_loss ? `${strategyConfig.stop_loss}%` : '未设置'}
                      </p>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-zinc-700">
                    <Button
                      className="w-full bg-amber-500 hover:bg-amber-600"
                      onClick={saveStrategy}
                      disabled={
                        loading ||
                        strategyConfig.factors.filter((f) => f.enabled).length === 0 ||
                        !strategyConfig.name
                      }
                    >
                      <Save className="w-4 h-4 mr-2" />
                      保存策略
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
