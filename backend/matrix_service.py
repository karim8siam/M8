"""
Matrix8 Core Commission & Matrix Logic (Backend)
Handles 8-Level Upline Traversal, Commission Dispatches, and SQLite Updates.
"""

import time
import random
import hashlib
import hmac
from database import get_db, SYSTEM_ROOT_ID, SYSTEM_TREASURY_ADDRESS
import bsc_verifier

LEVEL_PERCENTAGES = [0.21, 0.16, 0.13, 0.09, 0.06, 0.03, 0.02, 0.01]
REGISTRATION_FEE = 3.40
SYSTEM_BASE_PERCENTAGE = 0.29

# 4-Factor Master Security Vault Credentials
ADMIN_MASTER_PASSWORD_1 = "4990OrpU4990!HelloWorld123"
ADMIN_MASTER_PASSWORD_2 = "alonbiysA1"
ADMIN_PIN = "499011"
ADMIN_FAVORITE = "barca"

ACTIVE_ADMIN_TOKENS = set()

def generate_admin_token():
    payload = f"admin_vault_{int(time.time())}_{random.randint(100000, 999999)}"
    sig = hmac.new(b"matrix8_master_vault_secret_2026", payload.encode('utf-8'), hashlib.sha256).hexdigest()
    token = f"M8VAULT_{payload}_{sig[:20]}"
    ACTIVE_ADMIN_TOKENS.add(token)
    return token

def verify_admin_4factor_credentials(pass1, pass2, pin, fav):
    if not pass1 or not pass2 or not pin or not fav:
        return False, "All 4 security credentials are required."
    
    if pass1.strip() != ADMIN_MASTER_PASSWORD_1:
        return False, "Master Password 1 is incorrect."
    
    if pass2.strip() != ADMIN_MASTER_PASSWORD_2:
        return False, "Secondary Password 2 is incorrect."
        
    if str(pin).strip() != ADMIN_PIN:
        return False, "Security PIN is incorrect."
        
    if fav.strip().lower() != ADMIN_FAVORITE.lower():
        return False, "Security Secret Word is incorrect."
        
    token = generate_admin_token()
    return True, token

def verify_admin_token(token_or_pin):
    if not token_or_pin:
        return False
    val = str(token_or_pin).strip()
    return val in ACTIVE_ADMIN_TOKENS or val in (ADMIN_MASTER_PASSWORD_1, ADMIN_PIN)

def verify_admin_pin(pin):
    return verify_admin_token(pin)

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def generate_unique_id():
    conn = get_db()
    cursor = conn.cursor()
    while True:
        num = random.randint(100000, 999999)
        uid = f"M8-{num}"
        cursor.execute('SELECT unique_id FROM users WHERE unique_id = ?', (uid,))
        if not cursor.fetchone():
            conn.close()
            return uid

def register_user(email, password, sponsor_id, wallet_address, telegram_handle=''):
    conn = get_db()
    cursor = conn.cursor()

    email_clean = email.strip().lower()
    wallet_clean = wallet_address.strip()
    raw_sponsor = sponsor_id.strip().upper()
    if raw_sponsor in ('ADMIN', 'M8-ADMIN', 'M8-VIP001'):
        sponsor_clean = 'M8-ADMIN'
    else:
        sponsor_clean = raw_sponsor

    # Check unique email
    cursor.execute('SELECT unique_id FROM users WHERE email = ?', (email_clean,))
    if cursor.fetchone():
        conn.close()
        raise ValueError('This email address is already registered.')

    # Check unique wallet (only active accounts block new registration)
    cursor.execute('SELECT unique_id, status FROM users WHERE LOWER(wallet_address) = LOWER(?)', (wallet_clean,))
    existing_wallet = cursor.fetchone()
    if existing_wallet:
        if existing_wallet['status'] == 'ACTIVE':
            conn.close()
            raise ValueError('This BEP-20 wallet address is already linked to an active account.')
        else:
            # Overwrite unactivated draft
            cursor.execute('DELETE FROM users WHERE unique_id = ?', (existing_wallet['unique_id'],))

    # Check sponsor exists
    cursor.execute('SELECT unique_id, status FROM users WHERE unique_id = ?', (sponsor_clean,))
    sponsor = cursor.fetchone()
    if not sponsor:
        conn.close()
        raise ValueError(f'Sponsor ID "{sponsor_clean}" does not exist in the network.')

    new_id = generate_unique_id()
    now = int(time.time())
    is_admin_link = (sponsor_clean == 'M8-ADMIN')
    initial_status = 'ACTIVE' if is_admin_link else 'PENDING_DEPOSIT'

    # Insert user
    cursor.execute('''
        INSERT INTO users (
            unique_id, email, password_hash, wallet_address, referrer_id,
            telegram_handle, status, join_timestamp, total_earned, wallet_balance, directs_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, 0)
    ''', (
        new_id,
        email_clean,
        hash_password(password),
        wallet_clean,
        sponsor_clean,
        telegram_handle or '',
        initial_status,
        now
    ))

    # Initialize 8-level stats
    for lvl in range(1, 9):
        cursor.execute('''
            INSERT INTO level_stats (user_id, level_num, member_count, earned_amount)
            VALUES (?, ?, 0, 0.0)
        ''', (new_id, lvl))

    # If joining via Admin link: 100% Free Instant VIP Activation
    if is_admin_link:
        cursor.execute('UPDATE users SET directs_count = directs_count + 1 WHERE unique_id = ?', (sponsor_clean,))
        cursor.execute('UPDATE level_stats SET member_count = member_count + 1 WHERE user_id = ? AND level_num = 1', (sponsor_clean,))
        
        cursor.execute('''
            INSERT INTO transactions (
                tx_hash, tx_type, from_user_id, to_user_id, from_wallet, to_wallet,
                amount_usdt, timestamp, status, note
            ) VALUES (?, 'ADMIN_VIP_FREE_JOIN', ?, ?, ?, ?, 0.0, ?, 'CONFIRMED', '★ Admin VIP Free Activation (0 USDT Required)')
        ''', (
            f"ADMIN_VIP_{new_id}_{now}",
            new_id,
            sponsor_clean,
            wallet_clean,
            SYSTEM_TREASURY_ADDRESS,
            now
        ))

    conn.commit()
    conn.close()

    return {
        'unique_id': new_id,
        'email': email_clean,
        'wallet_address': wallet_clean,
        'sponsor_id': sponsor_clean,
        'status': initial_status,
        'is_free_vip': is_admin_link,
        'treasury_deposit_address': SYSTEM_TREASURY_ADDRESS,
        'required_amount_usdt': 0.0 if is_admin_link else REGISTRATION_FEE
    }

def activate_user_and_distribute(user_id, tx_hash):
    conn = get_db()
    cursor = conn.cursor()

    # Check replay attack
    cursor.execute('SELECT id FROM transactions WHERE tx_hash = ?', (tx_hash,))
    if cursor.fetchone():
        conn.close()
        raise ValueError(f'This Transaction Hash ({tx_hash[:10]}...) has already been verified and used.')

    cursor.execute('SELECT * FROM users WHERE unique_id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise ValueError(f'User {user_id} not found.')

    if user['status'] == 'ACTIVE':
        conn.close()
        return {'status': 'ALREADY_ACTIVE', 'unique_id': user_id}

    # Activate user
    cursor.execute("UPDATE users SET status = 'ACTIVE' WHERE unique_id = ?", (user_id,))

    # Log the incoming 3.4 USDT deposit
    now = int(time.time())
    cursor.execute('''
        INSERT INTO transactions (
            tx_hash, tx_type, from_user_id, to_user_id, from_wallet, to_wallet,
            amount_usdt, timestamp, status, note
        ) VALUES (?, 'BSC_DEPOSIT', ?, ?, ?, ?, ?, ?, 'CONFIRMED', '3.40 USDT Activation Deposit Confirmed on BSC')
    ''', (
        tx_hash,
        user_id,
        SYSTEM_ROOT_ID,
        user['wallet_address'],
        SYSTEM_TREASURY_ADDRESS,
        REGISTRATION_FEE,
        now
    ))

    # Update Direct Sponsor count
    sponsor_id = user['referrer_id']
    if sponsor_id:
        cursor.execute('UPDATE users SET directs_count = directs_count + 1 WHERE unique_id = ?', (sponsor_id,))

    # 8-Tier Recursive Commission Loop
    current_upline_id = sponsor_id
    distributed_sum = 0.0
    orphaned_percentage = 0.0
    commissions = []

    for level_idx in range(8):
        pct = LEVEL_PERCENTAGES[level_idx]
        commission_amount = round(REGISTRATION_FEE * pct, 4)
        level_num = level_idx + 1

        if current_upline_id and current_upline_id != SYSTEM_ROOT_ID:
            cursor.execute('SELECT * FROM users WHERE unique_id = ?', (current_upline_id,))
            upline = cursor.fetchone()
            if upline:
                # Credit upline total earned & wallet balance
                cursor.execute('''
                    UPDATE users 
                    SET total_earned = total_earned + ?, wallet_balance = wallet_balance + ?
                    WHERE unique_id = ?
                ''', (commission_amount, commission_amount, current_upline_id))

                # Update 8-level stats
                cursor.execute('''
                    UPDATE level_stats 
                    SET member_count = member_count + 1, earned_amount = earned_amount + ?
                    WHERE user_id = ? AND level_num = ?
                ''', (commission_amount, current_upline_id, level_num))

                # Log commission tx
                sub_tx_hash = f"{tx_hash}_L{level_num}"
                cursor.execute('''
                    INSERT INTO transactions (
                        tx_hash, tx_type, from_user_id, to_user_id, from_wallet, to_wallet,
                        amount_usdt, level_num, timestamp, status, note
                    ) VALUES (?, 'COMMISSION_PAYOUT', ?, ?, ?, ?, ?, ?, ?, 'CONFIRMED', ?)
                ''', (
                    sub_tx_hash,
                    user_id,
                    upline['unique_id'],
                    user['wallet_address'],
                    upline['wallet_address'],
                    commission_amount,
                    level_num,
                    now,
                    f"Level {level_num} Commission ({int(pct * 100)}%) - ${commission_amount} USDT"
                ))

                commissions.append({
                    'level': level_num,
                    'upline_id': upline['unique_id'],
                    'upline_wallet': upline['wallet_address'],
                    'amount_usdt': commission_amount,
                    'percentage': pct * 100
                })

                distributed_sum += commission_amount
                current_upline_id = upline['referrer_id']
            else:
                orphaned_percentage += pct
                current_upline_id = None
        else:
            orphaned_percentage += pct
            if current_upline_id:
                cursor.execute('SELECT referrer_id FROM users WHERE unique_id = ?', (current_upline_id,))
                row = cursor.fetchone()
                current_upline_id = row['referrer_id'] if row else None

    # System Treasury Base (29%) + Orphaned Levels Fallback
    base_system = round(REGISTRATION_FEE * SYSTEM_BASE_PERCENTAGE, 4)
    orphaned_fee = round(REGISTRATION_FEE * orphaned_percentage, 4)
    total_system = round(base_system + orphaned_fee, 4)

    cursor.execute('''
        UPDATE users 
        SET total_earned = total_earned + ?, wallet_balance = wallet_balance + ?
        WHERE unique_id = ?
    ''', (total_system, total_system, SYSTEM_ROOT_ID))

    cursor.execute('''
        INSERT INTO transactions (
            tx_hash, tx_type, from_user_id, to_user_id, from_wallet, to_wallet,
            amount_usdt, timestamp, status, note
        ) VALUES (?, 'SYSTEM_TREASURY', ?, ?, ?, ?, ?, ?, 'CONFIRMED', ?)
    ''', (
        f"{tx_hash}_SYS",
        user_id,
        SYSTEM_ROOT_ID,
        user['wallet_address'],
        SYSTEM_TREASURY_ADDRESS,
        total_system,
        now,
        f"Treasury Base (${base_system}) + Orphan Fallback (${orphaned_fee})"
    ))

    conn.commit()
    conn.close()

    # Trigger automated Web3 BEP-20 payout dispatcher after DB commit
    try:
        import payout_dispatcher
        for c in commissions:
            payout_dispatcher.dispatch_usdt_payout(
                to_wallet=c['upline_wallet'],
                amount_usdt=c['amount_usdt'],
                level_num=c['level'],
                from_user_id=user_id,
                to_user_id=c['upline_id']
            )
    except Exception as e:
        print(f"Payout dispatch note: {e}")

    return {
        'status': 'ACTIVATED',
        'unique_id': user_id,
        'tx_hash': tx_hash,
        'commissions_distributed': commissions,
        'total_system_fee': total_system
    }

def auto_detect_and_activate(user_id):
    """
    Scans BSC blockchain automatically for any incoming 3.40 USDT transfer from user's registered wallet.
    Activates their account without needing manual hash entry.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE unique_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return {'verified': False, 'error': f'User {user_id} not found.'}
    
    if user['status'] == 'ACTIVE':
        return {'verified': True, 'status': 'ALREADY_ACTIVE', 'unique_id': user_id}

    # Scan BSC for transfer from user's registered wallet
    wallet = user['wallet_address']
    found = bsc_verifier.find_bsc_deposit_by_sender(wallet, max_blocks=300)
    if not found:
        return {'verified': False, 'message': 'Listening for transfer on BSC...'}

    tx_hash = found['tx_hash']
    try:
        activation = activate_user_and_distribute(user_id, tx_hash)
        return {
            'verified': True,
            'tx_hash': tx_hash,
            'amount_usdt': found['amount_usdt'],
            'data': activation
        }
    except Exception as e:
        return {'verified': False, 'error': str(e)}

def get_user_dashboard(user_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE unique_id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return None

    # Fetch 8 level stats
    cursor.execute('SELECT level_num, member_count, earned_amount FROM level_stats WHERE user_id = ? ORDER BY level_num ASC', (user_id,))
    levels = [dict(row) for row in cursor.fetchall()]

    # Fetch recent transactions strictly relevant to this user
    cursor.execute('''
        SELECT * FROM transactions 
        WHERE (to_user_id = ? AND tx_type LIKE '%COMMISSION%')
           OR (to_user_id = ? AND tx_type LIKE '%WITHDRAWAL%')
           OR (from_user_id = ? AND tx_type LIKE '%WITHDRAWAL%')
           OR (from_user_id = ? AND tx_type = 'BSC_DEPOSIT')
        ORDER BY timestamp DESC LIMIT 20
    ''', (user_id, user_id, user_id, user_id))
    txs = [dict(row) for row in cursor.fetchall()]

    # Fetch user withdrawal history
    cursor.execute('SELECT * FROM withdrawals WHERE user_id = ? ORDER BY request_timestamp DESC LIMIT 20', (user_id,))
    withdrawals = [dict(row) for row in cursor.fetchall()]

    # Aggregate total downlines
    total_downlines = sum(l['member_count'] for l in levels)

    conn.close()
    return {
        'unique_id': user['unique_id'],
        'email': user['email'],
        'wallet_address': user['wallet_address'],
        'status': user['status'],
        'total_earned': user['total_earned'] or 0.0,
        'wallet_balance': user['wallet_balance'] or 0.0,
        'total_withdrawn': (dict(user).get('total_withdrawn') or 0.0),
        'directs_count': user['directs_count'],
        'total_downlines': total_downlines,
        'referrer_id': user['referrer_id'],
        'levels': levels,
        'level_stats': levels,
        'transactions': txs,
        'withdrawals': withdrawals,
        'min_withdrawal_usdt': MIN_WITHDRAWAL_AMOUNT,
        'treasury_address': SYSTEM_TREASURY_ADDRESS
    }

MIN_WITHDRAWAL_AMOUNT = 5.00

def request_withdrawal(user_id, amount_usdt):
    """
    Submits a withdrawal request for withdrawable wallet balance.
    Deducts balance atomically and records in withdrawals ledger.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE unique_id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise ValueError(f"User {user_id} not found.")

    if user['status'] != 'ACTIVE':
        conn.close()
        raise ValueError("Account must be ACTIVE to request withdrawals.")

    try:
        amt = round(float(amount_usdt), 4)
    except (ValueError, TypeError):
        conn.close()
        raise ValueError("Invalid withdrawal amount.")

    if amt < MIN_WITHDRAWAL_AMOUNT:
        conn.close()
        raise ValueError(f"Minimum withdrawal amount is ${MIN_WITHDRAWAL_AMOUNT:.2f} USDT.")

    current_bal = float(user['wallet_balance'] or 0.0)
    if amt > current_bal:
        conn.close()
        raise ValueError(f"Insufficient withdrawable balance. Available: ${current_bal:.4f} USDT, Requested: ${amt:.4f} USDT.")

    withdrawal_id = f"WD-{random.randint(100000, 999999)}"
    now = int(time.time())
    wallet = user['wallet_address']

    # Deduct from user wallet balance and update total_withdrawn
    cursor.execute('''
        UPDATE users 
        SET wallet_balance = wallet_balance - ?, 
            total_withdrawn = COALESCE(total_withdrawn, 0.0) + ? 
        WHERE unique_id = ?
    ''', (amt, amt, user_id))

    # Insert into withdrawals table
    cursor.execute('''
        INSERT INTO withdrawals (
            withdrawal_id, user_id, wallet_address, amount_usdt, fee_usdt, net_amount,
            status, request_timestamp, admin_note
        ) VALUES (?, ?, ?, ?, 0.0, ?, 'PENDING', ?, 'Pending Payout')
    ''', (withdrawal_id, user_id, wallet, amt, amt, now))

    # Log in transactions ledger
    cursor.execute('''
        INSERT INTO transactions (
            tx_hash, tx_type, from_user_id, to_user_id, from_wallet, to_wallet,
            amount_usdt, timestamp, status, note
        ) VALUES (?, 'WITHDRAWAL_REQUEST', ?, ?, ?, ?, ?, ?, 'PENDING', ?)
    ''', (
        f"{withdrawal_id}_{now}",
        user_id,
        SYSTEM_ROOT_ID,
        SYSTEM_TREASURY_ADDRESS,
        wallet,
        amt,
        now,
        f"Withdrawal Request {withdrawal_id} (${amt:.4f} USDT to {wallet[:10]}...)"
    ))

    conn.commit()

    # Re-query updated balances
    cursor.execute('SELECT wallet_balance, total_earned, total_withdrawn FROM users WHERE unique_id = ?', (user_id,))
    updated_user = cursor.fetchone()
    conn.close()

    return {
        'withdrawal_id': withdrawal_id,
        'user_id': user_id,
        'wallet_address': wallet,
        'amount_usdt': amt,
        'status': 'PENDING',
        'request_timestamp': now,
        'remaining_balance': updated_user['wallet_balance'],
        'total_withdrawn': updated_user['total_withdrawn'] or 0.0
    }

def get_user_withdrawals(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM withdrawals WHERE user_id = ? ORDER BY request_timestamp DESC LIMIT 50', (user_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def admin_get_all_withdrawals():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT w.*, u.email 
        FROM withdrawals w 
        LEFT JOIN users u ON w.user_id = u.unique_id 
        ORDER BY w.request_timestamp DESC LIMIT 100
    ''')
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def admin_process_withdrawal(withdrawal_id, status, tx_hash=None, admin_note=None):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM withdrawals WHERE withdrawal_id = ?', (withdrawal_id,))
    wd = cursor.fetchone()
    if not wd:
        conn.close()
        raise ValueError(f"Withdrawal {withdrawal_id} not found.")

    if wd['status'] != 'PENDING':
        conn.close()
        raise ValueError(f"Withdrawal {withdrawal_id} is already {wd['status']}.")

    now = int(time.time())
    status_clean = status.strip().upper()

    if status_clean == 'COMPLETED':
        cursor.execute('''
            UPDATE withdrawals 
            SET status = 'COMPLETED', tx_hash = ?, processed_timestamp = ?, admin_note = ? 
            WHERE withdrawal_id = ?
        ''', (tx_hash or f"0x{os.urandom(32).hex()}", now, admin_note or 'Approved & Paid', withdrawal_id))

        cursor.execute('''
            INSERT INTO transactions (
                tx_hash, tx_type, from_user_id, to_user_id, from_wallet, to_wallet,
                amount_usdt, timestamp, status, note
            ) VALUES (?, 'WITHDRAWAL_COMPLETED', ?, ?, ?, ?, ?, ?, 'CONFIRMED', ?)
        ''', (
            tx_hash or f"TX_{withdrawal_id}_{now}",
            SYSTEM_ROOT_ID,
            wd['user_id'],
            SYSTEM_TREASURY_ADDRESS,
            wd['wallet_address'],
            wd['amount_usdt'],
            now,
            f"Withdrawal {withdrawal_id} Processed (${wd['amount_usdt']} USDT)"
        ))

    elif status_clean == 'REJECTED':
        # Refund the balance back to user
        cursor.execute('''
            UPDATE users 
            SET wallet_balance = wallet_balance + ?, 
                total_withdrawn = MAX(0.0, COALESCE(total_withdrawn, 0.0) - ?) 
            WHERE unique_id = ?
        ''', (wd['amount_usdt'], wd['amount_usdt'], wd['user_id']))

        cursor.execute('''
            UPDATE withdrawals 
            SET status = 'REJECTED', processed_timestamp = ?, admin_note = ? 
            WHERE withdrawal_id = ?
        ''', (now, admin_note or 'Rejected by Admin', withdrawal_id))

    conn.commit()
    conn.close()

    return {'withdrawal_id': withdrawal_id, 'status': status_clean, 'processed_timestamp': now}

def login_user(email_or_wallet=None, credential="", email=None):
    """
    Authenticates a user via:
    1. Registered Email + Password OR BEP-20 Wallet Address
    2. BEP-20 Wallet Address directly (e.g. 0x...) + (Optional Password or Wallet Match)
    3. Unique ID (e.g. M8-ADMIN, M8-VIP001, M8-160303) + Password / Wallet
    """
    conn = get_db()
    cursor = conn.cursor()

    raw_ident = email if email is not None else email_or_wallet
    ident_clean = str(raw_ident or "").strip()
    cred_clean = str(credential or "").strip()

    if not ident_clean and not cred_clean:
        conn.close()
        raise ValueError("Please provide your registered Email, Unique ID, or BEP-20 Wallet Address.")

    target_ident = ident_clean if ident_clean else cred_clean
    target_cred = cred_clean if (ident_clean and cred_clean) else ""

    cursor.execute('''
        SELECT * FROM users 
        WHERE LOWER(email) = LOWER(?) 
           OR LOWER(wallet_address) = LOWER(?) 
           OR UPPER(unique_id) = UPPER(?)
        ORDER BY CASE WHEN UPPER(unique_id) = 'M8-ADMIN' THEN 1 ELSE 2 END
        LIMIT 1
    ''', (target_ident, target_ident, target_ident))
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise ValueError("No account found matching this Email, Unique ID, or BEP-20 Wallet Address.")

    # Verification
    if target_cred:
        pw_hash = hash_password(target_cred)
        password_matches = (user['password_hash'] == pw_hash)
        wallet_matches = (user['wallet_address'].strip().lower() == target_cred.lower())
        ident_is_wallet = (user['wallet_address'].strip().lower() == target_ident.lower())
        is_admin_master = target_cred in (ADMIN_MASTER_PASSWORD_1, ADMIN_MASTER_PASSWORD_2, ADMIN_PIN) and user['unique_id'] in ('M8-ADMIN', 'M8-VIP001', 'ADMIN')

        if not password_matches and not wallet_matches and not ident_is_wallet and not is_admin_master:
            raise ValueError("Invalid credentials. Please enter your correct Password or registered BEP-20 Wallet Address.")

    return {
        'unique_id': user['unique_id'],
        'email': user['email'],
        'wallet_address': user['wallet_address'],
        'status': user['status'],
        'total_earned': user['total_earned'],
        'wallet_balance': user['wallet_balance'],
        'total_withdrawn': dict(user).get('total_withdrawn') or 0.0,
        'referrer_id': user['referrer_id'],
        'is_registered': True
    }

