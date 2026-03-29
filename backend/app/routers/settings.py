import logging
import re
import time
from fastapi import APIRouter, HTTPException, Body
from ..db import get_db_connection
from ..crypto import encrypt_value, decrypt_value
from ..config import Config

logger = logging.getLogger(__name__)
router = APIRouter()

ENCRYPTED_FIELDS = {"OPENAI_API_KEY", "SMTP_PASSWORD"}

def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_url(url: str) -> bool:
    pattern = r'^https?://[^\s]+$'
    return re.match(pattern, url) is not None

def validate_port(port: str) -> bool:
    try:
        p = int(port)
        return 1 <= p <= 65535
    except:
        return False

@router.get("/settings")
def get_settings():
    """获取所有设置（加密字段用 *** 掩码）"""
    start_time = time.time()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value, encrypted FROM settings")
        rows = cursor.fetchall()
        conn.close()

        settings = {}
        for row in rows:
            key = row["key"]
            value = row["value"]
            encrypted = row["encrypted"]

            if encrypted and value:
                settings[key] = "***"
            else:
                settings[key] = value

        if not settings:
            settings = {
                "OPENAI_API_KEY": "***" if Config.OPENAI_API_KEY else "",
                "OPENAI_API_BASE": Config.OPENAI_API_BASE,
                "AI_MODEL_NAME": Config.AI_MODEL_NAME,
                "SMTP_HOST": Config.SMTP_HOST,
                "SMTP_PORT": str(Config.SMTP_PORT),
                "SMTP_USER": Config.SMTP_USER,
                "SMTP_PASSWORD": "***" if Config.SMTP_PASSWORD else "",
                "EMAIL_FROM": Config.EMAIL_FROM,
                "NOTIFICATION_EMAIL": "",
                "INTRADAY_COLLECT_INTERVAL": "5",
            }

        elapsed = time.time() - start_time
        logger.debug(f"Settings loaded in {elapsed:.3f}s")
        return {"settings": settings}
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/settings")
def update_settings(data: dict = Body(...)):
    """更新设置（部分更新，验证输入）"""
    try:
        settings = data.get("settings", {})
        errors = {}

        # 验证输入
        if "SMTP_PORT" in settings:
            if not validate_port(settings["SMTP_PORT"]):
                errors["SMTP_PORT"] = "端口必须在 1-65535 之间"

        if "SMTP_USER" in settings and settings["SMTP_USER"]:
            if not validate_email(settings["SMTP_USER"]):
                errors["SMTP_USER"] = "邮箱格式不正确"

        if "EMAIL_FROM" in settings and settings["EMAIL_FROM"]:
            if not validate_email(settings["EMAIL_FROM"]):
                errors["EMAIL_FROM"] = "邮箱格式不正确"

        if "OPENAI_API_BASE" in settings and settings["OPENAI_API_BASE"]:
            if not validate_url(settings["OPENAI_API_BASE"]):
                errors["OPENAI_API_BASE"] = "URL 格式不正确"

        if errors:
            raise HTTPException(status_code=400, detail={"errors": errors})

        # 保存到数据库
        conn = get_db_connection()
        cursor = conn.cursor()

        for key, value in settings.items():
            # 跳过掩码值（用户没有修改）
            if value == "***":
                continue

            # 判断是否需要加密
            encrypted = 1 if key in ENCRYPTED_FIELDS else 0
            if encrypted and value:
                value = encrypt_value(value)

            # Upsert
            cursor.execute("""
                INSERT INTO settings (key, value, encrypted, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    encrypted = excluded.encrypted,
                    updated_at = CURRENT_TIMESTAMP
            """, (key, value, encrypted))

        conn.commit()
        conn.close()

        # 重新加载配置
        Config.reload()

        return {"message": "设置已保存"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-email")
def test_email():
    """测试邮件发送功能"""
    from ..services.email import send_email
    
    logger.info("开始测试邮件发送...")
    logger.info(f"SMTP_HOST: {Config.SMTP_HOST}")
    logger.info(f"SMTP_PORT: {Config.SMTP_PORT}")
    logger.info(f"SMTP_USER: {Config.SMTP_USER}")
    logger.info(f"EMAIL_FROM: {Config.EMAIL_FROM}")
    logger.info(f"NOTIFICATION_EMAIL: {Config.NOTIFICATION_EMAIL}")
    
    if not Config.SMTP_HOST or not Config.SMTP_USER:
        logger.error("SMTP未配置")
        raise HTTPException(status_code=400, detail="SMTP未配置，请先设置SMTP服务器和用户")
    
    if not Config.NOTIFICATION_EMAIL:
        logger.error("通知邮箱未配置")
        raise HTTPException(status_code=400, detail="通知邮箱未配置，请先设置通知接收邮箱")
    
    subject = "【FundVal】邮件测试"
    content = """
    <h3>邮件测试成功</h3>
    <p>这是一封测试邮件，如果您收到此邮件，说明邮件配置正确。</p>
    <hr/>
    <p>FundVal Live</p>
    """
    
    try:
        success = send_email(Config.NOTIFICATION_EMAIL, subject, content, is_html=True)
        
        if success:
            logger.info(f"测试邮件发送成功到 {Config.NOTIFICATION_EMAIL}")
            return {"success": True, "message": f"测试邮件已发送到 {Config.NOTIFICATION_EMAIL}"}
        else:
            logger.error("邮件发送函数返回False")
            raise HTTPException(status_code=500, detail="邮件发送失败，请检查SMTP配置")
    except Exception as e:
        logger.error(f"邮件发送异常: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"邮件发送失败: {str(e)}")
