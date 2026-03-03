"""
Research report data collectors.

This module provides collectors for research reports from various sources
including Eastmoney, THSHY, and other financial data providers.
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote

from ..core.base_collector import (
    BaseCollector,
    CollectionConfig,
    CollectionResult,
    DataCategory,
    DataFrequency,
    DataSource,
    DataType,
)
from ..quant_collector import FundamentalDataCollector

logger = logging.getLogger(__name__)


class ResearchReportCollector(FundamentalDataCollector):
    """
    Collector for research reports from multiple sources.
    
    Supports:
    - Eastmoney (东方财富)
    - THSHY (同花顺)
    
    Usage:
        collector = ResearchReportCollector()
        reports = await collector.collect(
            source="eastmoney",
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.STOCK_RESEARCH_REPORT,
                category=DataCategory.FUNDAMENTAL,
                frequency=DataFrequency.DAILY,
            )
        super().__init__(config)
        self._sources = {
            "eastmoney": self._collect_eastmoney,
            "thshy": self._collect_thshy,
        }

    @property
    def source(self) -> DataSource:
        return DataSource.EASTMONEY

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[dict[str, Any]]:
        source = kwargs.get("source", "eastmoney")
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")
        codes = kwargs.get("codes")
        industries = kwargs.get("industries")
        report_types = kwargs.get("report_types")

        if start_date is None:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        collector_func = self._sources.get(source)
        if collector_func is None:
            logger.warning(f"Unknown source: {source}, using eastmoney")
            collector_func = self._collect_eastmoney

        reports = await collector_func(
            start_date=start_date,
            end_date=end_date,
            codes=codes,
            industries=industries,
            report_types=report_types,
        )

        return reports

    async def _collect_eastmoney(
        self,
        start_date: str,
        end_date: str,
        codes: list[str] | None = None,
        industries: list[str] | None = None,
        report_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Collect research reports from Eastmoney.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            codes: Optional list of stock codes to filter
            industries: Optional list of industries to filter
            report_types: Optional list of report types to filter
        
        Returns:
            List of research report dictionaries
        """
        import aiohttp

        reports = []
        
        url = "https://reportapi.eastmoney.com/report/list"
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        page = 1
        page_size = 100
        
        async with aiohttp.ClientSession() as session:
            while True:
                params = {
                    "cb": "datatable",
                    "industryCode": "*",
                    "pageSize": str(page_size),
                    "industry": "",
                    "rating": "",
                    "ratingChange": "",
                    "beginTime": start_date,
                    "endTime": end_date,
                    "pageNo": str(page),
                    "fields": "",
                    "qType": "0",
                    "orgCode": "",
                    "code": "",
                    "rcode": "",
                    "p": str(page),
                    "page_num": str(page),
                    "pageNumber": str(page),
                }
                
                try:
                    async with session.get(url, params=params, timeout=30) as response:
                        text = await response.text()
                        
                        json_str = re.sub(r'^datatable\(', '', text)
                        json_str = re.sub(r'\)$', '', json_str)
                        
                        try:
                            data = json.loads(json_str)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse JSON from Eastmoney response")
                            break
                    
                    if not data.get("data"):
                        break
                    
                    for item in data["data"]:
                        report = self._parse_eastmoney_report(item)
                        if report:
                            if codes and report.get("related_codes"):
                                if not any(c in report.get("related_codes", []) for c in codes):
                                    continue
                            reports.append(report)
                    
                    total_pages = data.get("totalPage", 1)
                    if page >= total_pages:
                        break
                    
                    page += 1
                    
                except aiohttp.ClientError as e:
                    logger.error(f"Eastmoney API error: {e}")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error collecting from Eastmoney: {e}")
                    break

        logger.info(f"Collected {len(reports)} reports from Eastmoney")
        return reports

    def _parse_eastmoney_report(self, item: dict[str, Any]) -> dict[str, Any] | None:
        """Parse a single Eastmoney report item."""
        try:
            title = item.get("title", "")
            if not title:
                return None
            
            report_id = self._generate_report_id(
                "eastmoney",
                item.get("code", ""),
                item.get("publishDate", ""),
                title,
            )
            
            related_codes = []
            related_names = []
            if item.get("code"):
                related_codes.append(item.get("code"))
            if item.get("stockName"):
                related_names.append(item.get("stockName"))
            
            publish_date = None
            if item.get("publishDate"):
                try:
                    publish_date = datetime.strptime(
                        item.get("publishDate"), "%Y-%m-%d"
                    )
                except ValueError:
                    pass
            
            return {
                "report_id": report_id,
                "title": title,
                "summary": item.get("summary", ""),
                "content": None,
                "source": "eastmoney",
                "source_url": f"https://data.eastmoney.com/report/zw_macresearch.jshtml?code={item.get('code', '')}",
                "related_codes": related_codes,
                "related_names": related_names,
                "industry": item.get("industry", ""),
                "institution": item.get("orgSName", ""),
                "analyst": item.get("researcher", ""),
                "rating": item.get("emRatingName", ""),
                "target_price": None,
                "publish_date": publish_date,
                "report_type": self._classify_report_type(title),
                "collected_at": datetime.utcnow(),
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse Eastmoney report: {e}")
            return None

    async def _collect_thshy(
        self,
        start_date: str,
        end_date: str,
        codes: list[str] | None = None,
        industries: list[str] | None = None,
        report_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Collect research reports from THSHY (同花顺).
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            codes: Optional list of stock codes to filter
            industries: Optional list of industries to filter
            report_types: Optional list of report types to filter
        
        Returns:
            List of research report dictionaries
        """
        import aiohttp

        reports = []
        
        url = "https://stockpage.10jqka.com.cn/159791/research/"
        
        logger.info(f"THSHY collection not fully implemented, returning empty list")
        return reports

    def _generate_report_id(
        self,
        source: str,
        code: str,
        date: str,
        title: str,
    ) -> str:
        """Generate a unique report ID."""
        content = f"{source}_{code}_{date}_{title}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _classify_report_type(self, title: str) -> str:
        """Classify report type based on title."""
        title_lower = title.lower()
        
        if any(kw in title for kw in ["深度", "研究", "报告", "分析"]):
            return "depth_report"
        elif any(kw in title for kw in ["快报", "简报", "点评", "快评"]):
            return "quick_report"
        elif any(kw in title for kw in ["季报", "半年报", "年报", "财报"]):
            return "financial_report"
        elif any(kw in title for kw in ["调研", "纪要"]):
            return "research_note"
        else:
            return "general_report"

    def _get_record_hash(self, record: dict[str, Any]) -> str:
        return record.get("report_id", "")

    async def _is_valid(self, record: dict[str, Any]) -> bool:
        if not record.get("report_id"):
            return False
        if not record.get("title"):
            return False
        return True


class ResearchReportDetailCollector(BaseCollector[dict[str, Any]]):
    """
    Collector for detailed research report content.
    
    Fetches the full content of a research report from its source.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.EASTMONEY,
                data_type=DataType.STOCK_RESEARCH_REPORT,
                category=DataCategory.FUNDAMENTAL,
                frequency=DataFrequency.DAILY,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.EASTMONEY

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[dict[str, Any]]:
        report_id = kwargs.get("report_id")
        source_url = kwargs.get("source_url")
        source = kwargs.get("source", "eastmoney")
        
        if not source_url:
            return []
        
        content = await self._fetch_report_content(source_url, source)
        
        if content:
            return [{
                "report_id": report_id,
                "content": content,
            }]
        
        return []

    async def _fetch_report_content(
        self,
        url: str,
        source: str,
    ) -> str | None:
        """Fetch report content from URL."""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
                
                async with session.get(url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._extract_content(html, source)
                    
        except Exception as e:
            logger.warning(f"Failed to fetch report content: {e}")
        
        return None

    def _extract_content(self, html: str, source: str) -> str | None:
        """Extract text content from HTML."""
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text(separator="\n", strip=True)
            
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            content = "\n".join(lines)
            
            return content[:50000] if len(content) > 50000 else content
            
        except Exception as e:
            logger.warning(f"Failed to extract content: {e}")
            return None

    def _get_record_hash(self, record: dict[str, Any]) -> str:
        return record.get("report_id", "")

    async def _is_valid(self, record: dict[str, Any]) -> bool:
        return bool(record.get("report_id") and record.get("content"))
