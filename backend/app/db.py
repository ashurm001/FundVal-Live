import sqlite3
import logging
import os
from pathlib import Path
from .config import Config

logger = logging.getLogger(__name__)

def get_db_connection():
    """获取数据库连接"""
    # 确保数据库目录存在
    db_dir = Path(Config.DB_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(Config.DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")
    # 优化性能设置
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=10000")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn

def init_db():
    """Initialize database schema with migration support."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check database version
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("SELECT MAX(version) FROM schema_version")
    current_version = cursor.fetchone()[0] or 0

    logger.info(f"Current database schema version: {current_version}")

    # Funds table - simplistic design, exactly what we need
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS funds (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create an index for searching names, it's cheap and speeds up "LIKE" queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_funds_name ON funds(name);
    """)

    # Positions table - store user holdings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            code TEXT PRIMARY KEY,
            cost REAL NOT NULL DEFAULT 0.0,
            shares REAL NOT NULL DEFAULT 0.0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Subscriptions table - store email alert settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            email TEXT NOT NULL,
            threshold_up REAL,
            threshold_down REAL,
            enable_digest INTEGER DEFAULT 0,
            digest_time TEXT DEFAULT '14:45',
            enable_volatility INTEGER DEFAULT 1,
            last_notified_at TIMESTAMP,
            last_digest_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(code, email)
        )
    """)

    # Settings table - store user configuration (for client/desktop)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            encrypted INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 初始化默认配置（如果不存在）
    default_settings = [
        ('OPENAI_API_KEY', '', 1),
        ('OPENAI_API_BASE', 'https://api.openai.com/v1', 0),
        ('AI_MODEL_NAME', 'gpt-3.5-turbo', 0),
        ('SMTP_HOST', 'smtp.gmail.com', 0),
        ('SMTP_PORT', '587', 0),
        ('SMTP_USER', '', 0),
        ('SMTP_PASSWORD', '', 1),
        ('EMAIL_FROM', 'noreply@fundval.live', 0),
        ('NOTIFICATION_EMAIL', '', 0),
        ('INTRADAY_COLLECT_INTERVAL', '5', 0),
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO settings (key, value, encrypted) VALUES (?, ?, ?)
    """, default_settings)

    # Transactions table - add/reduce position log (T+1 confirm by real NAV)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            op_type TEXT NOT NULL,
            amount_cny REAL,
            shares_redeemed REAL,
            confirm_date TEXT NOT NULL,
            confirm_nav REAL,
            shares_added REAL,
            cost_after REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            applied_at TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_code ON transactions(code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_confirm_date ON transactions(confirm_date);")

    # Fund history table - cache historical NAV data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fund_history (
            code TEXT NOT NULL,
            date TEXT NOT NULL,
            nav REAL NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (code, date)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fund_history_code ON fund_history(code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fund_history_date ON fund_history(date);")

    # Intraday snapshots table - store intraday valuation data for charts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fund_intraday_snapshots (
            fund_code TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            estimate REAL NOT NULL,
            PRIMARY KEY (fund_code, date, time)
        )
    """)

    # Fund NAV estimation cache table - store real-time NAV estimation data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fund_nav_estimation (
            code TEXT NOT NULL,
            date TEXT NOT NULL,
            estimate REAL,
            estimate_rate REAL,
            published_nav REAL,
            published_rate REAL,
            deviation REAL,
            previous_nav REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (code, date)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fund_nav_estimation_code ON fund_nav_estimation(code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fund_nav_estimation_date ON fund_nav_estimation(date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fund_nav_estimation_updated ON fund_nav_estimation(updated_at);")

    # AI analysis history table - store AI analysis results for historical review
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_code TEXT NOT NULL,
            fund_name TEXT,
            analysis_date TEXT NOT NULL,
            analysis_time TEXT NOT NULL,
            risk_level TEXT,
            status TEXT,
            indicators_desc TEXT,
            analysis_report TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_analysis_history_code ON ai_analysis_history(fund_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_analysis_history_date ON ai_analysis_history(analysis_date);")

    # User notes table - store user notes for funds
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fund_code TEXT NOT NULL,
            fund_name TEXT,
            note_date TEXT NOT NULL,
            note_time TEXT NOT NULL,
            note_content TEXT NOT NULL,
            note_color TEXT DEFAULT '#10b981',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_notes_code ON user_notes(fund_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_notes_date ON user_notes(note_date);")

    # Migration: Drop old incompatible tables
    if current_version < 1:
        logger.info("Running migration: dropping old incompatible tables")
        cursor.execute("DROP TABLE IF EXISTS valuation_accuracy")
        cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (1)")

    # Migration: Multi-account support
    if current_version < 2:
        logger.info("Running migration: adding multi-account support")

        # 1. Create accounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Insert default account
        cursor.execute("""
            INSERT OR IGNORE INTO accounts (id, name, description)
            VALUES (1, '默认账户', '系统默认账户')
        """)

        # 3. Check if positions table needs migration
        cursor.execute("PRAGMA table_info(positions)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'account_id' not in columns:
            logger.info("Migrating positions table to multi-account")

            # Backup old data
            cursor.execute("SELECT code, cost, shares, updated_at FROM positions")
            old_positions = cursor.fetchall()

            # Drop old table
            cursor.execute("DROP TABLE positions")

            # Create new table with account_id
            cursor.execute("""
                CREATE TABLE positions (
                    account_id INTEGER NOT NULL DEFAULT 1,
                    code TEXT NOT NULL,
                    cost REAL NOT NULL DEFAULT 0.0,
                    shares REAL NOT NULL DEFAULT 0.0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (account_id, code),
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE RESTRICT
                )
            """)

            # Restore data with default account_id = 1
            for row in old_positions:
                cursor.execute("""
                    INSERT INTO positions (account_id, code, cost, shares, updated_at)
                    VALUES (1, ?, ?, ?, ?)
                """, row)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_account ON positions(account_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_code ON positions(code)")

        # 4. Check if transactions table needs migration
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'account_id' not in columns:
            logger.info("Migrating transactions table to multi-account")

            # Backup old data
            cursor.execute("""
                SELECT id, code, op_type, amount_cny, shares_redeemed,
                       confirm_date, confirm_nav, shares_added, cost_after,
                       created_at, applied_at
                FROM transactions
            """)
            old_transactions = cursor.fetchall()

            # Drop old table
            cursor.execute("DROP TABLE transactions")

            # Create new table with account_id
            cursor.execute("""
                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL DEFAULT 1,
                    code TEXT NOT NULL,
                    op_type TEXT NOT NULL,
                    amount_cny REAL,
                    shares_redeemed REAL,
                    confirm_date TEXT NOT NULL,
                    confirm_nav REAL,
                    shares_added REAL,
                    cost_after REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    applied_at TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE RESTRICT
                )
            """)

            # Restore data with default account_id = 1
            for row in old_transactions:
                cursor.execute("""
                    INSERT INTO transactions
                    (id, account_id, code, op_type, amount_cny, shares_redeemed,
                     confirm_date, confirm_nav, shares_added, cost_after,
                     created_at, applied_at)
                    VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, row)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_code ON transactions(code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_confirm_date ON transactions(confirm_date)")

        cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (2)")

    # Migration: Messages table for storing portfolio analysis and other messages
    if current_version < 3:
        logger.info("Running migration: adding messages table")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                msg_type TEXT NOT NULL DEFAULT 'portfolio_analysis',
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                score INTEGER,
                risk_level TEXT,
                fund_count INTEGER,
                total_value REAL,
                read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(msg_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_read ON messages(read);")

        cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (3)")

    # Migration: Crypto positions and prices tables
    if current_version < 4:
        logger.info("Running migration: adding crypto tables")

        # Crypto positions table - store cryptocurrency holdings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crypto_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL DEFAULT 1,
                symbol TEXT NOT NULL,
                name TEXT,
                cost REAL NOT NULL DEFAULT 0.0,
                amount REAL NOT NULL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE RESTRICT,
                UNIQUE(account_id, symbol)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_crypto_positions_account ON crypto_positions(account_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_crypto_positions_symbol ON crypto_positions(symbol);")

        # Crypto prices table - cache cryptocurrency prices
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crypto_prices (
                symbol TEXT NOT NULL,
                price_usd REAL NOT NULL,
                price_cny REAL NOT NULL,
                change_24h REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (symbol)
            )
        """)

        # Crypto transactions table - log crypto trades
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crypto_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL DEFAULT 1,
                symbol TEXT NOT NULL,
                op_type TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL NOT NULL,
                total_cny REAL NOT NULL,
                trade_time TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE RESTRICT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_crypto_transactions_account ON crypto_transactions(account_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_crypto_transactions_symbol ON crypto_transactions(symbol);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_crypto_transactions_time ON crypto_transactions(trade_time);")

        cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (4)")

    # Migration: AI模拟账户支持
    if current_version < 5:
        logger.info("Running migration: adding AI simulation account support")

        # 1. AI模拟账户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_simulation_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT 'AI模拟账户',
                description TEXT,
                source_account_id INTEGER NOT NULL,
                source_type TEXT DEFAULT 'fund',
                initial_capital REAL NOT NULL DEFAULT 0.0,
                current_value REAL NOT NULL DEFAULT 0.0,
                total_return_rate REAL DEFAULT 0.0,
                is_active INTEGER DEFAULT 1,
                review_day_of_week INTEGER DEFAULT 1,
                review_interval_type TEXT DEFAULT 'week',  -- 审视周期类型：day, week, month, hour
                review_interval INTEGER DEFAULT 1,       -- 审视间隔：1表示每天/每周/每月/每小时
                last_review_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_account_id) REFERENCES accounts(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_sim_accounts_source ON ai_simulation_accounts(source_account_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_sim_accounts_active ON ai_simulation_accounts(is_active);")

        # 2. AI模拟持仓表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_simulation_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ai_account_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                name TEXT,
                asset_type TEXT DEFAULT 'fund',
                cost REAL NOT NULL DEFAULT 0.0,
                shares REAL NOT NULL DEFAULT 0.0,
                current_price REAL DEFAULT 0.0,
                market_value REAL DEFAULT 0.0,
                return_rate REAL DEFAULT 0.0,
                weight REAL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ai_account_id) REFERENCES ai_simulation_accounts(id) ON DELETE CASCADE,
                UNIQUE(ai_account_id, code)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_sim_positions_account ON ai_simulation_positions(ai_account_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_sim_positions_code ON ai_simulation_positions(code);")

        # 3. AI调仓历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_simulation_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ai_account_id INTEGER NOT NULL,
                trade_date TEXT NOT NULL,
                code TEXT NOT NULL,
                name TEXT,
                asset_type TEXT DEFAULT 'fund',
                trade_type TEXT NOT NULL,
                shares REAL NOT NULL,
                price REAL NOT NULL,
                amount REAL NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ai_account_id) REFERENCES ai_simulation_accounts(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_sim_trades_account ON ai_simulation_trades(ai_account_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_sim_trades_date ON ai_simulation_trades(trade_date);")

        # 4. AI账户资产历史表（用于绘制走势对比）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_simulation_value_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ai_account_id INTEGER NOT NULL,
                record_date TEXT NOT NULL,
                ai_value REAL NOT NULL,
                source_value REAL NOT NULL,
                ai_return_rate REAL DEFAULT 0.0,
                source_return_rate REAL DEFAULT 0.0,
                outperformance REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ai_account_id) REFERENCES ai_simulation_accounts(id) ON DELETE CASCADE,
                UNIQUE(ai_account_id, record_date)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_sim_value_account ON ai_simulation_value_history(ai_account_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_sim_value_date ON ai_simulation_value_history(record_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_sim_value_account_date ON ai_simulation_value_history(ai_account_id, record_date);")

        # 5. AI审视记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_simulation_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ai_account_id INTEGER NOT NULL,
                review_date TEXT NOT NULL,
                review_type TEXT DEFAULT 'weekly',
                market_analysis TEXT,
                portfolio_analysis TEXT,
                adjustment_strategy TEXT,
                executed_trades INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ai_account_id) REFERENCES ai_simulation_accounts(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_sim_reviews_account ON ai_simulation_reviews(ai_account_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_sim_reviews_date ON ai_simulation_reviews(review_date);")

        cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (5)")

    # Migration: AI模拟账户支持数字货币
    if current_version < 6:
        logger.info("Running migration: adding crypto support for AI simulation accounts")

        # 添加 source_type 列（如果不存在）
        try:
            cursor.execute("ALTER TABLE ai_simulation_accounts ADD COLUMN source_type TEXT DEFAULT 'fund'")
            logger.info("Added source_type column to ai_simulation_accounts")
        except Exception as e:
            logger.info(f"source_type column may already exist: {e}")

        # 创建数字货币账户（如果不存在）
        try:
            cursor.execute("INSERT OR IGNORE INTO accounts (name, description) VALUES (?, ?)", ("数字货币账户", "数字货币持仓账户"))
            logger.info("Created default crypto account")
        except Exception as e:
            logger.info(f"Crypto account may already exist: {e}")

        cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (6)")

    # Migration: 添加 crypto_positions current_price 列
    if current_version < 7:
        logger.info("Running migration: adding current_price column to crypto_positions")

        # 添加 current_price 列（如果不存在）
        try:
            cursor.execute("ALTER TABLE crypto_positions ADD COLUMN current_price REAL DEFAULT 0.0")
            logger.info("Added current_price column to crypto_positions")
        except Exception as e:
            logger.info(f"current_price column may already exist: {e}")

        cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (7)")

    # Migration: Add review interval fields to AI accounts
    if current_version < 8:
        logger.info("Running migration: adding review interval fields to AI accounts")
        try:
            cursor.execute("ALTER TABLE ai_simulation_accounts ADD COLUMN review_interval_type TEXT DEFAULT 'week'")
            cursor.execute("ALTER TABLE ai_simulation_accounts ADD COLUMN review_interval INTEGER DEFAULT 1")
            logger.info("Added review interval fields to ai_simulation_accounts")
        except Exception as e:
            logger.info(f"Review interval fields may already exist: {e}")

        cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (8)")

    # Migration: Add performance_comparison field to AI reviews
    if current_version < 9:
        logger.info("Running migration: adding performance_comparison field to AI reviews")
        try:
            cursor.execute("ALTER TABLE ai_simulation_reviews ADD COLUMN performance_comparison TEXT")
            logger.info("Added performance_comparison field to ai_simulation_reviews")
        except Exception as e:
            logger.info(f"performance_comparison field may already exist: {e}")

        cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (9)")

    conn.commit()
    conn.close()
    logger.info("Database initialized.")
