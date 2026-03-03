"""
Complete Backtest Workflow for Strong Stock Strategy.

This script demonstrates the full professional backtest process:
1. Load strategy configuration
2. Get historical data
3. Calculate factors
4. Run backtest
5. Generate comprehensive report
6. Visualize results
"""

import asyncio
import logging
from datetime import datetime, timedelta, date
from pathlib import Path
import json
import pandas as pd
import numpy as np

from openfinance.quant.strategy.config_loader import get_strategy_config_loader
from openfinance.quant.backtest.engine import BacktestEngine
from openfinance.quant.backtest.report_generator import BacktestReportGenerator
from openfinance.domain.models.quant import BacktestConfig
from openfinance.datacenter.models.analytical import ADSKLineModel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StrongStockBacktestWorkflow:
    """
    Complete backtest workflow for strong stock strategy.
    
    Steps:
    1. Initialize components
    2. Load strategy configuration
    3. Prepare historical data
    4. Calculate factors
    5. Run backtest
    6. Generate report
    7. Save results
    """
    
    def __init__(self):
        self.config_loader = None
        self.backtest_engine = None
        self.report_generator = None
        self.strategy_config = None
        self.strategy = None
    
    async def initialize(self):
        """Initialize all components."""
        logger.info("="*80)
        logger.info("初始化回测系统")
        logger.info("="*80)
        
        self.config_loader = get_strategy_config_loader()
        self.backtest_engine = BacktestEngine()
        self.report_generator = BacktestReportGenerator()
        
        logger.info("✓ 配置加载器已初始化")
        logger.info("✓ 回测引擎已初始化")
        logger.info("✓ 报告生成器已初始化")
    
    async def load_strategy(self, strategy_id: str = "strategy_strong_stock"):
        """Load strategy configuration."""
        logger.info(f"\n加载策略配置: {strategy_id}")
        
        self.strategy_config = self.config_loader.get_config(strategy_id)
        
        if not self.strategy_config:
            raise ValueError(f"Strategy config not found: {strategy_id}")
        
        self.strategy = self.config_loader.to_domain_strategy(self.strategy_config)
        
        logger.info(f"✓ 策略名称: {self.strategy.name}")
        logger.info(f"✓ 策略ID: {self.strategy.strategy_id}")
        logger.info(f"✓ 因子数量: {len(self.strategy.factors)}")
        logger.info(f"✓ 最大持仓: {self.strategy_config.portfolio.max_positions}")
        logger.info(f"✓ 调仓频率: {self.strategy_config.portfolio.rebalance_freq}")
        
        return self.strategy
    
    async def prepare_data(
        self,
        start_date: date,
        end_date: date,
        stock_codes: list[str] | None = None,
    ) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
        """
        Prepare historical data for backtest.
        
        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            stock_codes: Optional list of stock codes
        
        Returns:
            Tuple of (price_data, factor_values)
        """
        logger.info(f"\n准备历史数据")
        logger.info(f"时间范围: {start_date} 至 {end_date}")
        
        if stock_codes is None:
            stock_codes = self._get_default_stock_universe()
        
        logger.info(f"股票池大小: {len(stock_codes)}")
        
        price_data = await self._get_price_data(stock_codes, start_date, end_date)
        
        logger.info(f"价格数据: {len(price_data)} 条记录")
        
        factor_values = await self._calculate_factors(price_data)
        
        logger.info(f"因子数据: {len(factor_values)} 个因子")
        
        return price_data, factor_values
    
    async def run_backtest(
        self,
        start_date: date,
        end_date: date,
        initial_capital: float = 1000000.0,
    ) -> dict:
        """
        Run complete backtest workflow.
        
        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Initial capital
        
        Returns:
            Dictionary with backtest results and report
        """
        logger.info("\n" + "="*80)
        logger.info("开始回测流程")
        logger.info("="*80)
        
        price_data, factor_values = await self.prepare_data(start_date, end_date)
        
        backtest_config = BacktestConfig(
            backtest_id=f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            strategy_id=self.strategy.strategy_id,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            commission=self.strategy_config.backtest.commission,
            slippage=self.strategy_config.backtest.slippage,
            benchmark=self.strategy_config.backtest.benchmark,
            risk_free_rate=self.strategy_config.backtest.risk_free_rate,
        )
        
        logger.info(f"\n回测配置:")
        logger.info(f"  初始资金: {initial_capital:,.2f}")
        logger.info(f"  佣金率: {backtest_config.commission:.4f}")
        logger.info(f"  滑点: {backtest_config.slippage:.4f}")
        
        logger.info("\n执行回测...")
        result = await self.backtest_engine.run(
            strategy=self.strategy,
            config=backtest_config,
            price_data=price_data,
            factor_values=factor_values,
        )
        
        logger.info(f"✓ 回测完成，状态: {result.status}")
        
        logger.info("\n生成回测报告...")
        report = self.report_generator.generate_report(result)
        
        logger.info("✓ 报告生成完成")
        
        return {
            "result": result,
            "report": report,
        }
    
    def print_executive_summary(self, report: dict):
        """Print executive summary of backtest report."""
        summary = report.get("executive_summary", {})
        metadata = report.get("metadata", {})
        
        print("\n" + "="*80)
        print("回测报告摘要")
        print("="*80)
        
        print(f"\n【基本信息】")
        print(f"  策略名称: {self.strategy.name}")
        print(f"  回测区间: {metadata.get('start_date')} 至 {metadata.get('end_date')}")
        print(f"  回测天数: {metadata.get('duration_days')} 天")
        print(f"  初始资金: {metadata.get('initial_capital'):,.2f}")
        
        print(f"\n【核心指标】")
        print(f"  最终权益: {summary.get('final_equity', 0):,.2f}")
        print(f"  总收益: {summary.get('profit_percentage', 0):.2f}%")
        print(f"  年化收益: {summary.get('annual_return', 0) * 100:.2f}%")
        print(f"  最大回撤: {summary.get('max_drawdown', 0) * 100:.2f}%")
        print(f"  夏普比率: {summary.get('sharpe_ratio', 0):.2f}")
        print(f"  胜率: {summary.get('win_rate', 0) * 100:.2f}%")
        print(f"  交易次数: {summary.get('total_trades', 0)}")
        
        print(f"\n【策略评级】")
        print(f"  评级: {summary.get('strategy_grade', 'N/A')}")
        print(f"  得分: {summary.get('strategy_score', 0):.1f}/100")
        print(f"  评估: {summary.get('performance_assessment', 'N/A')}")
        
        print("\n" + "="*80)
    
    def print_performance_metrics(self, report: dict):
        """Print detailed performance metrics."""
        metrics = report.get("performance_metrics", {})
        
        print("\n" + "="*80)
        print("详细绩效指标")
        print("="*80)
        
        returns = metrics.get("returns", {})
        print(f"\n【收益指标】")
        for key, val in returns.items():
            if isinstance(val, dict):
                print(f"  {val.get('description', key)}: {val.get('formatted', val.get('value'))}")
        
        risk = metrics.get("risk", {})
        print(f"\n【风险指标】")
        for key, val in risk.items():
            if isinstance(val, dict):
                print(f"  {val.get('description', key)}: {val.get('formatted', val.get('value'))}")
        
        risk_adjusted = metrics.get("risk_adjusted", {})
        print(f"\n【风险调整收益】")
        for key, val in risk_adjusted.items():
            if isinstance(val, dict):
                rating = val.get('rating', '')
                print(f"  {val.get('description', key)}: {val.get('formatted', val.get('value'))} {rating}")
        
        trading = metrics.get("trading", {})
        print(f"\n【交易统计】")
        for key, val in trading.items():
            if isinstance(val, dict):
                print(f"  {val.get('description', key)}: {val.get('formatted', val.get('value'))}")
        
        print("\n" + "="*80)
    
    def print_risk_analysis(self, report: dict):
        """Print risk analysis."""
        risk_analysis = report.get("risk_analysis", {})
        
        if not risk_analysis:
            return
        
        print("\n" + "="*80)
        print("风险分析")
        print("="*80)
        
        vol = risk_analysis.get("volatility_analysis", {})
        print(f"\n【波动率分析】")
        print(f"  日波动率: {vol.get('daily_vol', 0) * 100:.2f}%")
        print(f"  年化波动率: {vol.get('annual_vol', 0) * 100:.2f}%")
        
        dd_stats = risk_analysis.get("drawdown_statistics", {})
        print(f"\n【回撤统计】")
        print(f"  最大回撤: {dd_stats.get('max_drawdown', 0) * 100:.2f}%")
        print(f"  平均回撤: {dd_stats.get('avg_drawdown', 0) * 100:.2f}%")
        print(f"  回撤标准差: {dd_stats.get('drawdown_std', 0) * 100:.2f}%")
        
        tail = risk_analysis.get("tail_risk", {})
        print(f"\n【尾部风险】")
        print(f"  偏度: {tail.get('skewness', 0):.2f}")
        print(f"  峰度: {tail.get('kurtosis', 0):.2f}")
        print(f"  尾部比率: {tail.get('tail_ratio', 0):.2f}")
        
        worst = risk_analysis.get("worst_days", {})
        print(f"\n【最差交易日】")
        print(f"  最差1天: {worst.get('worst_1_day', 0) * 100:.2f}%")
        print(f"  最差5%天: {worst.get('worst_5_days', 0) * 100:.2f}%")
        
        best = risk_analysis.get("best_days", {})
        print(f"\n【最佳交易日】")
        print(f"  最佳1天: {best.get('best_1_day', 0) * 100:.2f}%")
        print(f"  最佳5%天: {best.get('best_5_days', 0) * 100:.2f}%")
        
        print("\n" + "="*80)
    
    def print_recommendations(self, report: dict):
        """Print recommendations."""
        recommendations = report.get("recommendations", [])
        
        if not recommendations:
            return
        
        print("\n" + "="*80)
        print("优化建议")
        print("="*80)
        
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. [{rec.get('priority', '中')}] {rec.get('category', '')}")
            print(f"   问题: {rec.get('issue', '')}")
            print(f"   建议: {rec.get('recommendation', '')}")
        
        print("\n" + "="*80)
    
    def save_report(self, report: dict, output_dir: Path | None = None):
        """Save report to file."""
        if output_dir is None:
            output_dir = Path(__file__).parent / "backtest_results"
        
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backtest_report_{timestamp}.json"
        filepath = output_dir / filename
        
        def convert_to_serializable(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            elif hasattr(obj, 'value'):
                return obj.value
            elif isinstance(obj, (np.integer, np.floating)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            else:
                return obj
        
        serializable_report = convert_to_serializable(report)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(serializable_report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n报告已保存: {filepath}")
        
        return filepath
    
    def _get_default_stock_universe(self) -> list[str]:
        """Get default stock universe for backtest."""
        return [
            "600000", "600036", "600519", "600887", "600030",
            "601318", "600276", "600309", "600585", "600660",
            "600886", "601166", "600009", "600104", "600196",
            "600885", "600893", "600900", "601012", "601288",
            "601328", "601398", "601601", "601668", "601688",
            "601728", "601818", "601857", "601888", "601899",
            "000001", "000002", "000063", "000333", "000338",
            "000425", "000568", "000625", "000651", "000661",
            "000703", "000708", "000725", "000768", "000776",
            "000858", "000876", "000895", "000938", "002001",
        ]
    
    async def _get_price_data(
        self,
        stock_codes: list[str],
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Get price data for stocks."""
        logger.info("获取价格数据...")
        
        try:
            from openfinance.datacenter.models.analytical import get_ads_service
            ads_service = get_ads_service()
            
            if ads_service and hasattr(ads_service, 'get_kline_batch'):
                raw_data = await ads_service.get_kline_batch(
                    codes=stock_codes,
                    start_date=start_date,
                    end_date=end_date,
                )
                
                price_data_list = []
                for code, klines in raw_data.items():
                    for k in klines:
                        price_data_list.append({
                            'stock_code': code,
                            'trade_date': k.trade_date,
                            'open': k.open,
                            'high': k.high,
                            'low': k.low,
                            'close': k.close,
                            'volume': k.volume,
                            'amount': k.amount,
                        })
                
                if price_data_list:
                    return pd.DataFrame(price_data_list)
        except Exception as e:
            logger.warning(f"Failed to get price data from ADS: {e}")
        
        logger.info("生成模拟价格数据...")
        return self._generate_mock_price_data(stock_codes, start_date, end_date)
    
    def _generate_mock_price_data(
        self,
        stock_codes: list[str],
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Generate mock price data for testing."""
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
        
        price_data_list = []
        
        for code in stock_codes:
            np.random.seed(hash(code) % 2**32)
            
            n = len(dates)
            returns = np.random.randn(n) * 0.02
            prices = 100 * np.exp(np.cumsum(returns))
            
            for i, date in enumerate(dates):
                price_data_list.append({
                    'stock_code': code,
                    'trade_date': date,
                    'open': prices[i] * (1 + np.random.randn() * 0.005),
                    'high': prices[i] * (1 + abs(np.random.randn() * 0.01)),
                    'low': prices[i] * (1 - abs(np.random.randn() * 0.01)),
                    'close': prices[i],
                    'volume': int(np.random.randint(1000000, 10000000)),
                    'amount': prices[i] * np.random.randint(1000000, 10000000),
                })
        
        return pd.DataFrame(price_data_list)
    
    async def _calculate_factors(
        self,
        price_data: pd.DataFrame,
    ) -> dict[str, list]:
        """Calculate factor values."""
        logger.info("计算因子值...")
        
        from openfinance.quant.factors.indicators import (
            MomentumFactor,
            RelativeStrengthFactor,
            VolumeStrengthFactor,
            TrendStrengthFactor,
        )
        from openfinance.domain.models.quant import FactorValue
        
        factors = [
            MomentumFactor(),
            RelativeStrengthFactor(),
            VolumeStrengthFactor(),
            TrendStrengthFactor(),
        ]
        
        factor_values = {}
        
        for factor in factors:
            logger.info(f"  计算 {factor.name}...")
            
            values_list = []
            
            for code in price_data['stock_code'].unique():
                stock_data = price_data[price_data['stock_code'] == code].sort_values('trade_date')
                
                klines = []
                for _, row in stock_data.iterrows():
                    kline = ADSKLineModel(
                        code=code,
                        trade_date=row['trade_date'],
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=row['volume'],
                        amount=row['amount'],
                        pre_close=row['close'],
                        turnover=0.0,
                    )
                    klines.append(kline)
                
                if len(klines) >= factor.lookback_period:
                    result = factor.calculate(klines)
                    
                    if result and result.value is not None:
                        values_list.append(FactorValue(
                            factor_id=factor.factor_id,
                            stock_code=code,
                            trade_date=result.trade_date,
                            value=result.value,
                            value_normalized=result.value_normalized,
                        ))
            
            factor_values[factor.factor_id] = values_list
            logger.info(f"    完成: {len(values_list)} 条记录")
        
        return factor_values


async def main():
    """Main function to run complete backtest workflow."""
    workflow = StrongStockBacktestWorkflow()
    
    await workflow.initialize()
    
    await workflow.load_strategy("strategy_strong_stock")
    
    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    
    results = await workflow.run_backtest(
        start_date=start_date,
        end_date=end_date,
        initial_capital=1000000.0,
    )
    
    report = results["report"]
    
    workflow.print_executive_summary(report)
    workflow.print_performance_metrics(report)
    workflow.print_risk_analysis(report)
    workflow.print_recommendations(report)
    
    report_path = workflow.save_report(report)
    
    print(f"\n完整报告已保存至: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
