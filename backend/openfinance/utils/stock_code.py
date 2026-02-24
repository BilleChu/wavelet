"""
股票代码规范化工具

统一处理股票代码格式：
- 支持 6 位数字代码 (000001)
- 支持 Wind 格式 (000001.SZ)
- 支持 东财格式 (000001.SZ)

统一输出：6 位数字代码
"""

import re
from typing import Optional


def normalize_stock_code(code: str) -> str:
    """
    规范化股票代码为 6 位数字格式。
    
    支持的输入格式：
    - "000001" -> "000001"
    - "000001.SZ" -> "000001"
    - "000001.SH" -> "000001"
    - "SZ000001" -> "000001"
    - "SH600000" -> "600000"
    
    Args:
        code: 原始股票代码
        
    Returns:
        6 位数字股票代码
    """
    if not code:
        return code
    
    code = code.strip().upper()
    
    # 处理 SH600000 或 SZ000001 格式
    if code.startswith(('SH', 'SZ', 'BJ')):
        code = code[2:]
    
    # 处理 000001.SZ 或 000001.SH 格式
    if '.' in code:
        code = code.split('.')[0]
    
    # 验证是否为 6 位数字
    if re.match(r'^\d{6}$', code):
        return code
    
    # 如果不是 6 位数字，返回原始代码（让调用方处理）
    return code


def get_stock_exchange(code: str) -> Optional[str]:
    """
    根据股票代码判断交易所。
    
    Args:
        code: 6 位股票代码
        
    Returns:
        交易所代码: "SH" (上海), "SZ" (深圳), "BJ" (北交所), None (未知)
    """
    if not code or len(code) != 6:
        return None
    
    code = code.strip()
    
    if not code.isdigit():
        return None
    
    # 上海交易所
    if code.startswith(('60', '68')):
        return 'SH'
    
    # 深圳交易所
    if code.startswith(('00', '30')):
        return 'SZ'
    
    # 北交所
    if code.startswith(('82', '83', '87', '88')):
        return 'BJ'
    
    return None


def format_stock_code_with_exchange(code: str, exchange: Optional[str] = None) -> str:
    """
    格式化股票代码为带交易所后缀的格式。
    
    Args:
        code: 6 位股票代码
        exchange: 交易所代码，如果不提供则自动判断
        
    Returns:
        带交易所后缀的股票代码，如 "000001.SZ"
    """
    normalized = normalize_stock_code(code)
    
    if exchange is None:
        exchange = get_stock_exchange(normalized)
    
    if exchange:
        return f"{normalized}.{exchange}"
    
    return normalized


def is_valid_stock_code(code: str) -> bool:
    """
    检查是否为有效的股票代码格式。
    
    Args:
        code: 股票代码
        
    Returns:
        是否有效
    """
    normalized = normalize_stock_code(code)
    return bool(re.match(r'^\d{6}$', normalized))
