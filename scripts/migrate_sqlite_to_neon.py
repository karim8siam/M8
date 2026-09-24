#!/usr/bin/env python3
"""
Matrix8 SQLite to Neon PostgreSQL Data Migration Script
Transfers all user accounts, stages, level stats, transactions, and withdrawals.
"""

import os
import sys
import sqlite3
import psycopg2

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_PATH = os.path.join(BASE_DIR, 'matrix8.db')

def load_env():
    env_path = os.path.join(BASE_DIR, '.env')
    if os.path.isfile(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k and k not in os.environ:
                        os.environ[k] = v

load_env()
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not set in environment or .env")
    sys.exit(1)

def migrate():
    print(f"Connecting to SQLite: {SQLITE_PATH}")
    s_conn = sqlite3.connect(SQLITE_PATH)
    s_conn.row_factory = sqlite3.Row
    s_cur = s_conn.cursor()

    print(f"Connecting to Neon PostgreSQL...")
    p_conn = psycopg2.connect(DATABASE_URL)
    p_cur = p_conn.cursor()

    # 1. Migrate Users
    print("\n--- Migrating Users ---")
    s_cur.execute("SELECT * FROM users")
    users = s_cur.fetchall()
    print(f"Found {len(users)} users in SQLite.")
    user_upsert = """
        INSERT INTO users (
            unique_id, email, password_hash, wallet_address, referrer_id,
            telegram_handle, status, join_timestamp, total_earned, wallet_balance,
            directs_count, total_withdrawn, current_stage
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s
        )
        ON CONFLICT (unique_id) DO UPDATE SET
            email = EXCLUDED.email,
            password_hash = EXCLUDED.password_hash,
            wallet_address = EXCLUDED.wallet_address,
            referrer_id = EXCLUDED.referrer_id,
            telegram_handle = EXCLUDED.telegram_handle,
            status = EXCLUDED.status,
            join_timestamp = EXCLUDED.join_timestamp,
            total_earned = EXCLUDED.total_earned,
            wallet_balance = EXCLUDED.wallet_balance,
            directs_count = EXCLUDED.directs_count,
            total_withdrawn = EXCLUDED.total_withdrawn,
            current_stage = EXCLUDED.current_stage;
    """
    for u in users:
        u_dict = dict(u)
        current_stage = u_dict.get('current_stage', 1) or 1
        total_withdrawn = u_dict.get('total_withdrawn', 0.0) or 0.0
        p_cur.execute(user_upsert, (
            u_dict['unique_id'],
            u_dict['email'],
            u_dict['password_hash'],
            u_dict['wallet_address'],
            u_dict['referrer_id'],
            u_dict.get('telegram_handle', ''),
            u_dict.get('status', 'ACTIVE'),
            u_dict['join_timestamp'],
            u_dict.get('total_earned', 0.0),
            u_dict.get('wallet_balance', 0.0),
            u_dict.get('directs_count', 0),
            total_withdrawn,
            current_stage
        ))
    p_conn.commit()
    print(f"✅ Migrated {len(users)} users.")

    # 2. Migrate User Stages
    print("\n--- Migrating User Stages ---")
    s_cur.execute("SELECT * FROM user_stages")
    stages = s_cur.fetchall()
    print(f"Found {len(stages)} user stages in SQLite.")
    stage_upsert = """
        INSERT INTO user_stages (
            user_id, stage, fee_paid, sponsor_id, tx_hash, activated_timestamp, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, stage) DO UPDATE SET
            fee_paid = EXCLUDED.fee_paid,
            sponsor_id = EXCLUDED.sponsor_id,
            tx_hash = EXCLUDED.tx_hash,
            activated_timestamp = EXCLUDED.activated_timestamp,
            status = EXCLUDED.status;
    """
    for st in stages:
        st_dict = dict(st)
        p_cur.execute(stage_upsert, (
            st_dict['user_id'],
            st_dict['stage'],
            st_dict['fee_paid'],
            st_dict.get('sponsor_id'),
            st_dict.get('tx_hash'),
            st_dict['activated_timestamp'],
            st_dict.get('status', 'ACTIVE')
        ))
    p_conn.commit()
    print(f"✅ Migrated {len(stages)} user stages.")

    # 3. Migrate Level Stats
    print("\n--- Migrating Level Stats ---")
    s_cur.execute("SELECT * FROM level_stats")
    stats = s_cur.fetchall()
    print(f"Found {len(stats)} level_stats rows in SQLite.")
    stats_upsert = """
        INSERT INTO level_stats (
            user_id, stage, level_num, member_count, earned_amount
        ) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id, stage, level_num) DO UPDATE SET
            member_count = EXCLUDED.member_count,
            earned_amount = EXCLUDED.earned_amount;
    """
    for s in stats:
        s_dict = dict(s)
        stage_val = s_dict.get('stage', 1) or 1
        p_cur.execute(stats_upsert, (
            s_dict['user_id'],
            stage_val,
            s_dict['level_num'],
            s_dict.get('member_count', 0),
            s_dict.get('earned_amount', 0.0)
        ))
    p_conn.commit()
    print(f"✅ Migrated {len(stats)} level_stats rows.")

    # 4. Migrate Transactions
    print("\n--- Migrating Transactions ---")
    s_cur.execute("SELECT * FROM transactions")
    txs = s_cur.fetchall()
    print(f"Found {len(txs)} transactions in SQLite.")
    tx_insert = """
        INSERT INTO transactions (
            id, tx_hash, tx_type, from_user_id, to_user_id, from_wallet, to_wallet,
            amount_usdt, level_num, timestamp, status, note
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (tx_hash) DO NOTHING;
    """
    for tx in txs:
        t_dict = dict(tx)
        p_cur.execute(tx_insert, (
            t_dict['id'],
            t_dict['tx_hash'],
            t_dict['tx_type'],
            t_dict.get('from_user_id'),
            t_dict.get('to_user_id'),
            t_dict.get('from_wallet'),
            t_dict.get('to_wallet'),
            t_dict['amount_usdt'],
            t_dict.get('level_num'),
            t_dict['timestamp'],
            t_dict.get('status', 'CONFIRMED'),
            t_dict.get('note')
        ))
    # Update transactions id sequence
    p_cur.execute("SELECT setval(pg_get_serial_sequence('transactions', 'id'), COALESCE(max(id), 1)) FROM transactions;")
    p_conn.commit()
    print(f"✅ Migrated {len(txs)} transactions.")

    # 5. Migrate Withdrawals
    print("\n--- Migrating Withdrawals ---")
    s_cur.execute("SELECT * FROM withdrawals")
    wds = s_cur.fetchall()
    print(f"Found {len(wds)} withdrawals in SQLite.")
    wd_insert = """
        INSERT INTO withdrawals (
            id, withdrawal_id, user_id, wallet_address, amount_usdt, fee_usdt,
            net_amount, status, tx_hash, request_timestamp, processed_timestamp, admin_note
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (withdrawal_id) DO NOTHING;
    """
    for w in wds:
        w_dict = dict(w)
        p_cur.execute(wd_insert, (
            w_dict['id'],
            w_dict['withdrawal_id'],
            w_dict['user_id'],
            w_dict['wallet_address'],
            w_dict['amount_usdt'],
            w_dict.get('fee_usdt', 0.0),
            w_dict['net_amount'],
            w_dict.get('status', 'PENDING'),
            w_dict.get('tx_hash'),
            w_dict['request_timestamp'],
            w_dict.get('processed_timestamp'),
            w_dict.get('admin_note')
        ))
    # Update withdrawals id sequence
    p_cur.execute("SELECT setval(pg_get_serial_sequence('withdrawals', 'id'), COALESCE(max(id), 1)) FROM withdrawals;")
    p_conn.commit()
    print(f"✅ Migrated {len(wds)} withdrawals.")

    # Summary verification
    print("\n================ VERIFICATION SUMMARY ================")
    for table in ['users', 'user_stages', 'level_stats', 'transactions', 'withdrawals']:
        p_cur.execute(f"SELECT count(*) FROM {table}")
        count = p_cur.fetchone()[0]
        print(f"Table [{table}] has {count} rows in Neon PostgreSQL.")

    p_cur.execute("SELECT unique_id, email, wallet_address, current_stage, wallet_balance, total_earned FROM users")
    print("\nAll Users in Neon:")
    for r in p_cur.fetchall():
        print("  ", r)

    s_conn.close()
    p_conn.close()
    print("\n🎉 SQLite to Neon PostgreSQL migration complete and verified!")

if __name__ == '__main__':
    migrate()
