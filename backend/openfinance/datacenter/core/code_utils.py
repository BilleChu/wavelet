"""
Stock Code Utilities.

Provides unified stock code conversion and validation utilities.
Supports multiple exchange formats and normalization.

Usage:
    from datacenter.core import CodeUtils, normalize_code
    
    code = normalize_code("SH600000")  # "600000"
    em_code = CodeUtils.to_eastmoney_format("600000")  # "1.600000"
"""

from enum import Enum
from typing import Optional
import re


class Exchange(str, Enum):
    """Stock exchange identifiers."""
    SH = "sh"      # Shanghai Stock Exchange
    SZ = "sz"      # Shenzhen Stock Exchange
    BJ = "bj"      # Beijing Stock Exchange
    HK = "hk"      # Hong Kong Stock Exchange
    US = "us"      # US Markets
    
    @property
    def display_name(self) -> str:
        names = {
            "sh": "上海证券交易所",
            "sz": "深圳证券交易所",
            "bj": "北京证券交易所",
            "hk": "香港交易所",
            "us": "美国市场",
        }
        return names.get(self.value, self.value)


class CodeFormat(str, Enum):
    """Stock code format types."""
    STANDARD = "standard"           # 6-digit: "600000"
    WITH_EXCHANGE = "with_exchange" # With exchange: "600000.SH"
    EASTMONEY = "eastmoney"         # EastMoney format: "1.600000"
    TUSHARE = "tushare"             # Tushare format: "600000.SH"
    WIND = "wind"                   # Wind format: "600000.SH"
    SINAFINANCE = "sina"            # Sina format: "sh600000"


class CodeUtils:
    """
    Unified stock code conversion utilities.
    
    Supports conversion between different formats used by
    various data providers.
    """
    
    SH_PREFIXES = ("60", "68", "50", "51", "52", "58", "11", "13")
    SZ_PREFIXES = ("00", "30", "12", "15", "16", "18", "20", "30")
    BJ_PREFIXES = ("4", "8")
    
    @classmethod
    def normalize(cls, code: str) -> str:
        """
        Normalize stock code to 6-digit format.
        
        Args:
            code: Input code in any format
            
        Returns:
            6-digit code string
            
        Examples:
            >>> CodeUtils.normalize("SH600000")
            "600000"
            >>> CodeUtils.normalize("1.600000")
            "600000"
            >>> CodeUtils.normalize("sh600000")
            "600000"
        """
        if not code:
            return ""
        
        code = code.strip().upper()
        
        code = re.sub(r"^(SH|SZ|BJ|HK|US)", "", code, flags=re.IGNORECASE)
        
        code = re.sub(r"^[0-9]\.", "", code)
        
        code = re.sub(r"\.(SH|SZ|BJ|HK|US)$", "", code, flags=re.IGNORECASE)
        
        if len(code) < 6:
            code = code.zfill(6)
        
        return code
    
    @classmethod
    def get_exchange(cls, code: str) -> Exchange | None:
        """
        Determine exchange from stock code.
        
        Args:
            code: Stock code (6-digit format preferred)
            
        Returns:
            Exchange enum or None if unknown
        """
        normalized = cls.normalize(code)
        
        if not normalized or len(normalized) != 6:
            return None
        
        if normalized.startswith(cls.SH_PREFIXES):
            return Exchange.SH
        elif normalized.startswith(cls.SZ_PREFIXES):
            return Exchange.SZ
        elif normalized.startswith(cls.BJ_PREFIXES):
            return Exchange.BJ
        
        return None
    
    @classmethod
    def to_eastmoney_format(cls, code: str) -> str:
        """
        Convert to EastMoney API format.
        
        Args:
            code: Stock code in any format
            
        Returns:
            EastMoney format (e.g., "1.600000" for SH, "0.000001" for SZ)
            
        Examples:
            >>> CodeUtils.to_eastmoney_format("600000")
            "1.600000"
            >>> CodeUtils.to_eastmoney_format("000001")
            "0.000001"
        """
        normalized = cls.normalize(code)
        exchange = cls.get_exchange(normalized)
        
        if exchange == Exchange.SH:
            return f"1.{normalized}"
        elif exchange == Exchange.SZ:
            return f"0.{normalized}"
        elif exchange == Exchange.BJ:
            return f"0.{normalized}"
        
        return f"1.{normalized}"
    
    @classmethod
    def to_tushare_format(cls, code: str) -> str:
        """
        Convert to Tushare format.
        
        Args:
            code: Stock code in any format
            
        Returns:
            Tushare format (e.g., "600000.SH")
        """
        normalized = cls.normalize(code)
        exchange = cls.get_exchange(normalized)
        
        if exchange:
            return f"{normalized}.{exchange.value.upper()}"
        
        return normalized
    
    @classmethod
    def to_wind_format(cls, code: str) -> str:
        """
        Convert to Wind format.
        
        Args:
            code: Stock code in any format
            
        Returns:
            Wind format (e.g., "600000.SH")
        """
        return cls.to_tushare_format(code)
    
    @classmethod
    def to_sina_format(cls, code: str) -> str:
        """
        Convert to Sina Finance format.
        
        Args:
            code: Stock code in any format
            
        Returns:
            Sina format (e.g., "sh600000")
        """
        normalized = cls.normalize(code)
        exchange = cls.get_exchange(normalized)
        
        if exchange:
            return f"{exchange.value}{normalized}"
        
        return normalized
    
    @classmethod
    def to_eastmoney_secid(cls, code: str) -> str:
        """
        Convert to EastMoney SECID format.
        
        Args:
            code: Stock code in any format
            
        Returns:
            SECID format (e.g., "1.600000")
        """
        return cls.to_eastmoney_format(code)
    
    @classmethod
    def is_valid(cls, code: str) -> bool:
        """
        Validate stock code format.
        
        Args:
            code: Stock code to validate
            
        Returns:
            True if valid 6-digit code
        """
        normalized = cls.normalize(code)
        
        if not normalized or len(normalized) != 6:
            return False
        
        if not normalized.isdigit():
            return False
        
        return cls.get_exchange(normalized) is not None
    
    @classmethod
    def get_market_code(cls, code: str) -> str:
        """
        Get market code for EastMoney API.
        
        Args:
            code: Stock code
            
        Returns:
            Market code ("1" for SH, "0" for SZ)
        """
        exchange = cls.get_exchange(code)
        
        if exchange == Exchange.SH:
            return "1"
        elif exchange == Exchange.SZ:
            return "0"
        
        return "1"
    
    @classmethod
    def format_display(cls, code: str, name: str | None = None) -> str:
        """
        Format code for display.
        
        Args:
            code: Stock code
            name: Optional stock name
            
        Returns:
            Display string (e.g., "600000.SH 浦发银行")
        """
        normalized = cls.normalize(code)
        exchange = cls.get_exchange(normalized)
        
        if exchange:
            result = f"{normalized}.{exchange.value.upper()}"
        else:
            result = normalized
        
        if name:
            result = f"{result} {name}"
        
        return result


def normalize_code(code: str) -> str:
    """Convenience function for CodeUtils.normalize."""
    return CodeUtils.normalize(code)


def format_code(code: str, format: CodeFormat = CodeFormat.STANDARD) -> str:
    """
    Format stock code to specified format.
    
    Args:
        code: Stock code in any format
        format: Target format
        
    Returns:
        Formatted code string
    """
    normalized = CodeUtils.normalize(code)
    
    if format == CodeFormat.STANDARD:
        return normalized
    elif format == CodeFormat.EASTMONEY:
        return CodeUtils.to_eastmoney_format(normalized)
    elif format == CodeFormat.TUSHARE:
        return CodeUtils.to_tushare_format(normalized)
    elif format == CodeFormat.WIND:
        return CodeUtils.to_wind_format(normalized)
    elif format == CodeFormat.SINAFINANCE:
        return CodeUtils.to_sina_format(normalized)
    elif format == CodeFormat.WITH_EXCHANGE:
        return CodeUtils.to_tushare_format(normalized)
    
    return normalized


def validate_code(code: str) -> tuple[bool, str]:
    """
    Validate stock code and return result with message.
    
    Args:
        code: Stock code to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not code:
        return False, "Code cannot be empty"
    
    normalized = CodeUtils.normalize(code)
    
    if len(normalized) != 6:
        return False, f"Invalid code length: {len(normalized)}"
    
    if not normalized.isdigit():
        return False, "Code must contain only digits"
    
    exchange = CodeUtils.get_exchange(normalized)
    if exchange is None:
        return False, f"Unknown exchange for code: {normalized}"
    
    return True, f"Valid {exchange.display_name} code"
