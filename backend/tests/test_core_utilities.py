"""
Tests for Core Utility Modules.

Tests for converters, code_utils, and other core utilities.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal

from openfinance.datacenter.core.converters import (
    ValueConverter,
    DateConverter,
    PercentageConverter,
    safe_float,
    safe_int,
    safe_str,
    safe_decimal,
)
from openfinance.datacenter.core.code_utils import (
    CodeUtils,
    Exchange,
    CodeFormat,
    normalize_code,
    format_code,
    validate_code,
)


class TestValueConverter:
    """Tests for ValueConverter class."""

    def test_to_float_with_valid_float(self):
        assert ValueConverter.to_float(123.45) == 123.45

    def test_to_float_with_valid_int(self):
        assert ValueConverter.to_float(123) == 123.0

    def test_to_float_with_valid_string(self):
        assert ValueConverter.to_float("123.45") == 123.45

    def test_to_float_with_comma_string(self):
        assert ValueConverter.to_float("1,234.56") == 1234.56

    def test_to_float_with_percentage_string(self):
        assert ValueConverter.to_float("5.5%") == 5.5

    def test_to_float_with_dash(self):
        assert ValueConverter.to_float("-") is None
        assert ValueConverter.to_float("--") is None

    def test_to_float_with_empty_string(self):
        assert ValueConverter.to_float("") is None

    def test_to_float_with_none(self):
        assert ValueConverter.to_float(None) is None

    def test_to_float_with_default(self):
        assert ValueConverter.to_float(None, default=0.0) == 0.0

    def test_to_float_with_precision(self):
        assert ValueConverter.to_float("123.456", precision=2) == 123.46

    def test_to_int_with_valid_int(self):
        assert ValueConverter.to_int(123) == 123

    def test_to_int_with_valid_float(self):
        assert ValueConverter.to_int(123.9) == 123

    def test_to_int_with_valid_string(self):
        assert ValueConverter.to_int("123") == 123

    def test_to_int_with_comma_string(self):
        assert ValueConverter.to_int("1,234") == 1234

    def test_to_int_with_float_string(self):
        assert ValueConverter.to_int("123.9") == 123

    def test_to_int_with_dash(self):
        assert ValueConverter.to_int("-") is None

    def test_to_int_with_none(self):
        assert ValueConverter.to_int(None) is None

    def test_to_int_with_default(self):
        assert ValueConverter.to_int(None, default=0) == 0

    def test_to_str_with_valid_string(self):
        assert ValueConverter.to_str("hello") == "hello"

    def test_to_str_with_int(self):
        assert ValueConverter.to_str(123) == "123"

    def test_to_str_with_none(self):
        assert ValueConverter.to_str(None) is None

    def test_to_str_with_default(self):
        assert ValueConverter.to_str(None, default="N/A") == "N/A"

    def test_to_str_with_strip(self):
        assert ValueConverter.to_str("  hello  ") == "hello"

    def test_to_str_without_strip(self):
        assert ValueConverter.to_str("  hello  ", strip=False) == "  hello  "

    def test_to_decimal_with_valid_decimal(self):
        assert ValueConverter.to_decimal(Decimal("123.45")) == Decimal("123.45")

    def test_to_decimal_with_valid_string(self):
        assert ValueConverter.to_decimal("123.45") == Decimal("123.45")

    def test_to_decimal_with_none(self):
        assert ValueConverter.to_decimal(None) is None

    def test_to_bool_with_true_string(self):
        assert ValueConverter.to_bool("true") is True
        assert ValueConverter.to_bool("yes") is True
        assert ValueConverter.to_bool("1") is True

    def test_to_bool_with_false_string(self):
        assert ValueConverter.to_bool("false") is False
        assert ValueConverter.to_bool("no") is False
        assert ValueConverter.to_bool("0") is False

    def test_to_bool_with_none(self):
        assert ValueConverter.to_bool(None) is None


class TestDateConverter:
    """Tests for DateConverter class."""

    def test_to_date_with_date(self):
        d = date(2024, 1, 15)
        assert DateConverter.to_date(d) == d

    def test_to_date_with_datetime(self):
        dt = datetime(2024, 1, 15, 10, 30)
        assert DateConverter.to_date(dt) == date(2024, 1, 15)

    def test_to_date_with_iso_string(self):
        assert DateConverter.to_date("2024-01-15") == date(2024, 1, 15)

    def test_to_date_with_slash_string(self):
        assert DateConverter.to_date("2024/01/15") == date(2024, 1, 15)

    def test_to_date_with_compact_string(self):
        assert DateConverter.to_date("20240115") == date(2024, 1, 15)

    def test_to_date_with_none(self):
        assert DateConverter.to_date(None) is None

    def test_to_date_with_default(self):
        default = date(2020, 1, 1)
        assert DateConverter.to_date(None, default=default) == default

    def test_to_datetime_with_datetime(self):
        dt = datetime(2024, 1, 15, 10, 30)
        assert DateConverter.to_datetime(dt) == dt

    def test_to_datetime_with_date(self):
        d = date(2024, 1, 15)
        result = DateConverter.to_datetime(d)
        assert result == datetime(2024, 1, 15, 0, 0)

    def test_to_datetime_with_iso_string(self):
        result = DateConverter.to_datetime("2024-01-15T10:30:00")
        assert result == datetime(2024, 1, 15, 10, 30)


class TestPercentageConverter:
    """Tests for PercentageConverter class."""

    def test_to_decimal_with_percentage_string(self):
        assert PercentageConverter.to_decimal("5.5%") == 0.055

    def test_to_decimal_with_decimal_value(self):
        assert PercentageConverter.to_decimal(0.055) == 0.055

    def test_to_decimal_with_large_value(self):
        assert PercentageConverter.to_decimal(5.5, is_percentage=True) == 0.055

    def test_from_decimal(self):
        assert PercentageConverter.from_decimal(0.055) == "5.50%"

    def test_from_decimal_with_precision(self):
        assert PercentageConverter.from_decimal(0.055, precision=4) == "5.5000%"


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_safe_float(self):
        assert safe_float("123.45") == 123.45
        assert safe_float(None, default=0.0) == 0.0

    def test_safe_int(self):
        assert safe_int("123") == 123
        assert safe_int(None, default=0) == 0

    def test_safe_str(self):
        assert safe_str("hello") == "hello"
        assert safe_str(None, default="N/A") == "N/A"

    def test_safe_decimal(self):
        assert safe_decimal("123.45") == Decimal("123.45")


class TestCodeUtils:
    """Tests for CodeUtils class."""

    def test_normalize_with_standard_code(self):
        assert CodeUtils.normalize("600000") == "600000"

    def test_normalize_with_exchange_prefix(self):
        assert CodeUtils.normalize("SH600000") == "600000"
        assert CodeUtils.normalize("sz000001") == "000001"

    def test_normalize_with_eastmoney_format(self):
        assert CodeUtils.normalize("1.600000") == "600000"
        assert CodeUtils.normalize("0.000001") == "000001"

    def test_normalize_with_tushare_format(self):
        assert CodeUtils.normalize("600000.SH") == "600000"
        assert CodeUtils.normalize("000001.SZ") == "000001"

    def test_normalize_with_short_code(self):
        assert CodeUtils.normalize("1") == "000001"

    def test_get_exchange_shanghai(self):
        assert CodeUtils.get_exchange("600000") == Exchange.SH
        assert CodeUtils.get_exchange("688001") == Exchange.SH

    def test_get_exchange_shenzhen(self):
        assert CodeUtils.get_exchange("000001") == Exchange.SZ
        assert CodeUtils.get_exchange("300001") == Exchange.SZ

    def test_get_exchange_beijing(self):
        assert CodeUtils.get_exchange("430001") == Exchange.BJ
        assert CodeUtils.get_exchange("830001") == Exchange.BJ

    def test_to_eastmoney_format_shanghai(self):
        assert CodeUtils.to_eastmoney_format("600000") == "1.600000"

    def test_to_eastmoney_format_shenzhen(self):
        assert CodeUtils.to_eastmoney_format("000001") == "0.000001"

    def test_to_tushare_format(self):
        assert CodeUtils.to_tushare_format("600000") == "600000.SH"
        assert CodeUtils.to_tushare_format("000001") == "000001.SZ"

    def test_to_sina_format(self):
        assert CodeUtils.to_sina_format("600000") == "sh600000"
        assert CodeUtils.to_sina_format("000001") == "sz000001"

    def test_is_valid(self):
        assert CodeUtils.is_valid("600000") is True
        assert CodeUtils.is_valid("000001") is True
        assert CodeUtils.is_valid("123") is False
        assert CodeUtils.is_valid("abcdef") is False

    def test_get_market_code(self):
        assert CodeUtils.get_market_code("600000") == "1"
        assert CodeUtils.get_market_code("000001") == "0"


class TestConvenienceCodeFunctions:
    """Tests for convenience code functions."""

    def test_normalize_code(self):
        assert normalize_code("SH600000") == "600000"

    def test_format_code_standard(self):
        assert format_code("SH600000", CodeFormat.STANDARD) == "600000"

    def test_format_code_eastmoney(self):
        assert format_code("600000", CodeFormat.EASTMONEY) == "1.600000"

    def test_format_code_tushare(self):
        assert format_code("600000", CodeFormat.TUSHARE) == "600000.SH"

    def test_validate_code_valid(self):
        is_valid, message = validate_code("600000")
        assert is_valid is True
        assert "上海证券交易所" in message

    def test_validate_code_invalid(self):
        is_valid, message = validate_code("123")
        assert is_valid is False
        assert "Invalid code length" in message

    def test_validate_code_empty(self):
        is_valid, message = validate_code("")
        assert is_valid is False
        assert "empty" in message.lower()
