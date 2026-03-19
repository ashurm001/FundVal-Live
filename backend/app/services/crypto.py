import requests
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..db import get_db_connection

logger = logging.getLogger(__name__)

# CoinGecko API 配置
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Binance API 配置（国内可访问的备用方案）
BINANCE_BASE_URL = "https://api.binance.com"

# 币种符号到 Binance 交易对的映射
BINANCE_SYMBOL_MAP = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "BNB": "BNBUSDT",
    "DOGE": "DOGEUSDT",
    "SOL": "SOLUSDT",
    "XRP": "XRPUSDT",
    "ADA": "ADAUSDT",
    "DOT": "DOTUSDT",
    "LINK": "LINKUSDT",
}

# 支持的币种列表
SUPPORTED_CRYPTOS = {
    "bitcoin": {"symbol": "BTC", "name": "Bitcoin"},
    "ethereum": {"symbol": "ETH", "name": "Ethereum"},
    "binancecoin": {"symbol": "BNB", "name": "BNB"},
    "dogecoin": {"symbol": "DOGE", "name": "Dogecoin"},
    "solana": {"symbol": "SOL", "name": "Solana"},
    "ripple": {"symbol": "XRP", "name": "XRP"},
    "cardano": {"symbol": "ADA", "name": "Cardano"},
    "polkadot": {"symbol": "DOT", "name": "Polkadot"},
    "chainlink": {"symbol": "LINK", "name": "Chainlink"},
}

# USD 到 CNY 的汇率（固定汇率，也可以从API获取）
USD_TO_CNY_RATE = 7.2

# 默认价格（当 API 无法访问时作为备用）- 2025年3月更新
DEFAULT_CRYPTO_PRICES = {
    "BTC": {"price_usd": 92000.0, "change_24h": 0.0},    # ~662,400 CNY
    "ETH": {"price_usd": 2400.0, "change_24h": 0.0},     # ~17,280 CNY
    "BNB": {"price_usd": 620.0, "change_24h": 0.0},      # ~4,464 CNY
    "DOGE": {"price_usd": 0.22, "change_24h": 0.0},      # ~1.58 CNY
    "SOL": {"price_usd": 145.0, "change_24h": 0.0},      # ~1,044 CNY
    "XRP": {"price_usd": 2.4, "change_24h": 0.0},        # ~17.28 CNY
    "ADA": {"price_usd": 0.75, "change_24h": 0.0},       # ~5.4 CNY
    "DOT": {"price_usd": 5.2, "change_24h": 0.0},        # ~37.44 CNY
    "LINK": {"price_usd": 15.0, "change_24h": 0.0},      # ~108 CNY
}

def get_crypto_prices(symbols: List[str] = None) -> Dict[str, Any]:
    """
    从 CryptoCompare API 获取数字货币价格（只获取美元价格，再换算为人民币）
    
    Args:
        symbols: 币种符号列表，如 ["BTC", "ETH"]，如果为 None 则获取所有支持的币种
    
    Returns:
        币种到价格信息的映射
    """
    if symbols is None:
        symbols = [info["symbol"] for info in SUPPORTED_CRYPTOS.values()]
    
    prices = {}
    
    try:
        # 从 CryptoCompare API 获取价格（只获取USD）
        for symbol in symbols:
            url = "https://min-api.cryptocompare.com/data/price"
            params = {
                "fsym": symbol,
                "tsyms": "USD"  # 只获取美元价格
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if "USD" in data:
                price_usd = data["USD"]
                # 手动换算为人民币
                price_cny = price_usd * USD_TO_CNY_RATE
                
                # 找到对应的币种信息
                name = symbol
                for coin_id, info in SUPPORTED_CRYPTOS.items():
                    if info["symbol"] == symbol:
                        name = info["name"]
                        break
                
                # 获取 24 小时变化率
                change_url = "https://min-api.cryptocompare.com/data/v2/histoday"
                change_params = {
                    "fsym": symbol,
                    "tsym": "USD",
                    "limit": 1
                }
                
                try:
                    change_response = requests.get(change_url, params=change_params, timeout=10)
                    change_response.raise_for_status()
                    change_data = change_response.json()
                    
                    change_24h = 0.0
                    if change_data.get("Response") == "Success" and "Data" in change_data:
                        data_points = change_data["Data"].get("Data", [])
                        if len(data_points) >= 2:
                            open_price = data_points[0].get("open", 0.0)
                            close_price = data_points[1].get("close", 0.0)
                            if open_price > 0:
                                change_24h = ((close_price - open_price) / open_price) * 100
                except Exception as e:
                    logger.warning(f"Failed to get 24h change for {symbol}: {e}")
                    change_24h = 0.0
                
                prices[symbol] = {
                    "symbol": symbol,
                    "name": name,
                    "price_usd": price_usd,
                    "price_cny": price_cny,
                    "change_24h": change_24h,
                    "updated_at": datetime.now().isoformat()
                }
        
        if not prices:
            # 如果 CryptoCompare API 失败，使用默认价格
            for symbol in symbols:
                if symbol in DEFAULT_CRYPTO_PRICES:
                    default_price = DEFAULT_CRYPTO_PRICES[symbol]
                    name = symbol
                    for coin_id, info in SUPPORTED_CRYPTOS.items():
                        if info["symbol"] == symbol:
                            name = info["name"]
                            break
                    
                    price_usd = default_price["price_usd"]
                    change_24h = default_price["change_24h"]
                    price_cny = price_usd * USD_TO_CNY_RATE
                    
                    prices[symbol] = {
                        "symbol": symbol,
                        "name": name,
                        "price_usd": price_usd,
                        "price_cny": price_cny,
                        "change_24h": change_24h,
                        "updated_at": datetime.now().isoformat()
                    }
        
        logger.info(f"Successfully fetched {len(prices)} crypto prices from CryptoCompare")
        return prices
    
    except Exception as e:
        logger.error(f"Failed to fetch crypto prices from CryptoCompare: {e}")
        # 使用默认价格作为备用
        prices = {}
        for symbol in symbols:
            if symbol in DEFAULT_CRYPTO_PRICES:
                default_price = DEFAULT_CRYPTO_PRICES[symbol]
                name = symbol
                for coin_id, info in SUPPORTED_CRYPTOS.items():
                    if info["symbol"] == symbol:
                        name = info["name"]
                        break
                
                price_usd = default_price["price_usd"]
                change_24h = default_price["change_24h"]
                price_cny = price_usd * USD_TO_CNY_RATE
                
                prices[symbol] = {
                    "symbol": symbol,
                    "name": name,
                    "price_usd": price_usd,
                    "price_cny": price_cny,
                    "change_24h": change_24h,
                    "updated_at": datetime.now().isoformat()
                }
        return prices

def get_crypto_prices_from_binance(symbols: List[str] = None) -> Dict[str, Any]:
    """
    从 Binance API 获取数字货币价格（备用方案）
    
    Args:
        symbols: 币种符号列表，如 ["BTC", "ETH"]，如果为 None 则获取所有支持的币种
    
    Returns:
        币种到价格信息的映射
    """
    if symbols is None:
        symbols = [info["symbol"] for info in SUPPORTED_CRYPTOS.values()]
    
    prices = {}
    
    try:
        # Binance API 可以批量获取多个交易对
        symbol_pairs = []
        for symbol in symbols:
            if symbol.upper() in BINANCE_SYMBOL_MAP:
                symbol_pairs.append(BINANCE_SYMBOL_MAP[symbol.upper()])
        
        if not symbol_pairs:
            return prices
        
        # 调用 Binance API 获取 24 小时价格变动统计
        url = f"{BINANCE_BASE_URL}/api/v3/ticker/24hr"
        params = {"symbols": str(symbol_pairs).replace("'", '"')}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # 构建反向映射：交易对 -> 币种符号
        reverse_map = {v: k for k, v in BINANCE_SYMBOL_MAP.items()}
        
        for ticker in data:
            symbol_pair = ticker.get("symbol", "")
            if symbol_pair in reverse_map:
                symbol = reverse_map[symbol_pair]
                # 找到对应的币种信息
                name = symbol
                for coin_id, info in SUPPORTED_CRYPTOS.items():
                    if info["symbol"] == symbol:
                        name = info["name"]
                        break
                
                price_usd = float(ticker.get("lastPrice", 0.0))
                change_24h = float(ticker.get("priceChangePercent", 0.0))
                price_cny = price_usd * USD_TO_CNY_RATE
                
                prices[symbol] = {
                    "symbol": symbol,
                    "name": name,
                    "price_usd": price_usd,
                    "price_cny": price_cny,
                    "change_24h": change_24h,
                    "updated_at": datetime.now().isoformat()
                }
        
        logger.info(f"Successfully fetched {len(prices)} crypto prices from Binance")
        return prices
    
    except Exception as e:
        logger.error(f"Failed to fetch crypto prices from Binance: {e}")
        return prices

def update_crypto_prices_cache(symbols: List[str] = None) -> bool:
    """
    更新数据库中的价格缓存
    
    Args:
        symbols: 要更新的币种列表，如果为 None 则更新所有
    
    Returns:
        是否成功
    """
    try:
        prices = get_crypto_prices(symbols)
        
        if not prices:
            return False
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            for symbol, price_data in prices.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO crypto_prices 
                    (symbol, price_usd, price_cny, change_24h, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    symbol,
                    price_data["price_usd"],
                    price_data["price_cny"],
                    price_data["change_24h"]
                ))
            
            conn.commit()
            logger.info(f"Updated {len(prices)} crypto prices in cache")
            return True
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Failed to update crypto prices cache: {e}")
        return False

def get_cached_prices(symbols: List[str] = None) -> Dict[str, Any]:
    """
    从数据库获取缓存的价格
    
    Args:
        symbols: 要获取的币种列表，如果为 None 则获取所有
    
    Returns:
        币种到价格信息的映射
    """
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            if symbols:
                placeholders = ",".join(["?"] * len(symbols))
                cursor.execute(f"""
                    SELECT symbol, price_usd, price_cny, change_24h, updated_at
                    FROM crypto_prices
                    WHERE symbol IN ({placeholders})
                """, symbols)
            else:
                cursor.execute("""
                    SELECT symbol, price_usd, price_cny, change_24h, updated_at
                    FROM crypto_prices
                """)
            
            rows = cursor.fetchall()
            
            prices = {}
            for row in rows:
                prices[row["symbol"]] = {
                    "symbol": row["symbol"],
                    "price_usd": row["price_usd"],
                    "price_cny": row["price_cny"],
                    "change_24h": row["change_24h"],
                    "updated_at": row["updated_at"]
                }
            
            return prices
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Failed to get cached prices: {e}")
        return {}

def get_all_crypto_positions(account_id: int = 1) -> Dict[str, Any]:
    """
    获取指定账户的所有数字货币持仓
    
    Args:
        account_id: 账户ID
    
    Returns:
        包含持仓列表和汇总信息的字典
    """
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # 获取持仓
            cursor.execute("""
                SELECT * FROM crypto_positions
                WHERE account_id = ?
                ORDER BY amount DESC
            """, (account_id,))
            
            rows = cursor.fetchall()
            
            positions = []
            total_market_value = 0.0
            total_cost = 0.0
            total_day_income = 0.0
            usdt_cash = 0.0  # USDT现金账户金额
            usdt_position = None  # USDT现金账户持仓对象
            
            if not rows:
                return {
                    "summary": {
                        "total_market_value": 0.0,
                        "total_cost": 0.0,
                        "total_income": 0.0,
                        "total_return_rate": 0.0,
                        "total_day_income": 0.0,
                        "position_count": 0,
                        "usdt_cash": 0.0
                    },
                    "positions": []
                }
            
            symbols = [row["symbol"] for row in rows]
            prices = get_cached_prices(symbols)
            
            if len(prices) < len(symbols):
                import threading
                def update_prices_async():
                    try:
                        update_crypto_prices_cache(symbols)
                    except Exception as e:
                        logger.error(f"Background price update failed: {e}")
                
                thread = threading.Thread(target=update_prices_async, daemon=True)
                thread.start()
            
            for row in rows:
                symbol = row["symbol"]
                name = row["name"]
                cost = float(row["cost"])
                amount = float(row["amount"])
                
                # 处理USDT现金账户
                if symbol == "USDT":
                    usdt_cash = amount
                    usdt_position = {
                        "id": row["id"],
                        "symbol": "USDT",
                        "name": "USDT现金",
                        "cost": 1.0,
                        "amount": amount,
                        "current_price": 1.0,
                        "market_value": round(amount, 2),
                        "cost_basis": round(amount, 2),
                        "income": 0.0,
                        "return_rate": 0.0,
                        "day_income": 0.0,
                        "change_24h": 0.0,
                        "updated_at": row["updated_at"],
                        "is_cash": True  # 标记为现金账户
                    }
                    continue
                
                # 获取当前价格（使用美元价格）
                price_data = prices.get(symbol, {})
                current_price = price_data.get("price_usd", 0.0)  # 改为使用美元价格
                change_24h = price_data.get("change_24h", 0.0)
                
                # 计算各项指标（基于美元）
                market_value = amount * current_price
                cost_basis = amount * cost
                income = market_value - cost_basis
                return_rate = (income / cost_basis * 100) if cost_basis > 0 else 0.0
                day_income = market_value * (change_24h / 100) if current_price > 0 else 0.0
                
                positions.append({
                    "id": row["id"],
                    "symbol": symbol,
                    "name": name,
                    "cost": cost,
                    "amount": amount,
                    "current_price": current_price,
                    "market_value": round(market_value, 2),
                    "cost_basis": round(cost_basis, 2),
                    "income": round(income, 2),
                    "return_rate": round(return_rate, 2),
                    "day_income": round(day_income, 2),
                    "change_24h": round(change_24h, 2),
                    "updated_at": row["updated_at"]
                })
                
                total_market_value += market_value
                total_cost += cost_basis
                total_day_income += day_income
            
            # 将USDT现金账户添加到持仓列表
            if usdt_position:
                positions.append(usdt_position)
            
            # 总资产包含USDT现金
            total_market_value += usdt_cash
            total_cost += usdt_cash
            
            total_income = total_market_value - total_cost
            total_return_rate = (total_income / total_cost * 100) if total_cost > 0 else 0.0
            
            return {
                "summary": {
                    "total_market_value": round(total_market_value, 2),
                    "total_cost": round(total_cost, 2),
                    "total_income": round(total_income, 2),
                    "total_return_rate": round(total_return_rate, 2),
                    "total_day_income": round(total_day_income, 2),
                    "position_count": len(positions),
                    "usdt_cash": round(usdt_cash, 2)
                },
                "positions": positions
            }
        
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Failed to get crypto positions: {e}")
        return {
            "summary": {
                "total_market_value": 0.0,
                "total_cost": 0.0,
                "total_income": 0.0,
                "total_return_rate": 0.0,
                "total_day_income": 0.0,
                "position_count": 0
            },
            "positions": []
        }

def upsert_crypto_position(account_id: int, symbol: str, name: str, cost: float, amount: float) -> bool:
    """
    添加或更新数字货币持仓
    
    Args:
        account_id: 账户ID
        symbol: 币种符号
        name: 币种名称
        cost: 成本价
        amount: 持仓数量
    
    Returns:
        是否成功
    """
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO crypto_positions (account_id, symbol, name, cost, amount)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(account_id, symbol) DO UPDATE SET
                    name = excluded.name,
                    cost = excluded.cost,
                    amount = excluded.amount,
                    updated_at = CURRENT_TIMESTAMP
            """, (account_id, symbol.upper(), name, cost, amount))
            
            conn.commit()
            logger.info(f"Upserted crypto position: {symbol}")
            return True
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Failed to upsert crypto position: {e}")
        return False

def remove_crypto_position(account_id: int, symbol: str) -> bool:
    """
    删除数字货币持仓
    
    Args:
        account_id: 账户ID
        symbol: 币种符号
    
    Returns:
        是否成功
    """
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM crypto_positions
                WHERE account_id = ? AND symbol = ?
            """, (account_id, symbol.upper()))
            
            conn.commit()
            logger.info(f"Removed crypto position: {symbol}")
            return True
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Failed to remove crypto position: {e}")
        return False

def execute_crypto_trade(account_id: int, symbol: str, op_type: str, amount: float, price: float, trade_time: str = None) -> bool:
    """
    执行数字货币交易（买入或卖出）
    
    Args:
        account_id: 账户ID
        symbol: 币种符号
        op_type: 操作类型 ('buy' 或 'sell')
        amount: 交易数量
        price: 交易价格
        trade_time: 交易时间（ISO格式），如果为 None 则使用当前时间
    
    Returns:
        是否成功
    """
    try:
        if not trade_time:
            trade_time = datetime.now().isoformat()
        
        total_usd = amount * price  # 交易总金额（美元）
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # 检查USDT现金账户余额
            cursor.execute("""
                SELECT amount FROM crypto_positions
                WHERE account_id = ? AND symbol = 'USDT'
            """, (account_id,))
            usdt_row = cursor.fetchone()
            usdt_balance = usdt_row["amount"] if usdt_row else 0.0
            
            # 更新持仓
            if op_type == "buy":
                # 买入：检查USDT余额是否足够
                if usdt_balance < total_usd:
                    logger.error(f"Insufficient USDT balance: {usdt_balance} < {total_usd}")
                    return False
                
                # 从USDT现金账户扣除金额
                cursor.execute("""
                    UPDATE crypto_positions
                    SET amount = amount - ?
                    WHERE account_id = ? AND symbol = 'USDT'
                """, (total_usd, account_id))
                
                # 增加持仓，更新成本价
                cursor.execute("""
                    INSERT INTO crypto_positions (account_id, symbol, name, cost, amount)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(account_id, symbol) DO UPDATE SET
                        cost = (cost * amount + ? * ?) / (amount + ?),
                        amount = amount + ?,
                        updated_at = CURRENT_TIMESTAMP
                """, (account_id, symbol.upper(), symbol, price, amount, price, amount, amount, amount))
            
            elif op_type == "sell":
                # 检查持仓是否足够
                cursor.execute("""
                    SELECT amount FROM crypto_positions
                    WHERE account_id = ? AND symbol = ?
                """, (account_id, symbol.upper()))
                position_row = cursor.fetchone()
                position_amount = position_row["amount"] if position_row else 0.0
                
                if position_amount < amount:
                    logger.error(f"Insufficient position: {position_amount} < {amount}")
                    return False
                
                # 减少持仓
                cursor.execute("""
                    UPDATE crypto_positions
                    SET amount = amount - ?
                    WHERE account_id = ? AND symbol = ?
                """, (amount, account_id, symbol.upper()))
                
                # 将金额加到USDT现金账户
                cursor.execute("""
                    INSERT INTO crypto_positions (account_id, symbol, name, cost, amount)
                    VALUES (?, 'USDT', 'USDT现金', 1.0, ?)
                    ON CONFLICT(account_id, symbol) DO UPDATE SET
                        amount = amount + ?,
                        updated_at = CURRENT_TIMESTAMP
                """, (account_id, total_usd, total_usd))
            
            # 记录交易
            cursor.execute("""
                INSERT INTO crypto_transactions (account_id, symbol, op_type, amount, price, total_cny, trade_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (account_id, symbol.upper(), op_type, amount, price, total_usd, trade_time))
            
            conn.commit()
            logger.info(f"Executed crypto trade: {op_type} {amount} {symbol} at {price}, total_usd: {total_usd}")
            return True
        
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Failed to execute crypto trade: {e}")
        return False

def get_crypto_transactions(account_id: int = 1, symbol: str = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """
    获取数字货币交易记录
    
    Args:
        account_id: 账户ID
        symbol: 币种符号，如果为 None 则获取所有币种
        limit: 返回数量限制
        offset: 偏移量
    
    Returns:
        包含交易记录的字典
    """
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # 获取总数
            if symbol:
                cursor.execute("""
                    SELECT COUNT(*) as count FROM crypto_transactions
                    WHERE account_id = ? AND symbol = ?
                """, (account_id, symbol.upper()))
            else:
                cursor.execute("""
                    SELECT COUNT(*) as count FROM crypto_transactions
                    WHERE account_id = ?
                """, (account_id,))
            
            total = cursor.fetchone()["count"]
            
            # 获取交易记录
            if symbol:
                cursor.execute("""
                    SELECT * FROM crypto_transactions
                    WHERE account_id = ? AND symbol = ?
                    ORDER BY trade_time DESC
                    LIMIT ? OFFSET ?
                """, (account_id, symbol.upper(), limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM crypto_transactions
                    WHERE account_id = ?
                    ORDER BY trade_time DESC
                    LIMIT ? OFFSET ?
                """, (account_id, limit, offset))
            
            rows = cursor.fetchall()
            
            transactions = []
            for row in rows:
                transactions.append({
                    "id": row["id"],
                    "account_id": row["account_id"],
                    "symbol": row["symbol"],
                    "op_type": row["op_type"],
                    "amount": row["amount"],
                    "price": row["price"],
                    "total_cny": row["total_cny"],
                    "trade_time": row["trade_time"],
                    "created_at": row["created_at"]
                })
            
            return {
                "transactions": transactions,
                "total": total,
                "limit": limit,
                "offset": offset
            }
        
        finally:
            conn.close()
    
    except Exception as e:
        logger.error(f"Failed to get crypto transactions: {e}")
        return {
            "transactions": [],
            "total": 0,
            "limit": limit,
            "offset": offset
        }
