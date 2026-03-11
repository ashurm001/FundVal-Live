from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from ..services.crypto import (
    get_all_crypto_positions,
    upsert_crypto_position,
    remove_crypto_position,
    execute_crypto_trade,
    get_crypto_transactions,
    update_crypto_prices_cache,
    get_cached_prices
)

router = APIRouter()

class CryptoAccountModel(BaseModel):
    id: int
    name: str

class CryptoPositionModel(BaseModel):
    symbol: str
    name: str
    cost: float
    amount: float

class CryptoTradeModel(BaseModel):
    symbol: str
    op_type: str  # 'buy' or 'sell'
    amount: float
    price: float
    trade_time: Optional[str] = None  # ISO datetime

# Crypto accounts endpoints
@router.get("/accounts")
def get_crypto_accounts():
    """获取数字货币账户列表（返回默认账户）"""
    try:
        # 数字货币使用默认账户ID为1
        return {"accounts": [{"id": 1, "name": "数字货币账户"}]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Crypto positions endpoints
@router.get("/positions")
def get_crypto_positions(account_id: int = Query(1, description="账户ID")):
    """获取数字货币持仓列表"""
    try:
        result = get_all_crypto_positions(account_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/positions")
def create_crypto_position(
    account_id: int = Query(1, description="账户ID"),
    data: CryptoPositionModel = Body(...)
):
    """添加数字货币持仓"""
    try:
        success = upsert_crypto_position(
            account_id,
            data.symbol,
            data.name,
            data.cost,
            data.amount
        )
        if success:
            return {"status": "ok"}
        else:
            raise HTTPException(status_code=500, detail="添加持仓失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/positions/{symbol}")
def update_crypto_position(
    symbol: str,
    account_id: int = Query(1, description="账户ID"),
    data: CryptoPositionModel = Body(...)
):
    """更新数字货币持仓"""
    try:
        success = upsert_crypto_position(
            account_id,
            data.symbol,
            data.name,
            data.cost,
            data.amount
        )
        if success:
            return {"status": "ok"}
        else:
            raise HTTPException(status_code=500, detail="更新持仓失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/positions/{symbol}")
def delete_crypto_position(
    symbol: str,
    account_id: int = Query(1, description="账户ID")
):
    """删除数字货币持仓"""
    try:
        success = remove_crypto_position(account_id, symbol)
        if success:
            return {"status": "ok"}
        else:
            raise HTTPException(status_code=500, detail="删除持仓失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Crypto trade endpoints
@router.post("/buy")
def buy_crypto(
    account_id: int = Query(1, description="账户ID"),
    data: CryptoTradeModel = Body(...)
):
    """买入数字货币"""
    try:
        if data.op_type != "buy":
            raise HTTPException(status_code=400, detail="操作类型必须是 'buy'")
        
        success = execute_crypto_trade(
            account_id,
            data.symbol,
            data.op_type,
            data.amount,
            data.price,
            data.trade_time
        )
        if success:
            return {"status": "ok"}
        else:
            raise HTTPException(status_code=500, detail="买入失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sell")
def sell_crypto(
    account_id: int = Query(1, description="账户ID"),
    data: CryptoTradeModel = Body(...)
):
    """卖出数字货币"""
    try:
        if data.op_type != "sell":
            raise HTTPException(status_code=400, detail="操作类型必须是 'sell'")
        
        success = execute_crypto_trade(
            account_id,
            data.symbol,
            data.op_type,
            data.amount,
            data.price,
            data.trade_time
        )
        if success:
            return {"status": "ok"}
        else:
            raise HTTPException(status_code=500, detail="卖出失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Crypto transactions endpoints
@router.get("/transactions")
def get_transactions(
    account_id: int = Query(1, description="账户ID"),
    symbol: Optional[str] = Query(None, description="币种符号"),
    limit: int = Query(50, description="返回数量限制"),
    offset: int = Query(0, description="偏移量")
):
    """获取数字货币交易记录"""
    try:
        result = get_crypto_transactions(account_id, symbol, limit, offset)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Crypto prices endpoints
@router.get("/prices")
def get_prices(symbols: Optional[str] = Query(None, description="币种符号，多个用逗号分隔")):
    """获取数字货币价格"""
    try:
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(",")]
        else:
            symbol_list = None
        
        prices = get_cached_prices(symbol_list)
        return {"prices": prices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update_prices")
def update_prices(symbols: Optional[str] = Query(None, description="币种符号，多个用逗号分隔")):
    """更新数字货币价格"""
    try:
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(",")]
        else:
            symbol_list = None
        
        success = update_crypto_prices_cache(symbol_list)
        if success:
            return {"status": "ok"}
        else:
            raise HTTPException(status_code=500, detail="更新价格失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
