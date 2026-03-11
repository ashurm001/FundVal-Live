from fastapi import APIRouter, HTTPException
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import asyncio

from ..services.ai_simulation import ai_simulation_service

router = APIRouter(prefix="/ai-simulation", tags=["ai_simulation"])


class CreateAIAccountRequest(BaseModel):
    source_account_id: int
    name: Optional[str] = "AI模拟账户"
    description: Optional[str] = ""
    review_day_of_week: Optional[int] = 0
    source_type: Optional[str] = "fund"  # 'fund' 或 'crypto'
    review_interval_type: Optional[str] = "week"  # 'day', 'week', 'month', 'hour'
    review_interval: Optional[int] = 1


class AIAccountResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    source_account_id: int
    source_account_name: str
    initial_capital: float
    current_value: float
    total_return_rate: float
    is_active: bool
    review_day_of_week: int
    last_review_date: Optional[str]
    created_at: str
    updated_at: str


@router.post("/accounts", response_model=Dict[str, Any])
async def create_ai_account(request: CreateAIAccountRequest):
    """创建AI模拟账户"""
    result = ai_simulation_service.create_ai_account(
        source_account_id=request.source_account_id,
        name=request.name,
        description=request.description,
        review_day_of_week=request.review_day_of_week,
        source_type=request.source_type,
        review_interval_type=request.review_interval_type,
        review_interval=request.review_interval
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "创建失败"))

    return result


@router.get("/accounts", response_model=List[Dict[str, Any]])
async def get_ai_accounts(source_account_id: Optional[int] = None):
    """获取AI模拟账户列表"""
    accounts = ai_simulation_service.get_ai_accounts(source_account_id)
    return accounts


@router.get("/accounts/{ai_account_id}", response_model=Dict[str, Any])
async def get_ai_account_detail(
    ai_account_id: int,
    include_positions: bool = True,
    include_trades: bool = True,
    include_history: bool = True,
    trades_limit: int = 20,
    history_days: int = 90
):
    """获取AI模拟账户详情
    
    Args:
        ai_account_id: AI账户ID
        include_positions: 是否包含持仓数据（默认true）
        include_trades: 是否包含交易记录（默认true）
        include_history: 是否包含历史走势（默认true）
        trades_limit: 交易记录数量限制（默认20）
        history_days: 历史数据天数限制（默认90）
    """
    account = ai_simulation_service.get_ai_account_detail(
        ai_account_id,
        include_positions=include_positions,
        include_trades=include_trades,
        include_history=include_history,
        trades_limit=trades_limit,
        history_days=history_days
    )

    if "error" in account:
        raise HTTPException(status_code=404, detail=account["error"])

    return account


@router.post("/accounts/{ai_account_id}/review", response_model=Dict[str, Any])
async def perform_weekly_review(ai_account_id: int):
    """执行每周审视和调仓"""
    result = await ai_simulation_service.perform_weekly_review(ai_account_id)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.put("/accounts/{ai_account_id}", response_model=Dict[str, Any])
async def update_ai_account(ai_account_id: int, data: Dict[str, Any]):
    """更新AI模拟账户信息"""
    result = ai_simulation_service.update_ai_account(ai_account_id, **data)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/accounts/{ai_account_id}/update-prices", response_model=Dict[str, Any])
async def update_ai_account_prices(ai_account_id: int):
    """手动更新AI账户持仓价格和收益"""
    try:
        ai_simulation_service.update_ai_positions_prices(ai_account_id)
        return {"success": True, "message": "价格和收益已更新"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"更新失败: {str(e)}")


@router.delete("/accounts/{ai_account_id}", response_model=Dict[str, Any])
async def delete_ai_account(ai_account_id: int):
    """删除AI模拟账户"""
    result = ai_simulation_service.delete_ai_account(ai_account_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "删除失败"))

    return result


@router.get("/accounts/{ai_account_id}/comparison", response_model=Dict[str, Any])
async def get_account_comparison(ai_account_id: int):
    """获取AI账户与源账户的对比数据"""
    account = ai_simulation_service.get_ai_account_detail(ai_account_id)

    if "error" in account:
        raise HTTPException(status_code=404, detail=account["error"])

    return {
        "ai_account": {
            "id": account["id"],
            "name": account["name"],
            "initial_capital": account["initial_capital"],
            "current_value": account["current_value"],
            "total_return_rate": account["total_return_rate"]
        },
        "value_history": account.get("value_history", []),
        "trades": account.get("trades", []),
        "positions": account.get("positions", [])
    }
