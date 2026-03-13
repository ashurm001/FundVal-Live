import json
import datetime
from typing import Dict, Any, Optional, List
from ..db import get_db_connection

def format_local_time(timestamp):
    """将时间戳转换为本地时间字符串"""
    if not timestamp:
        return None
    try:
        if isinstance(timestamp, str):
            # 处理SQLite返回的时间字符串格式
            if ' ' in timestamp:
                # SQLite返回的时间字符串，假设是UTC时间，转换为本地时间
                dt = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                dt = dt.replace(tzinfo=datetime.timezone.utc)
                local_dt = dt.astimezone()
                return local_dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                # ISO格式时间，转换为本地时间
                dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                local_dt = dt.astimezone()
                return local_dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            # datetime对象，转换为本地时间
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
            local_dt = timestamp.astimezone()
            return local_dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Error formatting time: {e}, timestamp: {timestamp}")
        return str(timestamp)

class MessageService:
    def get_messages(
        self, 
        msg_type: Optional[str] = None, 
        limit: int = 20, 
        offset: int = 0
    ) -> Dict[str, Any]:
        """获取消息列表"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 构建查询
            if msg_type:
                cursor.execute("""
                    SELECT COUNT(*) FROM messages WHERE msg_type = ?
                """, (msg_type,))
                total = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT id, msg_type, title, summary, score, risk_level, 
                           fund_count, total_value, read, created_at
                    FROM messages 
                    WHERE msg_type = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (msg_type, limit, offset))
            else:
                cursor.execute("SELECT COUNT(*) FROM messages")
                total = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT id, msg_type, title, summary, score, risk_level, 
                           fund_count, total_value, read, created_at
                    FROM messages 
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            rows = cursor.fetchall()
            
            messages = []
            for row in rows:
                messages.append({
                    "id": row["id"],
                    "msg_type": row["msg_type"],
                    "title": row["title"],
                    "summary": row["summary"],
                    "score": row["score"],
                    "risk_level": row["risk_level"],
                    "fund_count": row["fund_count"],
                    "total_value": row["total_value"],
                    "read": bool(row["read"]),
                    "created_at": format_local_time(row["created_at"])
                })
            
            return {
                "messages": messages,
                "total": total,
                "limit": limit,
                "offset": offset
            }
        finally:
            conn.close()
    
    def get_message(self, message_id: int) -> Dict[str, Any]:
        """获取单条消息详情"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, msg_type, title, content, summary, score, risk_level,
                       fund_count, total_value, read, created_at
                FROM messages
                WHERE id = ?
            """, (message_id,))
            
            row = cursor.fetchone()
            if not row:
                return {"error": "Message not found"}
            
            # 解析 content (JSON string)
            content = row["content"]
            if content:
                try:
                    content = json.loads(content)
                except:
                    pass
            
            return {
                "id": row["id"],
                "msg_type": row["msg_type"],
                "title": row["title"],
                "content": content,
                "summary": row["summary"],
                "score": row["score"],
                "risk_level": row["risk_level"],
                "fund_count": row["fund_count"],
                "total_value": row["total_value"],
                "read": bool(row["read"]),
                "created_at": format_local_time(row["created_at"])
            }
        finally:
            conn.close()
    
    def create_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新消息"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            msg_type = data.get("msg_type", "portfolio_analysis")
            title = data.get("title", "")
            content = data.get("content", {})
            summary = data.get("summary", "")
            score = data.get("score")
            risk_level = data.get("risk_level", "")
            fund_count = data.get("fund_count")
            total_value = data.get("total_value")
            
            # 将 content 转为 JSON 字符串
            if isinstance(content, dict):
                content = json.dumps(content, ensure_ascii=False, separators=(',', ':'))
            
            cursor.execute("""
                INSERT INTO messages 
                (msg_type, title, content, summary, score, risk_level, fund_count, total_value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (msg_type, title, content, summary, score, risk_level, fund_count, total_value))
            
            conn.commit()
            message_id = cursor.lastrowid
            
            return {
                "id": message_id,
                "msg_type": msg_type,
                "title": title,
                "success": True
            }
        except Exception as e:
            conn.rollback()
            return {"error": str(e), "success": False}
        finally:
            conn.close()
    
    def mark_as_read(self, message_id: int) -> Dict[str, Any]:
        """标记消息为已读"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE messages SET read = 1 WHERE id = ?
            """, (message_id,))
            conn.commit()
            
            return {"success": True}
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def mark_all_as_read(self, msg_type: Optional[str] = None) -> Dict[str, Any]:
        """标记所有消息为已读"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if msg_type:
                cursor.execute("""
                    UPDATE messages SET read = 1 WHERE msg_type = ? AND read = 0
                """, (msg_type,))
            else:
                cursor.execute("UPDATE messages SET read = 1 WHERE read = 0")
            
            conn.commit()
            updated = cursor.rowcount
            
            return {"success": True, "updated_count": updated}
        except Exception as e:
            conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            conn.close()
    
    def delete_message(self, message_id: int) -> bool:
        """删除消息"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
            conn.commit()
            return cursor.rowcount > 0
        except:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_unread_count(self, msg_type: Optional[str] = None) -> Dict[str, Any]:
        """获取未读消息数量"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if msg_type:
                cursor.execute("""
                    SELECT COUNT(*) FROM messages WHERE msg_type = ? AND read = 0
                """, (msg_type,))
            else:
                cursor.execute("SELECT COUNT(*) FROM messages WHERE read = 0")
            
            count = cursor.fetchone()[0]
            return {"count": count}
        finally:
            conn.close()

message_service = MessageService()
