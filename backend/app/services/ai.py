import os
import re
import datetime
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, List
from duckduckgo_search import DDGS
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from ..config import Config
from ..db import get_db_connection
from .prompts import LINUS_FINANCIAL_ANALYSIS_PROMPT
from .fund import get_fund_history, _calculate_technical_indicators


class AIService:
    def __init__(self):
        # 不在初始化时创建 LLM，而是每次调用时动态创建
        pass

    def _init_llm(self, fast_mode=True):
        # 每次调用时重新读取配置，支持热重载
        api_base = Config.OPENAI_API_BASE
        api_key = Config.OPENAI_API_KEY
        model = Config.AI_MODEL_NAME

        if not api_key:
            return None

        # 支持OpenAI和DeepSeek等兼容OpenAI API格式的模型
        # DeepSeek配置示例：
        # OPENAI_API_KEY = "your_deepseek_api_key"
        # OPENAI_API_BASE = "https://api.deepseek.com/v1"
        # AI_MODEL_NAME = "deepseek-chat"
        try:
            return ChatOpenAI(
                model=model,
                openai_api_key=api_key,
                openai_api_base=api_base,
                temperature=0.3, # Linus needs to be sharp, not creative
                request_timeout=60 if fast_mode else 120
            )
        except Exception as e:
            print(f"Failed to initialize LLM: {e}")
            return None

    def search_news(self, query: str) -> str:
        try:
            # Simple wrapper to fetch news
            ddgs = DDGS(verify=False)
            results = ddgs.text(
                keywords=query,
                region="cn-zh",
                safesearch="off",
                timelimit="w", # last week
                max_results=5,
            )
            
            if not results:
                return "暂无相关近期新闻。"
            
            output = ""
            for i, res in enumerate(results, 1):
                output += f"{i}. {res.get('title')} - {res.get('body')}\n"
            return output
        except Exception as e:
            print(f"Search error: {e}")
            return "新闻搜索服务暂时不可用。"

    def _calculate_indicators(self, history: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Calculate simple technical indicators based on recent history.
        """
        if not history or len(history) < 5:
            return {"status": "数据不足", "desc": "新基金或数据缺失"}

        navs = [item['nav'] for item in history]
        current_nav = navs[-1]
        max_nav = max(navs)
        min_nav = min(navs)
        avg_nav = sum(navs) / len(navs)

        # Position in range
        position = (current_nav - min_nav) / (max_nav - min_nav) if max_nav > min_nav else 0.5

        status = "正常"
        if position > 0.9: status = "高位"
        elif position < 0.1: status = "低位"
        elif current_nav > avg_nav * 1.05: status = "偏高"
        elif current_nav < avg_nav * 0.95: status = "偏低"

        return {
            "status": status,
            "desc": f"近30日最高{max_nav:.4f}, 最低{min_nav:.4f}, 现价处于{'高位' if position>0.8 else '低位' if position<0.2 else '中位'}区间 ({int(position*100)}%)"
        }

    def _save_analysis_to_db(self, fund_code: str, fund_name: str, analysis: Dict[str, Any]):
        """
        Save AI analysis result to database for historical review.
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            now = datetime.datetime.now()
            analysis_date = now.strftime("%Y-%m-%d")
            analysis_time = now.strftime("%H:%M:%S")

            cursor.execute("""
                INSERT INTO ai_analysis_history
                (fund_code, fund_name, analysis_date, analysis_time, risk_level, status,
                 indicators_desc, analysis_report, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fund_code,
                fund_name,
                analysis_date,
                analysis_time,
                analysis.get("risk_level"),
                analysis.get("indicators", {}).get("status"),
                analysis.get("indicators", {}).get("desc"),
                analysis.get("analysis_report"),
                analysis.get("summary")
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Failed to save analysis to database: {e}")

    def get_analysis_history(self, fund_code: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get AI analysis history for a specific fund.
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, fund_code, fund_name, analysis_date, analysis_time,
                       risk_level, status, indicators_desc, analysis_report, summary
                FROM ai_analysis_history
                WHERE fund_code = ?
                ORDER BY analysis_date DESC, analysis_time DESC
                LIMIT ?
            """, (fund_code, limit))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Failed to get analysis history: {e}")
            return []

    def get_user_notes(self, fund_code: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get user notes for a specific fund.
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, fund_code, fund_name, note_date, note_time, note_content, note_color
                FROM user_notes
                WHERE fund_code = ?
                ORDER BY note_date DESC, note_time DESC
                LIMIT ?
            """, (fund_code, limit))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Failed to get user notes: {e}")
            return []

    def save_user_note(self, fund_code: str, fund_name: str, note_content: str, note_date: str = None, note_color: str = "#10b981") -> Dict[str, Any]:
        """
        Save a user note for a specific fund.
        """
        try:
            now = datetime.datetime.now()
            if not note_date:
                note_date = now.strftime("%Y-%m-%d")
            note_time = now.strftime("%H:%M:%S")

            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_notes (fund_code, fund_name, note_date, note_time, note_content, note_color)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (fund_code, fund_name, note_date, note_time, note_content, note_color))
                
                note_id = cursor.lastrowid
                conn.commit()
            finally:
                conn.close()

            return {
                "id": note_id,
                "fund_code": fund_code,
                "fund_name": fund_name,
                "note_date": note_date,
                "note_time": note_time,
                "note_content": note_content,
                "note_color": note_color
            }
        except Exception as e:
            print(f"Failed to save user note: {e}")
            return {"error": str(e)}

    def delete_user_note(self, note_id: int) -> bool:
        """
        Delete a user note.
        """
        try:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM user_notes WHERE id = ?", (note_id,))
                conn.commit()
            finally:
                conn.close()
            return True
        except Exception as e:
            print(f"Failed to delete user note: {e}")
            return False

    def update_user_note(self, note_id: int, note_content: str, note_color: str = None) -> Dict[str, Any]:
        """
        Update a user note.
        """
        try:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()

                # Get current note to preserve other fields
                cursor.execute("SELECT * FROM user_notes WHERE id = ?", (note_id,))
                row = cursor.fetchone()
                if not row:
                    return {"error": "Note not found"}

                # Update note_content and note_color (if provided)
                if note_color:
                    cursor.execute("""
                        UPDATE user_notes 
                        SET note_content = ?, note_color = ?
                        WHERE id = ?
                    """, (note_content, note_color, note_id))
                else:
                    cursor.execute("""
                        UPDATE user_notes 
                        SET note_content = ?
                        WHERE id = ?
                    """, (note_content, note_id))

                conn.commit()

                # Fetch updated note
                cursor.execute("""
                    SELECT id, fund_code, fund_name, note_date, note_time, note_content, note_color
                    FROM user_notes
                    WHERE id = ?
                """, (note_id,))
                updated_row = cursor.fetchone()
            finally:
                conn.close()

            return dict(updated_row) if updated_row else {"error": "Failed to fetch updated note"}
        except Exception as e:
            print(f"Failed to update user note: {e}")
            return {"error": str(e)}

    async def analyze_fund(self, fund_info: Dict[str, Any]) -> Dict[str, Any]:
        # 每次调用时重新初始化 LLM，支持配置热重载
        llm = self._init_llm()

        if not llm:
            return {
                "summary": "未配置 LLM API Key，无法进行分析。",
                "risk_level": "未知",
                "analysis_report": "请在设置页面配置 OpenAI API Key 以启用 AI 分析功能。",
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            }

        fund_id = fund_info.get("id")
        fund_name = fund_info.get("name", "未知基金")

        # 1. Gather Data
        # History (Last 250 days for technical indicators)
        history = get_fund_history(fund_id, limit=250)
        indicators = self._calculate_indicators(history[:30] if len(history) >= 30 else history)

        # Calculate technical indicators (Sharpe, Volatility, Max Drawdown)
        technical_indicators = _calculate_technical_indicators(history)

        # 1.5 Data Consistency Check
        consistency_note = ""
        try:
            sharpe = technical_indicators.get("sharpe")
            annual_return_str = technical_indicators.get("annual_return", "")
            volatility_str = technical_indicators.get("volatility", "")

            if sharpe != "--" and annual_return_str != "--" and volatility_str != "--":
                # Parse percentage strings
                annual_return = float(annual_return_str.rstrip('%')) / 100.0
                volatility = float(volatility_str.rstrip('%')) / 100.0
                sharpe_val = float(sharpe)

                # Expected Sharpe = (annual_return - rf) / volatility
                rf = 0.02
                expected_sharpe = (annual_return - rf) / volatility if volatility > 0 else 0
                sharpe_diff = abs(expected_sharpe - sharpe_val)

                if sharpe_diff > 0.3:
                    consistency_note = f"\n 数据一致性警告：夏普比率 {sharpe_val} 与计算值 {expected_sharpe:.2f} 偏差 {sharpe_diff:.2f}，可能存在数据异常。"
                else:
                    consistency_note = f"\n✓ 数据自洽性验证通过：夏普比率与年化回报/波动率数学一致（偏差 {sharpe_diff:.2f}）。"
        except:
            pass

        history_summary = "暂无历史数据"
        if history:
            recent_history = history[:30]
            history_summary = f"近30日走势: 起始{recent_history[0]['nav']} -> 结束{recent_history[-1]['nav']}. {indicators['desc']}"

        # Prepare Fund Info Summary (Exclude detailed holdings to focus AI on Fund level)
        fund_summary = {
            "id": fund_id,
            "name": fund_name,
            "type": fund_info.get("type"),
            "manager": fund_info.get("manager"),
            "latest_nav": fund_info.get("nav"),
            "update_time": fund_info.get("time")
        }

        # Append consistency note to technical indicators
        technical_indicators_with_note = str(technical_indicators) + consistency_note

        # 2. Invoke LLM with Linus Prompt
        if not llm:
            return {
                "summary": "分析生成失败",
                "risk_level": "未知",
                "analysis_report": "LLM 初始化失败，请检查配置",
                "indicators": indicators,
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            }

        chain = LINUS_FINANCIAL_ANALYSIS_PROMPT | llm | StrOutputParser()

        try:
            raw_result = await chain.ainvoke({
                "fund_info": str(fund_summary),
                "history_summary": history_summary,
                "technical_indicators": technical_indicators_with_note
            })

            # 3. Parse Result
            clean_json = raw_result.strip()
            if "```json" in clean_json:
                clean_json = clean_json.split("```json")[1].split("```")[0]
            elif "```" in clean_json:
                clean_json = clean_json.split("```")[1].split("```")[0]

            import json
            result = json.loads(clean_json)

            # Enrich with indicators for frontend display
            result["indicators"] = indicators
            result["timestamp"] = datetime.datetime.now().strftime("%H:%M:%S")

            # Save analysis to database
            self._save_analysis_to_db(fund_id, fund_name, result)

            return result

        except Exception as e:
            print(f"AI Analysis Error: {e}")
            return {
                "summary": "分析生成失败",
                "risk_level": "未知",
                "analysis_report": f"LLM 调用或解析失败: {str(e)}",
                "indicators": indicators,
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            }

    async def analyze_portfolio(self, positions: List[Dict[str, Any]], summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a portfolio of fund positions.
        """
        llm = self._init_llm()

        if not llm:
            return {
                "error": "未配置 LLM API Key，无法进行分析。",
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            }

        # Calculate portfolio statistics
        total_value = summary.get("total_market_value", 0)
        total_cost = summary.get("total_cost", 0)
        total_income = summary.get("total_income", 0)
        total_return_rate = summary.get("total_return_rate", 0)

        # Group by fund type
        type_allocation = {}
        for pos in positions:
            fund_type = pos.get("type", "未知")
            if fund_type not in type_allocation:
                type_allocation[fund_type] = {"value": 0, "count": 0}
            type_allocation[fund_type]["value"] += pos.get("actual_market_value", 0)
            type_allocation[fund_type]["count"] += 1

        # Calculate percentages
        for fund_type in type_allocation:
            type_allocation[fund_type]["percentage"] = (
                type_allocation[fund_type]["value"] / total_value * 100 if total_value > 0 else 0
            )

        # Sort positions by market value
        sorted_positions = sorted(positions, key=lambda x: x.get("actual_market_value", 0), reverse=True)

        # Prepare portfolio summary
        portfolio_summary = {
            "fund_count": len(positions),
            "total_value": total_value,
            "total_cost": total_cost,
            "total_income": total_income,
            "return_rate": total_return_rate,
            "type_allocation": type_allocation,
            "top_holdings": [
                {
                    "code": pos.get("code"),
                    "name": pos.get("name"),
                    "type": pos.get("type"),
                    "market_value": pos.get("actual_market_value"),
                    "return_rate": pos.get("total_return_rate"),
                    "weight": pos.get("actual_market_value", 0) / total_value * 100 if total_value > 0 else 0
                }
                for pos in sorted_positions[:5]
            ]
        }

        # Create prompt for portfolio analysis
        from .prompts import LINUS_PORTFOLIO_CRITIQUE_PROMPT

        try:
            chain = LINUS_PORTFOLIO_CRITIQUE_PROMPT | llm | StrOutputParser()

            raw_result = await chain.ainvoke({
                "portfolio_summary": str(portfolio_summary),
                "total_value": str(total_value)
            })

            # Parse Result
            clean_json = raw_result.strip()
            if "```json" in clean_json:
                clean_json = clean_json.split("```json")[1].split("```")[0]
            elif "```" in clean_json:
                clean_json = clean_json.split("```")[1].split("```")[0]

            import json
            result = json.loads(clean_json)

            # Add portfolio overview
            result["portfolio_overview"] = {
                "fund_count": len(positions),
                "total_value": total_value,
                "total_income": total_income,
                "return_rate": total_return_rate
            }

            # Add asset allocation
            result["asset_allocation"] = {
                fund_type: {
                    "value": data["value"],
                    "percentage": data["percentage"],
                    "count": data["count"]
                }
                for fund_type, data in type_allocation.items()
            }

            result["timestamp"] = datetime.datetime.now().strftime("%H:%M:%S")

            # Save to messages
            self._save_portfolio_analysis_to_messages(result, len(positions), total_value)

            return result

        except Exception as e:
            print(f"Portfolio Analysis Error: {e}")
            return {
                "error": f"分析生成失败: {str(e)}",
                "portfolio_overview": {
                    "fund_count": len(positions),
                    "total_value": total_value,
                    "total_income": total_income,
                    "return_rate": total_return_rate
                },
                "asset_allocation": {
                    fund_type: {
                        "value": data["value"],
                        "percentage": data["percentage"]
                    }
                    for fund_type, data in type_allocation.items()
                },
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            }

    def _save_portfolio_analysis_to_messages(self, result: Dict[str, Any], fund_count: int, total_value: float):
        """保存持仓分析结果到消息表"""
        try:
            from .messages import message_service
            
            # 构建标题
            score = result.get("score", 0)
            risk_level = result.get("risk_level", "未知")
            title = f"持仓诊断报告 - 健康度{score}分 ({risk_level})"
            
            # 构建摘要
            critique = result.get("critique", "")
            summary = critique[:100] + "..." if len(critique) > 100 else critique
            
            # 保存消息
            message_service.create_message({
                "msg_type": "portfolio_analysis",
                "title": title,
                "content": result,
                "summary": summary,
                "score": score,
                "risk_level": risk_level,
                "fund_count": fund_count,
                "total_value": total_value
            })
        except Exception as e:
            print(f"Failed to save portfolio analysis to messages: {e}")

ai_service = AIService()
