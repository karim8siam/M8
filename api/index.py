"""
Matrix8 Vercel Serverless API & Static Gateway
Handles /api/* routes and serves frontend assets seamlessly on Vercel.
"""

import http.server
import os
import json
import urllib.parse
import sys

# Ensure backend directory is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))

import database
import matrix_service
import bsc_verifier

# Initialize database (creates tables if connecting to Neon PostgreSQL for first time)
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
    # GET ROUTES (STATIC ASSETS + API)
    # --------------------------------------------------------------------------
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        req_path = self.headers.get('x-matched-path') or parsed.path

        # 1. API: GET /api/config
        if 'config' in req_path:
            self.send_json_response({
                'treasury_address': database.SYSTEM_TREASURY_ADDRESS,
                'usdt_contract': bsc_verifier.BSC_USDT_CONTRACT,
                'registration_fee_usdt': matrix_service.REGISTRATION_FEE,
                'min_withdrawal_usdt': matrix_service.MIN_WITHDRAWAL_AMOUNT,
                'levels_count': 8,
                'database_mode': 'Neon PostgreSQL' if database.is_postgres() else 'SQLite'
            })
            return

        # 2. API: GET /api/user-dashboard
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

        # 3. API: GET /api/auto-check-deposit
        elif 'auto-check-deposit' in req_path:
            user_id = query.get('user_id', [None])[0]
            if not user_id:
                self.send_json_response({'verified': False, 'error': 'Missing user_id'}, status=400)
                return
            
            result = matrix_service.auto_detect_and_activate(user_id)
            self.send_json_response(result)
            return

        # 4. API: GET /api/withdrawals
        elif 'withdrawals' in req_path and 'admin' not in req_path:
            user_id = query.get('user_id', [None])[0]
            if not user_id:
                self.send_json_response({'error': 'Missing user_id'}, status=400)
                return
            wds = matrix_service.get_user_withdrawals(user_id)
            self.send_json_response(wds)
            return

        # 5. API: GET /api/admin/withdrawals
        elif 'admin/withdrawals' in req_path or 'admin_withdrawals' in req_path:
            admin_pin = self.headers.get('X-Admin-Pin') or query.get('admin_pin', [None])[0]
            if not matrix_service.verify_admin_pin(admin_pin):
                self.send_json_response({'error': 'Unauthorized: Valid Admin PIN required.'}, status=401)
                return
            wds = matrix_service.admin_get_all_withdrawals()
            self.send_json_response(wds)
            return

        # 6. Static / Fallback serving
        elif req_path.startswith('/css/') or req_path.startswith('/js/'):
            file_rel = req_path.lstrip('/')
            file_path = os.path.join(BASE_DIR, file_rel)
            if os.path.exists(file_path):
                mime = 'text/css' if file_path.endswith('.css') else 'application/javascript'
                with open(file_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', f'{mime}; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        # Fallback to index.html
        index_path = os.path.join(BASE_DIR, 'index.html')
        if os.path.exists(index_path):
            with open(index_path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_json_response({'error': f'Route not found: {parsed.path}'}, status=404)

    # --------------------------------------------------------------------------
    # POST ROUTES
    # --------------------------------------------------------------------------
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        body = self.read_json_body()
        req_path = self.headers.get('x-matched-path') or parsed.path

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

        else:
            self.send_json_response({'error': f'Route not found: {parsed.path}'}, status=404)
