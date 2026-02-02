import time
import json
import re
from typing import List, Dict, Any

import pandas as pd
import akshare as ak
import requests

from ..db import get_db_connection
from ..config import Config


# Major Sector Categories Mapping (from MaYiFund)
MAJOR_CATEGORIES = {
    "科技": ["人工智能", "半导体", "云计算", "5G", "光模块", "CPO", "F5G", "通信设备", "PCB", "消费电子",
             "计算机", "软件开发", "信创", "网络安全", "IT服务", "国产软件", "计算机设备", "光通信",
             "算力", "脑机接口", "通信", "电子", "光学光电子", "元件", "存储芯片", "第三代半导体",
             "光刻胶", "电子化学品", "LED", "毫米波", "智能穿戴", "东数西算", "数据要素", "国资云",
             "Web3.0", "AIGC", "AI应用", "AI手机", "AI眼镜", "DeepSeek", "TMT", "科技"],
    "医药健康": ["医药生物", "医疗器械", "生物疫苗", "CRO", "创新药", "精准医疗", "医疗服务", "中药",
                 "化学制药", "生物制品", "基因测序", "超级真菌"],
    "消费": ["食品饮料", "白酒", "家用电器", "纺织服饰", "商贸零售", "新零售", "家居用品", "文娱用品",
             "婴童", "养老产业", "体育", "教育", "在线教育", "社会服务", "轻工制造", "新消费",
             "可选消费", "消费", "家电零部件", "智能家居"],
    "金融": ["银行", "证券", "保险", "非银金融", "国有大型银行", "股份制银行", "城商行", "金融"],
    "能源": ["新能源", "煤炭", "石油石化", "电力", "绿色电力", "氢能源", "储能", "锂电池", "电池",
             "光伏设备", "风电设备", "充电桩", "固态电池", "能源", "煤炭开采", "公用事业", "锂矿"],
    "工业制造": ["机械设备", "汽车", "新能源车", "工程机械", "高端装备", "电力设备", "专用设备",
                 "通用设备", "自动化设备", "机器人", "人形机器人", "汽车零部件", "汽车服务",
                 "汽车热管理", "尾气治理", "特斯拉", "无人驾驶", "智能驾驶", "电网设备", "电机",
                 "高端制造", "工业4.0", "工业互联", "低空经济", "通用航空"],
    "材料": ["有色金属", "黄金股", "贵金属", "基础化工", "钢铁", "建筑材料", "稀土永磁", "小金属",
             "工业金属", "材料", "大宗商品", "资源"],
    "军工": ["国防军工", "航天装备", "航空装备", "航海装备", "军工电子", "军民融合", "商业航天",
             "卫星互联网", "航母", "航空机场"],
    "基建地产": ["建筑装饰", "房地产", "房地产开发", "房地产服务", "交通运输", "物流"],
    "环保": ["环保", "环保设备", "环境治理", "垃圾分类", "碳中和", "可控核聚变", "液冷"],
    "传媒": ["传媒", "游戏", "影视", "元宇宙", "超清视频", "数字孪生"],
    "主题": ["国企改革", "一带一路", "中特估", "中字头", "并购重组", "华为", "新兴产业",
             "国家安防", "安全主题", "农牧主题", "农林牧渔", "养殖业", "猪肉", "高端装备"]
}


def _df_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    return df.where(pd.notnull(df), None).to_dict(orient="records")


def get_eastmoney_valuation(code: str) -> Dict[str, Any]:
    """
    Fetch real-time valuation from Tiantian Jijin (Eastmoney) API.
    Returns: {name, jzrq, dwjz, gsz, gszzl, gztime}
    """
    url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={int(time.time()*1000)}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            text = response.text
            # Extract JSON from jsonpgz(...)
            match = re.search(r"jsonpgz\((.*)\);", text)
            if match:
                return json.loads(match.group(1))
    except Exception as e:
        print(f"Eastmoney API error for {code}: {e}")
    return {}


def search_funds(q: str) -> List[Dict[str, Any]]:
    """
    Search funds by keyword using local SQLite DB.
    Fast, cached, and doesn't kill the server.
    """
    if not q:
        return []

    q_clean = q.strip()
    # Simple SQL injection protection is handled by parameter substitution usually,
    # but for LIKE with wildcards we construct the pattern.
    pattern = f"%{q_clean}%"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT code, name, type 
            FROM funds 
            WHERE code LIKE ? OR name LIKE ? 
            LIMIT 20
        """, (pattern, pattern))
        
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": str(row["code"]),
                "name": row["name"],
                "type": row["type"] or "未知"
            })
        return results
    finally:
        conn.close()


# Global cache for stock spot data
_STOCK_SPOT_CACHE = {
    "data": {},
    "timestamp": 0
}

def _get_cached_stock_spot() -> Dict[str, float]:
    """
    Get stock spot data with simple in-memory caching.
    TTL: defined in Config (60s).
    """
    now = time.time()
    if now - _STOCK_SPOT_CACHE["timestamp"] < Config.STOCK_SPOT_CACHE_DURATION:
        return _STOCK_SPOT_CACHE["data"]
    
    try:
        # Still heavy, but limited to once per minute per server instance.
        # This is acceptable for a single-worker MVP.
        spot_df = ak.stock_zh_a_spot_em()
        spot_map = {str(r["代码"]): float(r["涨跌幅"]) for _, r in spot_df.iterrows() if "涨跌幅" in spot_df.columns}
        _STOCK_SPOT_CACHE["data"] = spot_map
        _STOCK_SPOT_CACHE["timestamp"] = now
        return spot_map
    except Exception as e:
        print(f"Failed to refresh stock spot cache: {e}")
        return _STOCK_SPOT_CACHE["data"] # Return old data if fetch fails


def get_fund_history(code: str, limit: int = 30) -> List[Dict[str, Any]]:
    """
    Get historical NAV data.
    """
    try:
        # ak.fund_open_fund_info_em returns historical data
        # Correct arg is 'symbol', not 'fund'
        df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        if df is None or df.empty:
            return []
            
        # Sort by date desc and take limit
        df = df.sort_values(by="净值日期", ascending=False).head(limit)
        # Sort back to asc for chart
        df = df.sort_values(by="净值日期", ascending=True)
        
        results = []
        for _, row in df.iterrows():
            results.append({
                "date": str(row["净值日期"]),
                "nav": float(row["单位净值"])
            })
        return results
    except Exception as e:
        print(f"History fetch error for {code}: {e}")
        return []


def get_fund_intraday(code: str) -> Dict[str, Any]:
    """
    Get fund holdings + real-time valuation estimate.
    Primary source: Eastmoney API.
    Enrichment: AkShare holdings.
    """
    # 1) Get real-time valuation from Eastmoney
    em_data = get_eastmoney_valuation(code)
    
    name = em_data.get("name")
    nav = float(em_data.get("dwjz", 0.0))
    estimate = float(em_data.get("gsz", 0.0))
    est_rate = float(em_data.get("gszzl", 0.0))
    update_time = em_data.get("gztime", time.strftime("%H:%M:%S"))

    # 2) Get holdings from AkShare for detail view
    holdings = []
    try:
        current_year = str(time.localtime().tm_year)
        # ak.fund_portfolio_hold_em returns dataframe
        # Correct arg is 'symbol', not 'code'
        holdings_df = ak.fund_portfolio_hold_em(symbol=code, date=current_year)
        if holdings_df is None or holdings_df.empty:
             prev_year = str(time.localtime().tm_year - 1)
             holdings_df = ak.fund_portfolio_hold_em(symbol=code, date=prev_year)
    except Exception as e:
        print(f"Holdings fetch error: {e}")
        holdings_df = pd.DataFrame()

    if not holdings_df.empty:
        # Clean up holdings data
        try:
            holdings_df = holdings_df.copy()
            # Ensure columns exist before operation
            if "占净值比例" in holdings_df.columns:
                holdings_df["占净值比例"] = (
                    holdings_df["占净值比例"].astype(str).str.replace("%", "", regex=False)
                )
                holdings_df["占净值比例"] = pd.to_numeric(holdings_df["占净值比例"], errors="coerce").fillna(0.0)
            else:
                 # Fallback if column missing (unlikely unless API changed)
                 holdings_df["占净值比例"] = 0.0

            # Get cached stock spot data
            spot_map = _get_cached_stock_spot()

            for _, row in holdings_df.iterrows():
                stock_code = str(row.get("股票代码"))
                holdings.append(
                    {
                        "name": row.get("股票名称"),
                        "percent": float(row.get("占净值比例", 0.0)),
                        "change": float(spot_map.get(stock_code, 0.0)),
                    }
                )
        except Exception as e:
            print(f"Holdings processing error: {e}")

    # 3) Fallback for name if Eastmoney failed
    if not name:
        try:
            fund_info_df = ak.fund_name_em()
            hit = fund_info_df[fund_info_df["基金代码"].astype(str) == str(code)]
            if not hit.empty:
                name = hit.iloc[0].get("基金简称")
        except:
            name = f"基金 {code}"

    # 4) Determine sector
    sector = "未知"
    for cat, keywords in MAJOR_CATEGORIES.items():
        if any(kw in name for kw in keywords):
            sector = cat
            break

    response = {
        "id": str(code),
        "name": name,
        "type": sector, # Use sector as type for frontend display
        "nav": nav,
        "estimate": estimate,
        "estRate": est_rate,
        "time": update_time,
        "holdings": holdings,
    }
    return response

