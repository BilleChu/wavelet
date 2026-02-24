"""
OpenFinance 自动化测试套件

执行方式:
    pytest tests/test_full_suite.py -v --tb=short
    pytest tests/test_full_suite.py -v -k "test_datacenter"  # 只运行数据中心测试
"""

import asyncio
import pytest
from datetime import date, timedelta
from typing import Any

import asyncpg


# ============================================================================
# 配置
# ============================================================================

DATABASE_URL = "postgresql://openfinance:openfinance@localhost:5432/openfinance"
API_BASE_URL = "http://localhost:8000"


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_connection():
    conn = await asyncpg.connect(DATABASE_URL)
    yield conn
    await conn.close()


# ============================================================================
# 第一部分：数据中心测试
# ============================================================================

class TestDataCenter:
    """数据中心测试类"""
    
    @pytest.mark.asyncio
    async def test_stock_daily_quote_count(self, db_connection):
        """TC-DC-002: 验证股票日线行情数据量"""
        count = await db_connection.fetchval(
            "SELECT COUNT(*) FROM openfinance.stock_daily_quote"
        )
        assert count > 2_000_000, f"股票行情数据量不足: {count}"
    
    @pytest.mark.asyncio
    async def test_stock_daily_quote_stocks(self, db_connection):
        """TC-DC-002: 验证股票数量"""
        count = await db_connection.fetchval(
            "SELECT COUNT(DISTINCT code) FROM openfinance.stock_daily_quote"
        )
        assert count > 5000, f"股票数量不足: {count}"
    
    @pytest.mark.asyncio
    async def test_stock_daily_quote_date_range(self, db_connection):
        """TC-DC-002: 验证日期范围"""
        min_date = await db_connection.fetchval(
            "SELECT MIN(trade_date) FROM openfinance.stock_daily_quote"
        )
        max_date = await db_connection.fetchval(
            "SELECT MAX(trade_date) FROM openfinance.stock_daily_quote"
        )
        assert min_date is not None, "没有数据"
        assert max_date is not None, "没有数据"
        
        days = (max_date - min_date).days
        assert days >= 365, f"数据日期范围不足一年: {days} 天"
    
    @pytest.mark.asyncio
    async def test_stock_basic_count(self, db_connection):
        """TC-DC-001: 验证股票基础信息数量"""
        count = await db_connection.fetchval(
            "SELECT COUNT(*) FROM openfinance.stock_basic"
        )
        assert count > 5000, f"股票基础信息数量不足: {count}"
    
    @pytest.mark.asyncio
    async def test_data_completeness(self, db_connection):
        """TC-DS-001: 验证数据完整性"""
        latest_date = await db_connection.fetchval(
            "SELECT MAX(trade_date) FROM openfinance.stock_daily_quote"
        )
        count = await db_connection.fetchval(
            "SELECT COUNT(DISTINCT code) FROM openfinance.stock_daily_quote WHERE trade_date = $1",
            latest_date
        )
        assert count > 5000, f"最新交易日 {latest_date} 数据不完整: {count} 只股票"


class TestTradingCalendar:
    """交易日历测试类"""
    
    @pytest.mark.asyncio
    async def test_trading_day_detection(self):
        """TC-TC-001: 验证交易日判断"""
        from openfinance.datacenter.task.trading_calendar import trading_calendar
        
        weekend = date(2026, 2, 21)  # 周六
        weekday = date(2026, 2, 20)  # 周五（春节假期）
        trading_day = date(2026, 2, 13)  # 交易日
        
        assert trading_calendar.is_trading_day(weekend) == False, "周末应该不是交易日"
        assert trading_calendar.is_trading_day(weekday) == False, "春节假期应该不是交易日"
        assert trading_calendar.is_trading_day(trading_day) == True, "应该是交易日"
    
    @pytest.mark.asyncio
    async def test_get_latest_trading_day(self):
        """TC-TC-004: 验证获取最近交易日"""
        from openfinance.datacenter.task.trading_calendar import get_latest_trading_day
        
        latest = get_latest_trading_day()
        assert latest is not None, "应该返回最近交易日"
        assert latest <= date.today(), "最近交易日不应晚于今天"


# ============================================================================
# 第二部分：因子计算测试
# ============================================================================

class TestFactorCalculation:
    """因子计算测试类"""
    
    @pytest.mark.asyncio
    async def test_factor_data_count(self, db_connection):
        """TC-FC-008: 验证因子数据量"""
        count = await db_connection.fetchval(
            "SELECT COUNT(*) FROM openfinance.factor_data"
        )
        assert count > 50000, f"因子数据量不足: {count}"
    
    @pytest.mark.asyncio
    async def test_factor_count(self, db_connection):
        """TC-FC-008: 验证因子数量"""
        count = await db_connection.fetchval(
            "SELECT COUNT(DISTINCT factor_id) FROM openfinance.factor_data"
        )
        assert count >= 14, f"因子数量不足: {count}"
    
    @pytest.mark.asyncio
    async def test_factor_stocks(self, db_connection):
        """TC-FC-008: 验证因子覆盖股票数"""
        count = await db_connection.fetchval(
            "SELECT COUNT(DISTINCT code) FROM openfinance.factor_data"
        )
        assert count > 5000, f"因子覆盖股票数不足: {count}"
    
    @pytest.mark.asyncio
    async def test_factor_registry(self):
        """TC-FA-001: 验证因子注册表"""
        from openfinance.quant.factors.registry import get_factor_registry
        
        registry = get_factor_registry()
        factors = registry.list_factors(include_builtin=True)
        
        assert len(factors) >= 14, f"注册因子数量不足: {len(factors)}"
    
    @pytest.mark.asyncio
    async def test_factor_instance_creation(self):
        """TC-FA-003: 验证因子实例创建"""
        from openfinance.quant.factors.registry import get_factor_registry
        
        registry = get_factor_registry()
        
        test_factors = ["factor_momentum", "factor_rsi", "factor_macd", "factor_kdj"]
        for factor_id in test_factors:
            factor = registry.get(factor_id)
            assert factor is not None, f"因子 {factor_id} 未找到"
    
    @pytest.mark.asyncio
    async def test_factor_data_query(self):
        """TC-FQ-001: 验证因子数据查询"""
        from openfinance.quant.factors.storage.database import get_factor_storage
        
        storage = await get_factor_storage()
        
        results = await storage.load_factor_data(
            factor_id="factor_momentum",
            codes=["000001"],
            start_date=date.today() - timedelta(days=365),
            end_date=date.today(),
        )
        
        assert len(results) > 0, "应该返回因子数据"
    
    @pytest.mark.asyncio
    async def test_factor_latest_values(self):
        """TC-FQ-002: 验证获取最新因子值"""
        from openfinance.quant.factors.storage.database import get_factor_storage
        
        storage = await get_factor_storage()
        
        latest = await storage.get_latest_factor_values("factor_momentum")
        
        assert len(latest) > 5000, f"最新因子值数量不足: {len(latest)}"


class TestFactorIndicators:
    """技术指标因子测试类"""
    
    @pytest.mark.asyncio
    async def test_rsi_calculation(self):
        """TC-FC-003: 验证 RSI 因子计算"""
        from openfinance.quant.factors.registry import get_factor_registry
        from openfinance.datacenter.models.analytical import ADSKLineModel
        import random
        
        registry = get_factor_registry()
        factor = registry.get_factor_instance("factor_rsi")
        
        assert factor is not None, "RSI 因子未注册"
        
        klines = []
        base_price = 10.0
        for i in range(30):
            klines.append(ADSKLineModel(
                code="000001",
                trade_date=date.today() - timedelta(days=30-i),
                open=base_price,
                high=base_price * 1.02,
                low=base_price * 0.98,
                close=base_price * (1 + random.uniform(-0.02, 0.02)),
                volume=1000000,
                amount=10000000,
            ))
        
        result = factor.calculate(klines)
        assert result is not None, "RSI 计算结果不应为空"
        assert 0 <= result.value <= 100, f"RSI 值应在 0-100 之间: {result.value}"
    
    @pytest.mark.asyncio
    async def test_macd_calculation(self):
        """TC-FC-004: 验证 MACD 因子计算"""
        from openfinance.quant.factors.registry import get_factor_registry
        from openfinance.datacenter.models.analytical import ADSKLineModel
        import random
        
        registry = get_factor_registry()
        factor = registry.get_factor_instance("factor_macd")
        
        assert factor is not None, "MACD 因子未注册"
        
        klines = []
        base_price = 10.0
        for i in range(35):
            klines.append(ADSKLineModel(
                code="000001",
                trade_date=date.today() - timedelta(days=35-i),
                open=base_price,
                high=base_price * 1.02,
                low=base_price * 0.98,
                close=base_price * (1 + random.uniform(-0.02, 0.02)),
                volume=1000000,
                amount=10000000,
            ))
        
        result = factor.calculate(klines)
        assert result is not None, "MACD 计算结果不应为空"


# ============================================================================
# 第三部分：策略测试
# ============================================================================

class TestStrategy:
    """策略测试类"""
    
    @pytest.mark.asyncio
    async def test_strategy_registry(self):
        """TC-SA-001: 验证策略注册表"""
        from openfinance.quant.strategy.registry import get_strategy_registry
        
        registry = get_strategy_registry()
        strategies = registry.list_all()
        
        assert len(strategies) > 0, "应该有注册的策略"
    
    @pytest.mark.asyncio
    async def test_strategy_info(self):
        """TC-SA-003: 验证策略信息获取"""
        from openfinance.quant.strategy.registry import get_strategy_registry
        
        registry = get_strategy_registry()
        strategies = registry.list_all()
        
        if strategies:
            info = registry.get_info(strategies[0])
            assert info is not None, "应该返回策略信息"
            assert info.name, "策略应该有名称"


# ============================================================================
# 第四部分：知识图谱测试
# ============================================================================

class TestKnowledgeGraph:
    """知识图谱测试类"""
    
    @pytest.mark.asyncio
    async def test_entity_count(self, db_connection):
        """TC-KG-001: 验证实体数量"""
        count = await db_connection.fetchval(
            "SELECT COUNT(*) FROM openfinance.entities"
        )
        assert count > 0, "应该有实体数据"
    
    @pytest.mark.asyncio
    async def test_entity_types(self, db_connection):
        """TC-KG-002: 验证实体类型"""
        types = await db_connection.fetch(
            "SELECT DISTINCT entity_type FROM openfinance.entities"
        )
        type_list = [t["entity_type"] for t in types]
        
        assert len(type_list) > 0, "应该有多种实体类型"
    
    @pytest.mark.asyncio
    async def test_relation_count(self, db_connection):
        """TC-MH-001: 验证关系数量"""
        count = await db_connection.fetchval(
            "SELECT COUNT(*) FROM openfinance.relations"
        )
        assert count > 0, "应该有关系数据"


# ============================================================================
# 第五部分：API 端点测试
# ============================================================================

class TestAPIEndpoints:
    """API 端点测试类"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """验证健康检查端点"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/api/health")
            assert response.status_code == 200, f"健康检查失败: {response.status_code}"
    
    @pytest.mark.asyncio
    async def test_factors_list_endpoint(self):
        """TC-FA-001: 验证因子列表端点"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/api/factors/list")
            assert response.status_code == 200, f"因子列表端点失败: {response.status_code}"
            
            data = response.json()
            assert "factors" in data or "total" in data, "响应格式不正确"
    
    @pytest.mark.asyncio
    async def test_factors_registry_endpoint(self):
        """TC-FA-002: 验证因子注册表端点"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/api/factors/registry")
            assert response.status_code == 200, f"因子注册表端点失败: {response.status_code}"
    
    @pytest.mark.asyncio
    async def test_strategies_list_endpoint(self):
        """TC-SA-001: 验证策略列表端点"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/api/strategies/list")
            assert response.status_code == 200, f"策略列表端点失败: {response.status_code}"
    
    @pytest.mark.asyncio
    async def test_graph_entities_endpoint(self):
        """TC-KG-001: 验证图谱实体端点"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/api/graph/entities")
            assert response.status_code in [200, 404], f"图谱实体端点失败: {response.status_code}"
    
    @pytest.mark.asyncio
    async def test_pipeline_dags_endpoint(self):
        """TC-PL-001: 验证 DAG 列表端点"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/api/pipeline/dags")
            assert response.status_code == 200, f"DAG 列表端点失败: {response.status_code}"


# ============================================================================
# 第六部分：性能测试
# ============================================================================

class TestPerformance:
    """性能测试类"""
    
    @pytest.mark.asyncio
    async def test_factor_query_performance(self):
        """验证因子查询性能"""
        import time
        from openfinance.quant.factors.storage.database import get_factor_storage
        
        storage = await get_factor_storage()
        
        start = time.time()
        results = await storage.load_factor_data(
            factor_id="factor_momentum",
            start_date=date.today() - timedelta(days=365),
            end_date=date.today(),
            limit=1000,
        )
        elapsed = time.time() - start
        
        assert elapsed < 1.0, f"因子查询耗时过长: {elapsed:.2f}s"
    
    @pytest.mark.asyncio
    async def test_latest_factor_values_performance(self):
        """验证获取最新因子值性能"""
        import time
        from openfinance.quant.factors.storage.database import get_factor_storage
        
        storage = await get_factor_storage()
        
        start = time.time()
        latest = await storage.get_latest_factor_values("factor_momentum")
        elapsed = time.time() - start
        
        assert elapsed < 0.5, f"获取最新因子值耗时过长: {elapsed:.2f}s"


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
