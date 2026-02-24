"""
批量计算历史因子数据 - 完整版

包含所有注册的因子
"""
import asyncio
import logging
from datetime import date
from collections import defaultdict
import math

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://openfinance:openfinance@localhost:5432/openfinance"


async def load_all_klines(conn) -> dict:
    """加载所有K线数据到内存"""
    print("加载K线数据...")
    rows = await conn.fetch('''
        SELECT code, trade_date, open, high, low, close, volume, amount
        FROM openfinance.stock_daily_quote
        WHERE trade_date >= '2024-06-01'
        AND code NOT LIKE 'IND_%'
        AND code NOT LIKE 'CON_%'
        AND code NOT LIKE 'BK%'
        AND LENGTH(code) = 6
        ORDER BY code, trade_date
    ''')
    
    data = defaultdict(list)
    for row in rows:
        data[row['code']].append({
            'trade_date': row['trade_date'],
            'open': float(row['open']) if row['open'] else None,
            'high': float(row['high']) if row['high'] else None,
            'low': float(row['low']) if row['low'] else None,
            'close': float(row['close']) if row['close'] else None,
            'volume': row['volume'],
            'amount': float(row['amount']) if row['amount'] else None,
        })
    
    print(f"加载完成: {len(data)} 只股票")
    return data


def calculate_factors_for_stock(klines: list[dict]) -> dict:
    """计算单只股票的所有因子"""
    results = defaultdict(dict)
    
    if len(klines) < 35:
        return results
    
    klines = sorted(klines, key=lambda x: x['trade_date'])
    
    for i in range(35, len(klines)):
        trade_date = klines[i]['trade_date']
        history = klines[:i+1]
        close_prices = [k['close'] for k in history]
        
        # 1. 动量因子 (factor_momentum)
        if len(history) >= 21:
            momentum = (close_prices[-1] - close_prices[-21]) / close_prices[-21]
            results[trade_date]['factor_momentum'] = momentum
        
        # 2. 波动率因子 (factor_volatility)
        if len(history) >= 21:
            returns = []
            for j in range(1, len(history)):
                if history[j-1]['close'] and history[j]['close']:
                    ret = (history[j]['close'] - history[j-1]['close']) / history[j-1]['close']
                    returns.append(ret)
            if len(returns) >= 20:
                recent = returns[-20:]
                mean = sum(recent) / len(recent)
                variance = sum((r - mean) ** 2 for r in recent) / len(recent)
                results[trade_date]['factor_volatility'] = math.sqrt(variance * 252)
        
        # 3. RSI (factor_rsi)
        if len(history) >= 15:
            gains = []
            losses = []
            for j in range(1, len(history)):
                if history[j-1]['close'] and history[j]['close']:
                    change = history[j]['close'] - history[j-1]['close']
                    if change > 0:
                        gains.append(change)
                        losses.append(0)
                    else:
                        gains.append(0)
                        losses.append(abs(change))
            if len(gains) >= 14:
                avg_gain = sum(gains[-14:]) / 14
                avg_loss = sum(losses[-14:]) / 14
                if avg_loss == 0:
                    results[trade_date]['factor_rsi'] = 100.0
                else:
                    rs = avg_gain / avg_loss
                    results[trade_date]['factor_rsi'] = 100 - (100 / (1 + rs))
        
        # 4. SMA (factor_sma)
        if len(history) >= 20:
            sma = sum(close_prices[-20:]) / 20
            results[trade_date]['factor_sma'] = sma
        
        # 5. EMA (factor_ema)
        if len(history) >= 20:
            multiplier = 2 / 21
            ema = sum(close_prices[:20]) / 20
            for price in close_prices[20:]:
                ema = (price - ema) * multiplier + ema
            results[trade_date]['factor_ema'] = ema
        
        # 6. MACD (factor_macd)
        if len(history) >= 35:
            def calc_ema(prices, period):
                multiplier = 2 / (period + 1)
                ema_val = sum(prices[:period]) / period
                for price in prices[period:]:
                    ema_val = (price - ema_val) * multiplier + ema_val
                return ema_val
            
            ema12 = calc_ema(close_prices, 12)
            ema26 = calc_ema(close_prices, 26)
            results[trade_date]['factor_macd'] = ema12 - ema26
        
        # 7. 布林带 (factor_boll)
        if len(history) >= 20:
            ma = sum(close_prices[-20:]) / 20
            variance = sum((p - ma) ** 2 for p in close_prices[-20:]) / 20
            results[trade_date]['factor_boll'] = ma
        
        # 8. ATR (factor_atr)
        if len(history) >= 15:
            true_ranges = []
            for j in range(1, len(history)):
                high = history[j]['high']
                low = history[j]['low']
                prev_close = history[j-1]['close']
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                true_ranges.append(tr)
            if len(true_ranges) >= 14:
                results[trade_date]['factor_atr'] = sum(true_ranges[-14:]) / 14
        
        # 9. KDJ (factor_kdj)
        if len(history) >= 9:
            period = 9
            highs = [k['high'] for k in history[-period:]]
            lows = [k['low'] for k in history[-period:]]
            close = history[-1]['close']
            
            highest = max(highs)
            lowest = min(lows)
            
            if highest == lowest:
                kdj_k = 50.0
            else:
                rsv = (close - lowest) / (highest - lowest) * 100
                kdj_k = rsv
            
            results[trade_date]['factor_kdj'] = kdj_k
        
        # 10. CCI (factor_cci)
        if len(history) >= 20:
            period = 20
            tp_list = []
            for k in history[-period:]:
                if k['high'] and k['low'] and k['close']:
                    tp = (k['high'] + k['low'] + k['close']) / 3
                    tp_list.append(tp)
            
            if len(tp_list) == period:
                sma_tp = sum(tp_list) / period
                mean_dev = sum(abs(tp - sma_tp) for tp in tp_list) / period
                if mean_dev > 0:
                    cci = (tp_list[-1] - sma_tp) / (0.015 * mean_dev)
                    results[trade_date]['factor_cci'] = cci
        
        # 11. Williams %R (factor_wr)
        if len(history) >= 14:
            period = 14
            highs = [k['high'] for k in history[-period:]]
            lows = [k['low'] for k in history[-period:]]
            close = history[-1]['close']
            
            highest = max(highs)
            lowest = min(lows)
            
            if highest == lowest:
                wr = -50.0
            else:
                wr = (highest - close) / (highest - lowest) * -100
            
            results[trade_date]['factor_wr'] = wr
        
        # 12. OBV (factor_obv)
        if len(history) >= 2:
            obv = 0
            for j in range(1, len(history)):
                if history[j]['close'] and history[j-1]['close'] and history[j]['volume']:
                    if history[j]['close'] > history[j-1]['close']:
                        obv += history[j]['volume']
                    elif history[j]['close'] < history[j-1]['close']:
                        obv -= history[j]['volume']
            results[trade_date]['factor_obv'] = obv
        
        # 13. Risk-Adjusted Momentum (factor_risk_adj_momentum)
        if len(history) >= 21:
            returns = []
            for j in range(1, len(history)):
                if history[j-1]['close'] and history[j]['close']:
                    ret = (history[j]['close'] - history[j-1]['close']) / history[j-1]['close']
                    returns.append(ret)
            if len(returns) >= 20:
                momentum = sum(returns[-20:])
                std = math.sqrt(sum((r - sum(returns[-20:])/20) ** 2 for r in returns[-20:]) / 20)
                if std > 0:
                    results[trade_date]['factor_risk_adj_momentum'] = momentum / std
        
        # 14. Idiosyncratic Volatility (factor_idio_volatility)
        if len(history) >= 21:
            returns = []
            for j in range(1, len(history)):
                if history[j-1]['close'] and history[j]['close']:
                    ret = (history[j]['close'] - history[j-1]['close']) / history[j-1]['close']
                    returns.append(ret)
            if len(returns) >= 20:
                variance = sum((r - sum(returns[-20:])/20) ** 2 for r in returns[-20:]) / 20
                results[trade_date]['factor_idio_volatility'] = math.sqrt(variance * 252)
    
    return results


async def main():
    conn = await asyncpg.connect(DATABASE_URL)
    
    print("=== 批量计算历史因子数据 (完整版) ===\n")
    
    klines_data = await load_all_klines(conn)
    
    print("清理旧的因子数据...")
    await conn.execute('TRUNCATE TABLE openfinance.factor_data')
    
    print("计算因子数据...")
    all_records = []
    
    start_time = asyncio.get_event_loop().time()
    
    for i, (code, klines) in enumerate(klines_data.items()):
        factors = calculate_factors_for_stock(klines)
        
        for trade_date, factor_values in factors.items():
            for factor_id, value in factor_values.items():
                if value is not None and not math.isnan(value) and not math.isinf(value):
                    all_records.append((factor_id, code, trade_date, value))
        
        if (i + 1) % 500 == 0:
            elapsed = asyncio.get_event_loop().time() - start_time
            speed = (i + 1) / elapsed
            eta = (len(klines_data) - i - 1) / speed / 60
            print(f"[{i+1}/{len(klines_data)}] 进度 {(i+1)/len(klines_data)*100:.1f}% | ETA {eta:.1f} 分钟")
    
    print(f"\n计算完成，共 {len(all_records):,} 条记录")
    
    print("保存到数据库...")
    batch_size = 50000
    for i in range(0, len(all_records), batch_size):
        batch = all_records[i:i+batch_size]
        await conn.executemany('''
            INSERT INTO openfinance.factor_data (
                factor_id, code, trade_date, factor_name, factor_category,
                factor_value, collected_at
            ) VALUES ($1, $2, $3, $1, 'technical', $4, CURRENT_TIMESTAMP)
            ON CONFLICT (factor_id, code, trade_date) DO UPDATE SET
                factor_value = EXCLUDED.factor_value,
                collected_at = CURRENT_TIMESTAMP
        ''', batch)
        print(f"  已保存 {min(i+batch_size, len(all_records)):,}/{len(all_records):,} 条")
    
    await conn.close()
    
    elapsed = asyncio.get_event_loop().time() - start_time
    print(f"\n完成! 总计 {len(all_records):,} 条因子数据，耗时 {elapsed:.1f} 秒")


if __name__ == "__main__":
    asyncio.run(main())
