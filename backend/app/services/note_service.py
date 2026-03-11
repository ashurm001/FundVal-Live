import datetime
from typing import List, Dict, Any

from ..db import get_db_connection


class NoteService:
    """用户笔记服务 - 管理基金相关的用户笔记"""

    def __init__(self):
        pass

    def get_user_notes(self, fund_code: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取指定基金的用户笔记列表

        Args:
            fund_code: 基金代码
            limit: 返回数量限制

        Returns:
            笔记列表
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, fund_code, fund_name, note_date, note_time, note_content, note_color
                FROM user_notes
                WHERE fund_code = ?
                ORDER BY note_date DESC, note_time DESC
                LIMIT ?
            """, (fund_code, limit))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Failed to get user notes: {e}")
            return []

    def save_user_note(self, fund_code: str, fund_name: str, note_content: str,
                       note_date: str = None, note_color: str = "#10b981") -> Dict[str, Any]:
        """
        保存用户笔记

        Args:
            fund_code: 基金代码
            fund_name: 基金名称
            note_content: 笔记内容
            note_date: 笔记日期，默认为今天
            note_color: 笔记颜色，默认为绿色

        Returns:
            保存的笔记信息
        """
        try:
            now = datetime.datetime.now()
            if not note_date:
                note_date = now.strftime("%Y-%m-%d")
            note_time = now.strftime("%H:%M:%S")

            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_notes (fund_code, fund_name, note_date, note_time, note_content, note_color)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (fund_code, fund_name, note_date, note_time, note_content, note_color))

                note_id = cursor.lastrowid
                conn.commit()
            finally:
                conn.close()

            return {
                "id": note_id,
                "fund_code": fund_code,
                "fund_name": fund_name,
                "note_date": note_date,
                "note_time": note_time,
                "note_content": note_content,
                "note_color": note_color
            }
        except Exception as e:
            print(f"Failed to save user note: {e}")
            return {"error": str(e)}

    def delete_user_note(self, note_id: int) -> bool:
        """
        删除用户笔记

        Args:
            note_id: 笔记ID

        Returns:
            是否删除成功
        """
        try:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM user_notes WHERE id = ?", (note_id,))
                conn.commit()
            finally:
                conn.close()
            return True
        except Exception as e:
            print(f"Failed to delete user note: {e}")
            return False

    def update_user_note(self, note_id: int, note_content: str,
                         note_color: str = None) -> Dict[str, Any]:
        """
        更新用户笔记

        Args:
            note_id: 笔记ID
            note_content: 笔记内容
            note_color: 笔记颜色，如果不传则保持原颜色

        Returns:
            更新后的笔记信息
        """
        try:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()

                # 获取当前笔记以保留其他字段
                cursor.execute("SELECT * FROM user_notes WHERE id = ?", (note_id,))
                row = cursor.fetchone()
                if not row:
                    return {"error": "Note not found"}

                # 更新 note_content 和 note_color（如果提供）
                if note_color:
                    cursor.execute("""
                        UPDATE user_notes
                        SET note_content = ?, note_color = ?
                        WHERE id = ?
                    """, (note_content, note_color, note_id))
                else:
                    cursor.execute("""
                        UPDATE user_notes
                        SET note_content = ?
                        WHERE id = ?
                    """, (note_content, note_id))

                conn.commit()

                # 获取更新后的笔记
                cursor.execute("""
                    SELECT id, fund_code, fund_name, note_date, note_time, note_content, note_color
                    FROM user_notes
                    WHERE id = ?
                """, (note_id,))
                updated_row = cursor.fetchone()
            finally:
                conn.close()

            return dict(updated_row) if updated_row else {"error": "Failed to fetch updated note"}
        except Exception as e:
            print(f"Failed to update user note: {e}")
            return {"error": str(e)}


# 创建全局实例
note_service = NoteService()
