import os
import re
import json
import sqlite3
import datetime
from datetime import timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from ..config import Config
from ..db import get_db_connection
from ..crypto import decrypt_value
from .prompts import AI_PORTFOLIO_REVIEW_PROMPT


class AISimulationService:
    """AI模拟账户服务 - 管理AI模拟交易和对比"""

    def __init__(self):
        # 内存缓存
        self._accounts_cache = None
        self._accounts_cache_time = None
        self._cache_ttl = 300  # 缓存有效期5分钟
        
    def _get_cached_accounts(self):
        """获取缓存的账户列表"""
        if self._accounts_cache is not None and self._accounts_cache_time is not None:
            elapsed = (datetime.datetime.now() - self._accounts_cache_time).total_seconds()
            if elapsed < self._cache_ttl:
                return self._accounts_cache
        return None
        
    def _set_cached_accounts(self, accounts):
        """设置账户列表缓存"""
        self._accounts_cache = accounts
        self._accounts_cache_time = datetime.datetime.now()
        
    def invalidate_cache(self):
        """使缓存失效"""
        self._accounts_cache = None
        self._accounts_cache_time = None

    def _get_local_time(self):
        """获取本地时间（东八区）"""
        utc_now = datetime.datetime.now(timezone.utc)
        local_tz = timezone(timedelta(hours=8))
        return utc_now.astimezone(local_tz)

    def _init_llm(self, fast_mode=True):
        """初始化LLM"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT value, encrypted FROM settings WHERE key = 'OPENAI_API_KEY'")
            api_key_row = cursor.fetchone()
            if api_key_row:
                api_key = decrypt_value(api_key_row[0]) if api_key_row[1] else api_key_row[0]
                print(f"[AI Simulation] API Key loaded, length: {len(api_key) if api_key else 0}, encrypted: {api_key_row[1]}")
            else:
                api_key = None
                print("[AI Simulation] No API Key found in database")

            cursor.execute("SELECT value FROM settings WHERE key = 'OPENAI_API_BASE'")
            api_base_row = cursor.fetchone()
            api_base = api_base_row[0] if api_base_row else 'https://api.openai.com/v1'
            print(f"[AI Simulation] API Base: {api_base}")

            cursor.execute("SELECT value FROM settings WHERE key = 'AI_MODEL_NAME'")
            model_row = cursor.fetchone()
            model_name = model_row[0] if model_row else 'gpt-3.5-turbo'

            conn.close()

            if not api_key:
                print("[AI Simulation] API Key is empty, returning None")
                return None

            if fast_mode:
                model_name = 'gpt-3.5-turbo'

            print(f"[AI Simulation] Creating LLM with model: {model_name}")
            return ChatOpenAI(
                model=model_name,
                api_key=api_key,
                base_url=api_base,
                temperature=0.7,
                max_tokens=2000,
                request_timeout=300
            )
        except Exception as e:
            print(f"LLM初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def create_ai_account(self, source_account_id: int, name: str = "AI模拟账户",
                         description: str = "", review_day_of_week: int = 0,
                         source_type: str = "fund", review_interval_type: str = "week",
                         review_interval: int = 1) -> Dict[str, Any]:
        """创建AI模拟账户
        
        Args:
            source_account_id: 源账户ID
            name: 账户名称
            description: 账户描述
            review_day_of_week: 审视日期（0-6，0=周一）
            source_type: 源账户类型，'fund'（基金）或 'crypto'（数字货币）
            review_interval_type: 审视周期类型：'day', 'week', 'month', 'hour'
            review_interval: 审视间隔：1表示每天/每周/每月/每小时
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            print(f"[DEBUG] 创建AI账户开始: source_account_id={source_account_id}, source_type={source_type}")
            
            # 根据源账户类型获取初始资产
            if source_type == "crypto":
                # 数字货币账户 - 使用crypto_prices表的价格
                print(f"[DEBUG] 获取数字货币账户资产")
                cursor.execute("""
                    SELECT SUM(cp.amount * COALESCE(cpr.price_usd, 0)) as total_value
                    FROM crypto_positions cp
                    LEFT JOIN crypto_prices cpr ON cp.symbol = cpr.symbol
                    WHERE cp.account_id = ?
                """, (source_account_id,))
                result = cursor.fetchone()
                initial_capital = result[0] if result and result[0] else 0.0
                print(f"[DEBUG] 数字货币账户初始资金: {initial_capital}")
                
                # 获取持仓数据
                cursor.execute("""
                    SELECT cp.symbol, cp.name, cp.cost, cp.amount, COALESCE(cpr.price_usd, 0) as current_price
                    FROM crypto_positions cp
                    LEFT JOIN crypto_prices cpr ON cp.symbol = cpr.symbol
                    WHERE cp.account_id = ?
                """, (source_account_id,))
                positions = cursor.fetchall()
                print(f"[DEBUG] 数字货币持仓数量: {len(positions)}")
            else:
                # 基金账户（默认）- 使用与get_all_positions相同的计算逻辑
                print(f"[DEBUG] 获取基金账户资产")
                from .account import get_all_positions
                account_data = get_all_positions(source_account_id)
                initial_capital = account_data.get("summary", {}).get("total_market_value", 0.0)
                print(f"[DEBUG] 基金账户初始资金: {initial_capital}")
                
                # 获取持仓数据用于复制
                positions_data = account_data.get("positions", [])
                positions_with_price = []
                for pos in positions_data:
                    code = pos.get("code")
                    shares = pos.get("shares", 0)
                    cost = pos.get("cost", 0)
                    current_price = pos.get("latest_nav", pos.get("nav", 0))
                    fund_name = pos.get("name", code)
                    positions_with_price.append((code, shares, cost, current_price, fund_name))
                print(f"[DEBUG] 基金持仓数量: {len(positions_with_price)}")

            # 检查初始资金
            if initial_capital <= 0:
                return {"success": False, "error": "源账户资产为0，无法创建AI模拟账户"}

            # 创建AI账户
            now = self._get_local_time()
            print(f"[DEBUG] 创建AI账户记录")
            cursor.execute("""
                INSERT INTO ai_simulation_accounts
                (name, description, source_account_id, source_type, initial_capital, current_value, 
                 review_day_of_week, review_interval_type, review_interval, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, description, source_account_id, source_type, initial_capital, initial_capital,
                   review_day_of_week, review_interval_type, review_interval,
                   now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")))
            ai_account_id = cursor.lastrowid
            print(f"[DEBUG] AI账户创建成功，ID: {ai_account_id}")

            # 复制源账户持仓到AI账户
            if source_type == "crypto":
                # 复制数字货币持仓
                print(f"[DEBUG] 复制数字货币持仓")
                for pos in positions:
                    symbol, name, cost, amount, current_price = pos
                    print(f"[DEBUG] 复制持仓: {symbol}, 数量: {amount}")
                    cursor.execute("""
                        INSERT INTO ai_simulation_positions
                        (ai_account_id, code, name, asset_type, cost, shares, current_price, market_value, updated_at)
                        VALUES (?, ?, ?, 'crypto', ?, ?, ?, ?, ?)
                    """, (ai_account_id, symbol, name, cost, amount, current_price, amount * current_price, now.strftime("%Y-%m-%d %H:%M:%S")))
            else:
                # 复制基金持仓 - 使用之前已经获取的数据
                print(f"[DEBUG] 复制基金持仓")
                total_positions_value = 0
                for code, shares, cost, current_price, fund_name in positions_with_price:
                    current_price = current_price or 0
                    market_value = shares * current_price
                    total_positions_value += market_value
                    print(f"[DEBUG] 复制持仓: {code}, 数量: {shares}")
                    cursor.execute("""
                        INSERT INTO ai_simulation_positions
                        (ai_account_id, code, name, asset_type, cost, shares, current_price, market_value, updated_at)
                        VALUES (?, ?, ?, 'fund', ?, ?, ?, ?, ?)
                    """, (ai_account_id, code, fund_name, cost, shares, current_price, market_value, now.strftime("%Y-%m-%d %H:%M:%S")))
                
                # 计算并创建初始现金持仓
                cash_value = initial_capital - total_positions_value
                if cash_value > 0:
                    print(f"[DEBUG] 创建初始现金持仓: {cash_value}")
                    cursor.execute("""
                        INSERT INTO ai_simulation_positions
                        (ai_account_id, code, name, asset_type, cost, shares, current_price, market_value, updated_at)
                        VALUES (?, 'CASH', '现金', 'cash', 1.0, ?, 1.0, ?, ?)
                    """, (ai_account_id, cash_value, cash_value, now.strftime("%Y-%m-%d %H:%M:%S")))

            # 记录初始资产
            print(f"[DEBUG] 记录初始资产")
            cursor.execute("""
                INSERT INTO ai_simulation_value_history
                (ai_account_id, record_date, ai_value, source_value, ai_return_rate, source_return_rate, outperformance)
                VALUES (?, ?, ?, ?, 0, 0, 0)
            """, (ai_account_id, now.strftime("%Y-%m-%d"), initial_capital, initial_capital))

            conn.commit()
            print(f"[DEBUG] 提交事务成功")
            
            # 使缓存失效
            self.invalidate_cache()

            return {
                "success": True,
                "ai_account_id": ai_account_id,
                "initial_capital": initial_capital,
                "message": "AI模拟账户创建成功"
            }

        except Exception as e:
            print(f"[ERROR] 创建AI账户失败: {str(e)}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()

    def get_ai_accounts(self, source_account_id: int = None) -> List[Dict[str, Any]]:
        """获取AI模拟账户列表（使用缓存）"""
        # 如果没有指定source_account_id，尝试使用缓存
        if source_account_id is None:
            cached = self._get_cached_accounts()
            if cached is not None:
                return cached
        
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            if source_account_id:
                cursor.execute("""
                    SELECT a.*, acc.name as source_account_name
                    FROM ai_simulation_accounts a
                    LEFT JOIN accounts acc ON a.source_account_id = acc.id
                    WHERE a.source_account_id = ?
                    ORDER BY a.created_at DESC
                """, (source_account_id,))
            else:
                cursor.execute("""
                    SELECT a.*, acc.name as source_account_name
                    FROM ai_simulation_accounts a
                    LEFT JOIN accounts acc ON a.source_account_id = acc.id
                    ORDER BY a.created_at DESC
                """)

            accounts = []
            for row in cursor.fetchall():
                # row structure: id, name, description, source_account_id, initial_capital, 
                #                current_value, total_return_rate, is_active, review_day_of_week, 
                #                last_review_date, created_at, updated_at, source_type, 
                #                review_interval_type, review_interval, source_account_name
                accounts.append({
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "source_account_id": row[3],
                    "source_type": row[12] if len(row) > 12 else 'fund',
                    "initial_capital": row[4],
                    "current_value": row[5],
                    "total_return_rate": row[6],
                    "is_active": row[7],
                    "review_day_of_week": row[8],
                    "review_interval_type": row[13] if len(row) > 13 else 'week',
                    "review_interval": row[14] if len(row) > 14 else 1,
                    "last_review_date": row[9],
                    "created_at": row[10],
                    "updated_at": row[11],
                    "source_account_name": row[15] if len(row) > 15 else ''
                })

            # 缓存结果（仅当没有指定source_account_id时）
            if source_account_id is None:
                self._set_cached_accounts(accounts)
            
            return accounts
        finally:
            conn.close()

    def get_ai_account_detail(self, ai_account_id: int, 
                                include_positions: bool = True,
                                include_trades: bool = True, 
                                include_history: bool = True,
                                trades_limit: int = 20,
                                history_days: int = 90) -> Dict[str, Any]:
        """获取AI模拟账户详情
        
        Args:
            ai_account_id: AI账户ID
            include_positions: 是否包含持仓数据
            include_trades: 是否包含交易记录
            include_history: 是否包含历史走势
            trades_limit: 交易记录数量限制
            history_days: 历史数据天数限制
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 获取账户信息
            cursor.execute("""
                SELECT a.*, acc.name as source_account_name
                FROM ai_simulation_accounts a
                LEFT JOIN accounts acc ON a.source_account_id = acc.id
                WHERE a.id = ?
            """, (ai_account_id,))
            row = cursor.fetchone()

            if not row:
                return {"error": "AI账户不存在"}

            source_account_id = row[3]
            source_type = row[12] if len(row) > 12 else 'fund'

            # 获取源账户当前价值
            if source_type == 'crypto':
                # 直接调用get_all_crypto_positions获取源账户的实际总资产
                from .crypto import get_all_crypto_positions
                account_data = get_all_crypto_positions(source_account_id)
                source_current_value = account_data.get("summary", {}).get("total_market_value", 0.0)
                source_position_count = account_data.get("summary", {}).get("position_count", 0)
            else:
                # 直接调用getAccountPositions获取源账户的实际总资产
                from .account import get_all_positions
                account_data = get_all_positions(source_account_id)
                source_current_value = account_data.get("summary", {}).get("total_market_value", 0.0)
                source_position_count = len(account_data.get("positions", []))

            # 计算源账户收益率
            initial_capital = row[4]
            source_return_rate = ((source_current_value - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0

            # row structure: id, name, description, source_account_id, initial_capital, 
            #                current_value, total_return_rate, is_active, review_day_of_week, 
            #                last_review_date, created_at, updated_at, source_type, 
            #                review_interval_type, review_interval, source_account_name
            account = {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "source_account_id": row[3],
                "source_type": source_type,
                "initial_capital": initial_capital,
                "current_value": row[5],
                "total_return_rate": row[6],
                "is_active": row[7],
                "review_day_of_week": row[8],
                "review_interval_type": row[13] if len(row) > 13 else 'week',
                "review_interval": row[14] if len(row) > 14 else 1,
                "last_review_date": row[9],
                "created_at": row[10],
                "updated_at": row[11],
                "source_account_name": row[15] if len(row) > 15 else '',
                "source_current_value": source_current_value,
                "source_position_count": source_position_count,
                "source_return_rate": source_return_rate
            }

            # 获取持仓
            cursor.execute("""
                SELECT * FROM ai_simulation_positions
                WHERE ai_account_id = ?
                ORDER BY market_value DESC
            """, (ai_account_id,))
            positions = []
            total_positions_value = 0.0
            for pos in cursor.fetchall():
                positions.append({
                    "id": pos[0],
                    "code": pos[2],
                    "name": pos[3],
                    "asset_type": pos[4],
                    "cost": pos[5],
                    "shares": pos[6],
                    "current_price": pos[7],
                    "market_value": pos[8],
                    "return_rate": pos[9],
                    "weight": pos[10]
                })
                total_positions_value += pos[8]

            # 计算现金
            if source_type == 'crypto':
                # 数字货币账户：现金 = USDT持仓的市值
                cursor.execute("""
                    SELECT market_value FROM ai_simulation_positions
                    WHERE ai_account_id = ? AND code = 'USDT'
                """, (ai_account_id,))
                usdt_row = cursor.fetchone()
                cash_value = usdt_row[0] if usdt_row else 0
            else:
                # 基金账户：现金 = CASH持仓的市值
                cursor.execute("""
                    SELECT market_value FROM ai_simulation_positions
                    WHERE ai_account_id = ? AND code = 'CASH'
                """, (ai_account_id,))
                cash_row = cursor.fetchone()
                cash_value = cash_row[0] if cash_row else 0

            # 添加现金信息到账户详情
            account["cash"] = round(cash_value, 2)
            account["positions"] = positions if include_positions else []

            # 获取调仓历史（条件加载）
            if include_trades:
                cursor.execute("""
                    SELECT id, trade_date, code, name, asset_type, trade_type, shares, price, amount, reason 
                    FROM ai_simulation_trades
                    WHERE ai_account_id = ?
                    ORDER BY trade_date DESC, id DESC
                    LIMIT ?
                """, (ai_account_id, trades_limit))
                trades = []
                for trade in cursor.fetchall():
                    trades.append({
                        "id": trade[0],
                        "trade_date": trade[1],
                        "code": trade[2],
                        "name": trade[3],
                        "asset_type": trade[4],
                        "trade_type": trade[5],
                        "shares": trade[6],
                        "price": trade[7],
                        "amount": trade[8],
                        "reason": trade[9]
                    })
                account["trades"] = trades
            else:
                account["trades"] = []

            # 获取资产走势对比（条件加载，限制天数）
            if include_history:
                cursor.execute("""
                    SELECT record_date, ai_value, source_value, ai_return_rate, source_return_rate, outperformance
                    FROM ai_simulation_value_history
                    WHERE ai_account_id = ?
                    AND record_date >= date('now', '-' || ? || ' days')
                    ORDER BY record_date ASC
                """, (ai_account_id, history_days))
                value_history = []
                for hist in cursor.fetchall():
                    value_history.append({
                        "record_date": hist[0],
                        "ai_value": hist[1],
                        "source_value": hist[2],
                        "ai_return_rate": hist[3],
                        "source_return_rate": hist[4],
                        "outperformance": hist[5]
                    })
                account["value_history"] = value_history
            else:
                account["value_history"] = []

            return account

        finally:
            conn.close()

    def update_ai_positions_prices(self, ai_account_id: int):
        """更新AI账户持仓价格"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 获取所有持仓
            cursor.execute("""
                SELECT id, code, asset_type, cost, shares, current_price
                FROM ai_simulation_positions
                WHERE ai_account_id = ?
            """, (ai_account_id,))
            positions = cursor.fetchall()

            total_value = 0
            now = self._get_local_time()

            for pos in positions:
                pos_id, code, asset_type, cost, shares, current_price = pos

                if code == 'CASH' or code == 'USDT':
                    # CASH和USDT持仓：价格固定为1，市值等于份额
                    if code == 'USDT':
                        cursor.execute("""
                            SELECT price_usd FROM crypto_prices WHERE symbol = 'USDT'
                        """)
                        price_row = cursor.fetchone()
                        current_price = price_row[0] if price_row else 1.0
                    else:
                        current_price = 1.0
                elif asset_type == 'fund':
                    # 获取基金最新净值 - 只使用已发布的净值，不使用估值
                    cursor.execute("""
                        SELECT published_nav
                        FROM fund_nav_estimation
                        WHERE code = ? AND published_nav IS NOT NULL AND published_nav > 0
                        ORDER BY date DESC
                        LIMIT 1
                    """, (code,))
                    price_row = cursor.fetchone()
                    
                    # 只使用已发布的净值，如果没有任何发布净值则保持原价格不变
                    if price_row and price_row[0] and price_row[0] > 0:
                        current_price = price_row[0]
                else:
                    # 获取加密货币价格
                    cursor.execute("""
                        SELECT price_usd FROM crypto_prices WHERE symbol = ?
                    """, (code,))
                    price_row = cursor.fetchone()
                    current_price = price_row[0] if price_row else 0

                market_value = shares * current_price if current_price else 0
                return_rate = ((current_price - cost) / cost * 100) if cost > 0 else 0

                cursor.execute("""
                    UPDATE ai_simulation_positions
                    SET current_price = ?, market_value = ?, return_rate = ?, updated_at = ?
                    WHERE id = ?
                """, (current_price, market_value, return_rate, now.strftime("%Y-%m-%d %H:%M:%S"), pos_id))

                total_value += market_value

            # 更新账户总价值
            cursor.execute("""
                SELECT initial_capital, current_value, source_type FROM ai_simulation_accounts WHERE id = ?
            """, (ai_account_id,))
            account_row = cursor.fetchone()
            initial = account_row[0]
            current_value = account_row[1]
            source_type = account_row[2] if len(account_row) > 2 else 'fund'
            
            # 对于所有账户类型，总价值 = 所有持仓市值之和（包括USDT现金持仓）
            # total_value 已经包含了所有持仓的市值，不需要额外处理
            total_account_value = total_value
            
            return_rate = ((total_account_value - initial) / initial * 100) if initial > 0 else 0

            cursor.execute("""
                UPDATE ai_simulation_accounts
                SET current_value = ?, total_return_rate = ?, updated_at = ?
                WHERE id = ?
            """, (total_account_value, return_rate, now.strftime("%Y-%m-%d %H:%M:%S"), ai_account_id))

            # 更新权重
            cursor.execute("""
                SELECT id, market_value FROM ai_simulation_positions
                WHERE ai_account_id = ?
            """, (ai_account_id,))
            for row in cursor.fetchall():
                weight = (row[1] / total_value * 100) if total_value > 0 else 0
                cursor.execute("""
                    UPDATE ai_simulation_positions SET weight = ? WHERE id = ?
                """, (weight, row[0]))

            conn.commit()

        finally:
            conn.close()

    async def perform_weekly_review(self, ai_account_id: int) -> Dict[str, Any]:
        """执行每周审视和调仓"""
        import time
        
        max_retries = 3
        retry_delay = 0.5
        
        # 获取AI账户信息
        for attempt in range(max_retries):
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT * FROM ai_simulation_accounts WHERE id = ?
                """, (ai_account_id,))
                account = cursor.fetchone()
                if not account:
                    conn.close()
                    return {"error": "AI账户不存在"}

                source_account_id = account[3]
                source_type = account[12] if len(account) > 12 else 'fund'
                initial_capital = account[5] if len(account) > 5 else 0.0
                
                conn.close()
                break
            except sqlite3.OperationalError as e:
                conn.close()
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    return {"error": f"数据库锁定: {str(e)}"}
        
        # 更新价格
        self.update_ai_positions_prices(ai_account_id)

        # 获取当前持仓和源账户持仓
        for attempt in range(max_retries):
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT code, name, asset_type, cost, shares, current_price, market_value, weight
                    FROM ai_simulation_positions
                    WHERE ai_account_id = ?
                """, (ai_account_id,))
                ai_positions = cursor.fetchall()

                if source_type == 'crypto':
                    cursor.execute("""
                        SELECT cp.symbol, cp.name, cp.cost, cp.amount, COALESCE(cpr.price_usd, 0) as current_price
                        FROM crypto_positions cp
                        LEFT JOIN crypto_prices cpr ON cp.symbol = cpr.symbol
                        WHERE cp.account_id = ?
                    """, (source_account_id,))
                    source_positions = cursor.fetchall()
                else:
                    cursor.execute("""
                        SELECT p.code, f.name, p.cost, p.shares,
                               CASE 
                                   WHEN p.code = 'CASH' THEN 1.0
                                   ELSE COALESCE(fne.estimate, fne.published_nav, 0)
                               END as price
                        FROM positions p
                        LEFT JOIN funds f ON p.code = f.code
                        LEFT JOIN fund_nav_estimation fne ON p.code = fne.code AND p.code != 'CASH'
                        WHERE p.account_id = ?
                        AND (p.code = 'CASH' OR fne.date = (SELECT MAX(date) FROM fund_nav_estimation WHERE code = p.code) OR fne.date IS NULL)
                    """, (source_account_id,))
                    source_positions = cursor.fetchall()
                
                conn.close()
                break
            except sqlite3.OperationalError as e:
                conn.close()
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    return {"error": f"数据库锁定: {str(e)}"}

        # 计算统计数据
        ai_total_value = sum(p[6] for p in ai_positions)
        if source_type == 'crypto':
            source_total_value = sum(p[3] * p[4] for p in source_positions)
            print(f"[AI Simulation] 数字货币源账户持仓数: {len(source_positions)}")
            for p in source_positions:
                print(f"[AI Simulation] 源持仓: {p[0]}, amount={p[3]}, price={p[4]}, value={p[3]*p[4]}")
            print(f"[AI Simulation] 数字货币源账户总市值: {source_total_value}")
        else:
            # 基金账户：使用当前价格(索引4)计算市值，而不是成本价(索引2)
            source_total_value = sum(p[3] * p[4] for p in source_positions if p[4] > 0)
            print(f"[AI Simulation] 基金源账户持仓数: {len(source_positions)}, 总市值: {source_total_value}")
        
        ai_return_rate = ((ai_total_value - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0
        source_return_rate = ((source_total_value - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0

        # 调用AI进行分析
        llm = self._init_llm(fast_mode=False)
        if not llm:
            return {"error": "LLM未配置，请检查API Key设置"}

        # 准备持仓数据
        ai_portfolio = []
        for p in ai_positions:
            ai_portfolio.append({
                "code": p[0],
                "name": p[1],
                "type": p[2],
                "shares": p[4],
                "cost": p[3],
                "current_price": p[5],
                "market_value": p[6],
                "weight": p[7],
                "return_rate": ((p[5] - p[3]) / p[3] * 100) if p[3] > 0 else 0
            })

        source_portfolio = []
        for p in source_positions:
            if source_type == 'crypto':
                mv = p[3] * p[4]
                source_portfolio.append({
                    "code": p[0],
                    "name": p[1],
                    "shares": p[3],
                    "cost": p[2],
                    "current_price": p[4],
                    "market_value": mv
                })
            else:
                # 基金账户：使用当前价格计算市值
                current_price = p[4] if p[4] > 0 else p[2]  # 如果当前价格无效，使用成本价
                mv = p[3] * current_price
                source_portfolio.append({
                    "code": p[0],
                    "name": p[1],
                    "shares": p[3],
                    "cost": p[2],
                    "current_price": current_price,
                    "market_value": mv
                })

        # 获取历史交易记录
        for attempt in range(max_retries):
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    SELECT trade_date, code, name, trade_type, shares, price, amount, reason
                    FROM ai_simulation_trades
                    WHERE ai_account_id = ?
                    ORDER BY trade_date DESC, id DESC
                    LIMIT 10
                """, (ai_account_id,))
                recent_trades = cursor.fetchall()
                conn.close()
                break
            except sqlite3.OperationalError as e:
                conn.close()
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    return {"error": f"数据库锁定: {str(e)}"}
        
        trade_history = []
        for t in recent_trades:
            trade_history.append({
                "date": t[0],
                "code": t[1],
                "name": t[2],
                "type": "买入" if t[3] == "buy" else "卖出",
                "shares": t[4],
                "price": t[5],
                "amount": t[6],
                "reason": t[7]
            })
        
        trade_history_str = json.dumps(trade_history, ensure_ascii=False, indent=2) if trade_history else "暂无历史交易记录"

        account_type_desc = "数字货币账户" if source_type == 'crypto' else "基金账户"
        account_type_detail = """当前账户为数字货币账户，你只能交易数字货币（如BTC、ETH、USDT等主流加密货币）。
- 禁止买入或卖出任何基金（如005827、110022等基金代码）
- 只能交易数字货币资产
- 可以推荐买入主流数字货币来优化组合配置""" if source_type == 'crypto' else """当前账户为基金账户，你只能交易基金产品。
- 禁止买入或卖出任何数字货币（如BTC、ETH等）
- 只能交易基金资产（如005827、110022等基金代码）
- 可以推荐买入市场上的优秀基金来优化组合配置"""
        
        # 调用AI进行审视
        try:
            print(f"[AI Simulation] Starting AI review call...")
            chain = AI_PORTFOLIO_REVIEW_PROMPT | llm | StrOutputParser()

            review_result = await chain.ainvoke({
                "account_type": f"{account_type_desc}\n{account_type_detail}",
                "ai_portfolio": json.dumps(ai_portfolio, ensure_ascii=False, indent=2),
                "source_portfolio": json.dumps(source_portfolio, ensure_ascii=False, indent=2),
                "ai_total_value": str(ai_total_value),
                "ai_initial_capital": str(initial_capital),
                "ai_return_rate": f"{ai_return_rate:.2f}",
                "source_total_value": str(source_total_value),
                "source_initial_capital": str(initial_capital),
                "source_return_rate": f"{source_return_rate:.2f}",
                "trade_history": trade_history_str,
                "review_date": self._get_local_time().strftime("%Y-%m-%d")
            })
            print(f"[AI Simulation] AI review call completed successfully")
        except Exception as api_error:
            error_msg = str(api_error)
            print(f"[AI Simulation] API Error: {error_msg}")
            import traceback
            traceback.print_exc()
            if "401" in error_msg or "Unauthorized" in error_msg or "Authentication" in error_msg:
                return {"error": f"API认证失败，请检查API Key是否正确。错误: {error_msg}"}
            elif "429" in error_msg or "rate" in error_msg.lower():
                return {"error": "API调用频率超限，请稍后再试"}
            else:
                return {"error": f"AI调用失败: {error_msg}"}

        # 解析AI返回的调仓建议
        try:
            clean_json = review_result.strip()
            if "```json" in clean_json:
                clean_json = clean_json.split("```json")[1].split("```")[0]
            elif "```" in clean_json:
                clean_json = clean_json.split("```")[1].split("```")[0]

            review_data = json.loads(clean_json)
        except:
            review_data = {
                "market_analysis": "解析失败",
                "portfolio_analysis": "解析失败",
                "adjustment_strategy": "解析失败",
                "trades": []
            }

        # 执行调仓操作
        for attempt in range(max_retries):
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                # 记录审视
                now = self._get_local_time()
                cursor.execute("""
                    INSERT INTO ai_simulation_reviews
                    (ai_account_id, review_date, review_type, market_analysis, portfolio_analysis, performance_comparison, adjustment_strategy, executed_trades)
                    VALUES (?, ?, 'weekly', ?, ?, ?, ?, ?)
                """, (ai_account_id, now.strftime("%Y-%m-%d"),
                       review_data.get("market_analysis", ""),
                       review_data.get("portfolio_analysis", ""),
                       review_data.get("performance_comparison", ""),
                       review_data.get("adjustment_strategy", ""),
                       json.dumps(review_data.get("trades", []))))

                # 执行调仓逻辑
                raw_trades = review_data.get("trades", [])
                merged_trades = {}
                final_trades = []
                
                for trade in raw_trades:
                    code = trade.get("code")
                    trade_type = trade.get("trade_type")
                    shares = trade.get("shares", 0)
                    reason = trade.get("reason", "")
                    
                    if not code or shares <= 0:
                        continue
                    
                    net_shares = shares if trade_type == 'buy' else -shares
                    
                    if code not in merged_trades:
                        merged_trades[code] = {
                            "net_shares": 0,
                            "reasons": [],
                            "name": trade.get("name", "")
                        }
                    
                    merged_trades[code]["net_shares"] += net_shares
                    if reason:
                        merged_trades[code]["reasons"].append(f"{trade_type}:{reason}")
                
                # 计算可用余额
                available_balance = 0
                if source_type == 'crypto':
                    cursor.execute("""
                        SELECT market_value FROM ai_simulation_positions
                        WHERE ai_account_id = ? AND code = 'USDT'
                    """, (ai_account_id,))
                    usdt_row = cursor.fetchone()
                    available_balance = usdt_row[0] if usdt_row else 0
                else:
                    # 基金账户：可用余额 = CASH持仓的市值
                    cursor.execute("""
                        SELECT market_value FROM ai_simulation_positions
                        WHERE ai_account_id = ? AND code = 'CASH'
                    """, (ai_account_id,))
                    cash_row = cursor.fetchone()
                    available_balance = cash_row[0] if cash_row else 0

                executed_count = 0

                for code, trade_info in merged_trades.items():
                    net_shares = trade_info["net_shares"]
                    reasons = trade_info["reasons"]
                    
                    if net_shares == 0:
                        continue
                    
                    trade_type = 'buy' if net_shares > 0 else 'sell'
                    shares = abs(net_shares)
                    reason = "; ".join(reasons) if reasons else ""
                    
                    if shares <= 0:
                        continue
                    
                    # 资产类型过滤
                    if source_type == 'crypto':
                        if code.isdigit():
                            print(f"[AI Simulation] 跳过基金代码 {code}，当前为数字货币账户")
                            continue
                    else:
                        if not code.isdigit():
                            print(f"[AI Simulation] 跳过数字货币代码 {code}，当前为基金账户")
                            continue

                    # 获取当前持仓信息
                    cursor.execute("""
                        SELECT current_price, name, shares FROM ai_simulation_positions
                        WHERE ai_account_id = ? AND code = ?
                    """, (ai_account_id, code))
                    pos_row = cursor.fetchone()

                    if pos_row:
                        price = pos_row[0]
                        name = pos_row[1]
                        old_shares = pos_row[2]
                    else:
                        old_shares = 0
                        if source_type == 'crypto':
                            cursor.execute("""
                                SELECT price_usd FROM crypto_prices WHERE symbol = ?
                            """, (code,))
                            price_row = cursor.fetchone()
                            price = price_row[0] if price_row else 0
                        else:
                            cursor.execute("""
                                SELECT estimate, published_nav FROM fund_nav_estimation
                                WHERE code = ? ORDER BY date DESC LIMIT 1
                            """, (code,))
                            price_row = cursor.fetchone()
                            price = price_row[0] or price_row[1] if price_row else 0

                        cursor.execute("SELECT name FROM funds WHERE code = ?", (code,))
                        name_row = cursor.fetchone()
                        name = name_row[0] if name_row else code

                    if not price or price <= 0:
                        print(f"[AI Simulation] {code} 价格无效 ({price})，跳过此交易")
                        continue

                    amount = shares * price

                    if trade_type == 'buy':
                        if amount > available_balance:
                            print(f"[AI Simulation] 买入 {code} 金额 {amount} 超过可用余额 {available_balance}，跳过此交易")
                            continue
                        else:
                            available_balance -= amount
                    else:
                        available_balance += amount

                    # 记录交易
                    asset_type = 'crypto' if source_type == 'crypto' else 'fund'
                    cursor.execute("""
                        INSERT INTO ai_simulation_trades
                        (ai_account_id, trade_date, code, name, asset_type, trade_type, shares, price, amount, reason)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (ai_account_id, now.strftime("%Y-%m-%d"), code, name, asset_type, trade_type,
                          shares, price, amount, reason))
                    
                    final_trades.append({
                        "code": code,
                        "name": name,
                        "trade_type": trade_type,
                        "shares": shares,
                        "price": price,
                        "amount": amount,
                        "reason": reason
                    })

                    # 更新持仓
                    if trade_type == 'buy':
                        if pos_row:
                            cursor.execute("""
                                SELECT cost FROM ai_simulation_positions
                                WHERE ai_account_id = ? AND code = ?
                            """, (ai_account_id, code))
                            old_cost = cursor.fetchone()[0]
                            new_shares = old_shares + shares
                            new_cost = (old_cost * old_shares + price * shares) / new_shares if new_shares > 0 else 0
                            new_market_value = new_shares * price

                            cursor.execute("""
                                UPDATE ai_simulation_positions
                                SET cost = ?, shares = ?, current_price = ?, market_value = ?, updated_at = ?
                                WHERE ai_account_id = ? AND code = ?
                            """, (new_cost, new_shares, price, new_market_value, now.strftime("%Y-%m-%d %H:%M:%S"), ai_account_id, code))
                        else:
                            new_market_value = shares * price
                            cursor.execute("""
                                INSERT INTO ai_simulation_positions
                                (ai_account_id, code, name, asset_type, cost, shares, current_price, market_value, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (ai_account_id, code, name, asset_type, price, shares, price, new_market_value, now.strftime("%Y-%m-%d %H:%M:%S")))

                    elif trade_type == 'sell' and pos_row:
                        new_shares = old_shares - shares

                        if new_shares <= 0:
                            cursor.execute("""
                                DELETE FROM ai_simulation_positions
                                WHERE ai_account_id = ? AND code = ?
                            """, (ai_account_id, code))
                        else:
                            new_market_value = new_shares * price
                            cursor.execute("""
                                UPDATE ai_simulation_positions
                                SET shares = ?, current_price = ?, market_value = ?, updated_at = ?
                                WHERE ai_account_id = ? AND code = ?
                            """, (new_shares, price, new_market_value, now.strftime("%Y-%m-%d %H:%M:%S"), ai_account_id, code))

                    executed_count += 1

                # 更新现金/USDT持仓
                if source_type == 'crypto':
                    # 数字货币账户：更新USDT持仓
                    cursor.execute("""
                        SELECT shares FROM ai_simulation_positions
                        WHERE ai_account_id = ? AND code = 'USDT'
                    """, (ai_account_id,))
                    usdt_pos = cursor.fetchone()
                    
                    cursor.execute("""
                        SELECT price_usd FROM crypto_prices WHERE symbol = 'USDT'
                    """)
                    usdt_price_row = cursor.fetchone()
                    usdt_price = usdt_price_row[0] if usdt_price_row else 1.0
                    
                    usdt_shares = available_balance / usdt_price if usdt_price > 0 else available_balance
                    usdt_market_value = available_balance
                    
                    if usdt_pos:
                        cursor.execute("""
                            UPDATE ai_simulation_positions
                            SET shares = ?, current_price = ?, market_value = ?, updated_at = ?
                            WHERE ai_account_id = ? AND code = 'USDT'
                        """, (usdt_shares, usdt_price, usdt_market_value, now.strftime("%Y-%m-%d %H:%M:%S"), ai_account_id))
                    else:
                        cursor.execute("""
                            INSERT INTO ai_simulation_positions
                            (ai_account_id, code, name, asset_type, cost, shares, current_price, market_value, updated_at)
                            VALUES (?, 'USDT', 'Tether USD', 'crypto', ?, ?, ?, ?, ?)
                        """, (ai_account_id, usdt_price, usdt_shares, usdt_price, usdt_market_value, now.strftime("%Y-%m-%d %H:%M:%S")))
                else:
                    # 基金账户：更新现金持仓（使用特殊代码CASH表示现金）
                    cursor.execute("""
                        SELECT shares FROM ai_simulation_positions
                        WHERE ai_account_id = ? AND code = 'CASH'
                    """, (ai_account_id,))
                    cash_pos = cursor.fetchone()
                    
                    cash_price = 1.0  # 现金价格为1
                    cash_shares = available_balance
                    cash_market_value = available_balance
                    
                    if cash_pos:
                        cursor.execute("""
                            UPDATE ai_simulation_positions
                            SET shares = ?, current_price = ?, market_value = ?, updated_at = ?
                            WHERE ai_account_id = ? AND code = 'CASH'
                        """, (cash_shares, cash_price, cash_market_value, now.strftime("%Y-%m-%d %H:%M:%S"), ai_account_id))
                    else:
                        cursor.execute("""
                            INSERT INTO ai_simulation_positions
                            (ai_account_id, code, name, asset_type, cost, shares, current_price, market_value, updated_at)
                            VALUES (?, 'CASH', '现金', 'cash', ?, ?, ?, ?, ?)
                        """, (ai_account_id, cash_price, cash_shares, cash_price, cash_market_value, now.strftime("%Y-%m-%d %H:%M:%S")))

                # 更新最后审视日期
                cursor.execute("""
                    UPDATE ai_simulation_accounts
                    SET last_review_date = ?, updated_at = ?
                    WHERE id = ?
                """, (now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d %H:%M:%S"), ai_account_id))

                conn.commit()
                conn.close()
                
                # 自动记录每日价值
                self.record_daily_value(ai_account_id)
                
                # 保存完整审视报告到消息系统
                try:
                    from .messages import MessageService
                    message_service = MessageService()
                    
                    # 构建完整报告内容
                    full_report = {
                        "ai_account_id": ai_account_id,
                        "review_date": now.strftime("%Y-%m-%d"),
                        "account_type": "数字货币账户" if source_type == 'crypto' else "基金账户",
                        "market_analysis": review_data.get("market_analysis", ""),
                        "portfolio_analysis": review_data.get("portfolio_analysis", ""),
                        "performance_comparison": review_data.get("performance_comparison", ""),
                        "adjustment_strategy": review_data.get("adjustment_strategy", ""),
                        "trades_executed": executed_count,
                        "trades": final_trades,
                        "ai_total_value": ai_total_value,
                        "ai_return_rate": ai_return_rate,
                        "source_total_value": source_total_value,
                        "source_return_rate": source_return_rate
                    }
                    
                    # 创建消息
                    message_service.create_message({
                        "msg_type": "ai_review",
                        "title": f"{account[1]} - AI审视报告 - {now.strftime('%Y-%m-%d')}",
                        "content": full_report,
                        "summary": f"AI账户收益率: {ai_return_rate:.2f}%, 用户账户收益率: {source_return_rate:.2f}%, 执行交易: {executed_count}笔",
                        "risk_level": "normal",
                        "fund_count": len(ai_portfolio),
                        "total_value": ai_total_value
                    })
                    print(f"[AI Simulation] 审视报告已保存到消息系统")
                except Exception as msg_error:
                    print(f"[AI Simulation] 保存消息失败: {str(msg_error)}")

                return {
                    "success": True,
                    "review_date": now.strftime("%Y-%m-%d"),
                    "market_analysis": review_data.get("market_analysis", ""),
                    "portfolio_analysis": review_data.get("portfolio_analysis", ""),
                    "adjustment_strategy": review_data.get("adjustment_strategy", ""),
                    "trades_executed": executed_count,
                    "trades": final_trades
                }
                
            except Exception as e:
                conn.rollback()
                conn.close()
                return {"error": str(e)}


    def record_daily_value(self, ai_account_id: int):
        """记录每日资产对比"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 获取AI账户信息
            cursor.execute("""
                SELECT source_account_id, source_type, initial_capital FROM ai_simulation_accounts WHERE id = ?
            """, (ai_account_id,))
            account = cursor.fetchone()
            if not account:
                return

            source_account_id, source_type, initial_capital = account

            # 更新AI持仓价格
            self.update_ai_positions_prices(ai_account_id)

            # 获取AI账户当前价值
            cursor.execute("""
                SELECT current_value FROM ai_simulation_accounts WHERE id = ?
            """, (ai_account_id,))
            ai_value = cursor.fetchone()[0]

            # 获取源账户当前价值（根据类型）
            if source_type == 'crypto':
                # 数字货币账户价值计算 - 包含USDT现金账户
                cursor.execute("""
                    SELECT SUM(
                        CASE 
                            WHEN cp.symbol = 'USDT' THEN cp.amount
                            ELSE cp.amount * COALESCE(cpr.price_usd, 0)
                        END
                    ) as total_value
                    FROM crypto_positions cp
                    LEFT JOIN crypto_prices cpr ON cp.symbol = cpr.symbol
                    WHERE cp.account_id = ?
                """, (source_account_id,))
            else:
                # 源账户价值计算 - 包含基金持仓和现金账户
                cursor.execute("""
                    SELECT SUM(
                        CASE 
                            WHEN p.code = 'CASH' THEN p.shares
                            ELSE p.shares * COALESCE(
                                (SELECT COALESCE(published_nav, estimate, 0)
                                 FROM fund_nav_estimation
                                 WHERE code = p.code
                                 AND (published_nav IS NOT NULL OR estimate IS NOT NULL)
                                 ORDER BY date DESC
                                 LIMIT 1
                            ), 0)
                        END
                    ) as total_value
                    FROM positions p
                    WHERE p.account_id = ?
                """, (source_account_id,))
            result = cursor.fetchone()
            source_value = result[0] if result and result[0] else 0

            # 计算收益率
            ai_return_rate = ((ai_value - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0
            source_return_rate = ((source_value - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0
            outperformance = ai_return_rate - source_return_rate

            now = self._get_local_time()

            # 记录或更新
            cursor.execute("""
                INSERT OR REPLACE INTO ai_simulation_value_history
                (ai_account_id, record_date, ai_value, source_value, ai_return_rate, source_return_rate, outperformance)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ai_account_id, now.strftime("%Y-%m-%d"), ai_value, source_value,
                  ai_return_rate, source_return_rate, outperformance))

            conn.commit()

        finally:
            conn.close()

    def update_ai_account(self, ai_account_id: int, **kwargs) -> Dict[str, Any]:
        """更新AI模拟账户信息
        
        Args:
            ai_account_id: AI账户ID
            **kwargs: 要更新的字段
        """
        import time
        
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                # 构建更新语句
                update_fields = []
                update_values = []
                
                if "name" in kwargs:
                    update_fields.append("name = ?")
                    update_values.append(kwargs["name"])
                if "description" in kwargs:
                    update_fields.append("description = ?")
                    update_values.append(kwargs["description"])
                if "review_day_of_week" in kwargs:
                    update_fields.append("review_day_of_week = ?")
                    update_values.append(kwargs["review_day_of_week"])
                if "review_interval_type" in kwargs:
                    update_fields.append("review_interval_type = ?")
                    update_values.append(kwargs["review_interval_type"])
                if "review_interval" in kwargs:
                    update_fields.append("review_interval = ?")
                    update_values.append(kwargs["review_interval"])
                if "is_active" in kwargs:
                    update_fields.append("is_active = ?")
                    update_values.append(1 if kwargs["is_active"] else 0)
                
                # 添加updated_at字段
                update_fields.append("updated_at = ?")
                update_values.append(self._get_local_time().strftime("%Y-%m-%d %H:%M:%S"))
                
                if update_fields:
                    query = f"UPDATE ai_simulation_accounts SET {', '.join(update_fields)} WHERE id = ?"
                    update_values.append(ai_account_id)
                    cursor.execute(query, update_values)
                    conn.commit()
                
                # 使缓存失效
                self.invalidate_cache()
                
                # 返回更新后的账户信息
                return self.get_ai_account_detail(ai_account_id)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    conn.close()
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    raise
            finally:
                conn.close()
        
        return {"error": "更新失败：数据库锁定"}

    def upsert_ai_position(self, ai_account_id: int, code: str, name: str, asset_type: str, cost: float, shares: float) -> Dict[str, Any]:
        """更新或插入AI账户持仓
        
        Args:
            ai_account_id: AI账户ID
            code: 资产代码
            name: 资产名称
            asset_type: 资产类型
            cost: 成本
            shares: 份额
        """
        import time
        
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                # 计算市值
                market_value = shares * cost if code != 'CASH' else shares
                
                # 插入或更新持仓
                cursor.execute("""
                    INSERT OR REPLACE INTO ai_simulation_positions
                    (ai_account_id, code, name, asset_type, cost, shares, current_price, market_value, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (ai_account_id, code, name, asset_type, cost, shares, cost, market_value, self._get_local_time().strftime("%Y-%m-%d %H:%M:%S")))
                
                # 重新计算权重
                cursor.execute("""
                    SELECT SUM(market_value) FROM ai_simulation_positions WHERE ai_account_id = ?
                """, (ai_account_id,))
                total_value = cursor.fetchone()[0] or 0
                
                if total_value > 0:
                    cursor.execute("""
                        UPDATE ai_simulation_positions
                        SET weight = (market_value / ?) * 100
                        WHERE ai_account_id = ?
                    """, (total_value, ai_account_id))
                
                # 更新账户当前价值
                cursor.execute("""
                    UPDATE ai_simulation_accounts
                    SET current_value = ?
                    WHERE id = ?
                """, (total_value, ai_account_id))
                
                conn.commit()
                
                # 使缓存失效
                self.invalidate_cache()
                
                return {"success": True, "message": "持仓更新成功"}
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    conn.close()
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    raise
            finally:
                conn.close()
        
        return {"error": "更新失败：数据库锁定"}


    def delete_ai_account(self, ai_account_id: int) -> Dict[str, Any]:
        """删除AI模拟账户"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 使用单个事务批量删除，减少锁竞争
            # 先删除子表数据，最后删除主表
            cursor.execute("DELETE FROM ai_simulation_positions WHERE ai_account_id = ?", (ai_account_id,))
            cursor.execute("DELETE FROM ai_simulation_trades WHERE ai_account_id = ?", (ai_account_id,))
            cursor.execute("DELETE FROM ai_simulation_value_history WHERE ai_account_id = ?", (ai_account_id,))
            cursor.execute("DELETE FROM ai_simulation_reviews WHERE ai_account_id = ?", (ai_account_id,))
            cursor.execute("DELETE FROM ai_simulation_accounts WHERE id = ?", (ai_account_id,))
            conn.commit()
            
            # 使缓存失效
            self.invalidate_cache()
            
            return {"success": True, "message": "AI模拟账户已删除"}
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()


# 服务实例
ai_simulation_service = AISimulationService()
