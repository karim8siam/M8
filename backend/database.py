"""
Matrix8 Dual-Mode Database Engine (Neon PostgreSQL & SQLite Fallback)
Supports Serverless Cloud Deployment on Vercel with Neon PostgreSQL,
as well as local development with SQLite.
"""

import os
import sys
import time
import re
import urllib.parse
import sqlite3

SYSTEM_TREASURY_ADDRESS = '0x9ff36bB1b16F1421b2CeBFFE311aCB8D5800AE43'
SYSTEM_ROOT_ID = 'M8-VIP001'

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'matrix8.db')

def get_database_url():
    """Fetches database connection string from environment variables."""
    return (
        os.environ.get('DATABASE_URL') or 
        os.environ.get('NEON_DATABASE_URL') or 
        os.environ.get('POSTGRES_URL') or 
        os.environ.get('POSTGRES_PRISMA_URL') or 
        os.environ.get('POSTGRES_URL_NON_POOLING') or 
        ''
    ).strip()

def is_postgres():
    """Checks if a PostgreSQL connection URL is configured."""
    url = get_database_url()
    return bool(url and (url.startswith('postgres://') or url.startswith('postgresql://')))

class PostgresRowDict(dict):
    """Row wrapper for PostgreSQL query results that behaves like sqlite3.Row / dict."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

class PostgresCursorWrapper:
    def __init__(self, real_cursor, is_pg8000=False):
        self.cursor = real_cursor
        self.is_pg8000 = is_pg8000
        self.col_names = []

    def _convert_sql(self, sql):
        # 1. Escape literal '%' in SQL by temporarily protecting '?'
        token = '__PARAM_PLACEHOLDER__'
        tmp = sql.replace('?', token)
        tmp = tmp.replace('%', '%%')
        converted = tmp.replace(token, '%s')

        # 2. Convert SQLite 'INSERT OR IGNORE' to Postgres 'INSERT ... ON CONFLICT DO NOTHING'
        if 'INSERT OR IGNORE INTO' in converted:
            converted = converted.replace('INSERT OR IGNORE INTO', 'INSERT INTO')
            if 'ON CONFLICT' not in converted:
                converted = converted + ' ON CONFLICT DO NOTHING'

        # 3. Safeguard: convert double-quoted SQL string constants to single quotes for Postgres
        import re
        converted = re.sub(r'\"([A-Za-z0-9_]+)\"', r"'\1'", converted)
        return converted

    def execute(self, sql, params=None):
        pg_sql = self._convert_sql(sql)
        if params is not None:
            # Flatten or format tuple/list
            p = list(params) if isinstance(params, (tuple, list)) else [params]
            self.cursor.execute(pg_sql, p)
        else:
            self.cursor.execute(pg_sql)

        if self.cursor.description:
            self.col_names = [col[0] for col in self.cursor.description]
        return self

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            return PostgresRowDict(row)
        return PostgresRowDict(zip(self.col_names, row))

    def fetchall(self):
        rows = self.cursor.fetchall()
        if not rows:
            return []
        res = []
        for row in rows:
            if isinstance(row, dict):
                res.append(PostgresRowDict(row))
            else:
                res.append(PostgresRowDict(zip(self.col_names, row)))
        return res

    def close(self):
        try:
            self.cursor.close()
        except Exception:
            pass

class PostgresConnectionWrapper:
    def __init__(self, real_conn, is_pg8000=False):
        self.conn = real_conn
        self.is_pg8000 = is_pg8000

    def cursor(self):
        real_cur = self.conn.cursor()
        return PostgresCursorWrapper(real_cur, self.is_pg8000)

    def commit(self):
        return self.conn.commit()

    def rollback(self):
        return self.conn.rollback()

    def close(self):
        return self.conn.close()

def _connect_postgres(url):
    """Establishes connection to PostgreSQL using psycopg2, psycopg, or pg8000."""
    # Try psycopg2
    try:
        import psycopg2
        import psycopg2.extras
        # Replace postgres:// with postgresql:// if needed
        clean_url = url
        if clean_url.startswith('postgres://'):
            clean_url = clean_url.replace('postgres://', 'postgresql://', 1)
        conn = psycopg2.connect(clean_url, sslmode='require')
        return PostgresConnectionWrapper(conn, is_pg8000=False)
    except ImportError:
        pass

    # Try psycopg (v3)
    try:
        import psycopg
        conn = psycopg.connect(url)
        return PostgresConnectionWrapper(conn, is_pg8000=False)
    except ImportError:
        pass

    # Try pg8000 (Pure Python)
    try:
        import pg8000
        import ssl
        p = urllib.parse.urlparse(url)
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        conn = pg8000.connect(
            user=p.username,
            password=p.password,
            host=p.hostname,
            port=p.port or 5432,
            database=p.path.lstrip('/'),
            ssl_context=ssl_ctx
        )
        return PostgresConnectionWrapper(conn, is_pg8000=True)
    except ImportError:
        pass

    raise RuntimeError("PostgreSQL connection URL provided, but neither psycopg2, psycopg, nor pg8000 are installed.")

def get_db():
    """
    Returns a unified database connection.
    Connects to Neon PostgreSQL if DATABASE_URL is set; otherwise falls back to SQLite.
    """
    if is_postgres():
        return _connect_postgres(get_database_url())
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """Initializes tables and Genesis Root Admin records in either PostgreSQL or SQLite."""
    conn = get_db()
    cursor = conn.cursor()

    if is_postgres():
        # PostgreSQL Schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                unique_id VARCHAR(64) PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                wallet_address VARCHAR(128) NOT NULL,
                referrer_id VARCHAR(64),
                telegram_handle VARCHAR(128),
                status VARCHAR(32) DEFAULT 'ACTIVE',
                join_timestamp BIGINT NOT NULL,
                total_earned DOUBLE PRECISION DEFAULT 0.0,
                wallet_balance DOUBLE PRECISION DEFAULT 0.0,
                total_withdrawn DOUBLE PRECISION DEFAULT 0.0,
                directs_count INTEGER DEFAULT 0
            );
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS level_stats (
                user_id VARCHAR(64) NOT NULL,
                level_num INTEGER NOT NULL,
                member_count INTEGER DEFAULT 0,
                earned_amount DOUBLE PRECISION DEFAULT 0.0,
                PRIMARY KEY (user_id, level_num)
            );
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id SERIAL PRIMARY KEY,
                withdrawal_id VARCHAR(64) UNIQUE NOT NULL,
                user_id VARCHAR(64) NOT NULL,
                wallet_address VARCHAR(128) NOT NULL,
                amount_usdt DOUBLE PRECISION NOT NULL,
                fee_usdt DOUBLE PRECISION DEFAULT 0.0,
                net_amount DOUBLE PRECISION NOT NULL,
                status VARCHAR(32) DEFAULT 'PENDING',
                tx_hash VARCHAR(128),
                request_timestamp BIGINT NOT NULL,
                processed_timestamp BIGINT,
                admin_note TEXT
            );
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                tx_hash VARCHAR(128) UNIQUE,
                tx_type VARCHAR(64) NOT NULL,
                from_user_id VARCHAR(64),
                to_user_id VARCHAR(64),
                from_wallet VARCHAR(128),
                to_wallet VARCHAR(128),
                amount_usdt DOUBLE PRECISION NOT NULL,
                level_num INTEGER,
                timestamp BIGINT NOT NULL,
                status VARCHAR(32) DEFAULT 'CONFIRMED',
                note TEXT
            );
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_config (
                key VARCHAR(64) PRIMARY KEY,
                value TEXT
            );
        ''')

    else:
        # SQLite Schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                unique_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                wallet_address TEXT NOT NULL,
                referrer_id TEXT,
                telegram_handle TEXT,
                status TEXT DEFAULT 'ACTIVE',
                join_timestamp INTEGER NOT NULL,
                total_earned REAL DEFAULT 0.0,
                wallet_balance REAL DEFAULT 0.0,
                total_withdrawn REAL DEFAULT 0.0,
                directs_count INTEGER DEFAULT 0
            )
        ''')

        try:
            cursor.execute('ALTER TABLE users ADD COLUMN total_withdrawn REAL DEFAULT 0.0')
        except Exception:
            pass

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS level_stats (
                user_id TEXT NOT NULL,
                level_num INTEGER NOT NULL,
                member_count INTEGER DEFAULT 0,
                earned_amount REAL DEFAULT 0.0,
                PRIMARY KEY (user_id, level_num)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                withdrawal_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                wallet_address TEXT NOT NULL,
                amount_usdt REAL NOT NULL,
                fee_usdt REAL DEFAULT 0.0,
                net_amount REAL NOT NULL,
                status TEXT DEFAULT 'PENDING',
                tx_hash TEXT,
                request_timestamp INTEGER NOT NULL,
                processed_timestamp INTEGER,
                admin_note TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tx_hash TEXT UNIQUE,
                tx_type TEXT NOT NULL,
                from_user_id TEXT,
                to_user_id TEXT,
                from_wallet TEXT,
                to_wallet TEXT,
                amount_usdt REAL NOT NULL,
                level_num INTEGER,
                timestamp INTEGER NOT NULL,
                status TEXT DEFAULT 'CONFIRMED',
                note TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

    # Seed Genesis Root Admin Accounts (M8-ADMIN, M8-VIP001, ADMIN)
    admin_ids = ['M8-ADMIN', 'M8-VIP001', 'ADMIN']
    for admin_id in admin_ids:
        cursor.execute('SELECT unique_id FROM users WHERE unique_id = ?', (admin_id,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO users (
                    unique_id, email, password_hash, wallet_address, referrer_id,
                    telegram_handle, status, join_timestamp, total_earned, wallet_balance, directs_count
                ) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, 0.0, 0.0, 0)
            ''', (
                admin_id,
                f'{admin_id.lower()}@matrix8.io',
                'admin_hash',
                SYSTEM_TREASURY_ADDRESS,
                None,
                '@Matrix8Official',
                int(time.time())
            ))

            for lvl in range(1, 9):
                cursor.execute('''
                    INSERT OR IGNORE INTO level_stats (user_id, level_num, member_count, earned_amount)
                    VALUES (?, ?, 0, 0.0)
                ''', (admin_id, lvl))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    db_mode = "Neon PostgreSQL" if is_postgres() else f"SQLite ({DB_PATH})"
    print(f"✅ Matrix8 Database initialized successfully in [{db_mode}] mode!")

