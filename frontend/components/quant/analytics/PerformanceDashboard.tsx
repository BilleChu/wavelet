/**
 * Performance Dashboard Component
 * 
 * Displays comprehensive 60+ professional performance metrics
 * organized by category for quantitative strategy analysis.
 */

'use client';

import React, { memo, useMemo } from 'react';
import { TrendingUp, Shield, Activity, BarChart3, PieChart, Zap } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { 
  ReturnsMetrics,
  RiskMetrics,
  RiskAdjustedMetrics,
  MarketRiskMetrics,
  TradingMetrics,
  AdvancedMetrics,
} from '@/services/quantService';

interface PerformanceDashboardProps {
  returns: ReturnsMetrics;
  risk: RiskMetrics;
  riskAdjusted: RiskAdjustedMetrics;
  marketRisk: MarketRiskMetrics;
  trading: TradingMetrics;
  advanced: AdvancedMetrics;
  summary?: Record<string, number>;
}

// Utility function to format percentages
const formatPercent = (value: number): string => {
  return `${(value * 100).toFixed(2)}%`;
};

// Utility function to format ratios
const formatRatio = (value: number): string => {
  return value.toFixed(2);
};

// Metric Card Component
const MetricCard = memo(function MetricCard({
  label,
  value,
  subtext,
  trend,
}: {
  label: string;
  value: string | number;
  subtext?: string;
  trend?: 'up' | 'down' | 'neutral';
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
      <div className="text-sm text-gray-500 mb-1">{label}</div>
      <div className="flex items-baseline gap-2">
        <div
          className={`text-2xl font-bold ${
            trend === 'up'
              ? 'text-green-600'
              : trend === 'down'
              ? 'text-red-600'
              : 'text-gray-900'
          }`}
        >
          {value}
        </div>
        {subtext && <div className="text-xs text-gray-500">{subtext}</div>}
      </div>
    </div>
  );
});

// Returns Metrics Section
const ReturnsSection = memo(function ReturnsSection({ metrics }: { metrics: ReturnsMetrics }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-green-600" />
          收益指标
        </CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          label="总收益率"
          value={formatPercent(metrics.total_return)}
          trend={metrics.total_return > 0 ? 'up' : 'down'}
        />
        <MetricCard
          label="年化收益率"
          value={formatPercent(metrics.annualized_return)}
          trend={metrics.annualized_return > 0 ? 'up' : 'down'}
        />
        <MetricCard
          label="CAGR"
          value={formatPercent(metrics.cagr)}
          trend={metrics.cagr > 0 ? 'up' : 'down'}
        />
        <MetricCard
          label="超额收益"
          value={formatPercent(metrics.excess_return)}
          trend={metrics.excess_return > 0 ? 'up' : 'down'}
        />
        <MetricCard
          label="主动收益"
          value={formatPercent(metrics.active_return)}
          trend={metrics.active_return > 0 ? 'up' : 'down'}
        />
        <MetricCard
          label="累计收益率"
          value={formatPercent(metrics.cumulative_return)}
          trend={metrics.cumulative_return > 0 ? 'up' : 'down'}
        />
      </CardContent>
    </Card>
  );
});

// Risk Metrics Section
const RiskSection = memo(function RiskSection({ metrics }: { metrics: RiskMetrics }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-red-600" />
          风险指标
        </CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          label="波动率"
          value={formatPercent(metrics.volatility)}
          trend={metrics.volatility < 0.2 ? 'up' : 'down'}
        />
        <MetricCard
          label="最大回撤"
          value={formatPercent(metrics.max_drawdown)}
          trend={metrics.max_drawdown > -0.2 ? 'up' : 'down'}
        />
        <MetricCard
          label="平均回撤"
          value={formatPercent(metrics.avg_drawdown)}
          trend={metrics.avg_drawdown > -0.1 ? 'up' : 'down'}
        />
        <MetricCard
          label="VaR(95%)"
          value={formatPercent(Math.abs(metrics.var_95))}
          subtext="在险价值"
        />
        <MetricCard
          label="CVaR(95%)"
          value={formatPercent(Math.abs(metrics.cvar_95))}
          subtext="条件在险价值"
        />
        <MetricCard
          label="溃疡指数"
          value={formatRatio(metrics.ulcer_index)}
          subtext="风险调整指标"
        />
      </CardContent>
    </Card>
  );
});

// Risk-Adjusted Metrics Section
const RiskAdjustedSection = memo(function RiskAdjustedSection({
  metrics,
}: {
  metrics: RiskAdjustedMetrics;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-blue-600" />
          风险调整后收益
        </CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          label="夏普比率"
          value={formatRatio(metrics.sharpe_ratio)}
          trend={metrics.sharpe_ratio > 1 ? 'up' : metrics.sharpe_ratio > 0 ? 'neutral' : 'down'}
          subtext=">1 优秀"
        />
        <MetricCard
          label="索提诺比率"
          value={formatRatio(metrics.sortino_ratio)}
          trend={metrics.sortino_ratio > 1 ? 'up' : 'neutral'}
          subtext="下行风险调整"
        />
        <MetricCard
          label="卡玛比率"
          value={formatRatio(metrics.calmar_ratio)}
          trend={metrics.calmar_ratio > 1 ? 'up' : 'neutral'}
          subtext="回撤调整收益"
        />
        <MetricCard
          label="信息比率"
          value={formatRatio(metrics.information_ratio)}
          trend={metrics.information_ratio > 0.5 ? 'up' : 'neutral'}
          subtext="主动收益/跟踪误差"
        />
        <MetricCard
          label="欧米伽比率"
          value={formatRatio(metrics.omega_ratio)}
          trend={metrics.omega_ratio > 1 ? 'up' : 'neutral'}
          subtext="收益/损失比"
        />
      </CardContent>
    </Card>
  );
});

// Market Risk Metrics Section
const MarketRiskSection = memo(function MarketRiskSection({
  metrics,
}: {
  metrics: MarketRiskMetrics;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-purple-600" />
          市场风险指标
        </CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          label="Beta"
          value={formatRatio(metrics.beta)}
          subtext={`市场敏感度${Math.abs(metrics.beta) > 1 ? '(高波动)' : '(低波动)'}`}
        />
        <MetricCard
          label="Alpha"
          value={formatPercent(metrics.alpha)}
          trend={metrics.alpha > 0 ? 'up' : 'down'}
          subtext="超额收益能力"
        />
        <MetricCard
          label="跟踪误差"
          value={formatPercent(metrics.tracking_error)}
          subtext="相对基准偏离度"
        />
        <MetricCard label="R²" value={formatRatio(metrics.r_squared)} subtext="拟合优度" />
      </CardContent>
    </Card>
  );
});

// Trading Metrics Section
const TradingSection = memo(function TradingSection({ metrics }: { metrics: TradingMetrics }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <PieChart className="w-5 h-5 text-orange-600" />
          交易统计指标
        </CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          label="胜率"
          value={formatPercent(metrics.win_rate)}
          trend={metrics.win_rate > 0.5 ? 'up' : 'down'}
          subtext={`${(metrics.win_rate * 100).toFixed(1)}% 盈利概率`}
        />
        <MetricCard
          label="盈亏比"
          value={formatRatio(metrics.profit_loss_ratio)}
          trend={metrics.profit_loss_ratio > 1.5 ? 'up' : 'neutral'}
          subtext="平均盈利/平均亏损"
        />
        <MetricCard
          label="期望收益"
          value={formatPercent(metrics.expectancy)}
          trend={metrics.expectancy > 0 ? 'up' : 'down'}
        />
        <MetricCard
          label="换手率"
          value={formatPercent(metrics.turnover_rate)}
          subtext="年度换手频率"
        />
        <MetricCard
          label="平均持仓周期"
          value={`${metrics.avg_holding_period.toFixed(1)}天`}
          subtext="平均持仓时间"
        />
      </CardContent>
    </Card>
  );
});

// Advanced Metrics Section
const AdvancedSection = memo(function AdvancedSection({ metrics }: { metrics: AdvancedMetrics }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-indigo-600" />
          高级指标
        </CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          label="尾部比率"
          value={formatRatio(metrics.tail_ratio)}
          trend={metrics.tail_ratio > 1 ? 'up' : 'neutral'}
          subtext="右尾/左尾风险比"
        />
        <MetricCard
          label="偏度"
          value={formatRatio(metrics.skewness)}
          subtext={
            metrics.skewness > 0 ? '正偏 (长右尾)' : metrics.skewness < 0 ? '负偏 (长左尾)' : '对称分布'
          }
        />
        <MetricCard
          label="峰度"
          value={formatRatio(metrics.kurtosis)}
          subtext={metrics.kurtosis > 3 ? '尖峰 (厚尾)' : metrics.kurtosis < 3 ? '平峰 (薄尾)' : '正态分布'}
        />
      </CardContent>
    </Card>
  );
});

// Main Dashboard Component
export const PerformanceDashboard = memo(function PerformanceDashboard({
  returns,
  risk,
  riskAdjusted,
  marketRisk,
  trading,
  advanced,
  summary,
}: PerformanceDashboardProps) {
  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(summary).map(([key, value]) => (
            <MetricCard
              key={key}
              label={key.replace(/_/g, ' ').toUpperCase()}
              value={typeof value === 'number' ? formatPercent(value) : String(value)}
            />
          ))}
        </div>
      )}

      {/* Categorized Metrics */}
      <div className="space-y-4">
        <ReturnsSection metrics={returns} />
        <RiskSection metrics={risk} />
        <RiskAdjustedSection metrics={riskAdjusted} />
        <MarketRiskSection metrics={marketRisk} />
        <TradingSection metrics={trading} />
        <AdvancedSection metrics={advanced} />
      </div>
    </div>
  );
});

export default PerformanceDashboard;
