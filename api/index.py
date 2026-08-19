"""
Matrix8 Vercel Serverless REST API
Handles all /api/* backend routes and database operations for Matrix8 on Vercel.
"""

import http.server
import os
import json
import urllib.parse
import sys
import time

# Add backend directory to sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))

import database
import matrix_service
import bsc_verifier

# Initialize database on startup
try:
    database.init_db()
except Exception as e:
    print("Database init error:", e)

class handler(http.server.BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Pin, X-Admin-Token')
        self.end_headers()

    def send_json_response(self, data, status=200):
        response_bytes = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Pin, X-Admin-Token')
        self.end_headers()
        self.wfile.write(response_bytes)

    def read_json_body(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                return {}
            body = self.rfile.read(content_length).decode('utf-8')
            return json.loads(body)
        except Exception:
            return {}

    # --------------------------------------------------------------------------
    # GET ROUTES (/api/*)
    # --------------------------------------------------------------------------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        req_path = parsed.path

        # GET /api/config
        if req_path.endswith('/config') or 'config' in req_path:
            self.send_json_response({
                'treasury_address': database.SYSTEM_TREASURY_ADDRESS,
                'usdt_contract': bsc_verifier.BSC_USDT_CONTRACT,
                'registration_fee_usdt': matrix_service.REGISTRATION_FEE,
                'min_withdrawal_usdt': matrix_service.MIN_WITHDRAWAL_AMOUNT,
                'levels_count': 8,
                'database_mode': 'Neon PostgreSQL' if database.is_postgres() else 'SQLite'
            })
            return

        # GET /api/user-dashboard
        elif 'user-dashboard' in req_path:
            user_id = query.get('user_id', [None])[0]
            if not user_id:
                user_id = database.SYSTEM_ROOT_ID
            
            dashboard = matrix_service.get_user_dashboard(user_id)
            if dashboard:
                self.send_json_response(dashboard)
            else:
                self.send_json_response({'error': 'User not found'}, status=404)
            return

        # GET /api/auto-check-deposit
        elif 'auto-check-deposit' in req_path:
            user_id = query.get('user_id', [None])[0]
            if not user_id:
                self.send_json_response({'verified': False, 'error': 'Missing user_id'}, status=400)
                return
            
            result = matrix_service.auto_detect_and_activate(user_id)
            self.send_json_response(result)
            return

        # GET /api/withdrawals
        elif 'withdrawals' in req_path and 'admin' not in req_path:
            user_id = query.get('user_id', [None])[0]
            if not user_id:
                self.send_json_response({'error': 'Missing user_id'}, status=400)
                return
            wds = matrix_service.get_user_withdrawals(user_id)
            self.send_json_response(wds)
            return

        # GET /api/admin/withdrawals
        elif 'admin' in req_path and 'withdrawals' in req_path:
            admin_pin = self.headers.get('X-Admin-Pin') or query.get('admin_pin', [None])[0]
            if not matrix_service.verify_admin_pin(admin_pin):
                self.send_json_response({'error': 'Unauthorized: Valid Admin PIN required.'}, status=401)
                return
            wds = matrix_service.admin_get_all_withdrawals()
            self.send_json_response(wds)
            return

        else:
            self.send_json_response({'error': f'Route not found: {parsed.path}'}, status=404)

    # --------------------------------------------------------------------------
    # POST ROUTES (/api/*)
    # --------------------------------------------------------------------------
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        body = self.read_json_body()
        req_path = parsed.path

        # POST /api/register
        if 'register' in req_path:
            email = body.get('email', '')
            password = body.get('password', '')
            sponsor_id = body.get('sponsor_id', '')
            wallet_address = body.get('wallet_address', '')
            telegram = body.get('telegram_handle', '')

            try:
                result = matrix_service.register_user(
                    email=email,
                    password=password,
                    sponsor_id=sponsor_id,
                    wallet_address=wallet_address,
                    telegram_handle=telegram
                )
                self.send_json_response({'success': True, 'data': result})
            except Exception as e:
                self.send_json_response({'success': False, 'error': str(e)}, status=400)
            return

        # POST /api/verify-deposit
        elif 'verify-deposit' in req_path:
            user_id = body.get('user_id', '')
            tx_hash = body.get('tx_hash', '').strip()
            is_mock_test = body.get('is_mock_test', False)

            if not user_id:
                self.send_json_response({'success': False, 'error': 'Missing user_id'}, status=400)
                return

            if not tx_hash:
                self.send_json_response({'success': False, 'error': 'Please provide a valid BSC Transaction Hash (0x...)'}, status=400)
                return

            if not is_mock_test:
                conn = database.get_db()
                cursor = conn.cursor()
                cursor.execute('SELECT wallet_address FROM users WHERE unique_id = ?', (user_id,))
                user_row = cursor.fetchone()
                conn.close()

                expected_sender = user_row['wallet_address'] if user_row else None
                verification = bsc_verifier.verify_bsc_deposit(tx_hash, expected_sender_wallet=expected_sender)

                if not verification.get('verified'):
                    self.send_json_response({
                        'success': False,
                        'error': verification.get('error', 'On-chain verification failed.')
                    }, status=400)
                    return

            try:
                activation = matrix_service.activate_user_and_distribute(user_id, tx_hash)
                self.send_json_response({'success': True, 'data': activation})
            except Exception as e:
                self.send_json_response({'success': False, 'error': str(e)}, status=400)
            return

        # POST /api/login
        elif 'login' in req_path:
            email = body.get('email', '') or body.get('email_or_wallet', '') or body.get('wallet_address', '')
            credential = body.get('credential', '') or body.get('password', '')

            try:
                user = matrix_service.login_user(email_or_wallet=email, credential=credential)
                self.send_json_response({'success': True, 'data': user})
            except Exception as e:
                self.send_json_response({'success': False, 'error': str(e)}, status=400)
            return

        # POST /api/withdraw
        elif req_path.endswith('withdraw') or 'api/withdraw' in req_path:
            user_id = body.get('user_id', '')
            amount = body.get('amount', 0.0)

            if not user_id:
                self.send_json_response({'success': False, 'error': 'Missing user_id'}, status=400)
                return

            try:
                res = matrix_service.request_withdrawal(user_id=user_id, amount_usdt=amount)
                self.send_json_response({'success': True, 'data': res})
            except Exception as e:
                self.send_json_response({'success': False, 'error': str(e)}, status=400)
            return

        # POST /api/admin/verify-4factor
        elif 'verify-4factor' in req_path:
            pass1 = body.get('pass1', '') or body.get('password_1', '')
            pass2 = body.get('pass2', '') or body.get('password_2', '')
            pin = body.get('pin', '')
            fav = body.get('fav', '')

            ok, token_or_err = matrix_service.verify_admin_4factor_credentials(pass1, pass2, pin, fav)
            if ok:
                self.send_json_response({'success': True, 'token': token_or_err})
            else:
                self.send_json_response({'success': False, 'error': token_or_err}, status=401)
            return

        # POST /api/admin/verify-pin
        elif 'verify-pin' in req_path:
            pin = body.get('admin_pin', '')
            if matrix_service.verify_admin_pin(pin):
                self.send_json_response({'success': True, 'verified': True})
            else:
                self.send_json_response({'success': False, 'error': 'Invalid Admin PIN'}, status=401)
            return

        # POST /api/admin/process-withdrawal
        elif 'process-withdrawal' in req_path or 'process-payout' in req_path:
            admin_pin = self.headers.get('X-Admin-Pin') or body.get('admin_pin')
            if not matrix_service.verify_admin_pin(admin_pin):
                self.send_json_response({'success': False, 'error': 'Unauthorized: Valid Admin PIN required.'}, status=401)
                return

            withdrawal_id = body.get('withdrawal_id', '')
            status = body.get('status', '') or body.get('action', 'COMPLETED')
            tx_hash = body.get('tx_hash', '')

            try:
                res = matrix_service.admin_process_withdrawal(
                    withdrawal_id=withdrawal_id,
                    action=status,
                    tx_hash=tx_hash
                )
                self.send_json_response({'success': True, 'data': res})
            except Exception as e:
                self.send_json_response({'success': False, 'error': str(e)}, status=400)
            return

        # POST /api/admin/migrate-data
        elif 'migrate-data' in req_path:
            admin_pin = self.headers.get('X-Admin-Pin') or body.get('admin_pin', '')
            if not matrix_service.verify_admin_pin(admin_pin):
                self.send_json_response({'success': False, 'error': 'Unauthorized: Admin PIN required.'}, status=401)
                return

            data = body.get('data', {})
            try:
                conn = database.get_db()
                cursor = conn.cursor()

                migrated_counts = {'users': 0, 'level_stats': 0, 'withdrawals': 0, 'transactions': 0}

                # 1. Users
                for u in data.get('users', []):
                    cursor.execute('SELECT unique_id FROM users WHERE unique_id = ?', (u['unique_id'],))
                    if not cursor.fetchone():
                        cursor.execute('INSERT INTO users (unique_id, email, password_hash, wallet_address, referrer_id, telegram_handle, status, join_timestamp, total_earned, wallet_balance, total_withdrawn, directs_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (
                            u['unique_id'], u['email'], u['password_hash'], u['wallet_address'],
                            u.get('referrer_id'), u.get('telegram_handle', ''), u.get('status', 'ACTIVE'),
                            u.get('join_timestamp', int(time.time())), u.get('total_earned', 0.0),
                            u.get('wallet_balance', 0.0), u.get('total_withdrawn', 0.0), u.get('directs_count', 0)
                        ))
                    else:
                        cursor.execute('UPDATE users SET email = ?, password_hash = ?, wallet_address = ?, referrer_id = ?, telegram_handle = ?, status = ?, total_earned = ?, wallet_balance = ?, total_withdrawn = ?, directs_count = ? WHERE unique_id = ?', (
                            u['email'], u['password_hash'], u['wallet_address'], u.get('referrer_id'),
                            u.get('telegram_handle', ''), u.get('status', 'ACTIVE'), u.get('total_earned', 0.0),
                            u.get('wallet_balance', 0.0), u.get('total_withdrawn', 0.0), u.get('directs_count', 0),
                            u['unique_id']
                        ))
                    migrated_counts['users'] += 1

                # 2. Level Stats
                for ls in data.get('level_stats', []):
                    cursor.execute('SELECT user_id FROM level_stats WHERE user_id = ? AND level_num = ?', (ls['user_id'], ls['level_num']))
                    if not cursor.fetchone():
                        cursor.execute('INSERT INTO level_stats (user_id, level_num, member_count, earned_amount) VALUES (?, ?, ?, ?)', (ls['user_id'], ls['level_num'], ls.get('member_count', 0), ls.get('earned_amount', 0.0)))
                    else:
                        cursor.execute('UPDATE level_stats SET member_count = ?, earned_amount = ? WHERE user_id = ? AND level_num = ?', (ls.get('member_count', 0), ls.get('earned_amount', 0.0), ls['user_id'], ls['level_num']))
                    migrated_counts['level_stats'] += 1

                # 3. Withdrawals
                for w in data.get('withdrawals', []):
                    cursor.execute('SELECT withdrawal_id FROM withdrawals WHERE withdrawal_id = ?', (w['withdrawal_id'],))
                    if not cursor.fetchone():
                        cursor.execute('INSERT INTO withdrawals (withdrawal_id, user_id, wallet_address, amount_usdt, fee_usdt, net_amount, status, tx_hash, request_timestamp, processed_timestamp, admin_note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (
                            w['withdrawal_id'], w['user_id'], w.get('wallet_address') or w.get('target_wallet', ''),
                            w.get('amount_usdt', 0.0), w.get('fee_usdt', 0.0), w.get('net_amount', 0.0),
                            w.get('status', 'PENDING'), w.get('tx_hash', ''), w.get('request_timestamp', int(time.time())),
                            w.get('processed_timestamp'), w.get('admin_note') or w.get('admin_notes', '')
                        ))
                        migrated_counts['withdrawals'] += 1

                # 4. Transactions
                for tx in data.get('transactions', []):
                    if tx.get('tx_hash'):
                        cursor.execute('SELECT tx_hash FROM transactions WHERE tx_hash = ?', (tx['tx_hash'],))
                        if not cursor.fetchone():
                            cursor.execute('INSERT INTO transactions (tx_hash, tx_type, from_user_id, to_user_id, from_wallet, to_wallet, amount_usdt, level_num, timestamp, status, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (
                                tx['tx_hash'], tx.get('tx_type', ''), tx.get('from_user_id'),
                                tx.get('to_user_id'), tx.get('from_wallet'), tx.get('to_wallet'),
                                tx.get('amount_usdt', 0.0), tx.get('level_num'), tx.get('timestamp', int(time.time())),
                                tx.get('status', 'CONFIRMED'), tx.get('note')
                            ))
                            migrated_counts['transactions'] += 1

                conn.commit()
                conn.close()

                self.send_json_response({'success': True, 'migrated': migrated_counts})
            except Exception as e:
                self.send_json_response({'success': False, 'error': f'Migration error: {str(e)}'}, status=500)
            return

        else:
            self.send_json_response({'error': f'Route not found: {parsed.path}'}, status=404)
