"""
News data collectors migrated from qstock news.py.

This module provides collectors for news data including
Jinshi news, CLS news, and CCTV news.
"""

import hashlib
import logging
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


class JinshiNewsCollector(BaseCollector[NewsData]):
    """
    Collector for Jinshi (金十数据) news.
    Migrated from qstock news.py get_js_news function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.JINSHI,
                data_type=DataType.MARKET_NEWS,
                category=DataCategory.NEWS,
                frequency=DataFrequency.TICK,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.JINSHI

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[NewsData]:
        date = kwargs.get("date")
        max_count = kwargs.get("max_count", 100)
        return await self._collect_jinshi_news(date, max_count)

    async def _collect_jinshi_news(
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

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                data = await response.json()

        records = []
        if data.get("data"):
            for item in data["data"][:max_count]:
                try:
                    content = item.get("data", {}).get("content", "")
                    if not content:
                        content = item.get("data", {}).get("pic", "")

                    record = NewsData(
                        news_id=str(item.get("id", "")),
                        title=content[:100] if content else "",
                        content=content,
                        source="jinshi",
                        category="flash",
                        published_at=datetime.fromtimestamp(item.get("time", 0)),
                    )
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse jinshi news: {e}")

        return records


class CLSNewsCollector(BaseCollector[NewsData]):
    """
    Collector for CLS (财联社) news.
    Migrated from qstock news.py news_cls function.
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

    @property
    def source(self) -> DataSource:
        return DataSource.CLS

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[NewsData]:
        count = kwargs.get("count", 100)
        return await self._collect_cls_news(count)

    async def _collect_cls_news(self, count: int = 100) -> list[NewsData]:
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

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                data = await response.json()

        records = []
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

                    record = NewsData(
                        news_id=str(item.get("id", "")),
                        title=item.get("title", ""),
                        content=item.get("content", ""),
                        source="cls",
                        category="telegraph",
                        published_at=published_at,
                    )
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse CLS news: {e}")

        return records


class CCTVNewsCollector(BaseCollector[NewsData]):
    """
    Collector for CCTV news (新闻联播).
    Migrated from qstock news.py get_news_cctv function.
    """

    def __init__(self, config: CollectionConfig | None = None) -> None:
        if config is None:
            config = CollectionConfig(
                source=DataSource.CUSTOM,
                data_type=DataType.MARKET_NEWS,
                category=DataCategory.NEWS,
                frequency=DataFrequency.DAILY,
            )
        super().__init__(config)

    @property
    def source(self) -> DataSource:
        return DataSource.CUSTOM

    async def _initialize(self) -> None:
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _cleanup(self) -> None:
        logger.info(f"Cleaned up {self.__class__.__name__}")

    async def _collect(self, **kwargs: Any) -> list[NewsData]:
        date = kwargs.get("date")
        return await self._collect_cctv_news(date)

    async def _collect_cctv_news(self, date: str | None = None) -> list[NewsData]:
        import aiohttp
        from bs4 import BeautifulSoup

        now = datetime.now()
        now_date = now.strftime("%Y%m%d")

        if date is None:
            date = now_date
        else:
            date = "".join(date.split("-"))

        if date >= now_date:
            date = (now - timedelta(1)).strftime("%Y%m%d")

        url = f"http://cctv.cntv.cn/lm/xinwenlianbo/{date}.shtml"

        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                html = await response.text()

        soup = BeautifulSoup(html, "lxml")
        records = []

        try:
            if int(date) < int("20160203"):
                content_div = soup.find("div", attrs={"id": "contentELMT1368521805488378"})
                if content_div:
                    page_urls = [
                        item.find("a")["href"]
                        for item in content_div.find_all("li")[1:]
                    ]
            else:
                url = f"https://tv.cctv.com/lm/xwlb/day/{date}.shtml"
                async with session.get(url, headers=headers) as response:
                    html = await response.text()
                soup = BeautifulSoup(html, "lxml")
                page_urls = [item.find("a")["href"] for item in soup.find_all("li")[1:]]

            for page_url in page_urls:
                try:
                    async with session.get(page_url, headers=headers) as response:
                        page_html = await response.text()
                    page_soup = BeautifulSoup(page_html, "lxml")

                    title = ""
                    if page_soup.find("h3"):
                        title = page_soup.find("h3").text
                    elif page_soup.find("div", attrs={"class": "tit"}):
                        title = page_soup.find("div", attrs={"class": "tit"}).text

                    content = ""
                    if page_soup.find("div", attrs={"class": "cnt_bd"}):
                        content = page_soup.find("div", attrs={"class": "cnt_bd"}).text
                    elif page_soup.find("div", attrs={"class": "content_area"}):
                        content = page_soup.find("div", attrs={"class": "content_area"}).text

                    title = title.strip("[视频]").strip().replace("\n", " ")
                    content = (
                        content.strip()
                        .strip("央视网消息(新闻联播)：")
                        .strip("央视网消息（新闻联播）：")
                        .strip("(新闻联播)：")
                        .strip()
                        .replace("\n", " ")
                    )

                    record = NewsData(
                        news_id=f"cctv_{date}_{len(records)}",
                        title=title,
                        content=content,
                        source="cctv",
                        category="news_broadcast",
                        published_at=datetime.strptime(date, "%Y%m%d"),
                    )
                    records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to parse CCTV news page: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Failed to parse CCTV news: {e}")

        return records
