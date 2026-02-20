/**
 * Analytics Detail Page
 * 
 * Professional quantitative strategy analysis dashboard featuring:
 * - 60+ performance metrics with categorization
 * - Comprehensive risk analysis (VaR, CVaR, stress testing)
 * - Performance attribution (Brinson, factor, sector)
 * - Rolling window analysis
 * - Monte Carlo simulation
 * 
 * Optimized for performance with memoization and efficient data loading.
 */

'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { ArrowLeft, TrendingUp, Shield, PieChart, Activity, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { quantService } from '@/services/quantService';
import PerformanceDashboard from '@/components/quant/analytics/PerformanceDashboard';
import RiskAnalysisPanel from '@/components/quant/analytics/RiskAnalysisPanel';
import AttributionChart from '@/components/quant/analytics/AttributionChart';
import { EquityCurveChart, DrawdownChart } from '@/components/quant/charts';

export default function AnalyticsDetailPage() {
  const searchParams = useSearchParams();
  const backtestId = searchParams.get('backtest_id') || '';
  
  // State management
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('performance');
  const [refreshKey, setRefreshKey] = useState(0);
  
  // Analytics data state
  const [performanceData, setPerformanceData] = useState<any>(null);
  const [riskData, setRiskData] = useState<any>(null);
  const [attributionData, setAttributionData] = useState<any>(null);
  const [equityData, setEquityData] = useState<Array<{ date: string; value: number }>>([]);
  
  // Fetch all analytics data
  const fetchData = useCallback(async () => {
    if (!backtestId) return;
    
    setLoading(true);
    try {
      // Parallel API calls for better performance
      const [perfResponse, riskResponse, attrResponse] = await Promise.all([
        quantService.getPerformanceAnalytics({ backtest_id: backtestId, include_benchmark: true }),
        quantService.getRiskAnalysis({ backtest_id: backtestId }),
        quantService.getAttributionAnalysis({ backtest_id: backtestId }),
      ]);
      
      setPerformanceData(perfResponse.metrics);
      setRiskData(riskResponse);
      setAttributionData(attrResponse.attribution);
      
      // Mock equity curve data (in production, fetch from backtest result)
      const mockEquityData = generateMockEquityData;
      setEquityData(mockEquityData);
      
    } catch (error) {
      console.error('Failed to fetch analytics data:', error);
    } finally {
      setLoading(false);
    }
  }, [backtestId]);
  
  // Initial load
  useEffect(() => {
    fetchData();
  }, [fetchData]);
  
  // Handle refresh
  const handleRefresh = useCallback(() => {
    setRefreshKey(prev => prev + 1);
    fetchData();
  }, [fetchData]);
  
  // Generate mock equity data (replace with real data in production)
  const generateMockEquityData = useMemo(() => {
    const data: Array<{ date: string; value: number }> = [];
    const baseValue = 1_000_000;
    let currentValue = baseValue;
    const today = new Date();
    
    for (let i = 365; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      
      // Simulate realistic returns
      const dailyReturn = (Math.random() - 0.48) * 0.02; // Slight positive bias
      currentValue *= (1 + dailyReturn);
      
      data.push({
        date: date.toISOString().split('T')[0],
        value: currentValue,
      });
    }
    
    return data;
  }, []);
  
  // Loading state
  if (loading && !performanceData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-gray-600">Loading analytics data...</p>
        </div>
      </div>
    );
  }
  
  // No data state
  if (!performanceData && !riskData && !attributionData) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <Card>
            <CardHeader>
              <CardTitle>No Data Available</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 mb-4">No analytics data found for this backtest.</p>
              <Link href="/quant">
                <Button>Back to Quant Page</Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/quant">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
              </Link>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">策略分析详情</h1>
                <p className="text-sm text-gray-500">Backtest ID: {backtestId}</p>
              </div>
            </div>
            <Button onClick={handleRefresh} variant="outline" size="sm">
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="performance" className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              绩效指标
            </TabsTrigger>
            <TabsTrigger value="risk" className="flex items-center gap-2">
              <Shield className="w-4 h-4" />
              风险分析
            </TabsTrigger>
            <TabsTrigger value="attribution" className="flex items-center gap-2">
              <PieChart className="w-4 h-4" />
              归因分析
            </TabsTrigger>
            <TabsTrigger value="charts" className="flex items-center gap-2">
              <Activity className="w-4 h-4" />
              图表分析
            </TabsTrigger>
          </TabsList>
          
          {/* Performance Tab */}
          <TabsContent value="performance">
            {performanceData && (
              <PerformanceDashboard
                key={`perf-${refreshKey}`}
                returns={performanceData.returns}
                risk={performanceData.risk}
                riskAdjusted={performanceData.risk_adjusted}
                marketRisk={performanceData.market_risk}
                trading={performanceData.trading}
                advanced={performanceData.advanced}
                summary={performanceData.summary}
              />
            )}
          </TabsContent>
          
          {/* Risk Tab */}
          <TabsContent value="risk">
            {riskData && (
              <RiskAnalysisPanel
                key={`risk-${refreshKey}`}
                varValue={riskData.var.value}
                cvarValue={riskData.cvar}
                confidenceLevel={riskData.var.confidence_level}
                horizonDays={riskData.var.horizon_days}
                method={riskData.var.method}
                stressTests={riskData.stress_tests}
              />
            )}
          </TabsContent>
          
          {/* Attribution Tab */}
          <TabsContent value="attribution">
            {attributionData && (
              <AttributionChart
                key={`attr-${refreshKey}`}
                attribution={attributionData}
              />
            )}
          </TabsContent>
          
          {/* Charts Tab */}
          <TabsContent value="charts">
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>权益曲线</CardTitle>
                </CardHeader>
                <CardContent>
                  <EquityCurveChart
                    data={equityData.map(d => ({ date: d.date, portfolio: d.value }))}
                    height={400}
                    showBenchmark={true}
                  />
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle>回撤分析</CardTitle>
                </CardHeader>
                <CardContent>
                  <DrawdownChart
                    equityData={equityData}
                    height={200}
                  />
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
