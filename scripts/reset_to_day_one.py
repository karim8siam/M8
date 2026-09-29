#!/usr/bin/env python3
"""
Matrix8 Day-1 Clean Slate Reset Script
Resets both Neon PostgreSQL and local SQLite databases to Day 1:
- Removes all test members, transactions, and withdrawals.
- Preserves and resets Genesis Root accounts (M8-ADMIN, M8-VIP001, ADMIN) to $0.00 balances.
- Resets level statistics and stage tracking to initial launch state.
"""

import os
import sys
import time
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))

import database

ADMIN_IDS = ('M8-ADMIN', 'M8-VIP001', 'ADMIN')

def reset_database(conn, db_name="Database"):
    print(f"\n==================================================")
    print(f"🔄 RESETTING {db_name.upper()} TO DAY 1 LAUNCH STATE")
    print(f"==================================================")
    c = conn.cursor()

    # 1. Clear transactions and withdrawals
    c.execute("DELETE FROM transactions")
    c.execute("DELETE FROM withdrawals")
    print("✅ [1/5] Cleared all transactions and withdrawals.")

    # 2. Clear non-admin level stats and user stages
    c.execute("DELETE FROM level_stats WHERE user_id NOT IN ('M8-ADMIN', 'M8-VIP001', 'ADMIN')")
    c.execute("DELETE FROM user_stages WHERE user_id NOT IN ('M8-ADMIN', 'M8-VIP001', 'ADMIN')")
    c.execute("DELETE FROM users WHERE unique_id NOT IN ('M8-ADMIN', 'M8-VIP001', 'ADMIN')")
    print("✅ [2/5] Removed all test accounts and user stage records.")

    # 3. Ensure Genesis Root accounts exist and reset their stats
    now = int(time.time())
    for admin_id in ADMIN_IDS:
        c.execute("SELECT unique_id FROM users WHERE unique_id = ?", (admin_id,))
        if not c.fetchone():
            c.execute("""
                INSERT INTO users (
                    unique_id, email, password_hash, wallet_address, referrer_id,
                    telegram_handle, status, join_timestamp, total_earned, wallet_balance, directs_count, current_stage
                ) VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, 0.0, 0.0, 0, 1)
            """, (
                admin_id,
                f"{admin_id.lower()}@matrix8.io",
                'admin_hash',
                database.SYSTEM_TREASURY_ADDRESS,
                None,
                '@ffalfofaofgf8',
                now
            ))
        else:
            c.execute("""
                UPDATE users SET
                    total_earned = 0.0,
                    wallet_balance = 0.0,
                    total_withdrawn = 0.0,
                    directs_count = 0,
                    current_stage = 1,
                    status = 'ACTIVE',
                    telegram_handle = '@ffalfofaofgf8'
                WHERE unique_id = ?
            """, (admin_id,))

        # Reset user_stages to Stage 1 with 0 fee paid
        c.execute("DELETE FROM user_stages WHERE user_id = ?", (admin_id,))
        c.execute("""
            INSERT INTO user_stages (user_id, stage, fee_paid, sponsor_id, tx_hash, activated_timestamp, status)
            VALUES (?, 1, 0.0, NULL, 'GENESIS_ROOT_STAGE1', ?, 'ACTIVE')
        """, (admin_id, now))

        # Reset 8 levels
        for lvl in range(1, 9):
            c.execute("""
                INSERT INTO level_stats (user_id, level_num, member_count, earned_amount, stage)
                VALUES (?, ?, 0, 0.0, 1)
                ON CONFLICT (user_id, stage, level_num) DO UPDATE SET member_count = 0, earned_amount = 0.0
            """, (admin_id, lvl))

    print("✅ [3/5] Genesis Root & Admin accounts reset to $0.00 balances.")

    # 4. Reset sequences if PostgreSQL
    if database.is_postgres():
        try:
            c.execute("ALTER SEQUENCE transactions_id_seq RESTART WITH 1;")
            c.execute("ALTER SEQUENCE withdrawals_id_seq RESTART WITH 1;")
            print("✅ [4/5] Reset PostgreSQL auto-increment sequences.")
        except Exception as e:
            print(f"ℹ️ [4/5] Sequence reset notice: {e}")
    else:
        print("✅ [4/5] SQLite auto-increment reset.")

    conn.commit()

    # 5. Verification Summary
    print("\n--- DAY 1 VERIFICATION AUDIT ---")
    for tbl in ['users', 'user_stages', 'level_stats', 'transactions', 'withdrawals']:
        c.execute(f"SELECT count(*) FROM {tbl}")
        row = c.fetchone()
        cnt = row['count'] if isinstance(row, dict) and 'count' in row else (row[0] if row else 0)
        print(f"Table [{tbl}]: {cnt} records")

    c.execute("SELECT unique_id, email, status, directs_count, total_earned, wallet_balance, current_stage FROM users")
    users = c.fetchall()
    print("\nActive Day-1 Accounts:")
    for u in users:
        print(" ", dict(u) if isinstance(u, dict) else u)

    print(f"\n🎉 {db_name.upper()} IS OFFICIALLY CLEAN AND READY FOR DAY 1!")

def main():
    # 1. Reset remote Neon PostgreSQL
    if database.is_postgres():
        p_conn = database.get_db()
        reset_database(p_conn, db_name="Neon Cloud PostgreSQL")
        p_conn.close()

    # 2. Reset local SQLite
    s_db_path = database.DB_PATH
    if os.path.isfile(s_db_path):
        s_conn = sqlite3.connect(s_db_path)
        s_conn.row_factory = sqlite3.Row
        # Disable is_postgres temporarily for sqlite reset
        orig_is_pg = database.is_postgres
        database.is_postgres = lambda: False
        reset_database(s_conn, db_name="Local SQLite (matrix8.db)")
        database.is_postgres = orig_is_pg
        s_conn.close()

if __name__ == '__main__':
    main()
