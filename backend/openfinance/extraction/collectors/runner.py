"""
Data collection runner script.

This script runs data collection for all migrated qstock functions
and verifies the data collection process.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from .implementations import (
    MarketRealtimeCollector,
    StockRealtimeCollector,
    KLineCollector,
    IntradayDataCollector,
    StockBillboardCollector,
    IndexMemberCollector,
    InstitutionalRatingCollector,
    Top10HolderCollector,
    MainBusinessCollector,
    FinancialIndicatorCollector,
    StockValuationCollector,
    IntradayMoneyFlowCollector,
    DailyMoneyFlowCollector,
    NorthMoneyCollector,
    SectorMoneyFlowCollector,
    LPRCollector,
    MoneySupplyCollector,
    CPICollector,
    GDPCollector,
    PPICollector,
    PMICollector,
    InterbankRateCollector,
    JinshiNewsCollector,
    CLSNewsCollector,
    CCTVNewsCollector,
    BalanceSheetCollector,
    IncomeStatementCollector,
    CashFlowStatementCollector,
    PerformanceReportCollector,
    PerformanceForecastCollector,
    IndustryMemberCollector,
    ConceptMemberCollector,
    IndustryDataCollector,
    ConceptDataCollector,
)
from .core.base_collector import CollectionConfig, CollectionResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DataCollectionRunner:
    """Runner for data collection tasks."""

    def __init__(self) -> None:
        self.results: list[dict[str, Any]] = []

    async def run_collector(
        self,
        name: str,
        collector: Any,
        **kwargs: Any,
    ) -> CollectionResult:
        """Run a single collector and record results."""
        logger.info(f"Starting collection: {name}")

        try:
            await collector.start()
            result = await collector.collect(**kwargs)
            await collector.stop()

            logger.info(
                f"Completed {name}: {result.records_collected} records, "
                f"status: {result.status.value}"
            )

            self.results.append({
                "name": name,
                "status": result.status.value,
                "records_collected": result.records_collected,
                "duration_seconds": result.duration_seconds,
                "error": result.error_message,
            })

            return result

        except Exception as e:
            logger.exception(f"Failed to run collector {name}: {e}")
            self.results.append({
                "name": name,
                "status": "failed",
                "error": str(e),
            })
            raise

    async def run_market_data_tests(self) -> None:
        """Run market data collection tests."""
        logger.info("=" * 50)
        logger.info("Running Market Data Collection Tests")
        logger.info("=" * 50)

        collector = MarketRealtimeCollector()
        await self.run_collector("Market Realtime (沪深A)", collector, market="沪深A")

        collector = StockRealtimeCollector()
        await self.run_collector(
            "Stock Realtime",
            collector,
            codes=["000001", "600000", "000858"],
        )

        collector = KLineCollector()
        await self.run_collector(
            "K-Line Data",
            collector,
            symbols=["000001"],
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

        collector = IntradayDataCollector()
        await self.run_collector("Intraday Data", collector, code="000001")

        collector = StockBillboardCollector()
        await self.run_collector(
            "Dragon Tiger List",
            collector,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

        collector = IndexMemberCollector()
        await self.run_collector("Index Member", collector, code="000001")

    async def run_fundamental_data_tests(self) -> None:
        """Run fundamental data collection tests."""
        logger.info("=" * 50)
        logger.info("Running Fundamental Data Collection Tests")
        logger.info("=" * 50)

        collector = InstitutionalRatingCollector()
        await self.run_collector("Institutional Rating", collector, code="000001")

        collector = Top10HolderCollector()
        await self.run_collector("Top 10 Holders", collector, code="000001", n=1)

        collector = MainBusinessCollector()
        await self.run_collector("Main Business", collector, code="000001")

        collector = FinancialIndicatorCollector()
        await self.run_collector("Financial Indicators", collector, code="000001")

        collector = StockValuationCollector()
        await self.run_collector("Stock Valuation", collector, code="000001")

    async def run_money_flow_tests(self) -> None:
        """Run money flow data collection tests."""
        logger.info("=" * 50)
        logger.info("Running Money Flow Data Collection Tests")
        logger.info("=" * 50)

        collector = IntradayMoneyFlowCollector()
        await self.run_collector("Intraday Money Flow", collector, code="000001")

        collector = DailyMoneyFlowCollector()
        await self.run_collector("Daily Money Flow", collector, code="000001")

        collector = NorthMoneyCollector()
        await self.run_collector("North Money Flow", collector, flag="北上")

        collector = SectorMoneyFlowCollector()
        await self.run_collector("Sector Money Flow", collector, sector_type="行业")

    async def run_macro_data_tests(self) -> None:
        """Run macro economic data collection tests."""
        logger.info("=" * 50)
        logger.info("Running Macro Economic Data Collection Tests")
        logger.info("=" * 50)

        collector = LPRCollector()
        await self.run_collector("LPR Data", collector)

        collector = MoneySupplyCollector()
        await self.run_collector("Money Supply", collector)

        collector = CPICollector()
        await self.run_collector("CPI Data", collector)

        collector = GDPCollector()
        await self.run_collector("GDP Data", collector)

        collector = PPICollector()
        await self.run_collector("PPI Data", collector)

        collector = PMICollector()
        await self.run_collector("PMI Data", collector)

        collector = InterbankRateCollector()
        await self.run_collector("Interbank Rate", collector, market="sh")

    async def run_news_data_tests(self) -> None:
        """Run news data collection tests."""
        logger.info("=" * 50)
        logger.info("Running News Data Collection Tests")
        logger.info("=" * 50)

        collector = JinshiNewsCollector()
        await self.run_collector("Jinshi News", collector, max_count=50)

        collector = CLSNewsCollector()
        await self.run_collector("CLS News", collector, count=50)

    async def run_report_data_tests(self) -> None:
        """Run financial report data collection tests."""
        logger.info("=" * 50)
        logger.info("Running Financial Report Data Collection Tests")
        logger.info("=" * 50)

        collector = BalanceSheetCollector()
        await self.run_collector("Balance Sheet", collector)

        collector = IncomeStatementCollector()
        await self.run_collector("Income Statement", collector)

        collector = CashFlowStatementCollector()
        await self.run_collector("Cash Flow Statement", collector)

        collector = PerformanceReportCollector()
        await self.run_collector("Performance Report", collector)

        collector = PerformanceForecastCollector()
        await self.run_collector("Performance Forecast", collector)

    async def run_industry_data_tests(self) -> None:
        """Run industry and concept data collection tests."""
        logger.info("=" * 50)
        logger.info("Running Industry/Concept Data Collection Tests")
        logger.info("=" * 50)

        collector = IndustryMemberCollector()
        await self.run_collector("Industry Member", collector, code="半导体")

        collector = ConceptMemberCollector()
        await self.run_collector("Concept Member", collector, code="白酒概念")

        collector = IndustryDataCollector()
        await self.run_collector(
            "Industry Data",
            collector,
            code="半导体",
            start_date="2024-01-01",
        )

        collector = ConceptDataCollector()
        await self.run_collector("Concept Data", collector, code="白酒概念", start_date="2024")

    def generate_report(self) -> str:
        """Generate a summary report of all collection results."""
        total = len(self.results)
        successful = sum(1 for r in self.results if r["status"] == "completed")
        failed = total - successful

        total_records = sum(r.get("records_collected", 0) for r in self.results)

        report = f"""
========================================
Data Collection Summary Report
========================================
Total Tasks: {total}
Successful: {successful}
Failed: {failed}
Total Records Collected: {total_records}
========================================
Detailed Results:
"""

        for result in self.results:
            status_icon = "✓" if result["status"] == "completed" else "✗"
            report += f"\n{status_icon} {result['name']}: "
            if result["status"] == "completed":
                report += f"{result.get('records_collected', 0)} records"
                if result.get("duration_seconds"):
                    report += f" ({result['duration_seconds']:.2f}s)"
            else:
                report += f"FAILED - {result.get('error', 'Unknown error')}"

        return report


async def run_all_tests() -> str:
    """Run all data collection tests and return a report."""
    runner = DataCollectionRunner()

    try:
        await runner.run_market_data_tests()
    except Exception as e:
        logger.error(f"Market data tests failed: {e}")

    try:
        await runner.run_fundamental_data_tests()
    except Exception as e:
        logger.error(f"Fundamental data tests failed: {e}")

    try:
        await runner.run_money_flow_tests()
    except Exception as e:
        logger.error(f"Money flow tests failed: {e}")

    try:
        await runner.run_macro_data_tests()
    except Exception as e:
        logger.error(f"Macro data tests failed: {e}")

    try:
        await runner.run_news_data_tests()
    except Exception as e:
        logger.error(f"News data tests failed: {e}")

    try:
        await runner.run_report_data_tests()
    except Exception as e:
        logger.error(f"Report data tests failed: {e}")

    try:
        await runner.run_industry_data_tests()
    except Exception as e:
        logger.error(f"Industry data tests failed: {e}")

    return runner.generate_report()


async def run_quick_test() -> str:
    """Run a quick test with a subset of collectors."""
    runner = DataCollectionRunner()

    logger.info("Running Quick Data Collection Test...")

    try:
        collector = MarketRealtimeCollector()
        await runner.run_collector("Market Realtime", collector, market="沪深A")
    except Exception as e:
        logger.error(f"Market realtime test failed: {e}")

    try:
        collector = KLineCollector()
        await runner.run_collector(
            "K-Line Data",
            collector,
            symbols=["000001"],
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
    except Exception as e:
        logger.error(f"K-Line test failed: {e}")

    try:
        collector = CLSNewsCollector()
        await runner.run_collector("CLS News", collector, count=20)
    except Exception as e:
        logger.error(f"CLS news test failed: {e}")

    try:
        collector = CPICollector()
        await runner.run_collector("CPI Data", collector)
    except Exception as e:
        logger.error(f"CPI test failed: {e}")

    return runner.generate_report()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        report = asyncio.run(run_quick_test())
    else:
        report = asyncio.run(run_all_tests())

    print(report)
