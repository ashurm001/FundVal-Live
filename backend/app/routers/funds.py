from fastapi import APIRouter, HTTPException, Query, Body
from ..services.fund import search_funds, get_fund_intraday, get_fund_history
from ..config import Config

router = APIRouter()

@router.get("/search")
def search(q: str = Query(..., min_length=1)):
    try:
        return search_funds(q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fund/{fund_id}")
def fund_detail(fund_id: str):
    try:
        return get_fund_intraday(fund_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fund/{fund_id}/history")
def fund_history(fund_id: str, limit: int = 30):
    """
    Get historical NAV data for charts.
    """
    try:
        return get_fund_history(fund_id, limit=limit)
    except Exception as e:
        # Don't break UI if history fails
        print(f"History error: {e}")
        return []

@router.post("/fund/{fund_id}/subscribe")
def subscribe_fund(fund_id: str, data: dict = Body(...)):
    """
    Subscribe to fund alerts.
    """
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
        
    # TODO: Implement real persistence logic (SQLite)
    # For MVP, we just log it.
    print(f"Subscribe request: {email} -> {fund_id}, thresholds: {data.get('thresholdUp')}/{data.get('thresholdDown')}")
    
    return {"status": "ok", "message": "Subscription active (Simulation)"}
