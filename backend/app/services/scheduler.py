import logging
import threading
import time
from datetime import datetime, timedelta, timezone
import akshare as ak
import pandas as pd
from ..db import get_db_connection
from ..config import Config
from ..services.fund import get_combined_valuation
from ..services.subscription import get_active_subscriptions, update_notification_time
from ..services.email import send_email
from ..services.trade import process_pending_transactions

logger = logging.getLogger(__name__)

# Define China Standard Time (UTC+8)
CST = timezone(timedelta(hours=8))

def fetch_and_update_funds():
    """
    Fetches the complete fund list from AkShare and updates the SQLite DB.
    This is a blocking operation, should be run in a background thread.
    """
    logger.info("Starting fund list update...")
    try:
        # Fetch data
        df = ak.fund_name_em()
        if df is None or df.empty:
            logger.warning("Fetched empty fund list from AkShare.")
            return

        # Rename columns to match our simple schema
        # Expected cols: "基金代码", "基金简称", "基金类型"
        df = df.rename(columns={
            "基金代码": "code",
            "基金简称": "name",
            "基金类型": "type"
        })
        
        # Select only relevant columns
        data_to_insert = df[["code", "name", "type"]].to_dict(orient="records")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Use transaction for speed and safety
        conn.execute("BEGIN")
        
        # Upsert logic (Replace is easier here since we just want the latest list)
        # Using executemany is much faster than looping
        cursor.executemany("""
            INSERT OR REPLACE INTO funds (code, name, type, updated_at)
            VALUES (:code, :name, :type, CURRENT_TIMESTAMP)
        """, data_to_insert)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Fund list updated. Total funds: {len(data_to_insert)}")
        
    except Exception as e:
        logger.error(f"Failed to update fund list: {e}")

from ..services.subscription import get_active_subscriptions, update_notification_time, update_digest_time
from ..services.trading_calendar import is_trading_day

def collect_intraday_snapshots():
    """
    Collect intraday valuation snapshots for holdings (every N minutes during trading hours).
    Only runs on trading days between 09:35-15:05.
    Interval is configurable via INTRADAY_COLLECT_INTERVAL setting.
    """
    now_cst = datetime.now(CST)
    today = now_cst.date()

    # 1. Check if trading day
    if not is_trading_day(today):
        return

    # 2. Check if within collection window (09:35-15:05)
    current_time = now_cst.strftime("%H:%M")
    if current_time < "09:35" or current_time > "15:05":
        return

    # 3. Get holdings (only funds with shares > 0)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT code FROM positions WHERE shares > 0")
    codes = [row["code"] for row in cursor.fetchall()]

    if not codes:
        conn.close()
        return

    # 4. Collect valuation data
    date_str = today.strftime("%Y-%m-%d")
    time_str = now_cst.strftime("%H:%M")

    collected = 0
    for code in codes:
        try:
            data = get_combined_valuation(code)
            if data and data.get("estimate"):
                cursor.execute("""
                    INSERT OR IGNORE INTO fund_intraday_snapshots
                    (fund_code, date, time, estimate)
                    VALUES (?, ?, ?, ?)
                """, (code, date_str, time_str, float(data["estimate"])))
                collected += 1
            time.sleep(0.2)  # Avoid API rate limiting (reduced from 0.5s)
        except Exception as e:
            logger.error(f"Intraday collect failed for {code}: {e}")

    conn.commit()
    conn.close()

    if collected > 0:
        logger.info(f"Collected {collected} intraday snapshots at {time_str}")

def cleanup_old_intraday_data():
    """
    Clean up intraday snapshots older than 30 days.
    Runs once per day at 00:00.
    """
    now_cst = datetime.now(CST)
    cutoff = (now_cst - timedelta(days=30)).strftime("%Y-%m-%d")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fund_intraday_snapshots WHERE date < ?", (cutoff,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted > 0:
        logger.info(f"Cleaned up {deleted} old intraday records (before {cutoff})")

def update_holdings_nav():
    """
    Update NAV (net asset value) for all holdings.
    Fetches latest NAV from AkShare and updates fund_history table.
    Runs between 16:00-24:00 on trading days.
    Only counts as success if today's NAV is available.
    """
    from .fund import get_fund_history
    from .trading_calendar import is_trading_day

    now_cst = datetime.now(CST)
    today = now_cst.date()
    today_str = today.strftime("%Y-%m-%d")

    # Only run on trading days
    if not is_trading_day(today):
        return

    # Only run between 16:00-24:00
    current_hour = now_cst.hour
    if current_hour < 16:
        return

    # Get all holdings
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT code FROM positions WHERE shares > 0")
    codes = [row["code"] for row in cursor.fetchall()]
    conn.close()

    if not codes:
        return

    # Update NAV for each fund
    updated = 0  # Today's NAV available
    pending = 0  # Today's NAV not yet published

    for code in codes:
        try:
            # Fetch latest 5 days history
            history = get_fund_history(code, limit=5)
            if history:
                # Check if latest NAV is today's
                latest_date = history[-1]["date"]
                if latest_date == today_str:
                    updated += 1
                else:
                    pending += 1
            time.sleep(0.3)  # Avoid API rate limiting
        except Exception as e:
            logger.error(f"Failed to update NAV for {code}: {e}")

    if updated > 0 or pending > 0:
        logger.info(f"NAV update: {updated} updated, {pending} pending (total {len(codes)})")

def check_all_navs_published():
    """
    Check if all holdings' NAVs have been published for today.
    Returns True if all funds have published_nav > 0 in today's cache.
    """
    from datetime import datetime
    
    now_cst = datetime.now(CST)
    today_str = now_cst.strftime("%Y-%m-%d")
    
    # Get all holdings
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT code FROM positions WHERE shares > 0")
    codes = [row["code"] for row in cursor.fetchall()]
    conn.close()
    
    if not codes:
        return True
    
    # Check if all funds have published_nav in today's cache
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Count funds with published_nav > 0
    placeholders = ','.join(['?' for _ in codes])
    cursor.execute(f"""
        SELECT COUNT(*) as cnt
        FROM fund_nav_estimation
        WHERE code IN ({placeholders})
        AND date = ?
        AND published_nav IS NOT NULL
        AND published_nav > 0
    """, codes + [today_str])
    
    published_count = cursor.fetchone()["cnt"]
    conn.close()
    
    # All funds have published NAV
    return published_count == len(codes)

def update_nav_estimation_cache():
    """
    Update NAV estimation cache from fund_value_estimation_em API.
    Fetches all funds' real-time NAV estimation and published NAV.
    
    Refresh strategy:
    - 09:00-18:30: no refresh (trading hours and waiting for NAV publication)
    - 18:30-24:00: every 10 minutes for published NAV data, STOP when all NAVs published
    - 00:00-09:00: no refresh (minimal refresh)
    
    This reduces API calls significantly while ensuring data freshness when needed.
    Note: get_combined_valuation has no call rate limit - only cache update is limited.
    """
    now_cst = datetime.now(CST)
    today = now_cst.date()
    today_str = today.strftime("%Y-%m-%d")
    current_hour = now_cst.hour

    # Check if trading day
    if not is_trading_day(today):
        return

    # Fetch all fund types' estimation data
    fund_types = ['全部', '股票型', '混合型', '债券型', '指数型', 'QDII', 'ETF联接', 'LOF', '场内交易基金']

    conn = get_db_connection()
    cursor = conn.cursor()
    total_updated = 0

    for fund_type in fund_types:
        try:
            df = ak.fund_value_estimation_em(symbol=fund_type)
            if df is None or df.empty:
                continue

            # Parse column names dynamically (they contain date)
            columns = df.columns.tolist()
            estimate_col = None
            estimate_rate_col = None
            published_nav_col = None
            published_rate_col = None
            deviation_col = None
            previous_nav_col = None

            for col in columns:
                if '估算数据-估算值' in col:
                    estimate_col = col
                elif '估算数据-估算增长率' in col:
                    estimate_rate_col = col
                elif '公布数据-单位净值' in col:
                    published_nav_col = col
                elif '公布数据-日增长率' in col:
                    published_rate_col = col
                elif '估算偏差' in col:
                    deviation_col = col
                elif '单位净值' in col and '公布数据' not in col and '估算数据' not in col:
                    previous_nav_col = col

            if not all([estimate_col, published_nav_col, previous_nav_col]):
                continue

            # Update database
            for _, row in df.iterrows():
                code = row.get('基金代码')
                if not code:
                    continue

                # Parse numeric values
                estimate = row.get(estimate_col)
                estimate_rate = row.get(estimate_rate_col)
                published_nav = row.get(published_nav_col)
                published_rate = row.get(published_rate_col)
                deviation = row.get(deviation_col)
                previous_nav = row.get(previous_nav_col)

                # Parse rate strings (e.g., "3.28%" -> 3.28)
                def parse_rate(val):
                    if val is None or val == '' or val == '---':
                        return None
                    if isinstance(val, str):
                        try:
                            return float(val.replace('%', ''))
                        except:
                            return None
                    try:
                        return float(val)
                    except:
                        return None

                estimate_rate = parse_rate(estimate_rate)
                published_rate = parse_rate(published_rate)
                deviation = parse_rate(deviation)

                # Parse numeric values
                def parse_float(val):
                    if val is None or val == '' or val == '---':
                        return None
                    try:
                        return float(val)
                    except:
                        return None

                estimate = parse_float(estimate)
                published_nav = parse_float(published_nav)
                previous_nav = parse_float(previous_nav)

                # Insert or update
                cursor.execute("""
                    INSERT OR REPLACE INTO fund_nav_estimation
                    (code, date, estimate, estimate_rate, published_nav, published_rate, deviation, previous_nav, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    code,
                    today_str,
                    estimate,
                    estimate_rate,
                    published_nav,
                    published_rate,
                    deviation,
                    previous_nav
                ))

                total_updated += 1

            time.sleep(0.5)  # Avoid API rate limiting between types

        except Exception as e:
            logger.error(f"Failed to update estimation cache for type '{fund_type}': {e}")

    conn.commit()
    conn.close()

    if total_updated > 0:
        logger.info(f"NAV estimation cache updated: {total_updated} funds at {now_cst.strftime('%H:%M')}")

def check_subscriptions():
    """
    Check all subscriptions and send alerts (Volatility & Digest).
    """
    logger.info("Checking subscriptions...")
    subs = get_active_subscriptions()
    if not subs:
        return

    now_cst = datetime.now(CST)
    today_str = now_cst.strftime("%Y-%m-%d")
    current_time_str = now_cst.strftime("%H:%M")

    # Cache valuations during this run to avoid duplicate API calls
    valuations = {}

    for sub in subs:
        code = sub["code"]
        sub_id = sub["id"]
        email = sub["email"]
        
        # 1. Fetch data if needed
        if code not in valuations:
            valuations[code] = get_combined_valuation(code)
        
        data = valuations[code]
        if not data: continue
        
        est_rate = data.get("estRate", 0.0)
        fund_name = data.get("name", code)

        # --- Sub-task A: Real-time Volatility Alert ---
        # Logic: If volatility enabled AND threshold crossed AND not yet notified today
        if sub["enable_volatility"]:
            last_notified = sub["last_notified_at"]
            if not (last_notified and last_notified.startswith(today_str)):
                triggered = False
                reason = ""
                
                if sub["threshold_up"] > 0 and est_rate >= sub["threshold_up"]:
                    triggered = True
                    reason = f"上涨已达到 {est_rate}% (阈值: {sub['threshold_up']}%)"
                elif sub["threshold_down"] < 0 and est_rate <= sub["threshold_down"]:
                    triggered = True
                    reason = f"下跌已达到 {est_rate}% (阈值: {sub['threshold_down']}%)"
                
                if triggered:
                    subject = f"【异动提醒】{fund_name} ({code}) 预估 {est_rate}%"
                    content = f"""
                    <h3>基金异动提醒</h3>
                    <p>基金: {fund_name} ({code})</p>
                    <p>当前预估涨跌幅: <b>{est_rate}%</b></p>
                    <p>触发原因: {reason}</p>
                    <p>估值时间: {data.get('time')}</p>
                    <hr/>
                    <p>此邮件由 FundVal Live 自动发送。</p>
                    """
                    if send_email(email, subject, content, is_html=True):
                        update_notification_time(sub_id)

        # --- Sub-task B: Daily Scheduled Digest ---
        # Logic: If digest enabled AND current time >= digest time AND not yet sent today
        if sub["enable_digest"]:
            last_digest = sub["last_digest_at"]
            if not (last_digest and last_digest.startswith(today_str)):
                # If we are at or past the scheduled time
                if current_time_str >= sub["digest_time"]:
                    subject = f"【每日总结】{fund_name} ({code}) 今日估值汇总"
                    content = f"""
                    <h3>每日基金总结</h3>
                    <p>基金: {fund_name} ({code})</p>
                    <p>今日收盘/最新估值: {data.get('estimate', 'N/A')}</p>
                    <p>今日涨跌幅: <b>{est_rate}%</b></p>
                    <p>总结时间: {now_cst.strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <hr/>
                    <p>祝您投资愉快！</p>
                    """
                    if send_email(email, subject, content, is_html=True):
                        update_digest_time(sub_id)

def start_scheduler():
    """
    Simple background thread to check if data needs update.
    """
    def _run():
        # 1. Initial fund list update
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) as cnt FROM funds")
        count = cursor.fetchone()["cnt"]
        conn.close()

        if count == 0:
            logger.info("DB is empty. Performing initial fetch.")
            fetch_and_update_funds()

        # 2. Main loop
        last_cleanup_date = None
        last_nav_update_hour = None
        last_estimation_update_time = None

        while True:
            try:
                now_cst = datetime.now(CST)
                today_str = now_cst.strftime("%Y-%m-%d")

                # Get collection interval from settings
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM settings WHERE key = 'INTRADAY_COLLECT_INTERVAL'")
                row = cursor.fetchone()
                interval_minutes = int(row["value"]) if row and row["value"] else 5
                conn.close()

                # 24/7 Monitoring
                check_subscriptions()

                # Intraday data collection (trading hours only)
                collect_intraday_snapshots()

                # NAV estimation cache update
                # Optimized refresh strategy to reduce API calls:
                # - 09:00-18:30: no refresh (trading hours and waiting for NAV publication)
                # - 18:30-24:00: every 10 minutes for published NAV data, STOP when all NAVs published
                # - 00:00-09:00: no refresh (minimal refresh)
                
                # Check if all NAVs have been published
                all_published = check_all_navs_published()
                
                if last_estimation_update_time is None:
                    update_nav_estimation_cache()
                    last_estimation_update_time = now_cst
                else:
                    current_hour = now_cst.hour
                    current_minute = now_cst.minute
                    
                    # Determine refresh interval based on time of day
                    if current_hour < 18 or (current_hour == 18 and current_minute < 30):
                        # Trading hours and waiting for NAV publication: skip refresh
                        interval_seconds = float('inf')
                    elif 18 <= current_hour < 24:
                        # After NAV publication: refresh every 10 minutes
                        # BUT stop if all NAVs have been published
                        if all_published:
                            interval_seconds = float('inf')
                        else:
                            interval_seconds = 600  # 10 minutes
                    else:
                        # Early morning: no refresh
                        interval_seconds = float('inf')

                    if interval_seconds != float('inf') and (now_cst - last_estimation_update_time).total_seconds() >= interval_seconds:
                        update_nav_estimation_cache()
                        last_estimation_update_time = now_cst

                # 待确认加仓/减仓：用当日已公布净值更新持仓
                n = process_pending_transactions()
                if n:
                    logger.info(f"Applied {n} pending add/reduce transactions.")

                # Daily cleanup (once per day at 00:00)
                if last_cleanup_date != today_str and now_cst.hour == 0:
                    cleanup_old_intraday_data()
                    last_cleanup_date = today_str

                # NAV update (once per hour between 16:00-24:00)
                if 16 <= now_cst.hour <= 23 and last_nav_update_hour != now_cst.hour:
                    update_holdings_nav()
                    last_nav_update_hour = now_cst.hour

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")

            # Sleep for configured interval (default 5 minutes)
            time.sleep(interval_minutes * 60)
    
    t = threading.Thread(target=_run, daemon=True)
    t.start()
