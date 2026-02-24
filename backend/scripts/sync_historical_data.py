#!/usr/bin/env python3
"""
历史数据同步脚本 - 同步2年交易数据

使用方法:
    python scripts/sync_historical_data.py [--days 730] [--batch-size 50]
"""

import asyncio
import argparse
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


async def sync_stock_basic():
    from openfinance.datacenter.task.executors import register_all_executors
    from openfinance.datacenter.task.registry import TaskRegistry, TaskProgress
    import uuid
    
    register_all_executors()
    
    executor = TaskRegistry.get_executor("stock_basic_info")
    if not executor:
        logger.error("stock_basic_info executor not found")
        return 0
    
    progress = TaskProgress(task_id=str(uuid.uuid4()))
    result = await executor.execute({"market": "沪深A"}, progress)
    
    logger.info(f"Stock basic sync result: {result}")
    return result.get("records_saved", 0)


async def sync_daily_quotes(days: int = 730, batch_size: int = 50):
    from openfinance.datacenter.task.executors import register_all_executors
    from openfinance.datacenter.task.registry import TaskRegistry, TaskProgress
    import uuid
    
    register_all_executors()
    
    executor = TaskRegistry.get_executor("stock_daily_quote")
    if not executor:
        logger.error("stock_daily_quote executor not found")
        return 0
    
    progress = TaskProgress(task_id=str(uuid.uuid4()))
    
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"Syncing daily quotes from {start_date} to {end_date}")
    
    result = await executor.execute({"days": days}, progress)
    
    logger.info(f"Daily quotes sync result: {result}")
    return result.get("records_saved", 0)


async def sync_index_quotes(days: int = 730):
    from openfinance.datacenter.task.executors import register_all_executors
    from openfinance.datacenter.task.registry import TaskRegistry, TaskProgress
    import uuid
    
    register_all_executors()
    
    executor = TaskRegistry.get_executor("index_daily_quote")
    if not executor:
        logger.error("index_daily_quote executor not found")
        return 0
    
    progress = TaskProgress(task_id=str(uuid.uuid4()))
    
    codes = ["000001", "399001", "399006", "000300", "000905", "000016"]
    
    result = await executor.execute({"codes": codes, "days": days}, progress)
    
    logger.info(f"Index quotes sync result: {result}")
    return result.get("records_saved", 0)


async def sync_north_money():
    from openfinance.datacenter.task.executors import register_all_executors
    from openfinance.datacenter.task.registry import TaskRegistry, TaskProgress
    import uuid
    
    register_all_executors()
    
    executor = TaskRegistry.get_executor("north_money")
    if not executor:
        logger.error("north_money executor not found")
        return 0
    
    progress = TaskProgress(task_id=str(uuid.uuid4()))
    result = await executor.execute({}, progress)
    
    logger.info(f"North money sync result: {result}")
    return result.get("records_saved", 0)


async def sync_knowledge_graph():
    from openfinance.datacenter.task.executors import register_all_executors
    from openfinance.datacenter.task.registry import TaskRegistry, TaskProgress
    import uuid
    
    register_all_executors()
    
    executor = TaskRegistry.get_executor("sync_stock_entities")
    if not executor:
        logger.error("sync_stock_entities executor not found")
        return 0
    
    progress = TaskProgress(task_id=str(uuid.uuid4()))
    result = await executor.execute({"batch_size": 500}, progress)
    
    logger.info(f"Knowledge graph sync result: {result}")
    return result.get("records_saved", 0)


async def main(days: int = 730, batch_size: int = 50):
    logger.info("=" * 60)
    logger.info("Starting Historical Data Sync")
    logger.info(f"Days: {days}, Batch Size: {batch_size}")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    try:
        logger.info("\n[1/5] Syncing stock basic info...")
        count = await sync_stock_basic()
        logger.info(f"      Saved {count} records")
        
        logger.info("\n[2/5] Syncing index quotes...")
        count = await sync_index_quotes(days)
        logger.info(f"      Saved {count} records")
        
        logger.info("\n[3/5] Syncing daily quotes (this may take a while)...")
        count = await sync_daily_quotes(days, batch_size)
        logger.info(f"      Saved {count} records")
        
        logger.info("\n[4/5] Syncing north money...")
        count = await sync_north_money()
        logger.info(f"      Saved {count} records")
        
        logger.info("\n[5/5] Syncing knowledge graph...")
        count = await sync_knowledge_graph()
        logger.info(f"      Saved {count} records")
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise
    
    duration = (datetime.now() - start_time).total_seconds()
    logger.info("\n" + "=" * 60)
    logger.info(f"Historical Data Sync Completed in {duration:.1f} seconds")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync historical trading data")
    parser.add_argument("--days", type=int, default=730, help="Number of days to sync (default: 730 = 2 years)")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for API calls (default: 50)")
    
    args = parser.parse_args()
    
    asyncio.run(main(days=args.days, batch_size=args.batch_size))
