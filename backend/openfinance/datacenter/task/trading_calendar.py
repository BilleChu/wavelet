"""
Trading Calendar Service for A-share market.

Provides utilities to determine trading days, excluding:
- Weekends (Saturday, Sunday)
- Chinese statutory holidays
- Market closure days
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class TradingCalendar:
    """
    A-share trading calendar service.
    
    Determines trading days based on:
    1. Weekends (Saturday, Sunday) - always non-trading
    2. Chinese statutory holidays
    3. Database historical data (inferred trading days)
    """
    
    _instance: Optional["TradingCalendar"] = None
    
    CHINESE_HOLIDAYS_2024 = {
        date(2024, 1, 1),   
        date(2024, 2, 10), date(2024, 2, 11), date(2024, 2, 12),
        date(2024, 2, 13), date(2024, 2, 14), date(2024, 2, 15),
        date(2024, 2, 16), date(2024, 2, 17),
        date(2024, 4, 4), date(2024, 4, 5), date(2024, 4, 6),
        date(2024, 5, 1), date(2024, 5, 2), date(2024, 5, 3),
        date(2024, 5, 4), date(2024, 5, 5),
        date(2024, 6, 10),
        date(2024, 9, 15), date(2024, 9, 16), date(2024, 9, 17),
        date(2024, 10, 1), date(2024, 10, 2), date(2024, 10, 3),
        date(2024, 10, 4), date(2024, 10, 7),
    }
    
    CHINESE_HOLIDAYS_2025 = {
        date(2025, 1, 1),
        date(2025, 1, 28), date(2025, 1, 29), date(2025, 1, 30),
        date(2025, 1, 31), date(2025, 2, 1), date(2025, 2, 2),
        date(2025, 2, 3), date(2025, 2, 4),
        date(2025, 4, 4), date(2025, 4, 5), date(2025, 4, 6),
        date(2025, 5, 1), date(2025, 5, 2), date(2025, 5, 3),
        date(2025, 5, 4), date(2025, 5, 5),
        date(2025, 5, 31), date(2025, 6, 1), date(2025, 6, 2),
        date(2025, 10, 1), date(2025, 10, 2), date(2025, 10, 3),
        date(2025, 10, 4), date(2025, 10, 5), date(2025, 10, 6),
        date(2025, 10, 7), date(2025, 10, 8),
    }
    
    CHINESE_HOLIDAYS_2026 = {
        date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3),
        date(2026, 2, 16), date(2026, 2, 17), date(2026, 2, 18),
        date(2026, 2, 19), date(2026, 2, 20),
        date(2026, 4, 5), date(2026, 4, 6), date(2026, 4, 7),
        date(2026, 5, 1), date(2026, 5, 2), date(2026, 5, 3),
        date(2026, 5, 4), date(2026, 5, 5),
        date(2026, 6, 19), date(2026, 6, 20), date(2026, 6, 21),
        date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3),
        date(2026, 10, 4), date(2026, 10, 5), date(2026, 10, 6),
        date(2026, 10, 7), date(2026, 10, 8),
    }
    
    ALL_HOLIDAYS = CHINESE_HOLIDAYS_2024 | CHINESE_HOLIDAYS_2025 | CHINESE_HOLIDAYS_2026
    
    def __new__(cls) -> "TradingCalendar":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._trading_days_cache: set[date] = set()
            cls._instance._cache_loaded = False
        return cls._instance
    
    def is_weekend(self, d: date) -> bool:
        """Check if the date is a weekend."""
        return d.weekday() >= 5
    
    def is_holiday(self, d: date) -> bool:
        """Check if the date is a Chinese statutory holiday."""
        return d in self.ALL_HOLIDAYS
    
    def is_trading_day(self, d: date) -> bool:
        """
        Check if the date is a trading day.
        
        A trading day must:
        1. Not be a weekend
        2. Not be a statutory holiday
        """
        if self.is_weekend(d):
            return False
        if self.is_holiday(d):
            return False
        return True
    
    def get_previous_trading_day(self, d: Optional[date] = None, max_lookback: int = 30) -> date:
        """
        Get the most recent trading day before the given date.
        
        Args:
            d: Reference date, defaults to today
            max_lookback: Maximum days to look back
            
        Returns:
            The most recent trading day
        """
        if d is None:
            d = date.today()
        
        current = d
        for _ in range(max_lookback):
            current = current - timedelta(days=1)
            if self.is_trading_day(current):
                return current
        
        logger.warning(f"No trading day found in last {max_lookback} days from {d}")
        return current
    
    def get_next_trading_day(self, d: Optional[date] = None, max_lookahead: int = 30) -> date:
        """
        Get the next trading day after the given date.
        
        Args:
            d: Reference date, defaults to today
            max_lookahead: Maximum days to look ahead
            
        Returns:
            The next trading day
        """
        if d is None:
            d = date.today()
        
        current = d
        for _ in range(max_lookahead):
            current = current + timedelta(days=1)
            if self.is_trading_day(current):
                return current
        
        logger.warning(f"No trading day found in next {max_lookahead} days from {d}")
        return current
    
    def get_latest_trading_day(self, d: Optional[date] = None) -> date:
        """
        Get the latest trading day (today if it's a trading day, otherwise previous).
        
        Args:
            d: Reference date, defaults to today
            
        Returns:
            The latest trading day
        """
        if d is None:
            d = date.today()
        
        if self.is_trading_day(d):
            return d
        return self.get_previous_trading_day(d)
    
    def get_trading_days_between(
        self, 
        start_date: date, 
        end_date: date
    ) -> list[date]:
        """
        Get all trading days between two dates (inclusive).
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of trading days
        """
        trading_days = []
        current = start_date
        
        while current <= end_date:
            if self.is_trading_day(current):
                trading_days.append(current)
            current = current + timedelta(days=1)
        
        return trading_days
    
    def get_recent_trading_days(self, count: int = 5, end_date: Optional[date] = None) -> list[date]:
        """
        Get the most recent N trading days.
        
        Args:
            count: Number of trading days to return
            end_date: End date, defaults to today
            
        Returns:
            List of recent trading days (most recent last)
        """
        if end_date is None:
            end_date = date.today()
        
        trading_days = []
        current = end_date
        
        while len(trading_days) < count:
            if self.is_trading_day(current):
                trading_days.append(current)
            current = current - timedelta(days=1)
        
        return list(reversed(trading_days))
    
    async def get_trading_days_from_db(
        self, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_stocks: int = 100
    ) -> list[date]:
        """
        Get trading days from database (inferred from actual trading data).
        
        This is more accurate as it reflects actual market data.
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            min_stocks: Minimum number of stocks to consider a valid trading day
            
        Returns:
            List of trading days
        """
        from ..persistence import persistence
        from sqlalchemy import text
        
        query_parts = [
            "SELECT DISTINCT trade_date FROM openfinance.stock_daily_quote",
            f"HAVING COUNT(DISTINCT code) >= {min_stocks}"
        ]
        
        conditions = []
        params = {}
        
        if start_date:
            conditions.append("trade_date >= :start_date")
            params["start_date"] = start_date
        if end_date:
            conditions.append("trade_date <= :end_date")
            params["end_date"] = end_date
        
        if conditions:
            query_parts.insert(1, "WHERE " + " AND ".join(conditions))
        
        query_parts.append("ORDER BY trade_date")
        
        query = text(" ".join(query_parts))
        
        async with persistence.session_maker() as session:
            result = await session.execute(query, params)
            return [row[0] for row in result.fetchall()]


trading_calendar = TradingCalendar()


def get_trading_calendar() -> TradingCalendar:
    """Get the singleton trading calendar instance."""
    return trading_calendar


def is_trading_day(d: Optional[date] = None) -> bool:
    """Check if a date is a trading day."""
    if d is None:
        d = date.today()
    return trading_calendar.is_trading_day(d)


def get_latest_trading_day(d: Optional[date] = None) -> date:
    """Get the latest trading day."""
    return trading_calendar.get_latest_trading_day(d)


def get_previous_trading_day(d: Optional[date] = None) -> date:
    """Get the previous trading day."""
    return trading_calendar.get_previous_trading_day(d)
