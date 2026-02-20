'use client';

import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Code,
  Play,
  Save,
  AlertCircle,
  CheckCircle,
  Loader2,
  ChevronRight,
  Settings,
  Layers,
  Tag,
  Info,
  Copy,
  Check,
  X,
  RefreshCw,
  Plus,
} from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

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
import { Textarea } from '@/components/ui/textarea';

import { 
  strategyCreatorService, 
  StrategyGenerateResponse, 
  StrategySuggestion,
  StreamEvent 
} from '@/services/strategyCreatorService';

interface StrategyCreatorProps {
  onStrategyCreated?: (strategyId: string) => void;
  onCancel?: () => void;
}

type Step = 'describe' | 'generate' | 'review' | 'save';

const STRATEGY_TYPES = [
  { value: 'single_factor', label: '单因子策略', description: '使用单个因子生成信号' },
  { value: 'multi_factor', label: '多因子策略', description: '组合多个因子信号' },
  { value: 'rule_based', label: '规则策略', description: '基于交易规则' },
];

const WEIGHT_METHODS = [
  { value: 'equal_weight', label: '等权重' },
  { value: 'risk_parity', label: '风险平价' },
  { value: 'mean_variance', label: '均值方差' },
];

const REBALANCE_FREQS = [
  { value: 'daily', label: '每日' },
  { value: 'weekly', label: '每周' },
  { value: 'monthly', label: '每月' },
  { value: 'quarterly', label: '每季度' },
];

export default function StrategyCreator({ onStrategyCreated, onCancel }: StrategyCreatorProps) {
  const [currentStep, setCurrentStep] = useState<Step>('describe');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const [description, setDescription] = useState('');
  const [strategyName, setStrategyName] = useState('');
  const [strategyType, setStrategyType] = useState('multi_factor');
  const [weightMethod, setWeightMethod] = useState('equal_weight');
  const [rebalanceFreq, setRebalanceFreq] = useState('monthly');
  const [maxPositions, setMaxPositions] = useState(50);

  const [availableFactors, setAvailableFactors] = useState<{ factor_id: string; name: string }[]>([]);
  const [selectedFactors, setSelectedFactors] = useState<string[]>([]);
  const [factorWeights, setFactorWeights] = useState<Record<string, number>>({});

  const [generatedStrategy, setGeneratedStrategy] = useState<StrategyGenerateResponse | null>(null);
  const [suggestions, setSuggestions] = useState<StrategySuggestion | null>(null);
  const [copied, setCopied] = useState(false);

  const [errors, setErrors] = useState<string[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);

  const [streamingContent, setStreamingContent] = useState('');
  const [statusMessage, setStatusMessage] = useState('');

  useEffect(() => {
    loadSuggestions();
  }, []);

  const loadSuggestions = async () => {
    try {
      const response = await strategyCreatorService.getSuggestions();
      if (response.success && response.suggestions) {
        setSuggestions(response.suggestions);
        const factors: { factor_id: string; name: string }[] = [];
        Object.entries(response.suggestions.recommended_factors || {}).forEach(([category, factorIds]) => {
          factorIds.forEach((id: string) => factors.push({ factor_id: id, name: id }));
        });
        setAvailableFactors(factors);
      }
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    }
  };

  const handleAddFactor = (factorId: string) => {
    if (!selectedFactors.includes(factorId)) {
      setSelectedFactors([...selectedFactors, factorId]);
      const newWeights = { ...factorWeights };
      const count = selectedFactors.length + 1;
      Object.keys(newWeights).forEach(k => newWeights[k] = 1 / count);
      newWeights[factorId] = 1 / count;
      setFactorWeights(newWeights);
    }
  };

  const handleRemoveFactor = (factorId: string) => {
    const newFactors = selectedFactors.filter((f) => f !== factorId);
    setSelectedFactors(newFactors);
    const newWeights = { ...factorWeights };
    delete newWeights[factorId];
    if (newFactors.length > 0) {
      Object.keys(newWeights).forEach(k => newWeights[k] = 1 / newFactors.length);
    }
    setFactorWeights(newWeights);
  };

  const handleWeightChange = (factorId: string, weight: number) => {
    setFactorWeights({ ...factorWeights, [factorId]: weight / 100 });
  };

  const handleGenerate = async () => {
    if (!description.trim()) {
      setErrors(['请输入策略描述']);
      return;
    }

    setIsGenerating(true);
    setErrors([]);
    setWarnings([]);
    setStreamingContent('');
    setStatusMessage('正在分析策略需求...');
    setCurrentStep('generate');

    try {
      const generator = strategyCreatorService.generateStrategyStream(
        {
          description: description.trim(),
          name: strategyName.trim() || undefined,
          strategy_type: strategyType,
          factors: selectedFactors,
          factor_weights: factorWeights,
          weight_method: weightMethod,
          rebalance_freq: rebalanceFreq,
          max_positions: maxPositions,
        },
        (status, message) => {
          setStatusMessage(message);
        },
        (content) => {
          setStreamingContent((prev) => prev + content);
        }
      );

      for await (const event of generator) {
        if (event.type === 'result' && event.data) {
          setGeneratedStrategy(event.data);
          if (event.data.validation.errors.length > 0) {
            setErrors(event.data.validation.errors);
          }
          if (event.data.validation.warnings.length > 0) {
            setWarnings(event.data.validation.warnings);
          }
          setCurrentStep('review');
        }

        if (event.type === 'error') {
          setErrors([event.message || '生成策略时发生错误']);
          setCurrentStep('describe');
        }
      }
    } catch (error) {
      console.error('Failed to generate strategy:', error);
      setErrors(['生成策略时发生错误，请稍后重试']);
      setCurrentStep('describe');
    } finally {
      setIsGenerating(false);
      setStatusMessage('');
    }
  };

  const handleSave = async () => {
    if (!generatedStrategy) return;

    setIsSaving(true);

    try {
      const response = await strategyCreatorService.saveStrategy({
        strategy_id: generatedStrategy.strategy_id,
        name: generatedStrategy.name,
        code: generatedStrategy.code,
        description: generatedStrategy.description,
        strategy_type: generatedStrategy.strategy_type,
        factors: generatedStrategy.factors,
        factor_weights: generatedStrategy.factor_weights,
        weight_method: weightMethod,
        rebalance_freq: rebalanceFreq,
        max_positions: maxPositions,
        tags: [generatedStrategy.strategy_type],
      });

      if (response.success) {
        setCurrentStep('save');
        if (onStrategyCreated) {
          setTimeout(() => onStrategyCreated(generatedStrategy.strategy_id), 1500);
        }
      }
    } catch (error) {
      console.error('Failed to save strategy:', error);
      setErrors(['保存策略时发生错误']);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCopyCode = async () => {
    if (generatedStrategy) {
      await navigator.clipboard.writeText(generatedStrategy.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleRegenerate = () => {
    setCurrentStep('describe');
    setGeneratedStrategy(null);
    setErrors([]);
    setWarnings([]);
    setStreamingContent('');
  };

  const steps = [
    { id: 'describe', label: '描述策略', icon: Sparkles },
    { id: 'generate', label: '生成代码', icon: Code },
    { id: 'review', label: '审查代码', icon: Settings },
    { id: 'save', label: '保存策略', icon: Save },
  ];

  const currentStepIndex = steps.findIndex((s) => s.id === currentStep);

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-5xl max-h-[90vh] overflow-hidden border-zinc-700 bg-zinc-900">
        <CardHeader className="bg-gradient-to-r from-amber-500 to-orange-500 pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Layers className="w-6 h-6 text-white" />
              <CardTitle className="text-xl text-white">AI 策略创建器</CardTitle>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onCancel}
              className="text-white/70 hover:text-white hover:bg-white/10"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>

          <div className="flex items-center gap-2 mt-4">
            {steps.map((step, index) => {
              const Icon = step.icon;
              const isActive = index === currentStepIndex;
              const isCompleted = index < currentStepIndex;

              return (
                <React.Fragment key={step.id}>
                  <div
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm transition-all ${
                      isActive
                        ? 'bg-white text-amber-600'
                        : isCompleted
                        ? 'bg-white/20 text-white'
                        : 'bg-white/10 text-white/50'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="hidden sm:inline">{step.label}</span>
                  </div>
                  {index < steps.length - 1 && (
                    <ChevronRight className="w-4 h-4 text-white/30" />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </CardHeader>

        <CardContent className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {currentStep === 'describe' && (
            <div className="space-y-6">
              <div>
                <Label className="text-zinc-300">策略名称（可选）</Label>
                <Input
                  value={strategyName}
                  onChange={(e) => setStrategyName(e.target.value)}
                  placeholder="例如：动量价值组合策略"
                  className="mt-2 bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
                />
              </div>

              <div>
                <Label className="text-zinc-300">策略描述 <span className="text-red-400">*</span></Label>
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="请详细描述您的策略逻辑，例如：&#10;创建一个动量+价值多因子策略，使用动量因子和价值因子等权重组合，月度再平衡，最大持仓50只股票。"
                  rows={4}
                  className="mt-2 bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500 resize-none"
                />
                <p className="mt-2 text-sm text-zinc-400">
                  描述越详细，生成的策略代码越准确
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <Label className="text-zinc-300">策略类型</Label>
                  <Select value={strategyType} onValueChange={setStrategyType}>
                    <SelectTrigger className="mt-2 bg-zinc-800 border-zinc-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-zinc-800 border-zinc-700">
                      {STRATEGY_TYPES.map((type) => (
                        <SelectItem
                          key={type.value}
                          value={type.value}
                          className="text-white hover:bg-zinc-700"
                        >
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-zinc-300">权重方法</Label>
                  <Select value={weightMethod} onValueChange={setWeightMethod}>
                    <SelectTrigger className="mt-2 bg-zinc-800 border-zinc-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-zinc-800 border-zinc-700">
                      {WEIGHT_METHODS.map((method) => (
                        <SelectItem
                          key={method.value}
                          value={method.value}
                          className="text-white hover:bg-zinc-700"
                        >
                          {method.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-zinc-300">再平衡频率</Label>
                  <Select value={rebalanceFreq} onValueChange={setRebalanceFreq}>
                    <SelectTrigger className="mt-2 bg-zinc-800 border-zinc-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-zinc-800 border-zinc-700">
                      {REBALANCE_FREQS.map((freq) => (
                        <SelectItem
                          key={freq.value}
                          value={freq.value}
                          className="text-white hover:bg-zinc-700"
                        >
                          {freq.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div>
                <Label className="text-zinc-300">最大持仓数</Label>
                <Input
                  type="number"
                  value={maxPositions}
                  onChange={(e) => setMaxPositions(parseInt(e.target.value) || 50)}
                  min={1}
                  max={500}
                  className="mt-2 bg-zinc-800 border-zinc-700 text-white w-32"
                />
              </div>

              <div>
                <Label className="text-zinc-300">选择因子</Label>
                <div className="mt-2 flex flex-wrap gap-2">
                  {selectedFactors.map((factorId) => (
                    <Badge
                      key={factorId}
                      className="bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 flex items-center gap-1"
                    >
                      {factorId}
                      <X
                        className="w-3 h-3 cursor-pointer"
                        onClick={() => handleRemoveFactor(factorId)}
                      />
                    </Badge>
                  ))}
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-3">
                  {suggestions?.recommended_factors &&
                    Object.entries(suggestions.recommended_factors).map(([category, factors]) => (
                      <div key={category}>
                        <div className="text-xs text-zinc-500 mb-1 capitalize">{category}</div>
                        {factors.map((factorId) => (
                          <Button
                            key={factorId}
                            variant="outline"
                            size="sm"
                            onClick={() => handleAddFactor(factorId)}
                            disabled={selectedFactors.includes(factorId)}
                            className="w-full justify-start mb-1 bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700 hover:text-white text-xs"
                          >
                            <Plus className="w-3 h-3 mr-1" />
                            {factorId}
                          </Button>
                        ))}
                      </div>
                    ))}
                </div>
              </div>

              {selectedFactors.length > 0 && (
                <div>
                  <Label className="text-zinc-300">因子权重 (%)</Label>
                  <div className="space-y-3 mt-2">
                    {selectedFactors.map((factorId) => (
                      <div key={factorId} className="flex items-center gap-4">
                        <span className="text-sm text-zinc-400 w-40 truncate">{factorId}</span>
                        <Input
                          type="number"
                          value={Math.round((factorWeights[factorId] || 0) * 100)}
                          onChange={(e) => handleWeightChange(factorId, parseInt(e.target.value) || 0)}
                          min={0}
                          max={100}
                          className="flex-1 bg-zinc-800 border-zinc-700 text-white"
                        />
                        <span className="text-sm text-white w-8">%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {errors.length > 0 && (
                <div className="bg-red-900/30 border border-red-500 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-red-400">
                    <AlertCircle className="w-5 h-5" />
                    <span className="font-medium">错误</span>
                  </div>
                  <ul className="mt-2 text-sm text-red-300 list-disc list-inside">
                    {errors.map((error, i) => (
                      <li key={i}>{error}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  onClick={onCancel}
                  className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                >
                  取消
                </Button>
                <Button
                  onClick={handleGenerate}
                  disabled={isGenerating || !description.trim()}
                  className="bg-amber-500 hover:bg-amber-600 text-white"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      生成中...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 mr-2" />
                      生成策略
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}

          {currentStep === 'generate' && (
            <div className="space-y-6">
              <Card className="bg-zinc-800 border-zinc-700">
                <CardContent className="p-4">
                  <div className="flex items-center gap-3 mb-4">
                    <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />
                    <span className="text-white font-medium">{statusMessage}</span>
                  </div>

                  <div className="bg-zinc-900 rounded-lg p-4 max-h-96 overflow-auto">
                    <pre className="text-sm text-zinc-300 whitespace-pre-wrap font-mono">
                      {streamingContent || '正在生成...'}
                    </pre>
                  </div>
                </CardContent>
              </Card>

              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  onClick={handleRegenerate}
                  className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                >
                  取消
                </Button>
              </div>
            </div>
          )}

          {currentStep === 'review' && generatedStrategy && (
            <div className="space-y-6">
              <Card className="bg-zinc-800 border-zinc-700">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-white">{generatedStrategy.name}</h3>
                      <p className="text-zinc-400 text-sm mt-1">{generatedStrategy.description}</p>
                    </div>
                    <div className="flex gap-2">
                      <Badge className="bg-amber-500/20 text-amber-400 hover:bg-amber-500/30">
                        {STRATEGY_TYPES.find((t) => t.value === generatedStrategy.strategy_type)?.label ||
                          generatedStrategy.strategy_type}
                      </Badge>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4 mt-4">
                    <div className="flex items-center gap-2">
                      <Layers className="w-4 h-4 text-zinc-400" />
                      <span className="text-sm text-zinc-300">
                        因子: {generatedStrategy.factors.length}个
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Info className="w-4 h-4 text-zinc-400" />
                      <span className="text-sm text-zinc-300 truncate">
                        ID: {generatedStrategy.strategy_id.slice(0, 20)}...
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {generatedStrategy.validation.is_valid ? (
                        <CheckCircle className="w-4 h-4 text-green-400" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-yellow-400" />
                      )}
                      <span className="text-sm text-zinc-300">
                        {generatedStrategy.validation.is_valid ? '验证通过' : '需要检查'}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {(errors.length > 0 || warnings.length > 0) && (
                <div className="space-y-2">
                  {errors.length > 0 && (
                    <div className="bg-red-900/30 border border-red-500 rounded-lg p-4">
                      <div className="flex items-center gap-2 text-red-400">
                        <AlertCircle className="w-5 h-5" />
                        <span className="font-medium">错误</span>
                      </div>
                      <ul className="mt-2 text-sm text-red-300 list-disc list-inside">
                        {errors.map((error, i) => (
                          <li key={i}>{error}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {warnings.length > 0 && (
                    <div className="bg-yellow-900/30 border border-yellow-500 rounded-lg p-4">
                      <div className="flex items-center gap-2 text-yellow-400">
                        <AlertCircle className="w-5 h-5" />
                        <span className="font-medium">警告</span>
                      </div>
                      <ul className="mt-2 text-sm text-yellow-300 list-disc list-inside">
                        {warnings.map((warning, i) => (
                          <li key={i}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label className="text-zinc-300">生成的代码</Label>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCopyCode}
                    className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                  >
                    {copied ? (
                      <>
                        <Check className="w-4 h-4 mr-1" />
                        已复制
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4 mr-1" />
                        复制代码
                      </>
                    )}
                  </Button>
                </div>
                <div className="bg-zinc-950 rounded-lg overflow-hidden border border-zinc-700">
                  <SyntaxHighlighter
                    language="python"
                    style={vscDarkPlus}
                    customStyle={{
                      margin: 0,
                      padding: '1rem',
                      fontSize: '0.85rem',
                      maxHeight: '400px',
                      overflow: 'auto',
                    }}
                  >
                    {generatedStrategy.code}
                  </SyntaxHighlighter>
                </div>
              </div>

              <Card className="bg-amber-900/20 border-amber-500/30">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 text-amber-400 mb-2">
                    <Info className="w-5 h-5" />
                    <span className="font-medium">策略说明</span>
                  </div>
                  <div className="text-sm text-zinc-300 whitespace-pre-wrap">
                    {generatedStrategy.explanation}
                  </div>
                </CardContent>
              </Card>

              <div className="flex justify-between">
                <Button
                  variant="outline"
                  onClick={handleRegenerate}
                  className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  重新生成
                </Button>
                <div className="flex gap-3">
                  <Button
                    variant="outline"
                    onClick={onCancel}
                    className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                  >
                    取消
                  </Button>
                  <Button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="bg-amber-500 hover:bg-amber-600 text-white"
                  >
                    {isSaving ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        保存中...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4 mr-2" />
                        保存策略
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}

          {currentStep === 'save' && generatedStrategy && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mb-6">
                <CheckCircle className="w-10 h-10 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-2">策略创建成功！</h3>
              <p className="text-zinc-400 mb-4">
                策略 <span className="text-amber-400">{generatedStrategy.name}</span> 已保存到策略库
              </p>
              <Card className="bg-zinc-800 border-zinc-700 px-4 py-2">
                <span className="text-sm text-zinc-300">
                  策略ID: {generatedStrategy.strategy_id}
                </span>
              </Card>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
