from typing import List, Dict, Any
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

from ..db import get_db_connection
from .fund import get_combined_valuation, get_fund_type

logger = logging.getLogger(__name__)

def get_all_positions(account_id: int = 1) -> Dict[str, Any]:
    """
    Fetch all positions for a specific account, get real-time valuations in parallel,
    and compute portfolio statistics.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM positions WHERE account_id = ?", (account_id,))
    rows = cursor.fetchall()
    conn.close()

    positions = []
    total_market_value = 0.0
    total_actual_market_value = 0.0
    total_cost = 0.0
    total_day_income = 0.0

    position_map = {row["code"]: row for row in rows}
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_code = {
            executor.submit(get_combined_valuation, code): code 
            for code in position_map.keys()
        }
        
        for future in as_completed(future_to_code):
            code = future_to_code[future]
            row = position_map[code]
            
            try:
                data = future.result(timeout=3) or {}
                name = data.get("name")
                fund_type = None

                # If name is missing, fetch from database
                if not name:
                    conn_temp = get_db_connection()
                    cursor_temp = conn_temp.cursor()
                    cursor_temp.execute("SELECT name, type FROM funds WHERE code = ?", (code,))
                    db_row = cursor_temp.fetchone()
                    conn_temp.close()
                    if db_row:
                        name = db_row["name"]
                        fund_type = db_row["type"]
                    else:
                        name = code

                # Get fund type (use cached value or call get_fund_type)
                if not fund_type:
                    fund_type = get_fund_type(code, name)

                nav = float(data.get("nav", 0.0))
                published_nav = float(data.get("published_nav", 0.0))
                estimate = float(data.get("estimate", 0.0))
                
                # Check if today's NAV is available
                # nav_updated_today is True if published_nav > 0 (today's published NAV is available)
                nav_updated_today = published_nav > 0
                
                # Use published_nav as latest_nav if available (today's published NAV)
                # Otherwise fall back to latest_nav from fund_history (yesterday's NAV)
                latest_nav = published_nav if published_nav > 0 else float(data.get("latest_nav", 0.0))
                
                # If estimate is 0 (e.g. market closed or error), use NAV
                current_price = estimate if estimate > 0 else (published_nav if published_nav > 0 else nav)
                
                # Calculations
                cost = float(row["cost"])
                shares = float(row["shares"])
                
                # 1. Base Metrics
                nav_market_value = nav * shares
                published_nav_market_value = published_nav * shares
                cost_basis = cost * shares
                
                # 2. Estimate & Reliability Check
                # est_rate is percent, e.g. 1.5 for +1.5%
                est_rate = data.get("est_rate", data.get("estRate", 0.0))
                
                # Validation: If estRate is absurdly high for a fund (abs > 10%), ignore estimate unless confirmed valid
                is_est_valid = False
                if estimate > 0 and nav > 0:
                    if abs(est_rate) < 10.0 or "ETF" in name or "联接" in name: 
                        # Allow higher volatility for ETFs, but 10% is still a good sanity check for generic funds.
                        # Actually, let's stick to the 10% clamp for safety, or trust the user knows.
                        # Linus: "Trust, but verify." We'll flag it but calculate it.
                        is_est_valid = True
                    else:
                        is_est_valid = False
                
                # 3. Derived Metrics
                
                # A. Confirmed (Based on Yesterday's NAV)
                accumulated_income = nav_market_value - cost_basis
                accumulated_return_rate = (accumulated_income / cost_basis * 100) if cost_basis > 0 else 0.0
                
                # B. Intraday (Based on Real-time Estimate)
                if is_est_valid:
                    day_income = (estimate - nav) * shares
                    est_market_value = estimate * shares
                else:
                    day_income = 0.0
                    est_market_value = nav_market_value # Fallback to confirmed value
                
                # Calculate day income from published NAV (actual daily change)
                # If published_nav is available (today's NAV), use it
                # Otherwise, fall back to 0 (no actual change yet)
                if published_nav > 0:
                    day_income_from_nav = (published_nav - nav) * shares
                else:
                    day_income_from_nav = 0.0
                
                # Calculate actual market value based on latest_nav (published_nav if available, else yesterday's nav)
                actual_market_value = latest_nav * shares if latest_nav > 0 else nav_market_value
                
                # C. Total Income (Based on latest NAV)
                # latest_nav is now published_nav (today's NAV) if available
                total_income = (latest_nav - cost) * shares if latest_nav > 0 else (nav - cost) * shares
                total_return_rate = (total_income / cost_basis * 100) if cost_basis > 0 else 0.0
                
                positions.append({
                    "code": code,
                    "name": name,
                    "type": fund_type,
                    "cost": cost,
                    "shares": shares,
                    "nav": nav,
                    "latest_nav": latest_nav,
                    "nav_date": data.get("navDate", "--"), # If available, else implicit
                    "nav_updated_today": nav_updated_today,
                    "estimate": estimate,
                    "est_rate": est_rate,
                    "is_est_valid": is_est_valid,
                    
                    # Values
                    "cost_basis": round(cost_basis, 2),
                    "nav_market_value": round(nav_market_value, 2),
                    "est_market_value": round(est_market_value, 2),
                    "actual_market_value": round(actual_market_value, 2),  # 基于实际净值的市值
                    
                    # PnL
                    "accumulated_income": round(accumulated_income, 2),
                    "accumulated_return_rate": round(accumulated_return_rate, 2),
                    
                    "day_income": round(day_income, 2),
                    "day_income_from_nav": round(day_income_from_nav, 2),
                    
                    "total_income": round(total_income, 2),
                    "total_return_rate": round(total_return_rate, 2),
                    
                    "update_time": data.get("time", "--")
                })
                
                total_market_value += est_market_value
                total_actual_market_value += actual_market_value
                total_day_income += day_income
                total_cost += cost_basis
                # accumulated income sum not strictly needed for top card but good to have?
                # Let's keep total_income as the projected total.

            except TimeoutError:
                logger.warning(f"Timeout fetching valuation for {code}")
                positions.append({
                    "code": code,
                    "name": "Timeout",
                    "cost": float(row["cost"]),
                    "shares": float(row["shares"]),
                    "nav": 0.0,
                    "estimate": 0.0,
                    "est_market_value": 0.0,
                    "day_income": 0.0,
                    "total_income": 0.0,
                    "total_return_rate": 0.0,
                    "accumulated_income": 0.0,
                    "est_rate": 0.0,
                    "is_est_valid": False,
                    "update_time": "--"
                })
            except Exception as e:
                logger.error(f"Error processing position {code}: {e}")
                positions.append({
                    "code": code,
                    "name": "Error",
                    "cost": float(row["cost"]),
                    "shares": float(row["shares"]),
                    "nav": 0.0,
                    "estimate": 0.0,
                    "est_market_value": 0.0,
                    "day_income": 0.0,
                    "total_income": 0.0,
                    "total_return_rate": 0.0,
                    "accumulated_income": 0.0,
                    "est_rate": 0.0,
                    "is_est_valid": False,
                    "update_time": "--"
                })

    total_income = total_actual_market_value - total_cost
    total_return_rate = (total_income / total_cost * 100) if total_cost > 0 else 0.0

    return {
        "summary": {
            "total_market_value": round(total_actual_market_value, 2), # 实际总资产（基于实际净值）
            "total_cost": round(total_cost, 2),
            "total_day_income": round(total_day_income, 2),
            "total_income": round(total_income, 2),
            "total_return_rate": round(total_return_rate, 2)
        },
        "positions": sorted(positions, key=lambda x: x["actual_market_value"], reverse=True)
    }

def upsert_position(account_id: int, code: str, cost: float, shares: float):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO positions (account_id, code, cost, shares)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(account_id, code) DO UPDATE SET
            cost = excluded.cost,
            shares = excluded.shares,
            updated_at = CURRENT_TIMESTAMP
    """, (account_id, code, cost, shares))
    conn.commit()
    conn.close()

def remove_position(account_id: int, code: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM positions WHERE account_id = ? AND code = ?", (account_id, code))
    conn.commit()
    conn.close()
