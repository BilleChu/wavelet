"""
Market event collectors and processors for Wavelet analysis.

This module provides collectors for market events from various sources
including CLS (财联社), Jinshi (金十数据), etc.
"""

import hashlib
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any

from ..core.base_collector import (
    BaseCollector,
    CollectionConfig,
    DataCategory,
    DataFrequency,
    DataSource,
    DataType,
    NewsData,
)

logger = logging.getLogger(__name__)


class MarketEventCollector(BaseCollector[NewsData]):
    """
    Base collector for market events.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.CLS,
                data_type=DataType.MARKET_NEWS,
                category=DataCategory.NEWS,
                frequency=DataFrequency.TICK,
            )
        super().__init__(config)
        
        self.event_keywords = {
            'macro_global': [
                '美联储', 'Fed', '利率决议', '非农', '美国CPI', '美国GDP',
                '欧洲央行', 'ECB', '日本央行', '贸易战', '关税', '美元指数',
                'VIX', '恐慌指数', '美债', '国债收益率',
            ],
            'macro_china': [
                '中国GDP', 'CPI', 'PPI', 'PMI', '央行', '货币政策',
                '财政政策', '降准', '降息', 'LPR', '社融', 'M2',
                '国家统计局', '发改委', '国务院', '经济工作会议',
            ],
            'market': [
                '上证指数', '深证成指', '创业板', '科创板', '北向资金',
                '融资融券', '两市成交', '涨停', '跌停', '熔断',
                '股指期货', '期权', 'IPO', '再融资',
            ],
            'industry': [
                '新能源', '半导体', '芯片', '人工智能', 'AI', '医药',
                '白酒', '房地产', '银行', '保险', '券商', '汽车',
                '光伏', '风电', '储能', '锂电池', '稀土', '钢铁',
            ],
            'company': [
                '业绩', '财报', '分红', '回购', '增持', '减持',
                '重组', '并购', '高管', '股权', '质押', '解禁',
            ],
        }
        
        self.importance_keywords = {
            'critical': [
                '利率决议', '非农数据', 'GDP数据', '央行决议',
                '重大政策', '国务院会议', '经济工作会议',
            ],
            'high': [
                'CPI数据', 'PPI数据', 'PMI数据', '社融数据',
                '贸易数据', '行业政策', '监管政策',
            ],
            'medium': [
                '行业数据', '公司公告', '业绩预告', '调研',
            ],
        }
        
        self.positive_keywords = [
            '利好', '上涨', '增长', '突破', '创新高', '超预期',
            '降准', '降息', '宽松', '刺激', '扶持', '补贴',
            '盈利', '增长', '改善', '回暖', '复苏',
        ]
        
        self.negative_keywords = [
            '利空', '下跌', '下滑', '跌破', '新低', '不及预期',
            '加息', '收紧', '调控', '限制', '处罚', '调查',
            '亏损', '下降', '恶化', '衰退', '危机',
        ]

    @property
    def source(self) -> DataSource:
        return DataSource.CLS

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[NewsData]:
        raise NotImplementedError

    def classify_event(self, title: str, content: str = "") -> dict:
        """
        Classify event by category, importance, and impact direction.
        
        Returns:
            dict with keys: category, importance, impact_direction
        """
        text = f"{title} {content}".lower()
        
        category = 'market'
        for cat, keywords in self.event_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    category = cat
                    break
            if category != 'market':
                break
        
        importance = 'low'
        for imp, keywords in self.importance_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    importance = imp
                    break
            if importance != 'low':
                break
        
        impact_direction = 'neutral'
        positive_count = sum(1 for kw in self.positive_keywords if kw in text)
        negative_count = sum(1 for kw in self.negative_keywords if kw in text)
        
        if positive_count > negative_count:
            impact_direction = 'positive'
        elif negative_count > positive_count:
            impact_direction = 'negative'
        
        return {
            'category': category,
            'importance': importance,
            'impact_direction': impact_direction,
        }

    def estimate_impact_magnitude(self, classification: dict) -> float:
        """
        Estimate impact magnitude based on classification.
        
        Returns:
            float: 0-100 impact magnitude
        """
        importance_weights = {
            'critical': 80,
            'high': 60,
            'medium': 40,
            'low': 20,
        }
        
        direction_multipliers = {
            'positive': 1.0,
            'negative': -1.0,
            'neutral': 0.0,
        }
        
        base_magnitude = importance_weights.get(classification['importance'], 20)
        direction = classification['impact_direction']
        
        return base_magnitude * direction_multipliers.get(direction, 0)


class CLSEventCollector(MarketEventCollector):
    """
    Collector for CLS (财联社) market events with classification.
    """

    async def _collect(self, **kwargs: Any) -> list[NewsData]:
        count = kwargs.get("count", 100)
        return await self._collect_cls_events(count)

    async def _collect_cls_events(self, count: int = 100) -> list[NewsData]:
        import aiohttp

        current_time = int(time.time())

        url = "https://www.cls.cn/nodeapi/telegraphList"

        text = f"app=CailianpressWeb&category=&lastTime={current_time}&last_time={current_time}&os=web&refresh_type=1&rn={count}&sv=7.7.5"
        sha1 = hashlib.sha1(text.encode()).hexdigest()
        code = hashlib.md5(sha1.encode()).hexdigest()

        params = {
            "app": "CailianpressWeb",
            "category": "",
            "lastTime": current_time,
            "last_time": current_time,
            "os": "web",
            "refresh_type": "1",
            "rn": str(count),
            "sv": "7.7.5",
            "sign": code,
        }

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=utf-8",
            "Host": "www.cls.cn",
            "Referer": "https://www.cls.cn/telegraph",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        records = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    data = await response.json()

            if data.get("data") and data["data"].get("roll_data"):
                for item in data["data"]["roll_data"]:
                    try:
                        ctime = item.get("ctime", "")
                        if isinstance(ctime, int):
                            published_at = datetime.fromtimestamp(ctime)
                        elif isinstance(ctime, str) and ctime:
                            published_at = datetime.strptime(ctime, "%Y-%m-%d %H:%M:%S")
                        else:
                            published_at = datetime.now()

                        title = item.get("title", "") or item.get("content", "")[:100]
                        content = item.get("content", "")
                        
                        classification = self.classify_event(title, content)
                        impact_magnitude = self.estimate_impact_magnitude(classification)

                        record = NewsData(
                            news_id=str(item.get("id", "")),
                            title=title,
                            content=content,
                            source="cls",
                            category=classification['category'],
                            published_at=published_at,
                        )
                        record.properties = {
                            'importance': classification['importance'],
                            'impact_direction': classification['impact_direction'],
                            'impact_magnitude': impact_magnitude,
                            'event_type': 'telegraph',
                        }
                        records.append(record)
                    except Exception as e:
                        logger.warning(f"Failed to parse CLS event: {e}")
        except Exception as e:
            logger.error(f"Failed to collect CLS events: {e}")

        return records


class JinshiEventCollector(MarketEventCollector):
    """
    Collector for Jinshi (金十数据) market events with classification.
    """

    @property
    def source(self) -> DataSource:
        return DataSource.JINSHI

    async def _collect(self, **kwargs: Any) -> list[NewsData]:
        date = kwargs.get("date")
        max_count = kwargs.get("max_count", 100)
        return await self._collect_jinshi_events(date, max_count)

    async def _collect_jinshi_events(
        self, date: str | None = None, max_count: int = 100
    ) -> list[NewsData]:
        import aiohttp

        if date is None:
            date = (datetime.now() + timedelta(1)).strftime("%Y%m%d")
        else:
            date = "".join(date.split("-"))
            date = (datetime.strptime(date, "%Y%m%d") + timedelta(1)).strftime("%Y%m%d")

        url = "https://flash-api.jin10.com/get_flash_list"

        params = {
            "channel": "-8200",
            "vip": "1",
            "t": str(int(time.time() * 1000)),
            "max_time": date,
        }

        headers = {
            "accept": "application/json, text/plain, */*",
            "origin": "https://www.jin10.com",
            "referer": "https://www.jin10.com/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "x-app-id": "bVBF4FyRTn5NJF5n",
            "x-version": "1.0.0",
        }

        records = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    data = await response.json()

            if data.get("data"):
                for item in data["data"][:max_count]:
                    try:
                        content = item.get("data", {}).get("content", "")
                        if not content:
                            content = item.get("data", {}).get("pic", "")
                        
                        title = content[:100] if content else ""
                        
                        classification = self.classify_event(title, content)
                        impact_magnitude = self.estimate_impact_magnitude(classification)

                        record = NewsData(
                            news_id=str(item.get("id", "")),
                            title=title,
                            content=content,
                            source="jinshi",
                            category=classification['category'],
                            published_at=datetime.fromtimestamp(item.get("time", 0)),
                        )
                        record.properties = {
                            'importance': classification['importance'],
                            'impact_direction': classification['impact_direction'],
                            'impact_magnitude': impact_magnitude,
                            'event_type': 'flash',
                        }
                        records.append(record)
                    except Exception as e:
                        logger.warning(f"Failed to parse Jinshi event: {e}")
        except Exception as e:
            logger.error(f"Failed to collect Jinshi events: {e}")

        return records


class USMacroDataCollector(MarketEventCollector):
    """
    Collector for US macro economic data.
    """

    @property
    def source(self) -> DataSource:
        return DataSource.EASTMONEY

    async def _collect(self, **kwargs: Any) -> list[NewsData]:
        return await self._collect_us_macro()

    async def _collect_us_macro(self) -> list[NewsData]:
        import aiohttp

        records = []
        
        us_indicators = [
            {
                'name': '美国联邦基金利率',
                'code': 'FED_FUNDS_RATE',
                'url': 'https://datacenter-web.eastmoney.com/api/data/v1/get',
                'params': {
                    'reportName': 'RPT_USA_INTERESTRATE',
                    'columns': 'TRADE_DATE,INDEX_NAME,LATEST_PRICE',
                    'filter': '(INDEX_NAME="联邦基金利率")',
                    'pageNumber': '1',
                    'pageSize': '10',
                    'sortTypes': '-1',
                    'sortColumns': 'TRADE_DATE',
                },
            },
        ]

        async with aiohttp.ClientSession() as session:
            for indicator in us_indicators:
                try:
                    async with session.get(
                        indicator['url'], 
                        params=indicator['params'],
                        headers={'User-Agent': 'Mozilla/5.0'}
                    ) as response:
                        text = await response.text()
                        import json
                        data = json.loads(text)
                    
                    if data.get('result') and data['result'].get('data'):
                        for item in data['result']['data']:
                            record = NewsData(
                                news_id=f"us_macro_{indicator['code']}_{item.get('TRADE_DATE', '')}",
                                title=f"{indicator['name']}: {item.get('LATEST_PRICE', '')}",
                                content='',
                                source='eastmoney_us',
                                category='macro_global',
                                published_at=datetime.now(),
                            )
                            record.properties = {
                                'indicator_code': indicator['code'],
                                'indicator_value': item.get('LATEST_PRICE'),
                                'importance': 'high',
                                'impact_direction': 'neutral',
                            }
                            records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to collect US macro {indicator['name']}: {e}")

        return records
