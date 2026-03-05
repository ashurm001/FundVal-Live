from fastapi import APIRouter, Body, Query
from typing import List, Dict, Any
from ..services.ai import ai_service

router = APIRouter()

@router.post("/ai/analyze_fund")
async def analyze_fund(fund_info: Dict[str, Any] = Body(...)):
    return await ai_service.analyze_fund(fund_info)

@router.get("/ai/analysis_history/{fund_code}")
def get_analysis_history(fund_code: str, limit: int = Query(10, ge=1, le=100)):
    """获取基金的AI分析历史记录"""
    return ai_service.get_analysis_history(fund_code, limit)

@router.get("/ai/user_notes/{fund_code}")
def get_user_notes(fund_code: str, limit: int = Query(10, ge=1, le=100)):
    """获取基金的用户笔记"""
    return ai_service.get_user_notes(fund_code, limit)

@router.post("/ai/user_note")
def save_user_note(data: Dict[str, Any] = Body(...)):
    """保存用户笔记"""
    fund_code = data.get("fund_code")
    fund_name = data.get("fund_name", "")
    note_content = data.get("note_content")
    note_date = data.get("note_date")
    note_color = data.get("note_color", "#10b981")
    
    if not fund_code or not note_content:
        return {"error": "fund_code and note_content are required"}
    
    return ai_service.save_user_note(fund_code, fund_name, note_content, note_date, note_color)

@router.delete("/ai/user_note/{note_id}")
def delete_user_note(note_id: int):
    """删除用户笔记"""
    success = ai_service.delete_user_note(note_id)
    return {"success": success}

@router.put("/ai/user_note/{note_id}")
def update_user_note(note_id: int, data: Dict[str, Any] = Body(...)):
    """更新用户笔记"""
    note_content = data.get("note_content")
    note_color = data.get("note_color")
    
    if not note_content:
        return {"error": "note_content is required"}
    
    result = ai_service.update_user_note(note_id, note_content, note_color)
    return result

@router.post("/ai/analyze_portfolio")
async def analyze_portfolio(data: Dict[str, Any] = Body(...)):
    """分析持仓组合"""
    positions = data.get("positions", [])
    summary = data.get("summary", {})
    
    if not positions:
        return {"error": "positions is required"}
    
    return await ai_service.analyze_portfolio(positions, summary)

