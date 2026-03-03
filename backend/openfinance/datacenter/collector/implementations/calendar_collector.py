"""
Economic Calendar Collector Implementation.

Collects economic calendar events from Investing.com.
"""

import logging
from datetime import datetime, timedelta, date
from typing import Any, Optional

from openfinance.datacenter.collector.core.base_collector import (
    BaseCollector,
    CollectionConfig,
    CollectionResult,
    CollectionStatus,
    DataSource,
    DataType,
    DataCategory,
)

logger = logging.getLogger(__name__)


class EconomicEvent:
    """Economic calendar event data model."""
    
    event_id: str
    event_date: date
    event_time: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    importance: str = "low"
    event_name: str
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    source: str = "investing.com"
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class EconomicCalendarCollector(BaseCollector[EconomicEvent]):
    """Collector for economic calendar events from Investing.com."""
    
    def __init__(self, config: Optional[CollectionConfig] = None):
        if config is None:
            config = CollectionConfig(
                source=DataSource.CUSTOM,
                data_type=DataType.MACRO_DATA,
                category=DataCategory.MACRO,
            )
        super().__init__(config)
        self._investpy_available = self._check_investpy()
        self._cloudscraper_available = self._check_cloudscraper()
        self._selenium_available = self._check_selenium()
    
    @property
    def source(self) -> DataSource:
        return DataSource.CUSTOM
    
    @property
    def data_type(self) -> DataType:
        return DataType.MACRO_DATA
    
    async def _initialize(self) -> None:
        """Initialize collector resources."""
        logger.info(
            f"EconomicCalendarCollector initialized. "
            f"investpy={self._investpy_available}, "
            f"cloudscraper={self._cloudscraper_available}, "
            f"selenium={self._selenium_available}"
        )
    
    async def _cleanup(self) -> None:
        """Cleanup collector resources."""
        pass
    
    def _get_record_hash(self, record: EconomicEvent) -> str:
        """Get hash for deduplication."""
        return record.event_id
    
    async def _is_valid(self, record: EconomicEvent) -> bool:
        """Check if a record is valid."""
        return bool(record.event_id and record.event_date and record.event_name)
    
    async def _collect(self, **kwargs) -> list[EconomicEvent]:
        """Implement actual data collection logic."""
        from_date = kwargs.get('from_date', date.today() - timedelta(days=7))
        to_date = kwargs.get('to_date', date.today() + timedelta(days=30))
        countries = kwargs.get('countries')
        importances = kwargs.get('importances')
        strategy = kwargs.get('strategy', 'auto')
        
        if strategy == "auto":
            return await self._collect_auto(from_date, to_date, countries, importances)
        elif strategy == "investpy" and self._investpy_available:
            return await self._collect_investpy(from_date, to_date, countries, importances)
        elif strategy == "cloudscraper" and self._cloudscraper_available:
            return await self._collect_cloudscraper(from_date, to_date)
        elif strategy == "requests":
            return await self._collect_requests(from_date, to_date)
        elif strategy == "selenium" and self._selenium_available:
            return await self._collect_selenium(from_date, to_date)
        else:
            logger.warning(f"Unknown or unavailable strategy: {strategy}")
            return []
    
    def _check_investpy(self) -> bool:
        try:
            import investpy
            return True
        except ImportError:
            return False
    
    def _check_cloudscraper(self) -> bool:
        try:
            import cloudscraper
            return True
        except ImportError:
            return False
    
    def _check_selenium(self) -> bool:
        try:
            from selenium import webdriver
            return True
        except ImportError:
            return False
    
    async def _collect_auto(
        self,
        from_date: date,
        to_date: date,
        countries: Optional[list[str]],
        importances: Optional[list[str]],
    ) -> list[EconomicEvent]:
        strategies = []
        
        if self._investpy_available:
            strategies.append(("investpy", self._collect_investpy))
        if self._cloudscraper_available:
            strategies.append(("cloudscraper", self._collect_cloudscraper))
        strategies.append(("requests", self._collect_requests))
        if self._selenium_available:
            strategies.append(("selenium", self._collect_selenium))
        
        for name, collector in strategies:
            try:
                logger.info(f"Trying strategy: {name}")
                events = await collector(from_date, to_date, countries, importances)
                if events:
                    logger.info(f"Strategy {name} succeeded with {len(events)} events")
                    return events
            except Exception as e:
                logger.warning(f"Strategy {name} failed: {e}")
                continue
        
        return []
    
    async def _collect_investpy(
        self,
        from_date: date,
        to_date: date,
        countries: Optional[list[str]],
        importances: Optional[list[str]],
    ) -> list[EconomicEvent]:
        import investpy
        
        data = investpy.economic_calendar(
            from_date=from_date.strftime('%d/%m/%Y'),
            to_date=to_date.strftime('%d/%m/%Y'),
            countries=countries,
            importances=importances,
        )
        
        return self._parse_dataframe(data)
    
    async def _collect_cloudscraper(
        self,
        from_date: date,
        to_date: date,
        countries: Optional[list[str]] = None,
        importances: Optional[list[str]] = None,
    ) -> list[EconomicEvent]:
        import cloudscraper
        from bs4 import BeautifulSoup
        
        scraper = cloudscraper.create_scraper()
        url = 'https://www.investing.com/economic-calendar/'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        response = scraper.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"HTTP error: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        return self._parse_html(soup)
    
    async def _collect_requests(
        self,
        from_date: date,
        to_date: date,
        countries: Optional[list[str]] = None,
        importances: Optional[list[str]] = None,
    ) -> list[EconomicEvent]:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        url = 'https://www.investing.com/economic-calendar/'
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"HTTP error: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        return self._parse_html(soup)
    
    async def _collect_selenium(
        self,
        from_date: date,
        to_date: date,
        countries: Optional[list[str]] = None,
        importances: Optional[list[str]] = None,
    ) -> list[EconomicEvent]:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from bs4 import BeautifulSoup
        import time
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            driver.get('https://www.investing.com/economic-calendar/')
            time.sleep(5)
            
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            return self._parse_html(soup)
        finally:
            driver.quit()
    
    def _parse_dataframe(self, df) -> list[EconomicEvent]:
        import hashlib
        
        events = []
        
        for _, row in df.iterrows():
            event_date = self._parse_date(str(row.get('date', '')))
            if not event_date:
                continue
            
            event_name = str(row.get('event', ''))
            event_time = str(row.get('time', ''))
            currency = str(row.get('currency', ''))
            
            key = f"{event_date}_{event_time}_{event_name}_{currency}"
            event_id = hashlib.md5(key.encode()).hexdigest()[:16]
            
            events.append(EconomicEvent(
                event_id=event_id,
                event_date=event_date,
                event_time=event_time if event_time and event_time != 'nan' else None,
                country=str(row.get('country', '')) if row.get('country') else None,
                currency=currency if currency and currency != 'nan' else None,
                importance=self._map_importance(row.get('importance', 'low')),
                event_name=event_name,
                actual=str(row.get('actual', '')) if row.get('actual') else None,
                forecast=str(row.get('forecast', '')) if row.get('forecast') else None,
                previous=str(row.get('previous', '')) if row.get('previous') else None,
            ))
        
        return events
    
    def _parse_html(self, soup) -> list[EconomicEvent]:
        import hashlib
        
        events = []
        event_rows = soup.find_all('tr', class_=lambda x: x and 'js-event-item' in x if x else False)
        
        for row in event_rows:
            try:
                event = {}
                
                date_elem = row.find('td', class_='date')
                if date_elem:
                    event['date'] = date_elem.get_text(strip=True)
                
                time_elem = row.find('td', class_='time')
                if time_elem:
                    event['time'] = time_elem.get_text(strip=True)
                
                currency_elem = row.find('td', class_='flag')
                if currency_elem:
                    event['currency'] = currency_elem.get_text(strip=True)
                
                importance_elem = row.find('td', class_='sentiment')
                if importance_elem:
                    bull_icons = importance_elem.find_all('i', class_='grayFullBullishIcon')
                    importance_map = {3: 'high', 2: 'medium', 1: 'low'}
                    event['importance'] = importance_map.get(len(bull_icons), 'low')
                
                event_elem = row.find('td', class_='event')
                if event_elem:
                    event['event'] = event_elem.get_text(strip=True)
                
                actual_elem = row.find('td', class_='act')
                if actual_elem:
                    event['actual'] = actual_elem.get_text(strip=True)
                
                forecast_elem = row.find('td', class_='fore')
                if forecast_elem:
                    event['forecast'] = forecast_elem.get_text(strip=True)
                
                previous_elem = row.find('td', class_='prev')
                if previous_elem:
                    event['previous'] = previous_elem.get_text(strip=True)
                
                event_date = self._parse_date(event.get('date', ''))
                if not event_date or not event.get('event'):
                    continue
                
                event_name = event.get('event', '')
                event_time = event.get('time', '')
                currency = event.get('currency', '')
                
                key = f"{event_date}_{event_time}_{event_name}_{currency}"
                event_id = hashlib.md5(key.encode()).hexdigest()[:16]
                
                events.append(EconomicEvent(
                    event_id=event_id,
                    event_date=event_date,
                    event_time=event_time,
                    country=currency,
                    currency=currency,
                    importance=event.get('importance', 'low'),
                    event_name=event_name,
                    actual=event.get('actual'),
                    forecast=event.get('forecast'),
                    previous=event.get('previous'),
                ))
                
            except Exception as e:
                logger.debug(f"Failed to parse event row: {e}")
                continue
        
        return events
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        if not date_str:
            return None
        
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%b %d, %Y', '%Y年%m月%d日']:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None
    
    def _map_importance(self, value: Any) -> str:
        if isinstance(value, str):
            value = value.lower()
            if value in ['high', 'high importance']:
                return 'high'
            elif value in ['medium', 'medium importance']:
                return 'medium'
            elif value in ['low', 'low importance']:
                return 'low'
        return 'low'
