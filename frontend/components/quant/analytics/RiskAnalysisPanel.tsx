/**
 * Risk Analysis Panel Component
 * 
 * Comprehensive risk analysis including:
 * - VaR (Value at Risk)
 * - CVaR (Conditional Value at Risk)
 * - Stress Testing with historical scenarios
 * - Rolling risk metrics
 */

'use client';

import React, { memo } from 'react';
import { AlertTriangle, TrendingDown, Shield, Activity } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { StressTestResult } from '@/services/quantService';

interface RiskAnalysisPanelProps {
  varValue: number;
  cvarValue: number;
  confidenceLevel: number;
  horizonDays: number;
  method: string;
  stressTests?: StressTestResult[];
}

const formatPercent = (value: number): string => {
  return `${(value * 100).toFixed(2)}%`;
};

export const RiskAnalysisPanel = memo(function RiskAnalysisPanel({
  varValue,
  cvarValue,
  confidenceLevel,
  horizonDays,
  method,
  stressTests = [],
}: RiskAnalysisPanelProps) {
  return (
    <div className="space-y-6">
      {/* VaR & CVaR Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-red-600" />
            在险价值分析 (VaR & CVaR)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* VaR Card */}
            <div className="bg-gradient-to-br from-red-50 to-red-100 p-6 rounded-lg border border-red-200">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-red-900">VaR (在险价值)</h3>
                <Badge className="bg-red-600 text-white text-xs">
                  {confidenceLevel * 100}% 置信度
                </Badge>
              </div>
              <div className="text-3xl font-bold text-red-700 mb-2">
                {formatPercent(Math.abs(varValue))}
              </div>
              <p className="text-xs text-red-600">
                在{horizonDays}天内，有{(1 - confidenceLevel) * 100}%的概率最大损失不超过此值
              </p>
              <div className="mt-3 text-xs text-red-500">
                计算方法：{method === 'historical' ? '历史模拟法' : method === 'parametric' ? '参数法' : '蒙特卡洛模拟'}
              </div>
            </div>

            {/* CVaR Card */}
            <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-6 rounded-lg border border-orange-200">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-orange-900">CVaR (条件在险价值)</h3>
                <Badge className="bg-orange-500 text-white text-xs">期望短缺</Badge>
              </div>
              <div className="text-3xl font-bold text-orange-700 mb-2">
                {formatPercent(Math.abs(cvarValue))}
              </div>
              <p className="text-xs text-orange-600">
                当损失超过 VaR 时，预期的平均损失大小
              </p>
              <div className="mt-3 text-xs text-orange-500">
                {cvarValue > varValue ? '✓ CVaR > VaR，符合预期' : '⚠ CVaR 应大于 VaR'}
              </div>
            </div>
          </div>

          {/* Risk Interpretation */}
          <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
            <h4 className="text-sm font-semibold text-blue-900 mb-2 flex items-center gap-2">
              <Activity className="w-4 h-4" />
              风险解读
            </h4>
            <ul className="text-xs text-blue-700 space-y-1">
              <li>
                • <strong>VaR:</strong> 正常市场条件下，{horizonDays}天内可能的最大日损失为{' '}
                {formatPercent(Math.abs(varValue))}
              </li>
              <li>
                • <strong>CVaR:</strong> 极端情况下（超过 VaR 阈值），平均损失会达到{' '}
                {formatPercent(Math.abs(cvarValue))}
              </li>
              <li>
                • <strong>差距:</strong>{' '}
                {formatPercent(Math.abs(cvarValue) - Math.abs(varValue))}{' '}
                {(Math.abs(cvarValue) / Math.abs(varValue)).toFixed(2)}x VaR)
              </li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Stress Testing Section */}
      {stressTests && stressTests.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-600" />
              压力测试
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stressTests.map((test, index) => (
                <div
                  key={index}
                  className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h4 className="font-semibold text-gray-900">{test.scenario}</h4>
                      <p className="text-xs text-gray-500 mt-1">
                        恢复时间：{test.recovery_time}天
                      </p>
                    </div>
                    <Badge
                      variant={
                        test.portfolio_return > -0.1
                          ? 'default'
                          : test.portfolio_return > -0.2
                          ? 'secondary'
                          : 'danger'
                      }
                    >
                      {test.max_drawdown > -0.15 ? '轻度冲击' : test.max_drawdown > -0.25 ? '中度冲击' : '重度冲击'}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-3 gap-4 mt-3">
                    <div>
                      <div className="text-xs text-gray-500">组合收益</div>
                      <div
                        className={`text-lg font-bold ${
                          test.portfolio_return > 0 ? 'text-green-600' : 'text-red-600'
                        }`}
                      >
                        {formatPercent(test.portfolio_return)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500">基准收益</div>
                      <div
                        className={`text-lg font-bold ${
                          test.benchmark_return > 0 ? 'text-green-600' : 'text-red-600'
                        }`}
                      >
                        {formatPercent(test.benchmark_return)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-500">相对表现</div>
                      <div
                        className={`text-lg font-bold ${
                          test.relative_performance > 0 ? 'text-green-600' : 'text-red-600'
                        }`}
                      >
                        {formatPercent(test.relative_performance)}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Risk Metrics Summary */}
      <Card className="bg-gradient-to-br from-slate-50 to-slate-100">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-slate-600" />
            风险指标总结
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-xs text-gray-500 mb-1">VaR/CVaR 比率</div>
            <div className="text-xl font-bold text-gray-900">
              {(Math.abs(varValue) / Math.abs(cvarValue)).toFixed(2)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-500 mb-1">风险等级</div>
            <div
              className={`text-xl font-bold ${
                Math.abs(varValue) < 0.02
                  ? 'text-green-600'
                  : Math.abs(varValue) < 0.05
                  ? 'text-yellow-600'
                  : 'text-red-600'
              }`}
            >
              {Math.abs(varValue) < 0.02 ? '低风险' : Math.abs(varValue) < 0.05 ? '中等风险' : '高风险'}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-500 mb-1">压力测试平均损失</div>
            <div className="text-xl font-bold text-gray-900">
              {stressTests.length > 0
                ? formatPercent(stressTests.reduce((sum, t) => sum + t.portfolio_return, 0) / stressTests.length)
                : 'N/A'}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-gray-500 mb-1">置信水平</div>
            <div className="text-xl font-bold text-gray-900">{(confidenceLevel * 100).toFixed(0)}%</div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
});

export default RiskAnalysisPanel;
