from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from ..services.account import get_all_positions, upsert_position, remove_position
from ..services.trade import add_position_trade, reduce_position_trade, list_transactions
from ..db import get_db_connection

router = APIRouter()

class AccountModel(BaseModel):
    name: str
    description: Optional[str] = ""

class PositionModel(BaseModel):
    code: str
    cost: float
    shares: float


class AddTradeModel(BaseModel):
    amount: float
    trade_time: Optional[str] = None  # ISO datetime, e.g. 2025-02-05T14:30:00


class ReduceTradeModel(BaseModel):
    shares: float
    trade_time: Optional[str] = None

# Account management endpoints
@router.get("/accounts")
def list_accounts():
    """获取所有账户"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accounts ORDER BY id")
        accounts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {"accounts": accounts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/accounts")
def create_account(data: AccountModel):
    """创建新账户"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO accounts (name, description) VALUES (?, ?)",
            (data.name, data.description)
        )
        account_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {"id": account_id, "name": data.name}
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=400, detail="账户名称已存在")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/accounts/{account_id}")
def update_account(account_id: int, data: AccountModel):
    """更新账户信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE accounts SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (data.name, data.description, account_id)
        )
        conn.commit()
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=400, detail="账户名称已存在")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/accounts/{account_id}")
def delete_account(account_id: int):
    """删除账户（需检查是否有持仓）"""
    if account_id == 1:
        raise HTTPException(status_code=400, detail="默认账户不可删除")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查是否有持仓
        cursor.execute("SELECT COUNT(*) as cnt FROM positions WHERE account_id = ?", (account_id,))
        count = cursor.fetchone()["cnt"]

        if count > 0:
            conn.close()
            raise HTTPException(status_code=400, detail="账户下有持仓，无法删除")

        cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        conn.commit()
        conn.close()

        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Position endpoints (with account_id parameter)
@router.get("/account/positions")
def get_positions(account_id: int = Query(1)):
    """获取指定账户的持仓"""
    try:
        return get_all_positions(account_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/account/positions/update-nav")
def update_positions_nav(account_id: int = Query(1)):
    """
    手动更新持仓基金的净值。
    首先触发缓存刷新，然后优先从缓存获取最新净值。
    静默更新，不返回详细消息。
    """
    from datetime import datetime
    from ..services.scheduler import update_nav_estimation_cache

    try:
        # Step 1: Trigger cache refresh first
        update_nav_estimation_cache()
        
        # Step 2: Get all holdings for this account
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT code FROM positions WHERE account_id = ? AND shares > 0", (account_id,))
        codes = [row["code"] for row in cursor.fetchall()]
        conn.close()

        if not codes:
            return {"ok": True, "message": "无持仓基金", "total": 0}

        # Get today's date
        today = datetime.now().strftime("%Y-%m-%d")

        # Update NAV for each fund
        updated = 0  # 当日净值已更新
        pending = 0  # 当日净值未公布

        for code in codes:
            try:
                # Get from cache
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT published_nav
                    FROM fund_nav_estimation
                    WHERE code = ? AND date = ?
                """, (code, today))
                cache_row = cursor.fetchone()
                conn.close()

                if cache_row and cache_row["published_nav"] is not None:
                    updated += 1
                else:
                    pending += 1
            except Exception as e:
                print(f"Error updating NAV for {code}: {e}")

        return {
            "ok": True,
            "message": f"已更新 {updated} 个，待公布 {pending} 个",
            "updated": updated,
            "pending": pending,
            "total": len(codes)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/account/positions")
def update_position(data: PositionModel, account_id: int = Query(1)):
    """更新持仓（指定账户）"""
    try:
        upsert_position(account_id, data.code, data.cost, data.shares)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/account/positions/{code}")
def delete_position(code: str, account_id: int = Query(1)):
    """删除持仓（指定账户）"""
    try:
        remove_position(account_id, code)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/account/positions/{code}/add")
def add_trade(code: str, data: AddTradeModel, account_id: int = Query(1)):
    """加仓（指定账户）"""
    from datetime import datetime
    trade_ts = None
    if data.trade_time:
        try:
            trade_ts = datetime.fromisoformat(data.trade_time.replace("Z", "+00:00"))
            if trade_ts.tzinfo:
                trade_ts = trade_ts.replace(tzinfo=None)
        except Exception:
            pass
    try:
        result = add_position_trade(account_id, code, data.amount, trade_ts)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "加仓失败"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/account/positions/{code}/reduce")
def reduce_trade(code: str, data: ReduceTradeModel, account_id: int = Query(1)):
    """减仓（指定账户）"""
    from datetime import datetime
    trade_ts = None
    if data.trade_time:
        try:
            trade_ts = datetime.fromisoformat(data.trade_time.replace("Z", "+00:00"))
            if trade_ts.tzinfo:
                trade_ts = trade_ts.replace(tzinfo=None)
        except Exception:
            pass
    try:
        result = reduce_position_trade(account_id, code, data.shares, trade_ts)
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("message", "减仓失败"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/account/transactions")
def get_transactions(account_id: int = Query(1), code: Optional[str] = Query(None), limit: int = Query(100, le=500)):
    """获取交易记录（指定账户）"""
    try:
        return {"transactions": list_transactions(account_id, code, limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
