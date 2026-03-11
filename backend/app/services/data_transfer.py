import json
import csv
import io
from datetime import datetime
from typing import Dict, Any, List, Tuple
from ..db import get_db_connection


class DataTransferService:
    """数据导入导出服务 - 支持持仓数据的备份和恢复"""

    def __init__(self):
        pass

    def export_positions_json(self, account_id: int = 1) -> Dict[str, Any]:
        """
        导出持仓数据为JSON格式

        Args:
            account_id: 账户ID

        Returns:
            包含持仓数据的字典
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 获取账户信息
            cursor.execute("SELECT id, name, created_at FROM accounts WHERE id = ?", (account_id,))
            account_row = cursor.fetchone()

            if not account_row:
                return {"error": "Account not found"}

            # 获取持仓数据
            cursor.execute("""
                SELECT account_id, code, cost, shares, updated_at
                FROM positions
                WHERE account_id = ?
                ORDER BY code
            """, (account_id,))

            positions = [dict(row) for row in cursor.fetchall()]

            # 获取交易记录
            cursor.execute("""
                SELECT id, account_id, code, op_type, amount_cny, shares_redeemed, confirm_date, confirm_nav, shares_added, cost_after, created_at, applied_at
                FROM transactions
                WHERE account_id = ?
                ORDER BY confirm_date DESC
            """, (account_id,))

            transactions = [dict(row) for row in cursor.fetchall()]

            # 获取数字货币持仓
            cursor.execute("""
                SELECT id, account_id, symbol, name, cost, amount, updated_at
                FROM crypto_positions
                WHERE account_id = ?
                ORDER BY symbol
            """, (account_id,))

            crypto_positions = [dict(row) for row in cursor.fetchall()]

            # 获取数字货币交易记录
            cursor.execute("""
                SELECT id, account_id, symbol, op_type, amount, price, total_cny, trade_time, created_at
                FROM crypto_transactions
                WHERE account_id = ?
                ORDER BY trade_time DESC
            """, (account_id,))

            crypto_transactions = [dict(row) for row in cursor.fetchall()]

            # 获取AI模拟账户数据
            cursor.execute("""
                SELECT id, name, description, source_account_id, initial_capital, current_value,
                       total_return_rate, is_active, review_day_of_week, last_review_date, created_at, updated_at
                FROM ai_simulation_accounts
                WHERE source_account_id = ?
            """, (account_id,))
            ai_accounts = [dict(row) for row in cursor.fetchall()]

            ai_positions = []
            ai_trades = []
            ai_value_history = []
            ai_reviews = []

            for ai_acc in ai_accounts:
                ai_account_id = ai_acc["id"]

                # AI持仓
                cursor.execute("""
                    SELECT id, ai_account_id, code, name, asset_type, cost, shares, current_price,
                           market_value, return_rate, weight, updated_at
                    FROM ai_simulation_positions
                    WHERE ai_account_id = ?
                """, (ai_account_id,))
                ai_positions.extend([dict(row) for row in cursor.fetchall()])

                # AI交易记录
                cursor.execute("""
                    SELECT id, ai_account_id, trade_date, code, name, asset_type, trade_type,
                           shares, price, amount, reason, created_at
                    FROM ai_simulation_trades
                    WHERE ai_account_id = ?
                    ORDER BY trade_date DESC
                """, (ai_account_id,))
                ai_trades.extend([dict(row) for row in cursor.fetchall()])

                # AI资产历史
                cursor.execute("""
                    SELECT id, ai_account_id, record_date, ai_value, source_value,
                           ai_return_rate, source_return_rate, outperformance, created_at
                    FROM ai_simulation_value_history
                    WHERE ai_account_id = ?
                    ORDER BY record_date DESC
                """, (ai_account_id,))
                ai_value_history.extend([dict(row) for row in cursor.fetchall()])

                # AI审视记录
                cursor.execute("""
                    SELECT id, ai_account_id, review_date, review_type, market_analysis,
                           portfolio_analysis, adjustment_strategy, executed_trades, created_at
                    FROM ai_simulation_reviews
                    WHERE ai_account_id = ?
                    ORDER BY review_date DESC
                """, (ai_account_id,))
                ai_reviews.extend([dict(row) for row in cursor.fetchall()])

            conn.close()

            # 构建导出数据
            export_data = {
                "export_info": {
                    "version": "1.1",
                    "export_time": datetime.now().isoformat(),
                    "account_id": account_id,
                    "account_name": account_row["name"]
                },
                "positions": positions,
                "transactions": transactions,
                "crypto_positions": crypto_positions,
                "crypto_transactions": crypto_transactions,
                "ai_simulation": {
                    "accounts": ai_accounts,
                    "positions": ai_positions,
                    "trades": ai_trades,
                    "value_history": ai_value_history,
                    "reviews": ai_reviews
                }
            }

            return export_data

        except Exception as e:
            return {"error": str(e)}

    def export_positions_csv(self, account_id: int = 1) -> Tuple[str, str]:
        """
        导出持仓数据为CSV格式

        Args:
            account_id: 账户ID

        Returns:
            (csv内容, 文件名) 的元组
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 获取持仓数据
            cursor.execute("""
                SELECT code, cost, shares, updated_at
                FROM positions
                ORDER BY code
            """, ())

            positions = cursor.fetchall()
            conn.close()

            # 创建CSV
            output = io.StringIO()
            writer = csv.writer(output)

            # 写入表头
            writer.writerow(['基金代码', '成本价', '持仓数量', '更新时间'])

            # 写入数据
            for pos in positions:
                writer.writerow([
                    pos['code'],
                    pos['cost'],
                    pos['shares'],
                    pos['updated_at']
                ])

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"positions_export_{timestamp}.csv"

            return output.getvalue(), filename

        except Exception as e:
            return "", str(e)

    def import_positions_json(self, data: Dict[str, Any], account_id: int = 1,
                              merge_strategy: str = "replace") -> Dict[str, Any]:
        """
        从JSON导入持仓数据

        Args:
            data: 导入的数据
            account_id: 目标账户ID
            merge_strategy: 合并策略 - "replace"(替换)/"merge"(合并)/"skip"(跳过重复)

        Returns:
            导入结果统计
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            stats = {
                "positions_added": 0,
                "positions_updated": 0,
                "positions_skipped": 0,
                "transactions_added": 0,
                "crypto_positions_added": 0,
                "crypto_positions_updated": 0,
                "crypto_transactions_added": 0,
                "errors": []
            }

            # 导入基金持仓
            positions = data.get("positions", [])
            for pos in positions:
                try:
                    code = pos.get("code")
                    cost = pos.get("cost")
                    shares = pos.get("shares") or pos.get("amount")  # 兼容旧数据

                    if not code or cost is None or shares is None:
                        continue

                    # 检查是否已存在
                    cursor.execute("SELECT account_id FROM positions WHERE account_id = ? AND code = ?",
                                   (account_id, code))
                    existing = cursor.fetchone()

                    if existing:
                        if merge_strategy == "replace":
                            cursor.execute("""
                                UPDATE positions
                                SET cost = ?, shares = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE account_id = ? AND code = ?
                            """, (cost, shares, account_id, code))
                            stats["positions_updated"] += 1
                        elif merge_strategy == "skip":
                            stats["positions_skipped"] += 1
                        else:  # merge - 累加数量，加权平均成本
                            cursor.execute("""
                                UPDATE positions
                                SET cost = (cost * shares + ? * ?) / (shares + ?),
                                    shares = shares + ?,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE account_id = ? AND code = ?
                            """, (cost, shares, shares, shares, account_id, code))
                            stats["positions_updated"] += 1
                    else:
                        cursor.execute("""
                            INSERT INTO positions (account_id, code, cost, shares)
                            VALUES (?, ?, ?, ?)
                        """, (account_id, code, cost, shares))
                        stats["positions_added"] += 1

                except Exception as e:
                    stats["errors"].append(f"Position {pos.get('code')}: {str(e)}")

            # 导入交易记录
            transactions = data.get("transactions", [])
            for trans in transactions:
                try:
                    code = trans.get("code")
                    op_type = trans.get("op_type")
                    amount_cny = trans.get("amount_cny") or trans.get("amount")
                    shares_redeemed = trans.get("shares_redeemed")
                    confirm_date = trans.get("confirm_date") or trans.get("trade_time")
                    confirm_nav = trans.get("confirm_nav") or trans.get("price")
                    shares_added = trans.get("shares_added")
                    cost_after = trans.get("cost_after")

                    if not code or not op_type:
                        continue

                    cursor.execute("""
                        INSERT INTO transactions (account_id, code, op_type, amount_cny, shares_redeemed, confirm_date, confirm_nav, shares_added, cost_after)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (account_id, code, op_type, amount_cny, shares_redeemed, confirm_date, confirm_nav, shares_added, cost_after))
                    stats["transactions_added"] += 1

                except Exception as e:
                    stats["errors"].append(f"Transaction: {str(e)}")

            # 导入数字货币持仓
            crypto_positions = data.get("crypto_positions", [])
            for pos in crypto_positions:
                try:
                    symbol = pos.get("symbol")
                    name = pos.get("name")
                    cost = pos.get("cost")
                    amount = pos.get("amount")

                    if not symbol or cost is None or amount is None:
                        continue

                    cursor.execute("SELECT id FROM crypto_positions WHERE account_id = ? AND symbol = ?",
                                   (account_id, symbol))
                    existing = cursor.fetchone()

                    if existing:
                        if merge_strategy == "replace":
                            cursor.execute("""
                                UPDATE crypto_positions
                                SET name = ?, cost = ?, amount = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE account_id = ? AND symbol = ?
                            """, (name, cost, amount, account_id, symbol))
                            stats["crypto_positions_updated"] += 1
                        elif merge_strategy == "skip":
                            stats["positions_skipped"] += 1
                        else:  # merge
                            cursor.execute("""
                                UPDATE crypto_positions
                                SET cost = (cost * amount + ? * ?) / (amount + ?),
                                    amount = amount + ?,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE account_id = ? AND symbol = ?
                            """, (cost, amount, amount, amount, account_id, symbol))
                            stats["crypto_positions_updated"] += 1
                    else:
                        cursor.execute("""
                            INSERT INTO crypto_positions (account_id, symbol, name, cost, amount)
                            VALUES (?, ?, ?, ?, ?)
                        """, (account_id, symbol, name, cost, amount))
                        stats["crypto_positions_added"] += 1

                except Exception as e:
                    stats["errors"].append(f"Crypto position {pos.get('symbol')}: {str(e)}")

            # 导入数字货币交易记录
            crypto_transactions = data.get("crypto_transactions", [])
            for trans in crypto_transactions:
                try:
                    symbol = trans.get("symbol")
                    op_type = trans.get("op_type")
                    amount = trans.get("amount")
                    price = trans.get("price")
                    total_cny = trans.get("total_cny")
                    trade_time = trans.get("trade_time")

                    if not symbol or not op_type or amount is None or price is None:
                        continue

                    cursor.execute("""
                        INSERT INTO crypto_transactions (account_id, symbol, op_type, amount, price, total_cny, trade_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (account_id, symbol, op_type, amount, price, total_cny, trade_time))
                    stats["crypto_transactions_added"] += 1

                except Exception as e:
                    stats["errors"].append(f"Crypto transaction: {str(e)}")

            # 导入AI模拟账户数据
            ai_simulation = data.get("ai_simulation", {})
            if ai_simulation:
                ai_accounts = ai_simulation.get("accounts", [])
                ai_id_mapping = {}

                for ai_acc in ai_accounts:
                    try:
                        old_id = ai_acc.get("id")
                        name = ai_acc.get("name", "AI模拟账户")
                        description = ai_acc.get("description", "")
                        initial_capital = ai_acc.get("initial_capital", 0)
                        current_value = ai_acc.get("current_value", 0)
                        total_return_rate = ai_acc.get("total_return_rate", 0)
                        is_active = ai_acc.get("is_active", 1)
                        review_day_of_week = ai_acc.get("review_day_of_week", 0)
                        last_review_date = ai_acc.get("last_review_date")
                        created_at = ai_acc.get("created_at")
                        updated_at = ai_acc.get("updated_at")

                        cursor.execute("""
                            INSERT INTO ai_simulation_accounts
                            (name, description, source_account_id, initial_capital, current_value,
                             total_return_rate, is_active, review_day_of_week, last_review_date, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (name, description, account_id, initial_capital, current_value,
                              total_return_rate, is_active, review_day_of_week, last_review_date, created_at, updated_at))
                        new_id = cursor.lastrowid
                        ai_id_mapping[old_id] = new_id
                        stats.setdefault("ai_accounts_added", 0)
                        stats["ai_accounts_added"] += 1

                    except Exception as e:
                        stats["errors"].append(f"AI account: {str(e)}")

                # 导入AI持仓
                ai_positions = ai_simulation.get("positions", [])
                for pos in ai_positions:
                    try:
                        old_ai_id = pos.get("ai_account_id")
                        new_ai_id = ai_id_mapping.get(old_ai_id)
                        if not new_ai_id:
                            continue

                        cursor.execute("""
                            INSERT INTO ai_simulation_positions
                            (ai_account_id, code, name, asset_type, cost, shares, current_price, market_value, return_rate, weight, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (new_ai_id, pos.get("code"), pos.get("name"), pos.get("asset_type", "fund"),
                              pos.get("cost"), pos.get("shares"), pos.get("current_price"),
                              pos.get("market_value"), pos.get("return_rate"), pos.get("weight"), pos.get("updated_at")))
                        stats.setdefault("ai_positions_added", 0)
                        stats["ai_positions_added"] += 1

                    except Exception as e:
                        stats["errors"].append(f"AI position: {str(e)}")

                # 导入AI交易记录
                ai_trades = ai_simulation.get("trades", [])
                for trade in ai_trades:
                    try:
                        old_ai_id = trade.get("ai_account_id")
                        new_ai_id = ai_id_mapping.get(old_ai_id)
                        if not new_ai_id:
                            continue

                        cursor.execute("""
                            INSERT INTO ai_simulation_trades
                            (ai_account_id, trade_date, code, name, asset_type, trade_type, shares, price, amount, reason, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (new_ai_id, trade.get("trade_date"), trade.get("code"), trade.get("name"),
                              trade.get("asset_type", "fund"), trade.get("trade_type"), trade.get("shares"),
                              trade.get("price"), trade.get("amount"), trade.get("reason"), trade.get("created_at")))
                        stats.setdefault("ai_trades_added", 0)
                        stats["ai_trades_added"] += 1

                    except Exception as e:
                        stats["errors"].append(f"AI trade: {str(e)}")

                # 导入AI资产历史
                ai_value_history = ai_simulation.get("value_history", [])
                for vh in ai_value_history:
                    try:
                        old_ai_id = vh.get("ai_account_id")
                        new_ai_id = ai_id_mapping.get(old_ai_id)
                        if not new_ai_id:
                            continue

                        cursor.execute("""
                            INSERT INTO ai_simulation_value_history
                            (ai_account_id, record_date, ai_value, source_value, ai_return_rate, source_return_rate, outperformance, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (new_ai_id, vh.get("record_date"), vh.get("ai_value"), vh.get("source_value"),
                              vh.get("ai_return_rate"), vh.get("source_return_rate"), vh.get("outperformance"), vh.get("created_at")))
                        stats.setdefault("ai_value_history_added", 0)
                        stats["ai_value_history_added"] += 1

                    except Exception as e:
                        stats["errors"].append(f"AI value history: {str(e)}")

                # 导入AI审视记录
                ai_reviews = ai_simulation.get("reviews", [])
                for rev in ai_reviews:
                    try:
                        old_ai_id = rev.get("ai_account_id")
                        new_ai_id = ai_id_mapping.get(old_ai_id)
                        if not new_ai_id:
                            continue

                        cursor.execute("""
                            INSERT INTO ai_simulation_reviews
                            (ai_account_id, review_date, review_type, market_analysis, portfolio_analysis, adjustment_strategy, executed_trades, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (new_ai_id, rev.get("review_date"), rev.get("review_type", "weekly"),
                              rev.get("market_analysis"), rev.get("portfolio_analysis"),
                              rev.get("adjustment_strategy"), rev.get("executed_trades"), rev.get("created_at")))
                        stats.setdefault("ai_reviews_added", 0)
                        stats["ai_reviews_added"] += 1

                    except Exception as e:
                        stats["errors"].append(f"AI review: {str(e)}")

            conn.commit()
            conn.close()

            return {
                "success": True,
                "stats": stats,
                "account_id": account_id,
                "import_time": datetime.now().isoformat()
            }

        except Exception as e:
            return {"error": str(e), "success": False}

    def import_positions_csv(self, csv_content: str, account_id: int = 1,
                             merge_strategy: str = "replace") -> Dict[str, Any]:
        """
        从CSV导入持仓数据

        Args:
            csv_content: CSV文件内容
            account_id: 目标账户ID
            merge_strategy: 合并策略

        Returns:
            导入结果统计
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            stats = {
                "positions_added": 0,
                "positions_updated": 0,
                "positions_skipped": 0,
                "errors": []
            }

            # 解析CSV
            reader = csv.DictReader(io.StringIO(csv_content))

            for row in reader:
                try:
                    code = row.get('基金代码') or row.get('code')
                    cost = float(row.get('成本价') or row.get('cost', 0))
                    shares = float(row.get('持仓数量') or row.get('shares', 0))

                    if not code:
                        continue

                    # 检查是否已存在
                    cursor.execute("SELECT id FROM positions WHERE code = ?", (code,))
                    existing = cursor.fetchone()

                    if existing:
                        if merge_strategy == "replace":
                            cursor.execute("""
                                UPDATE positions
                                SET cost = ?, shares = ?, updated_at = CURRENT_TIMESTAMP
                                WHERE code = ?
                            """, (cost, shares, code))
                            stats["positions_updated"] += 1
                        elif merge_strategy == "skip":
                            stats["positions_skipped"] += 1
                        else:  # merge - 累加数量，加权平均成本
                            cursor.execute("""
                                UPDATE positions
                                SET cost = (cost * shares + ? * ?) / (shares + ?),
                                    shares = shares + ?,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE code = ?
                            """, (cost, shares, shares, shares, code))
                            stats["positions_updated"] += 1
                    else:
                        cursor.execute("""
                            INSERT INTO positions (code, cost, shares, updated_at)
                            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                        """, (code, cost, shares))
                        stats["positions_added"] += 1

                except Exception as e:
                    stats["errors"].append(f"Row {row}: {str(e)}")

            conn.commit()
            conn.close()

            return {
                "success": True,
                "stats": stats,
                "account_id": account_id,
                "import_time": datetime.now().isoformat()
            }

        except Exception as e:
            return {"error": str(e), "success": False}


# 创建全局实例
data_transfer_service = DataTransferService()
