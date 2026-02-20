"""
Type Conversion Utilities.

Provides unified type conversion functions to eliminate duplicate
_safe_float, _safe_int, etc. methods across collectors.

Usage:
    from datacenter.core import safe_float, safe_int, ValueConverter
    
    value = safe_float(data.get("price"), default=0.0)
    volume = safe_int(data.get("vol"), default=None)
"""

from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from typing import Any, Callable, TypeVar
import re

T = TypeVar("T")


class ValueConverter:
    """
    Unified value conversion utilities.
    
    Provides static methods for safe type conversion with
    configurable default values and error handling.
    """
    
    @staticmethod
    def to_float(
        value: Any,
        default: float | None = None,
        precision: int | None = None,
    ) -> float | None:
        """
        Safely convert value to float.
        
        Args:
            value: Input value to convert
            default: Default value if conversion fails
            precision: Optional decimal precision to round to
            
        Returns:
            Converted float or default value
            
        Examples:
            >>> ValueConverter.to_float("123.45")
            123.45
            >>> ValueConverter.to_float("invalid", default=0.0)
            0.0
            >>> ValueConverter.to_float("123.456", precision=2)
            123.46
        """
        if value is None:
            return default
        
        if isinstance(value, float):
            result = value
        elif isinstance(value, int):
            result = float(value)
        elif isinstance(value, Decimal):
            result = float(value)
        elif isinstance(value, str):
            cleaned = value.strip().replace(",", "").replace("%", "")
            if not cleaned or cleaned == "-" or cleaned == "--":
                return default
            try:
                result = float(cleaned)
            except ValueError:
                return default
        else:
            try:
                result = float(value)
            except (TypeError, ValueError):
                return default
        
        if precision is not None:
            result = round(result, precision)
        
        return result
    
    @staticmethod
    def to_int(
        value: Any,
        default: int | None = None,
    ) -> int | None:
        """
        Safely convert value to integer.
        
        Args:
            value: Input value to convert
            default: Default value if conversion fails
            
        Returns:
            Converted integer or default value
        """
        if value is None:
            return default
        
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        
        if isinstance(value, float):
            return int(value)
        
        if isinstance(value, str):
            cleaned = value.strip().replace(",", "")
            if not cleaned or cleaned == "-" or cleaned == "--":
                return default
            try:
                if "." in cleaned:
                    return int(float(cleaned))
                return int(cleaned)
            except ValueError:
                return default
        
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    
    @staticmethod
    def to_str(
        value: Any,
        default: str | None = None,
        strip: bool = True,
    ) -> str | None:
        """
        Safely convert value to string.
        
        Args:
            value: Input value to convert
            default: Default value if conversion fails
            strip: Whether to strip whitespace
            
        Returns:
            Converted string or default value
        """
        if value is None:
            return default
        
        if isinstance(value, str):
            result = value
        else:
            result = str(value)
        
        if strip:
            result = result.strip()
        
        return result if result else default
    
    @staticmethod
    def to_decimal(
        value: Any,
        default: Decimal | None = None,
        precision: int | None = None,
    ) -> Decimal | None:
        """
        Safely convert value to Decimal.
        
        Args:
            value: Input value to convert
            default: Default value if conversion fails
            precision: Optional decimal precision
            
        Returns:
            Converted Decimal or default value
        """
        if value is None:
            return default
        
        try:
            if isinstance(value, Decimal):
                result = value
            elif isinstance(value, str):
                cleaned = value.strip().replace(",", "")
                if not cleaned or cleaned == "-" or cleaned == "--":
                    return default
                result = Decimal(cleaned)
            else:
                result = Decimal(str(value))
            
            if precision is not None:
                result = result.quantize(Decimal(10) ** -precision)
            
            return result
        except (InvalidOperation, ValueError):
            return default
    
    @staticmethod
    def to_bool(
        value: Any,
        default: bool | None = None,
    ) -> bool | None:
        """
        Safely convert value to boolean.
        
        Args:
            value: Input value to convert
            default: Default value if conversion fails
            
        Returns:
            Converted boolean or default value
        """
        if value is None:
            return default
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            lower = value.strip().lower()
            if lower in ("true", "yes", "1", "on"):
                return True
            if lower in ("false", "no", "0", "off"):
                return False
            return default
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        return default


class DateConverter:
    """
    Date conversion utilities.
    
    Handles various date formats commonly encountered in financial data.
    """
    
    COMMON_FORMATS = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
    ]
    
    @classmethod
    def to_date(
        cls,
        value: Any,
        default: date | None = None,
        format: str | None = None,
    ) -> date | None:
        """
        Safely convert value to date.
        
        Args:
            value: Input value to convert
            default: Default value if conversion fails
            format: Optional specific format to use
            
        Returns:
            Converted date or default value
        """
        if value is None:
            return default
        
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        
        if isinstance(value, datetime):
            return value.date()
        
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return default
            
            if format:
                try:
                    return datetime.strptime(cleaned, format).date()
                except ValueError:
                    pass
            
            for fmt in cls.COMMON_FORMATS:
                try:
                    return datetime.strptime(cleaned, fmt).date()
                except ValueError:
                    continue
            
            try:
                return datetime.fromisoformat(cleaned).date()
            except ValueError:
                pass
        
        return default
    
    @classmethod
    def to_datetime(
        cls,
        value: Any,
        default: datetime | None = None,
        format: str | None = None,
    ) -> datetime | None:
        """
        Safely convert value to datetime.
        
        Args:
            value: Input value to convert
            default: Default value if conversion fails
            format: Optional specific format to use
            
        Returns:
            Converted datetime or default value
        """
        if value is None:
            return default
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return default
            
            if format:
                try:
                    return datetime.strptime(cleaned, format)
                except ValueError:
                    pass
            
            for fmt in cls.COMMON_FORMATS:
                try:
                    return datetime.strptime(cleaned, fmt)
                except ValueError:
                    continue
            
            try:
                return datetime.fromisoformat(cleaned)
            except ValueError:
                pass
        
        return default


class PercentageConverter:
    """
    Percentage and ratio conversion utilities.
    """
    
    @staticmethod
    def to_decimal(
        value: Any,
        default: float | None = None,
        is_percentage: bool = True,
    ) -> float | None:
        """
        Convert percentage/ratio string to decimal.
        
        Args:
            value: Input value (e.g., "5.5%", "0.055")
            default: Default value if conversion fails
            is_percentage: Whether input is percentage format
            
        Returns:
            Decimal value (e.g., 0.055)
        """
        if value is None:
            return default
        
        if isinstance(value, (int, float)):
            if is_percentage and abs(value) > 1:
                return value / 100
            return float(value)
        
        if isinstance(value, str):
            cleaned = value.strip().replace(",", "")
            if not cleaned:
                return default
            
            is_pct = "%" in cleaned
            cleaned = cleaned.replace("%", "")
            
            try:
                result = float(cleaned)
                if is_pct:
                    result = result / 100
                return result
            except ValueError:
                return default
        
        return default
    
    @staticmethod
    def from_decimal(
        value: float | None,
        precision: int = 2,
        as_percentage: bool = True,
    ) -> str | None:
        """
        Convert decimal to percentage string.
        
        Args:
            value: Decimal value (e.g., 0.055)
            precision: Decimal precision
            as_percentage: Whether to output as percentage
            
        Returns:
            Percentage string (e.g., "5.50%")
        """
        if value is None:
            return None
        
        if as_percentage:
            return f"{value * 100:.{precision}f}%"
        return f"{value:.{precision}f}"


def safe_float(
    value: Any,
    default: float | None = None,
    precision: int | None = None,
) -> float | None:
    """Convenience function for ValueConverter.to_float."""
    return ValueConverter.to_float(value, default, precision)


def safe_int(
    value: Any,
    default: int | None = None,
) -> int | None:
    """Convenience function for ValueConverter.to_int."""
    return ValueConverter.to_int(value, default)


def safe_str(
    value: Any,
    default: str | None = None,
    strip: bool = True,
) -> str | None:
    """Convenience function for ValueConverter.to_str."""
    return ValueConverter.to_str(value, default, strip)


def safe_decimal(
    value: Any,
    default: Decimal | None = None,
    precision: int | None = None,
) -> Decimal | None:
    """Convenience function for ValueConverter.to_decimal."""
    return ValueConverter.to_decimal(value, default, precision)
