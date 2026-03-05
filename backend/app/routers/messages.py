from fastapi import APIRouter, Body, Query
from typing import List, Dict, Any, Optional
from ..services.messages import message_service

router = APIRouter()

@router.get("/messages")
def get_messages(
    msg_type: Optional[str] = Query(None, description="消息类型筛选"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """获取消息列表"""
    return message_service.get_messages(msg_type, limit, offset)

@router.get("/messages/unread_count")
def get_unread_count(msg_type: Optional[str] = None):
    """获取未读消息数量"""
    return message_service.get_unread_count(msg_type)

@router.get("/messages/{message_id}")
def get_message(message_id: int):
    """获取单条消息详情"""
    return message_service.get_message(message_id)

@router.post("/messages")
def create_message(data: Dict[str, Any] = Body(...)):
    """创建新消息"""
    return message_service.create_message(data)

@router.put("/messages/{message_id}/read")
def mark_as_read(message_id: int):
    """标记消息为已读"""
    return message_service.mark_as_read(message_id)

@router.put("/messages/read_all")
def mark_all_as_read(msg_type: Optional[str] = Query(None)):
    """标记所有消息为已读"""
    return message_service.mark_all_as_read(msg_type)

@router.delete("/messages/{message_id}")
def delete_message(message_id: int):
    """删除消息"""
    success = message_service.delete_message(message_id)
    return {"success": success}
