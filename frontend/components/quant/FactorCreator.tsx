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
  Database,
  Tag,
  Info,
  Copy,
  Check,
  X,
  RefreshCw
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';

import { factorCreatorService, FactorGenerateResponse, FactorSuggestion, StreamEvent } from '@/services/factorCreatorService';

interface FactorCreatorProps {
  onFactorCreated?: (factorId: string) => void;
  onCancel?: () => void;
}

type Step = 'describe' | 'generate' | 'review' | 'test' | 'save';

const FACTOR_TYPES = [
  { value: 'technical', label: '技术因子', description: '基于价格、成交量等技术指标' },
  { value: 'fundamental', label: '基本面因子', description: '基于财务报表数据' },
  { value: 'sentiment', label: '情绪因子', description: '基于市场情绪和舆情数据' },
  { value: 'alternative', label: '另类因子', description: '基于另类数据源' },
];

const FACTOR_CATEGORIES = [
  { value: 'momentum', label: '动量' },
  { value: 'value', label: '价值' },
  { value: 'quality', label: '质量' },
  { value: 'volatility', label: '波动率' },
  { value: 'liquidity', label: '流动性' },
  { value: 'growth', label: '成长' },
  { value: 'custom', label: '自定义' },
];

export default function FactorCreator({ onFactorCreated, onCancel }: FactorCreatorProps) {
  const [currentStep, setCurrentStep] = useState<Step>('describe');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  
  const [description, setDescription] = useState('');
  const [factorName, setFactorName] = useState('');
  const [factorType, setFactorType] = useState('technical');
  const [category, setCategory] = useState('momentum');
  const [lookbackPeriod, setLookbackPeriod] = useState(20);
  
  const [generatedFactor, setGeneratedFactor] = useState<FactorGenerateResponse | null>(null);
  const [suggestions, setSuggestions] = useState<Record<string, FactorSuggestion>>({});
  const [testSymbol, setTestSymbol] = useState('600000.SH');
  const [testResult, setTestResult] = useState<{ value: number; date: string } | null>(null);
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
      const response = await factorCreatorService.getSuggestions();
      if (response.success && response.suggestions) {
        setSuggestions(response.suggestions as Record<string, FactorSuggestion>);
      }
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    }
  };

  const handleGenerate = async () => {
    if (!description.trim()) {
      setErrors(['请输入因子描述']);
      return;
    }

    setIsGenerating(true);
    setErrors([]);
    setWarnings([]);
    setStreamingContent('');
    setStatusMessage('正在分析因子需求...');
    setCurrentStep('generate');

    try {
      const generator = factorCreatorService.generateFactorStream(
        {
          description: description.trim(),
          name: factorName.trim() || undefined,
          context: {
            factor_type: factorType,
            category,
            lookback_period: lookbackPeriod,
          },
        },
        (status, message) => {
          setStatusMessage(message);
        },
        (content) => {
          setStreamingContent(prev => prev + content);
        }
      );

      for await (const event of generator) {
        if (event.type === 'result' && event.data) {
          setGeneratedFactor(event.data);
          if (event.data.validation.errors.length > 0) {
            setErrors(event.data.validation.errors);
          }
          if (event.data.validation.warnings.length > 0) {
            setWarnings(event.data.validation.warnings);
          }
          setCurrentStep('review');
        }
        
        if (event.type === 'error') {
          setErrors([event.message || '生成因子时发生错误']);
          setCurrentStep('describe');
        }
      }
    } catch (error) {
      console.error('Failed to generate factor:', error);
      setErrors(['生成因子时发生错误，请稍后重试']);
      setCurrentStep('describe');
    } finally {
      setIsGenerating(false);
      setStatusMessage('');
    }
  };

  const handleTest = async () => {
    if (!generatedFactor) return;

    setIsTesting(true);
    setTestResult(null);

    try {
      const response = await factorCreatorService.testFactor(
        generatedFactor.factor_id,
        testSymbol,
        generatedFactor.parameters,
        generatedFactor.code
      );

      if (response.success) {
        setTestResult(response.result);
        setCurrentStep('test');
      }
    } catch (error) {
      console.error('Failed to test factor:', error);
      setErrors(['测试因子时发生错误']);
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = async () => {
    if (!generatedFactor) return;

    setIsSaving(true);

    try {
      const response = await factorCreatorService.saveFactor({
        factor_id: generatedFactor.factor_id,
        name: generatedFactor.name,
        code: generatedFactor.code,
        description: generatedFactor.description,
        factor_type: generatedFactor.factor_type,
        category: generatedFactor.category,
        lookback_period: generatedFactor.lookback_period,
        parameters: generatedFactor.parameters,
        tags: [generatedFactor.category, generatedFactor.factor_type],
      });

      if (response.success) {
        setCurrentStep('save');
        if (onFactorCreated) {
          setTimeout(() => onFactorCreated(generatedFactor.factor_id), 1500);
        }
      }
    } catch (error) {
      console.error('Failed to save factor:', error);
      setErrors(['保存因子时发生错误']);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCopyCode = async () => {
    if (generatedFactor) {
      await navigator.clipboard.writeText(generatedFactor.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleRegenerate = () => {
    setCurrentStep('describe');
    setGeneratedFactor(null);
    setTestResult(null);
    setErrors([]);
    setWarnings([]);
    setStreamingContent('');
  };

  const steps = [
    { id: 'describe', label: '描述因子', icon: Sparkles },
    { id: 'generate', label: '生成代码', icon: Code },
    { id: 'review', label: '审查代码', icon: Settings },
    { id: 'test', label: '测试因子', icon: Play },
    { id: 'save', label: '保存因子', icon: Save },
  ];

  const currentStepIndex = steps.findIndex(s => s.id === currentStep);

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-5xl max-h-[90vh] overflow-hidden border-zinc-700 bg-zinc-900">
        <CardHeader className="bg-gradient-to-r from-amber-500 to-orange-500 pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Sparkles className="w-6 h-6 text-white" />
              <CardTitle className="text-xl text-white">AI 因子创建器</CardTitle>
            </div>
            <Button variant="ghost" size="sm" onClick={onCancel} className="text-white/70 hover:text-white hover:bg-white/10">
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
                <Label className="text-zinc-300">因子名称（可选）</Label>
                <Input
                  value={factorName}
                  onChange={(e) => setFactorName(e.target.value)}
                  placeholder="例如：动量反转因子"
                  className="mt-2 bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
                />
              </div>

              <div>
                <Label className="text-zinc-300">因子描述 <span className="text-red-400">*</span></Label>
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="请详细描述您想要的因子逻辑，例如：&#10;计算股票过去20天的累计收益率，并除以同期波动率，得到风险调整后的动量指标。"
                  rows={4}
                  className="mt-2 bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500 resize-none"
                />
                <p className="mt-2 text-sm text-zinc-400">
                  描述越详细，生成的因子代码越准确
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <Label className="text-zinc-300">因子类型</Label>
                  <Select value={factorType} onValueChange={setFactorType}>
                    <SelectTrigger className="mt-2 bg-zinc-800 border-zinc-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-zinc-800 border-zinc-700">
                      {FACTOR_TYPES.map((type) => (
                        <SelectItem key={type.value} value={type.value} className="text-white hover:bg-zinc-700">
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-zinc-300">因子类别</Label>
                  <Select value={category} onValueChange={setCategory}>
                    <SelectTrigger className="mt-2 bg-zinc-800 border-zinc-700 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-zinc-800 border-zinc-700">
                      {FACTOR_CATEGORIES.map((cat) => (
                        <SelectItem key={cat.value} value={cat.value} className="text-white hover:bg-zinc-700">
                          {cat.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label className="text-zinc-300">回看周期（天）</Label>
                  <Input
                    type="number"
                    value={lookbackPeriod}
                    onChange={(e) => setLookbackPeriod(parseInt(e.target.value) || 20)}
                    min={1}
                    max={500}
                    className="mt-2 bg-zinc-800 border-zinc-700 text-white"
                  />
                </div>
              </div>

              <div>
                <Label className="text-zinc-300">快速模板</Label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2">
                  {Object.entries(suggestions).map(([key, suggestion]) => (
                    <Button
                      key={key}
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setDescription(suggestion.description_template.replace('{period}', '20'));
                        setCategory(key);
                      }}
                      className="justify-start bg-zinc-800 border-zinc-700 text-zinc-300 hover:bg-zinc-700 hover:text-white"
                    >
                      <Tag className="w-4 h-4 mr-2" />
                      {key}
                    </Button>
                  ))}
                </div>
              </div>

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
                <Button variant="outline" onClick={onCancel} className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
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
                      生成因子
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
                <Button variant="outline" onClick={handleRegenerate} className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
                  取消
                </Button>
              </div>
            </div>
          )}

          {currentStep === 'review' && generatedFactor && (
            <div className="space-y-6">
              <Card className="bg-zinc-800 border-zinc-700">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-white">{generatedFactor.name}</h3>
                      <p className="text-zinc-400 text-sm mt-1">{generatedFactor.description}</p>
                    </div>
                    <div className="flex gap-2">
                      <Badge className="bg-amber-500/20 text-amber-400 hover:bg-amber-500/30">
                        {FACTOR_TYPES.find(t => t.value === generatedFactor.factor_type)?.label || generatedFactor.factor_type}
                      </Badge>
                      <Badge className="bg-orange-500/20 text-orange-400 hover:bg-orange-500/30">
                        {FACTOR_CATEGORIES.find(c => c.value === generatedFactor.category)?.label || generatedFactor.category}
                      </Badge>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4 mt-4">
                    <div className="flex items-center gap-2">
                      <Database className="w-4 h-4 text-zinc-400" />
                      <span className="text-sm text-zinc-300">回看周期: {generatedFactor.lookback_period}天</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Info className="w-4 h-4 text-zinc-400" />
                      <span className="text-sm text-zinc-300">ID: {generatedFactor.factor_id.slice(0, 20)}...</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {generatedFactor.validation.is_valid ? (
                        <CheckCircle className="w-4 h-4 text-green-400" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-yellow-400" />
                      )}
                      <span className="text-sm text-zinc-300">
                        {generatedFactor.validation.is_valid ? '验证通过' : '需要检查'}
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
                    {generatedFactor.code}
                  </SyntaxHighlighter>
                </div>
              </div>

              <Card className="bg-blue-900/20 border-blue-500/30">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 text-blue-400 mb-2">
                    <Info className="w-5 h-5" />
                    <span className="font-medium">因子说明</span>
                  </div>
                  <div className="text-sm text-zinc-300 whitespace-pre-wrap">
                    {generatedFactor.explanation}
                  </div>
                </CardContent>
              </Card>

              {Object.keys(generatedFactor.parameters).length > 0 && (
                <div>
                  <Label className="text-zinc-300">因子参数</Label>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2">
                    {Object.entries(generatedFactor.parameters).map(([key, value]) => (
                      <div key={key} className="bg-zinc-800 rounded-lg p-3 border border-zinc-700">
                        <span className="text-zinc-400 text-xs">{key}</span>
                        <div className="text-white font-mono">{String(value)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex justify-between">
                <Button variant="outline" onClick={handleRegenerate} className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
                  <RefreshCw className="w-4 h-4 mr-2" />
                  重新生成
                </Button>
                <div className="flex gap-3">
                  <Button variant="outline" onClick={onCancel} className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
                    取消
                  </Button>
                  <Button
                    onClick={handleTest}
                    disabled={isTesting}
                    className="bg-green-600 hover:bg-green-500 text-white"
                  >
                    {isTesting ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        测试中...
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 mr-2" />
                        测试因子
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}

          {currentStep === 'test' && generatedFactor && (
            <div className="space-y-6">
              <Card className="bg-zinc-800 border-zinc-700">
                <CardContent className="p-4">
                  <h3 className="text-lg font-semibold text-white mb-4">因子测试</h3>
                  
                  <div className="flex gap-4">
                    <div className="flex-1">
                      <Label className="text-zinc-300">测试标的</Label>
                      <Input
                        value={testSymbol}
                        onChange={(e) => setTestSymbol(e.target.value)}
                        placeholder="例如：600000.SH"
                        className="mt-2 bg-zinc-700 border-zinc-600 text-white placeholder:text-zinc-400"
                      />
                    </div>
                    <div className="flex items-end">
                      <Button
                        onClick={handleTest}
                        disabled={isTesting}
                        className="bg-amber-500 hover:bg-amber-600 text-white"
                      >
                        {isTesting ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            测试中...
                          </>
                        ) : (
                          <>
                            <Play className="w-4 h-4 mr-2" />
                            运行测试
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {testResult && (
                <Card className="bg-green-900/20 border-green-500/30">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 text-green-400 mb-2">
                      <CheckCircle className="w-5 h-5" />
                      <span className="font-medium">测试结果</span>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <span className="text-zinc-400 text-sm">因子值</span>
                        <div className="text-2xl font-bold text-white">{testResult.value.toFixed(4)}</div>
                      </div>
                      <div>
                        <span className="text-zinc-400 text-sm">标的</span>
                        <div className="text-lg text-white">{testSymbol}</div>
                      </div>
                      <div>
                        <span className="text-zinc-400 text-sm">日期</span>
                        <div className="text-lg text-white">{testResult.date}</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              <div className="flex justify-between">
                <Button variant="outline" onClick={() => setCurrentStep('review')} className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
                  返回修改
                </Button>
                <div className="flex gap-3">
                  <Button variant="outline" onClick={onCancel} className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
                    取消
                  </Button>
                  <Button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="bg-purple-600 hover:bg-purple-500 text-white"
                  >
                    {isSaving ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        保存中...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4 mr-2" />
                        保存因子
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}

          {currentStep === 'save' && generatedFactor && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mb-6">
                <CheckCircle className="w-10 h-10 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-2">因子创建成功！</h3>
              <p className="text-zinc-400 mb-4">
                因子 <span className="text-amber-400">{generatedFactor.name}</span> 已保存到因子库
              </p>
              <Card className="bg-zinc-800 border-zinc-700 px-4 py-2">
                <span className="text-sm text-zinc-300">因子ID: {generatedFactor.factor_id}</span>
              </Card>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
