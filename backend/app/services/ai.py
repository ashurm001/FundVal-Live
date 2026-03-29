import os
import re
import datetime
from datetime import timezone, timedelta
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

    def _get_local_time(self):
        """获取本地时间（东八区）"""
        utc_now = datetime.datetime.now(timezone.utc)
        local_tz = timezone(timedelta(hours=8))  # 东八区
        return utc_now.astimezone(local_tz)

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
        Also save to messages table for unified message center access.
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            now = self._get_local_time()
            analysis_date = now.strftime("%Y-%m-%d")
            analysis_time = now.strftime("%H:%M:%S")

            # Save to ai_analysis_history table
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

            # Also save to messages table for unified access
            self._save_fund_analysis_to_messages(fund_code, fund_name, analysis)

        except Exception as e:
            print(f"Failed to save analysis to database: {e}")

    def _save_fund_analysis_to_messages(self, fund_code: str, fund_name: str, analysis: Dict[str, Any]):
        """保存单个基金分析结果到消息表并发送邮件"""
        try:
            from .messages import message_service
            from .email import send_email
            import json

            risk_level = analysis.get("risk_level", "未知")
            status = analysis.get("indicators", {}).get("status", "--")
            summary = analysis.get("summary", "")
            analysis_report = analysis.get("analysis_report", "")
            indicators_desc = analysis.get("indicators", {}).get("desc", "")

            # 构建标题
            title = f"{fund_name} ({fund_code}) - AI分析"

            # 构建内容结构
            content = {
                "fund_code": fund_code,
                "fund_name": fund_name,
                "risk_level": risk_level,
                "status": status,
                "indicators": analysis.get("indicators", {}),
                "analysis_report": analysis_report,
                "summary": summary
            }

            # 保存消息
            message_service.create_message({
                "msg_type": "fund_analysis",
                "title": title,
                "content": content,
                "summary": summary[:100] + "..." if len(summary) > 100 else summary,
                "risk_level": risk_level,
                "fund_count": 1,
                "total_value": None
            })

            # 发送邮件通知
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM settings WHERE key = 'NOTIFICATION_EMAIL'")
                notif_row = cursor.fetchone()
                notification_email = notif_row[0] if notif_row and notif_row[0] else None
                conn.close()

                if notification_email:
                    now = self._get_local_time()
                    email_content = f"""
                    <h3>{fund_name} ({fund_code}) - AI分析报告</h3>
                    <p><b>分析时间:</b> {now.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><b>风险等级:</b> {risk_level}</p>
                    <p><b>状态:</b> {status}</p>
                    <p><b>技术指标:</b> {indicators_desc}</p>
                    <hr>
                    <h4>分析摘要:</h4>
                    <p>{summary}</p>
                    <hr>
                    <h4>详细分析:</h4>
                    <div style="white-space: pre-wrap; font-family: monospace; font-size: 12px;">{analysis_report}</div>
                    """
                    if send_email(notification_email, title, email_content, is_html=True):
                        print(f"[AI Service] 基金分析报告已发送到 {notification_email}")
            except Exception as email_error:
                print(f"[AI Service] 发送基金分析邮件失败: {str(email_error)}")
        except Exception as e:
            print(f"Failed to save fund analysis to messages: {e}")

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

    async def analyze_fund(self, fund_info: Dict[str, Any]) -> Dict[str, Any]:
        # 每次调用时重新初始化 LLM，支持配置热重载
        llm = self._init_llm()

        if not llm:
            return {
                "summary": "未配置 LLM API Key，无法进行分析。",
                "risk_level": "未知",
                "analysis_report": "请在设置页面配置 OpenAI API Key 以启用 AI 分析功能。",
                "timestamp": self._get_local_time().strftime("%H:%M:%S")
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
                "timestamp": self._get_local_time().strftime("%H:%M:%S")
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
            result["timestamp"] = self._get_local_time().strftime("%H:%M:%S")

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
                "timestamp": self._get_local_time().strftime("%H:%M:%S")
            }

    async def analyze_portfolio(self, positions: List[Dict[str, Any]], summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a portfolio of fund positions or crypto positions.
        """
        llm = self._init_llm()

        if not llm:
            return {
                "error": "未配置 LLM API Key，无法进行分析。",
                "timestamp": self._get_local_time().strftime("%H:%M:%S")
            }

        # Calculate portfolio statistics
        total_value = summary.get("total_market_value", 0)
        total_cost = summary.get("total_cost", 0)
        total_income = summary.get("total_income", 0)
        total_return_rate = summary.get("total_return_rate", 0)
        
        # 获取现金账户金额
        usdt_cash = summary.get("usdt_cash", 0)
        cash = summary.get("cash", 0)

        # Check if this is crypto portfolio (has 'symbol' field) or fund portfolio (has 'code' field)
        is_crypto = positions and "symbol" in positions[0] if positions else False

        # Group by type (fund type or crypto)
        type_allocation = {}
        for pos in positions:
            # 跳过现金账户（单独处理）
            if pos.get("is_cash", False):
                continue
                
            if is_crypto:
                # For crypto, group by "数字货币"
                asset_type = "数字货币"
            else:
                # For funds, use the fund type
                asset_type = pos.get("type", "未知")

            if asset_type not in type_allocation:
                type_allocation[asset_type] = {"value": 0, "count": 0}

            # Get market value - crypto uses 'market_value', funds use 'actual_market_value'
            market_value = pos.get("market_value", pos.get("actual_market_value", 0))
            type_allocation[asset_type]["value"] += market_value
            type_allocation[asset_type]["count"] += 1
        
        # 添加现金账户到类型分配
        if is_crypto and usdt_cash > 0:
            if "USDT现金" not in type_allocation:
                type_allocation["USDT现金"] = {"value": 0, "count": 0}
            type_allocation["USDT现金"]["value"] += usdt_cash
            type_allocation["USDT现金"]["count"] += 1
        elif not is_crypto and cash > 0:
            if "现金" not in type_allocation:
                type_allocation["现金"] = {"value": 0, "count": 0}
            type_allocation["现金"]["value"] += cash
            type_allocation["现金"]["count"] += 1

        # Calculate percentages
        for asset_type in type_allocation:
            type_allocation[asset_type]["percentage"] = (
                type_allocation[asset_type]["value"] / total_value * 100 if total_value > 0 else 0
            )

        # Sort positions by market value
        sorted_positions = sorted(
            positions,
            key=lambda x: x.get("market_value", x.get("actual_market_value", 0)),
            reverse=True
        )

        # Prepare portfolio summary
        portfolio_summary = {
            "asset_count": len(positions),
            "total_value": total_value,
            "total_cost": total_cost,
            "total_income": total_income,
            "return_rate": total_return_rate,
            "type_allocation": type_allocation,
            "top_holdings": [
                {
                    "code": pos.get("symbol") if is_crypto else pos.get("code"),
                    "name": pos.get("name"),
                    "type": "数字货币" if is_crypto else pos.get("type"),
                    "market_value": pos.get("market_value", pos.get("actual_market_value", 0)),
                    "return_rate": pos.get("total_return_rate"),
                    "weight": ((pos.get("market_value", pos.get("actual_market_value", 0)) / total_value * 100)
                    if total_value > 0 else 0)
                }
                for pos in sorted_positions[:5]
            ]
        }

        # Create prompt for portfolio analysis
        # Use crypto-specific prompt for crypto portfolios, fund prompt for fund portfolios
        from .prompts import PROFESSIONAL_PORTFOLIO_ANALYSIS_PROMPT, CRYPTO_PORTFOLIO_ANALYSIS_PROMPT

        prompt_template = CRYPTO_PORTFOLIO_ANALYSIS_PROMPT if is_crypto else PROFESSIONAL_PORTFOLIO_ANALYSIS_PROMPT

        try:
            chain = prompt_template | llm | StrOutputParser()

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
                "asset_count": len(positions),
                "total_value": total_value,
                "total_income": total_income,
                "return_rate": total_return_rate
            }

            # Add asset allocation
            result["asset_allocation"] = {
                asset_type: {
                    "value": data["value"],
                    "percentage": data["percentage"],
                    "count": data["count"]
                }
                for asset_type, data in type_allocation.items()
            }

            result["timestamp"] = self._get_local_time().strftime("%H:%M:%S")

            # Save to messages
            self._save_portfolio_analysis_to_messages(result, len(positions), total_value, is_crypto)

            return result

        except Exception as e:
            print(f"Portfolio Analysis Error: {e}")
            return {
                "error": f"分析生成失败: {str(e)}",
                "portfolio_overview": {
                    "asset_count": len(positions),
                    "total_value": total_value,
                    "total_income": total_income,
                    "return_rate": total_return_rate
                },
                "asset_allocation": {
                    asset_type: {
                        "value": data["value"],
                        "percentage": data["percentage"]
                    }
                    for asset_type, data in type_allocation.items()
                },
                "timestamp": self._get_local_time().strftime("%H:%M:%S")
            }

    def _save_portfolio_analysis_to_messages(self, result: Dict[str, Any], asset_count: int, total_value: float, is_crypto: bool = False):
        """保存持仓分析结果到消息表并发送邮件"""
        try:
            from .messages import message_service
            from .email import send_email
            import json

            # 从新的返回结构中提取信息
            risk_analysis = result.get("risk_analysis", {})
            risk_level = risk_analysis.get("risk_rating", "未知")
            overview = result.get("overview", {})
            conclusion = result.get("conclusion", "")
            portfolio_overview = result.get("portfolio_overview", {})
            asset_allocation = result.get("asset_allocation", {})

            # 构建标题
            asset_type = "数字货币" if is_crypto else "基金"
            title = f"{asset_type}持仓分析报告 - {risk_level}"

            # 构建摘要
            summary = conclusion[:100] + "..." if len(conclusion) > 100 else conclusion

            # 保存消息
            message_service.create_message({
                "msg_type": "portfolio_analysis",
                "title": title,
                "content": result,
                "summary": summary,
                "risk_level": risk_level,
                "asset_count": asset_count,
                "total_value": total_value,
                "is_crypto": is_crypto
            })

            # 发送邮件通知
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM settings WHERE key = 'NOTIFICATION_EMAIL'")
                notif_row = cursor.fetchone()
                notification_email = notif_row[0] if notif_row and notif_row[0] else None
                conn.close()

                if notification_email:
                    now = self._get_local_time()
                    
                    # 构建资产分配信息
                    allocation_html = ""
                    for asset_type_name, data in asset_allocation.items():
                        allocation_html += f"<li><b>{asset_type_name}:</b> {data.get('value', 0):.2f}元 ({data.get('percentage', 0):.1f}%)</li>"
                    
                    email_content = f"""
                    <h3>{title}</h3>
                    <p><b>分析时间:</b> {now.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <hr>
                    <h4>账户概览:</h4>
                    <ul>
                        <li><b>资产数量:</b> {portfolio_overview.get('asset_count', 0)}</li>
                        <li><b>总市值:</b> {total_value:.2f}元</li>
                        <li><b>总成本:</b> {portfolio_overview.get('total_income', 0) + portfolio_overview.get('total_cost', 0) if portfolio_overview.get('total_cost', 0) else '--':.2f}元</li>
                        <li><b>总收益:</b> {portfolio_overview.get('total_income', 0):.2f}元</li>
                        <li><b>收益率:</b> {portfolio_overview.get('return_rate', 0):.2f}%</li>
                        <li><b>风险等级:</b> {risk_level}</li>
                    </ul>
                    <h4>资产分配:</h4>
                    <ul>{allocation_html}</ul>
                    <hr>
                    <h4>分析结论:</h4>
                    <div style="white-space: pre-wrap;">{conclusion}</div>
                    """
                    if send_email(notification_email, title, email_content, is_html=True):
                        print(f"[AI Service] 持仓分析报告已发送到 {notification_email}")
            except Exception as email_error:
                print(f"[AI Service] 发送持仓分析邮件失败: {str(email_error)}")
        except Exception as e:
            print(f"Failed to save portfolio analysis to messages: {e}")

ai_service = AIService()
