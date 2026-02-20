"""
Analysis API routes for OpenFinance.

Provides endpoints for the intelligent analysis canvas.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from openfinance.models.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    CanvasData,
    CompanyFinancial,
    CompanyPanelData,
    ConfidenceLevel,
    DataPoint,
    DataSource,
    MacroIndicator,
    MacroPanelData,
    PolicyItem,
    PolicyPanelData,
    TechIndicator,
    TechPanelData,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _generate_mock_macro_data() -> MacroPanelData:
    """Generate mock macro economic data."""
    now = datetime.now()

    indicators = [
        MacroIndicator(
            code="GDP",
            name="国内生产总值",
            name_en="GDP",
            category="经济增长",
            unit="亿元",
            current_value=DataPoint(
                value=320000.0,
                timestamp=now - timedelta(days=30),
                source=DataSource.GOVERNMENT,
                confidence=ConfidenceLevel.HIGH,
            ),
            previous_value=DataPoint(
                value=310000.0,
                timestamp=now - timedelta(days=60),
                source=DataSource.GOVERNMENT,
                confidence=ConfidenceLevel.HIGH,
            ),
            yoy_change=5.2,
            mom_change=1.2,
            trend="up",
        ),
        MacroIndicator(
            code="CPI",
            name="居民消费价格指数",
            name_en="CPI",
            category="物价水平",
            unit="%",
            current_value=DataPoint(
                value=102.5,
                timestamp=now - timedelta(days=5),
                source=DataSource.GOVERNMENT,
                confidence=ConfidenceLevel.HIGH,
            ),
            previous_value=DataPoint(
                value=102.3,
                timestamp=now - timedelta(days=35),
                source=DataSource.GOVERNMENT,
                confidence=ConfidenceLevel.HIGH,
            ),
            yoy_change=2.5,
            mom_change=0.2,
            trend="stable",
        ),
        MacroIndicator(
            code="PMI",
            name="制造业采购经理指数",
            name_en="PMI",
            category="景气指数",
            unit="%",
            current_value=DataPoint(
                value=51.8,
                timestamp=now - timedelta(days=3),
                source=DataSource.GOVERNMENT,
                confidence=ConfidenceLevel.HIGH,
            ),
            previous_value=DataPoint(
                value=50.5,
                timestamp=now - timedelta(days=33),
                source=DataSource.GOVERNMENT,
                confidence=ConfidenceLevel.HIGH,
            ),
            yoy_change=1.3,
            mom_change=0.8,
            trend="up",
        ),
        MacroIndicator(
            code="M2",
            name="广义货币供应量",
            name_en="M2",
            category="货币供应",
            unit="万亿元",
            current_value=DataPoint(
                value=292.5,
                timestamp=now - timedelta(days=10),
                source=DataSource.GOVERNMENT,
                confidence=ConfidenceLevel.HIGH,
            ),
            previous_value=DataPoint(
                value=288.3,
                timestamp=now - timedelta(days=40),
                source=DataSource.GOVERNMENT,
                confidence=ConfidenceLevel.HIGH,
            ),
            yoy_change=8.7,
            mom_change=1.5,
            trend="up",
        ),
        MacroIndicator(
            code="PPI",
            name="工业生产者出厂价格指数",
            name_en="PPI",
            category="物价水平",
            unit="%",
            current_value=DataPoint(
                value=97.5,
                timestamp=now - timedelta(days=5),
                source=DataSource.GOVERNMENT,
                confidence=ConfidenceLevel.HIGH,
            ),
            previous_value=DataPoint(
                value=98.2,
                timestamp=now - timedelta(days=35),
                source=DataSource.GOVERNMENT,
                confidence=ConfidenceLevel.HIGH,
            ),
            yoy_change=-2.5,
            mom_change=-0.7,
            trend="down",
        ),
        MacroIndicator(
            code="UNEMPLOYMENT",
            name="城镇调查失业率",
            name_en="Unemployment Rate",
            category="就业",
            unit="%",
            current_value=DataPoint(
                value=5.2,
                timestamp=now - timedelta(days=7),
                source=DataSource.GOVERNMENT,
                confidence=ConfidenceLevel.MEDIUM,
            ),
            previous_value=DataPoint(
                value=5.3,
                timestamp=now - timedelta(days=37),
                source=DataSource.GOVERNMENT,
                confidence=ConfidenceLevel.MEDIUM,
            ),
            yoy_change=-0.1,
            mom_change=-0.1,
            trend="down",
        ),
    ]

    return MacroPanelData(
        indicators=indicators,
        last_updated=now,
        next_update=now + timedelta(minutes=5),
    )


def _generate_mock_policy_data() -> PolicyPanelData:
    """Generate mock policy data."""
    now = datetime.now()

    policies = [
        PolicyItem(
            policy_id="POL001",
            title="国务院发布稳增长政策措施",
            summary="国务院常务会议部署稳经济一揽子政策措施，包括财政、货币、稳投资促消费等六个方面33项措施。",
            source=DataSource.GOVERNMENT,
            publish_date=now - timedelta(days=2),
            issuer="国务院",
            category="宏观经济",
            impact_level="high",
            affected_sectors=["基建", "房地产", "消费"],
            affected_stocks=["600000", "000001", "601318"],
            sentiment="positive",
            relevance_score=0.95,
        ),
        PolicyItem(
            policy_id="POL002",
            title="央行下调存款准备金率",
            summary="中国人民银行决定下调金融机构存款准备金率0.25个百分点，释放长期资金约5000亿元。",
            source=DataSource.GOVERNMENT,
            publish_date=now - timedelta(days=5),
            issuer="中国人民银行",
            category="货币政策",
            impact_level="high",
            affected_sectors=["银行", "证券", "保险"],
            affected_stocks=["601398", "601288", "600036"],
            sentiment="positive",
            relevance_score=0.92,
        ),
        PolicyItem(
            policy_id="POL003",
            title="证监会优化IPO审核流程",
            summary="证监会发布新规优化IPO审核流程，提高审核效率，支持优质企业上市融资。",
            source=DataSource.GOVERNMENT,
            publish_date=now - timedelta(days=7),
            issuer="证监会",
            category="资本市场",
            impact_level="medium",
            affected_sectors=["证券", "创投"],
            affected_stocks=["600030", "601211"],
            sentiment="positive",
            relevance_score=0.78,
        ),
        PolicyItem(
            policy_id="POL004",
            title="新能源汽车购置税减免延续",
            summary="财政部、税务总局联合发布通知，新能源汽车购置税减免政策延续至2027年。",
            source=DataSource.GOVERNMENT,
            publish_date=now - timedelta(days=10),
            issuer="财政部",
            category="产业政策",
            impact_level="high",
            affected_sectors=["新能源汽车", "锂电池", "汽车零部件"],
            affected_stocks=["002594", "300750", "002475"],
            sentiment="positive",
            relevance_score=0.88,
        ),
        PolicyItem(
            policy_id="POL005",
            title="房地产调控政策优化",
            summary="多地出台房地产调控优化政策，包括降低首付比例、放松限购等措施。",
            source=DataSource.GOVERNMENT,
            publish_date=now - timedelta(days=3),
            issuer="地方政府",
            category="房地产",
            impact_level="medium",
            affected_sectors=["房地产", "建材", "家居"],
            affected_stocks=["000002", "600048", "002242"],
            sentiment="neutral",
            relevance_score=0.82,
        ),
    ]

    return PolicyPanelData(
        policies=policies,
        hot_topics=["稳增长", "降准", "新能源", "房地产", "资本市场改革"],
        last_updated=now,
    )


def _generate_mock_company_data() -> CompanyPanelData:
    """Generate mock company financial data."""
    now = datetime.now()

    companies = [
        CompanyFinancial(
            stock_code="600000",
            stock_name="浦发银行",
            report_date=now - timedelta(days=30),
            report_type="Q3",
            revenue=DataPoint(
                value=135000000000,
                timestamp=now - timedelta(days=30),
                source=DataSource.COMPANY_REPORT,
                confidence=ConfidenceLevel.HIGH,
            ),
            net_profit=DataPoint(
                value=42000000000,
                timestamp=now - timedelta(days=30),
                source=DataSource.COMPANY_REPORT,
                confidence=ConfidenceLevel.HIGH,
            ),
            gross_margin=DataPoint(
                value=45.2,
                timestamp=now - timedelta(days=30),
                source=DataSource.COMPANY_REPORT,
                confidence=ConfidenceLevel.HIGH,
            ),
            net_margin=DataPoint(
                value=31.1,
                timestamp=now - timedelta(days=30),
                source=DataSource.COMPANY_REPORT,
                confidence=ConfidenceLevel.HIGH,
            ),
            roe=DataPoint(
                value=12.5,
                timestamp=now - timedelta(days=30),
                source=DataSource.COMPANY_REPORT,
                confidence=ConfidenceLevel.HIGH,
            ),
            pe_ratio=5.2,
            pb_ratio=0.45,
            yoy_revenue_growth=3.2,
            yoy_profit_growth=-2.5,
            ai_insight="浦发银行作为股份制银行代表，估值处于历史低位，资产质量稳定，但净息差收窄压力较大。",
        ),
        CompanyFinancial(
            stock_code="000001",
            stock_name="平安银行",
            report_date=now - timedelta(days=30),
            report_type="Q3",
            revenue=DataPoint(
                value=128000000000,
                timestamp=now - timedelta(days=30),
                source=DataSource.COMPANY_REPORT,
                confidence=ConfidenceLevel.HIGH,
            ),
            net_profit=DataPoint(
                value=38000000000,
                timestamp=now - timedelta(days=30),
                source=DataSource.COMPANY_REPORT,
                confidence=ConfidenceLevel.HIGH,
            ),
            gross_margin=DataPoint(
                value=42.8,
                timestamp=now - timedelta(days=30),
                source=DataSource.COMPANY_REPORT,
                confidence=ConfidenceLevel.HIGH,
            ),
            net_margin=DataPoint(
                value=29.7,
                timestamp=now - timedelta(days=30),
                source=DataSource.COMPANY_REPORT,
                confidence=ConfidenceLevel.HIGH,
            ),
            roe=DataPoint(
                value=11.2,
                timestamp=now - timedelta(days=30),
                source=DataSource.COMPANY_REPORT,
                confidence=ConfidenceLevel.HIGH,
            ),
            pe_ratio=5.8,
            pb_ratio=0.52,
            yoy_revenue_growth=5.1,
            yoy_profit_growth=1.2,
            ai_insight="平安银行零售转型成效显著，财富管理业务增长强劲，但需关注房地产风险敞口。",
        ),
        CompanyFinancial(
            stock_code="600519",
            stock_name="贵州茅台",
            report_date=now - timedelta(days=30),
            report_type="Q3",
            revenue=DataPoint(
                value=87500000000,
                timestamp=now - timedelta(days=30),
                source=DataSource.COMPANY_REPORT,
                confidence=ConfidenceLevel.HIGH,
            ),
            net_profit=DataPoint(
                value=44500000000,
                timestamp=now - timedelta(days=30),
                source=DataSource.COMPANY_REPORT,
                confidence=ConfidenceLevel.HIGH,
            ),
            gross_margin=DataPoint(
                value=91.5,
                timestamp=now - timedelta(days=30),
                source=DataSource.COMPANY_REPORT,
                confidence=ConfidenceLevel.HIGH,
            ),
            net_margin=DataPoint(
                value=50.9,
                timestamp=now - timedelta(days=30),
                source=DataSource.COMPANY_REPORT,
                confidence=ConfidenceLevel.HIGH,
            ),
            roe=DataPoint(
                value=28.5,
                timestamp=now - timedelta(days=30),
                source=DataSource.COMPANY_REPORT,
                confidence=ConfidenceLevel.HIGH,
            ),
            pe_ratio=28.5,
            pb_ratio=8.2,
            yoy_revenue_growth=18.2,
            yoy_profit_growth=19.5,
            ai_insight="贵州茅台品牌护城河深厚，盈利能力极强，直销占比提升带动毛利率持续走高。",
        ),
    ]

    news = [
        {
            "title": "浦发银行发布三季报：净利润同比增长2.5%",
            "source": "东方财富",
            "time": (now - timedelta(hours=2)).isoformat(),
            "sentiment": "positive",
            "related_stocks": ["600000"],
        },
        {
            "title": "平安银行零售转型成效显著，财富管理收入创新高",
            "source": "证券时报",
            "time": (now - timedelta(hours=5)).isoformat(),
            "sentiment": "positive",
            "related_stocks": ["000001"],
        },
        {
            "title": "贵州茅台提价预期升温，机构看好长期价值",
            "source": "中国证券报",
            "time": (now - timedelta(hours=8)).isoformat(),
            "sentiment": "positive",
            "related_stocks": ["600519"],
        },
        {
            "title": "银行业净息差持续收窄，数字化转型成破局关键",
            "source": "财经杂志",
            "time": (now - timedelta(hours=12)).isoformat(),
            "sentiment": "neutral",
            "related_stocks": ["600000", "000001", "601398"],
        },
    ]

    return CompanyPanelData(
        companies=companies,
        news=news,
        last_updated=now,
    )


def _generate_mock_tech_data() -> TechPanelData:
    """Generate mock technical indicator data."""
    now = datetime.now()

    indicators = [
        TechIndicator(
            stock_code="600000",
            stock_name="浦发银行",
            timestamp=now,
            price=8.52,
            change=0.08,
            change_pct=0.95,
            volume=125000000,
            amount=1065000000,
            ma5=8.45,
            ma10=8.38,
            ma20=8.25,
            ma60=8.10,
            rsi_14=58.5,
            macd=0.025,
            macd_signal=0.018,
            macd_hist=0.007,
            kdj_k=62.3,
            kdj_d=55.8,
            kdj_j=75.3,
            boll_upper=8.85,
            boll_mid=8.45,
            boll_lower=8.05,
            trend_signal="bullish",
            support_level=8.20,
            resistance_level=8.80,
        ),
        TechIndicator(
            stock_code="000001",
            stock_name="平安银行",
            timestamp=now,
            price=11.85,
            change=0.15,
            change_pct=1.28,
            volume=98500000,
            amount=1168000000,
            ma5=11.72,
            ma10=11.58,
            ma20=11.35,
            ma60=11.20,
            rsi_14=62.8,
            macd=0.032,
            macd_signal=0.024,
            macd_hist=0.008,
            kdj_k=68.5,
            kdj_d=60.2,
            kdj_j=85.1,
            boll_upper=12.20,
            boll_mid=11.65,
            boll_lower=11.10,
            trend_signal="bullish",
            support_level=11.30,
            resistance_level=12.15,
        ),
        TechIndicator(
            stock_code="600519",
            stock_name="贵州茅台",
            timestamp=now,
            price=1685.00,
            change=-12.50,
            change_pct=-0.74,
            volume=2850000,
            amount=4800000000,
            ma5=1695.00,
            ma10=1710.00,
            ma20=1725.00,
            ma60=1750.00,
            rsi_14=45.2,
            macd=-8.5,
            macd_signal=-5.2,
            macd_hist=-3.3,
            kdj_k=42.5,
            kdj_d=48.3,
            kdj_j=30.9,
            boll_upper=1780.00,
            boll_mid=1700.00,
            boll_lower=1620.00,
            trend_signal="bearish",
            support_level=1650.00,
            resistance_level=1750.00,
        ),
        TechIndicator(
            stock_code="002594",
            stock_name="比亚迪",
            timestamp=now,
            price=258.50,
            change=5.80,
            change_pct=2.29,
            volume=15800000,
            amount=4085000000,
            ma5=252.30,
            ma10=248.50,
            ma20=245.00,
            ma60=238.00,
            rsi_14=68.5,
            macd=3.25,
            macd_signal=2.10,
            macd_hist=1.15,
            kdj_k=72.8,
            kdj_d=65.3,
            kdj_j=87.8,
            boll_upper=268.00,
            boll_mid=250.00,
            boll_lower=232.00,
            trend_signal="bullish",
            support_level=245.00,
            resistance_level=270.00,
        ),
    ]

    signals = [
        {
            "stock_code": "600000",
            "stock_name": "浦发银行",
            "signal": "买入",
            "reason": "MACD金叉，RSI处于强势区间",
            "confidence": 0.72,
        },
        {
            "stock_code": "000001",
            "stock_name": "平安银行",
            "signal": "买入",
            "reason": "突破20日均线，成交量放大",
            "confidence": 0.78,
        },
        {
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "signal": "观望",
            "reason": "RSI中性偏弱，等待企稳信号",
            "confidence": 0.65,
        },
        {
            "stock_code": "002594",
            "stock_name": "比亚迪",
            "signal": "买入",
            "reason": "KDJ金叉，突破布林中轨",
            "confidence": 0.82,
        },
    ]

    return TechPanelData(
        indicators=indicators,
        signals=signals,
        last_updated=now,
    )


@router.get("/canvas", response_model=CanvasData)
async def get_canvas_data() -> CanvasData:
    """Get all canvas data."""
    return CanvasData(
        macro=_generate_mock_macro_data(),
        policy=_generate_mock_policy_data(),
        company=_generate_mock_company_data(),
        tech=_generate_mock_tech_data(),
        last_updated=datetime.now(),
    )


@router.get("/macro", response_model=MacroPanelData)
async def get_macro_data() -> MacroPanelData:
    """Get macro economic data."""
    return _generate_mock_macro_data()


@router.get("/policy", response_model=PolicyPanelData)
async def get_policy_data() -> PolicyPanelData:
    """Get policy data."""
    return _generate_mock_policy_data()


@router.get("/company", response_model=CompanyPanelData)
async def get_company_data() -> CompanyPanelData:
    """Get company financial data."""
    return _generate_mock_company_data()


@router.get("/tech", response_model=TechPanelData)
async def get_tech_data() -> TechPanelData:
    """Get technical indicator data."""
    return _generate_mock_tech_data()


@router.post("/ai/analyze", response_model=AnalysisResponse)
async def ai_analyze(request: AnalysisRequest) -> AnalysisResponse:
    """Perform AI analysis using DashScope LLM."""
    import os
    import time

    from openai import AsyncOpenAI

    start_time = time.time()

    analysis_id = str(uuid.uuid4())

    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("DASHSCOPE_API_URL") or os.getenv("OPENAI_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model = os.getenv("LLM_MODEL", "qwen-max")

    canvas_data = await get_canvas_data()

    context = f"""
当前画布数据：

## 宏观经济数据
{chr(10).join([f"- {ind.name}: {ind.current_value.value} {ind.unit}, 同比{ind.yoy_change}%" for ind in canvas_data.macro.indicators[:4]])}

## 政策动态
{chr(10).join([f"- {pol.title}: {pol.summary}" for pol in canvas_data.policy.policies[:3]])}

## 公司财务
{chr(10).join([f"- {comp.stock_name}({comp.stock_code}): 营收{comp.revenue.value/1e9:.1f}亿, 净利润{comp.net_profit.value/1e9:.1f}亿, PE{comp.pe_ratio}" for comp in canvas_data.company.companies[:3]])}

## 技术指标
{chr(10).join([f"- {tech.stock_name}: 价格{tech.price}, 涨跌{tech.change_pct:+.2f}%, RSI{tech.rsi_14:.1f}" for tech in canvas_data.tech.indicators[:3]])}
"""

    system_prompt = """你是一位专业的金融分析师，擅长宏观经济分析、政策解读、公司基本面分析和技术分析。
请基于提供的画布数据，为用户提供专业、客观、有深度的分析。
回答请使用Markdown格式，结构清晰，观点明确。"""

    try:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"用户问题：{request.query}\n\n{context}"},
            ],
            temperature=0.7,
            max_tokens=2000,
        )

        analysis_content = response.choices[0].message.content or ""

    except Exception as e:
        analysis_content = f"""## 分析结果

针对您的问题「{request.query}」，基于当前画布数据，我为您进行以下分析：

### 宏观经济视角
当前宏观经济环境整体呈现温和复苏态势。GDP同比增长5.2%，PMI维持在荣枯线以上，显示制造业景气度持续改善。CPI同比上涨2.5%，通胀压力可控。

### 政策影响分析
近期降准政策释放约5000亿元长期资金，有利于降低银行负债成本，对银行板块形成利好。新能源汽车购置税减免政策延续，将持续支撑新能源产业链发展。

### 公司层面观察
从财务数据来看，银行业整体估值处于历史低位，浦发银行PE仅5.2倍，具有较高的安全边际。贵州茅台盈利能力极强，净利率超过50%，品牌护城河深厚。

### 技术面信号
当前技术指标显示，银行股普遍呈现多头排列，MACD金叉确认，短期趋势向好。建议关注成交量变化，确认上涨动能。

### 投资建议
综合考虑宏观环境、政策导向、基本面和技术面因素，建议：
1. 银行板块可逢低布局，关注估值修复机会
2. 新能源产业链受益政策支持，中长期看好
3. 白酒龙头基本面稳健，可作为防御性配置

---
*数据来源：Wind、东方财富、公司公告 | 置信度：中高*

*(注：LLM调用失败，使用默认回复。错误：{str(e)})*"""

    duration_ms = (time.time() - start_time) * 1000

    return AnalysisResponse(
        analysis_id=analysis_id,
        query=request.query,
        content=analysis_content,
        data_sources=[
            DataSource.WIND,
            DataSource.EASTMONEY,
            DataSource.COMPANY_REPORT,
        ],
        confidence=ConfidenceLevel.MEDIUM,
        related_entities=["600000", "000001", "600519", "002594"],
        follow_up_suggestions=[
            "浦发银行的详细财务分析",
            "银行业估值对比分析",
            "新能源汽车产业链投资机会",
            "贵州茅台的投资价值分析",
        ],
        duration_ms=duration_ms,
    )


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "analysis"}
