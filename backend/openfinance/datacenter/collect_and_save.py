#!/usr/bin/env python
"""
Complete Data Collection and Persistence Script.

Collects data from various sources and saves to database.
"""

import asyncio
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def collect_and_save_all():
    """Collect all data and save to database."""
    from openfinance.datacenter.persistence import persistence
    from openfinance.datacenter.collector.implementations.market_collectors import (
        MarketRealtimeCollector,
        KLineCollector,
        StockRealtimeCollector,
    )
    from openfinance.datacenter.collector.implementations.fundamental_collectors import (
        FinancialIndicatorCollector,
        StockValuationCollector,
    )
    from openfinance.datacenter.collector.implementations.money_flow_collectors import (
        DailyMoneyFlowCollector,
        NorthMoneyCollector,
    )
    from openfinance.datacenter.collector.implementations.macro_collectors import (
        CPICollector,
        GDPCollector,
        PMICollector,
        LPRCollector,
    )
    from openfinance.datacenter.collector.implementations.news_collectors import (
        CLSNewsCollector,
        JinshiNewsCollector,
    )
    
    results = {}
    
    # 1. Collect Market Realtime Data
    logger.info("=" * 50)
    logger.info("Collecting Market Realtime Data...")
    try:
        collector = MarketRealtimeCollector()
        await collector.start()
        result = await collector.collect(market="沪深A")
        await collector.stop()
        
        if result.data:
            saved = await persistence.save_stock_quotes(result.data)
            results["market_realtime"] = {"collected": result.records_collected, "saved": saved}
            logger.info(f"Market Realtime: {result.records_collected} collected, {saved} saved")
    except Exception as e:
        logger.error(f"Market realtime collection failed: {e}")
        results["market_realtime"] = {"error": str(e)}
    
    # 2. Collect K-Line Data for major stocks
    logger.info("=" * 50)
    logger.info("Collecting K-Line Data...")
    try:
        codes = ["000001", "600000", "600519", "000858", "002594", "300750", 
                 "601398", "601288", "600036", "601318"]
        
        total_collected = 0
        total_saved = 0
        
        for code in codes:
            try:
                collector = KLineCollector()
                await collector.start()
                result = await collector.collect(
                    symbols=[code],
                    start_date=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
                    end_date=datetime.now().strftime("%Y-%m-%d"),
                )
                await collector.stop()
                
                if result.data:
                    saved = await persistence.save_stock_quotes(result.data)
                    total_collected += result.records_collected
                    total_saved += saved
            except Exception as e:
                logger.warning(f"K-Line for {code} failed: {e}")
        
        results["kline"] = {"collected": total_collected, "saved": total_saved}
        logger.info(f"K-Line: {total_collected} collected, {total_saved} saved")
    except Exception as e:
        logger.error(f"K-Line collection failed: {e}")
        results["kline"] = {"error": str(e)}
    
    # 3. Collect Financial Indicators
    logger.info("=" * 50)
    logger.info("Collecting Financial Indicators...")
    try:
        codes = ["000001", "600000", "600519", "000858", "002594"]
        total_saved = 0
        
        for code in codes:
            try:
                collector = FinancialIndicatorCollector()
                await collector.start()
                result = await collector.collect(code=code)
                await collector.stop()
                
                if result.data:
                    saved = await persistence.save_financial_indicator(result.data)
                    total_saved += saved
            except Exception as e:
                logger.warning(f"Financial indicator for {code} failed: {e}")
        
        results["financial_indicator"] = {"saved": total_saved}
        logger.info(f"Financial Indicators: {total_saved} saved")
    except Exception as e:
        logger.error(f"Financial indicator collection failed: {e}")
        results["financial_indicator"] = {"error": str(e)}
    
    # 4. Collect Money Flow Data
    logger.info("=" * 50)
    logger.info("Collecting Money Flow Data...")
    try:
        collector = DailyMoneyFlowCollector()
        await collector.start()
        result = await collector.collect(code="000001")
        await collector.stop()
        
        if result.data:
            saved = await persistence.save_money_flow(result.data)
            results["money_flow"] = {"collected": result.records_collected, "saved": saved}
            logger.info(f"Money Flow: {result.records_collected} collected, {saved} saved")
    except Exception as e:
        logger.error(f"Money flow collection failed: {e}")
        results["money_flow"] = {"error": str(e)}
    
    # 5. Collect North Money Flow
    logger.info("=" * 50)
    logger.info("Collecting North Money Flow...")
    try:
        collector = NorthMoneyCollector()
        await collector.start()
        result = await collector.collect(flag="北上")
        await collector.stop()
        
        results["north_money"] = {"collected": result.records_collected}
        logger.info(f"North Money: {result.records_collected} collected")
    except Exception as e:
        logger.error(f"North money collection failed: {e}")
        results["north_money"] = {"error": str(e)}
    
    # 6. Collect Macro Economic Data
    logger.info("=" * 50)
    logger.info("Collecting Macro Economic Data...")
    try:
        # CPI
        collector = CPICollector()
        await collector.start()
        cpi_result = await collector.collect()
        await collector.stop()
        
        if cpi_result.data:
            await persistence.save_macro_data(cpi_result.data)
        
        # GDP
        collector = GDPCollector()
        await collector.start()
        gdp_result = await collector.collect()
        await collector.stop()
        
        if gdp_result.data:
            await persistence.save_macro_data(gdp_result.data)
        
        # PMI
        collector = PMICollector()
        await collector.start()
        pmi_result = await collector.collect()
        await collector.stop()
        
        if pmi_result.data:
            await persistence.save_macro_data(pmi_result.data)
        
        # LPR
        collector = LPRCollector()
        await collector.start()
        lpr_result = await collector.collect()
        await collector.stop()
        
        if lpr_result.data:
            await persistence.save_macro_data(lpr_result.data)
        
        total = cpi_result.records_collected + gdp_result.records_collected + pmi_result.records_collected + lpr_result.records_collected
        results["macro"] = {"collected": total}
        logger.info(f"Macro Economic: {total} collected")
    except Exception as e:
        logger.error(f"Macro collection failed: {e}")
        results["macro"] = {"error": str(e)}
    
    # 7. Collect News Data
    logger.info("=" * 50)
    logger.info("Collecting News Data...")
    try:
        # CLS News
        collector = CLSNewsCollector()
        await collector.start()
        cls_result = await collector.collect(count=100)
        await collector.stop()
        
        if cls_result.data:
            await persistence.save_news(cls_result.data)
        
        # Jinshi News
        collector = JinshiNewsCollector()
        await collector.start()
        jinshi_result = await collector.collect(max_count=100)
        await collector.stop()
        
        if jinshi_result.data:
            await persistence.save_news(jinshi_result.data)
        
        total = cls_result.records_collected + jinshi_result.records_collected
        results["news"] = {"collected": total}
        logger.info(f"News: {total} collected")
    except Exception as e:
        logger.error(f"News collection failed: {e}")
        results["news"] = {"error": str(e)}
    
    # Get final stats
    logger.info("=" * 50)
    logger.info("Getting Database Statistics...")
    stats = await persistence.get_stats()
    
    return {
        "collection_results": results,
        "database_stats": stats,
    }


async def main():
    """Main entry point."""
    logger.info("Starting Complete Data Collection...")
    start_time = datetime.now()
    
    try:
        result = await collect_and_save_all()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print("DATA COLLECTION SUMMARY")
        print("=" * 60)
        
        print("\nCollection Results:")
        for key, value in result["collection_results"].items():
            if "error" in value:
                print(f"  ❌ {key}: {value['error']}")
            else:
                collected = value.get("collected", 0)
                saved = value.get("saved", 0)
                print(f"  ✓ {key}: {collected} collected, {saved} saved")
        
        print("\nDatabase Statistics:")
        for table, count in result["database_stats"].items():
            print(f"  {table}: {count} records")
        
        print(f"\nTotal Duration: {duration:.2f} seconds")
        print("=" * 60)
        
    except Exception as e:
        logger.exception(f"Data collection failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
