import os
import re
import datetime
import requests
from typing import Optional, Dict, Any, List
from duckduckgo_search import DDGS
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ..config import Config

class AIService:
    def __init__(self):
        self.llm = self._init_llm()

    def _init_llm(self, fast_mode=True):
        api_base = Config.OPENAI_API_BASE
        api_key = Config.OPENAI_API_KEY
        model = Config.AI_MODEL_NAME

        if not api_key:
            return None

        return ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=0.2,
            request_timeout=60 if fast_mode else 120
        )

    def search_news(self, query: str) -> str:
        try:
            ddgs = DDGS(verify=False)
            results = ddgs.text(
                keywords=query,
                region="cn-zh",
                safesearch="off",
                timelimit="w",
                max_results=5,
            )
            
            if not results:
                return ""
            
            output = f"【{query}】相关新闻：\n"
            for i, res in enumerate(results, 1):
                output += f"{i}. {res.get('title')} - {res.get('body')}\n"
            return output
        except Exception as e:
            print(f"Search error: {e}")
            return ""

    async def analyze_fund(self, fund_info: Dict[str, Any]) -> Dict[str, Any]:
        if not self.llm:
            return {
                "summary": "未配置 LLM API Key，无法进行分析。",
                "risk": "未知",
                "sector": "未知",
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            }

        fund_name = fund_info.get("name", "未知基金")
        est_rate = fund_info.get("estRate", 0.0)
        
        # Simple sector heuristic from name
        sector_context = ""
        for k, v in {
            "科技": ["半导体", "电子", "计算机", "AI", "通信"],
            "消费": ["酒", "饮料", "食品", "消费"],
            "医药": ["医", "药", "生物"],
            "新能源": ["光伏", "电池", "新能源", "车"],
            "金融": ["银行", "证券", "保险"]
        }.items():
            if any(kw in fund_name for kw in v):
                sector_context = k
                break
        
        # Search news if we have a sector or fund name
        news_context = ""
        if sector_context:
            news_context = self.search_news(f"{sector_context}行业 最新消息")
        else:
            news_context = self.search_news(f"{fund_name} 基金")

        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一位资深基金分析师。请根据提供的基金数据和市场新闻，生成一份简短的实时估值解读。"),
            ("user", f"""
            基金名称：{fund_name}
            今日实时估值涨跌：{est_rate}%
            所属/相关板块：{sector_context}
            
            相关市场新闻：
            {news_context}
            
            请输出 JSON 格式，包含三个字段：
            1. summary: 走势解读（50字以内，结合估值和新闻）
            2. sector: 板块影响（30字以内）
            3. risk: 风险等级（低/中/高，并简述原因）
            """)
        ])

        chain = prompt | self.llm | StrOutputParser()
        
        try:
            raw_result = await chain.ainvoke({})
            # Debug log
            print(f"LLM Raw Output: {raw_result}")
            
            # Naive JSON extraction if LLM outputs markdown code block
            clean_json = raw_result.strip()
            if "```json" in clean_json:
                clean_json = clean_json.split("```json")[1].split("```")[0]
            elif "```" in clean_json:
                clean_json = clean_json.split("```")[1].split("```")[0]
            
            import json
            result = json.loads(clean_json)
            result["timestamp"] = datetime.datetime.now().strftime("%H:%M:%S")
            return result
        except Exception as e:
            print(f"AI Analysis Error: {e}")
            return {
                "summary": f"分析生成失败: {str(e)}",
                "risk": "未知",
                "sector": "未知",
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            }

ai_service = AIService()
