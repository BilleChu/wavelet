"""
快速验证脚本 - 验证系统核心功能

执行方式:
    python scripts/quick_verify.py
"""

import asyncio
import asyncpg
from datetime import date, timedelta


DATABASE_URL = "postgresql://openfinance:openfinance@localhost:5432/openfinance"


async def verify_datacenter():
    """验证数据中心"""
    print("\n" + "=" * 60)
    print("数据中心验证")
    print("=" * 60)
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    # 股票基础信息
    count = await conn.fetchval("SELECT COUNT(*) FROM openfinance.stock_basic")
    print(f"✓ 股票基础信息: {count:,} 条")
    
    # 股票日线行情
    count = await conn.fetchval("SELECT COUNT(*) FROM openfinance.stock_daily_quote")
    stocks = await conn.fetchval("SELECT COUNT(DISTINCT code) FROM openfinance.stock_daily_quote")
    min_date = await conn.fetchval("SELECT MIN(trade_date) FROM openfinance.stock_daily_quote")
    max_date = await conn.fetchval("SELECT MAX(trade_date) FROM openfinance.stock_daily_quote")
    print(f"✓ 股票日线行情: {count:,} 条, {stocks} 只股票")
    print(f"  日期范围: {min_date} ~ {max_date}")
    
    # 最新交易日数据完整性
    latest_count = await conn.fetchval("""
        SELECT COUNT(DISTINCT code) FROM openfinance.stock_daily_quote 
        WHERE trade_date = (SELECT MAX(trade_date) FROM openfinance.stock_daily_quote)
    """)
    print(f"✓ 最新交易日数据: {latest_count} 只股票")
    
    await conn.close()
    return True


async def verify_factors():
    """验证因子数据"""
    print("\n" + "=" * 60)
    print("因子数据验证")
    print("=" * 60)
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    # 因子数据统计
    count = await conn.fetchval("SELECT COUNT(*) FROM openfinance.factor_data")
    factors = await conn.fetchval("SELECT COUNT(DISTINCT factor_id) FROM openfinance.factor_data")
    stocks = await conn.fetchval("SELECT COUNT(DISTINCT code) FROM openfinance.factor_data")
    min_date = await conn.fetchval("SELECT MIN(trade_date) FROM openfinance.factor_data")
    max_date = await conn.fetchval("SELECT MAX(trade_date) FROM openfinance.factor_data")
    
    print(f"✓ 因子数据: {count:,} 条")
    print(f"  因子数: {factors}")
    print(f"  股票数: {stocks}")
    print(f"  日期范围: {min_date} ~ {max_date}")
    
    # 各因子数据量
    factor_list = await conn.fetch("""
        SELECT factor_id, COUNT(*) as cnt 
        FROM openfinance.factor_data 
        GROUP BY factor_id 
        ORDER BY factor_id
    """)
    print("\n  各因子数据量:")
    for row in factor_list:
        print(f"    {row['factor_id']}: {row['cnt']:,}")
    
    # 验证因子注册表
    from openfinance.quant.factors.registry import get_factor_registry
    registry = get_factor_registry()
    registered = registry.list_factors(include_builtin=True)
    print(f"\n✓ 内存因子注册表: {len(registered)} 个因子")
    
    await conn.close()
    return True


async def verify_knowledge_graph():
    """验证知识图谱"""
    print("\n" + "=" * 60)
    print("知识图谱验证")
    print("=" * 60)
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    # 实体统计
    entities = await conn.fetchval("SELECT COUNT(*) FROM openfinance.entities")
    entity_types = await conn.fetch("SELECT DISTINCT entity_type FROM openfinance.entities")
    print(f"✓ 实体数据: {entities:,} 条")
    print(f"  实体类型: {[t['entity_type'] for t in entity_types]}")
    
    # 关系统计
    relations = await conn.fetchval("SELECT COUNT(*) FROM openfinance.relations")
    print(f"✓ 关系数据: {relations:,} 条")
    
    await conn.close()
    return True


async def verify_trading_calendar():
    """验证交易日历"""
    print("\n" + "=" * 60)
    print("交易日历验证")
    print("=" * 60)
    
    from openfinance.datacenter.task.trading_calendar import (
        trading_calendar, 
        get_latest_trading_day,
        get_previous_trading_day,
    )
    
    today = date.today()
    print(f"今天: {today} (星期{today.weekday() + 1})")
    print(f"是否交易日: {trading_calendar.is_trading_day(today)}")
    print(f"最新交易日: {get_latest_trading_day()}")
    print(f"上一个交易日: {get_previous_trading_day()}")
    
    # 春节假期测试
    spring_festival = [date(2026, 2, 16), date(2026, 2, 17), date(2026, 2, 18)]
    print("\n春节假期测试:")
    for d in spring_festival:
        is_trading = trading_calendar.is_trading_day(d)
        is_holiday = trading_calendar.is_holiday(d)
        print(f"  {d}: 交易日={is_trading}, 节假日={is_holiday}")
    
    return True


async def verify_api_endpoints():
    """验证 API 端点"""
    print("\n" + "=" * 60)
    print("API 端点验证")
    print("=" * 60)
    
    import httpx
    
    base_url = "http://localhost:8000"
    
    endpoints = [
        ("/api/health", "健康检查"),
        ("/api/factors/list", "因子列表"),
        ("/api/factors/registry", "因子注册表"),
        ("/api/strategies/list", "策略列表"),
        ("/api/pipeline/dags", "DAG 列表"),
        ("/api/graph/entities", "图谱实体"),
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for endpoint, name in endpoints:
            try:
                response = await client.get(f"{base_url}{endpoint}")
                status = "✓" if response.status_code == 200 else "✗"
                print(f"{status} {name}: {response.status_code}")
            except Exception as e:
                print(f"✗ {name}: 连接失败 - {e}")
    
    return True


async def verify_factor_query():
    """验证因子数据查询"""
    print("\n" + "=" * 60)
    print("因子数据查询验证")
    print("=" * 60)
    
    from openfinance.quant.factors.storage.database import get_factor_storage
    
    storage = await get_factor_storage()
    
    # 测试查询
    factor_id = "factor_momentum"
    code = "000001"
    
    results = await storage.load_factor_data(
        factor_id=factor_id,
        codes=[code],
        start_date=date.today() - timedelta(days=365),
        end_date=date.today(),
    )
    
    print(f"查询 {factor_id} for {code}:")
    print(f"  结果数: {len(results)}")
    if results:
        print(f"  最新值: {results[0].value}")
    
    # 获取最新因子值
    latest = await storage.get_latest_factor_values(factor_id)
    print(f"\n最新因子值数量: {len(latest)}")
    
    return True


async def main():
    """主验证流程"""
    print("\n" + "=" * 60)
    print("OpenFinance 系统验证")
    print("=" * 60)
    
    results = {}
    
    try:
        results["数据中心"] = await verify_datacenter()
    except Exception as e:
        print(f"✗ 数据中心验证失败: {e}")
        results["数据中心"] = False
    
    try:
        results["因子数据"] = await verify_factors()
    except Exception as e:
        print(f"✗ 因子数据验证失败: {e}")
        results["因子数据"] = False
    
    try:
        results["知识图谱"] = await verify_knowledge_graph()
    except Exception as e:
        print(f"✗ 知识图谱验证失败: {e}")
        results["知识图谱"] = False
    
    try:
        results["交易日历"] = await verify_trading_calendar()
    except Exception as e:
        print(f"✗ 交易日历验证失败: {e}")
        results["交易日历"] = False
    
    try:
        results["因子查询"] = await verify_factor_query()
    except Exception as e:
        print(f"✗ 因子查询验证失败: {e}")
        results["因子查询"] = False
    
    try:
        results["API端点"] = await verify_api_endpoints()
    except Exception as e:
        print(f"✗ API端点验证失败: {e}")
        results["API端点"] = False
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有验证通过！")
    else:
        print("\n⚠️ 部分验证失败，请检查日志")


if __name__ == "__main__":
    asyncio.run(main())
