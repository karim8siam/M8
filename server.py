"""
Matrix8 Production HTTP & REST API Server
Binance Smart Chain (BEP-20) 8-Level Web3 Digital Marketing Platform.
"""

import http.server
import socketserver
import os
import json
import urllib.parse
import sys

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))

import database
import matrix_service
import bsc_verifier

# Initialize SQLite database
database.init_db()

PORT = 8080

class Matrix8RequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith('/api/'):
            self.handle_api_get(parsed)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith('/api/'):
            self.handle_api_post(parsed)
        else:
            self.send_error(404, "Endpoint Not Found")

    def read_json_body(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                return {}
            body = self.rfile.read(content_length).decode('utf-8')
            return json.loads(body)
        except Exception:
            return {}

    def send_json_response(self, data, status=200):
        response_bytes = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    # --------------------------------------------------------------------------
    # API GET HANDLERS
    # --------------------------------------------------------------------------
    def handle_api_get(self, parsed):
        query = urllib.parse.parse_qs(parsed.query)

        # GET /api/config
        if parsed.path == '/api/config':
            self.send_json_response({
                'treasury_address': database.SYSTEM_TREASURY_ADDRESS,
                'usdt_contract': bsc_verifier.BSC_USDT_CONTRACT,
                'registration_fee_usdt': matrix_service.REGISTRATION_FEE,
                'min_withdrawal_usdt': matrix_service.MIN_WITHDRAWAL_AMOUNT,
                'levels_count': 8
            })
            return

        # GET /api/user-dashboard?user_id=...
        elif parsed.path == '/api/user-dashboard':
            user_id = query.get('user_id', [None])[0]
            if not user_id:
                user_id = database.SYSTEM_ROOT_ID
            
            dashboard = matrix_service.get_user_dashboard(user_id)
            if dashboard:
                self.send_json_response(dashboard)
            else:
                self.send_json_response({'error': 'User not found'}, status=404)
            return

        # GET /api/auto-check-deposit?user_id=...
        elif parsed.path == '/api/auto-check-deposit':
            user_id = query.get('user_id', [None])[0]
            if not user_id:
                self.send_json_response({'verified': False, 'error': 'Missing user_id'}, status=400)
                return
            
            result = matrix_service.auto_detect_and_activate(user_id)
            self.send_json_response(result)
            return

        # GET /api/withdrawals?user_id=...
        elif parsed.path == '/api/withdrawals':
            user_id = query.get('user_id', [None])[0]
            if not user_id:
                self.send_json_response({'error': 'Missing user_id'}, status=400)
                return
            wds = matrix_service.get_user_withdrawals(user_id)
            self.send_json_response(wds)
            return

        # GET /api/admin/withdrawals (PROTECTED BY ADMIN PIN)
        elif parsed.path == '/api/admin/withdrawals':
            admin_pin = self.headers.get('X-Admin-Pin') or query.get('admin_pin', [None])[0]
            if not matrix_service.verify_admin_pin(admin_pin):
                self.send_json_response({'error': 'Unauthorized: Valid Admin PIN required.'}, status=401)
                return
            wds = matrix_service.admin_get_all_withdrawals()
            self.send_json_response(wds)
            return

        else:
            self.send_json_response({'error': 'API Route Not Found'}, status=404)

    # --------------------------------------------------------------------------
    # API POST HANDLERS
    # --------------------------------------------------------------------------
    def handle_api_post(self, parsed):
        body = self.read_json_body()

        # POST /api/register
        if parsed.path == '/api/register':
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
        elif parsed.path == '/api/verify-deposit':
            user_id = body.get('user_id', '')
            tx_hash = body.get('tx_hash', '').strip()
            is_mock_test = body.get('is_mock_test', False)

            if not user_id:
                self.send_json_response({'success': False, 'error': 'Missing user_id'}, status=400)
                return

            if not tx_hash:
                self.send_json_response({'success': False, 'error': 'Please provide a valid BSC Transaction Hash (0x...)'}, status=400)
                return

            # Check on-chain if not mock test
            if not is_mock_test:
                # Fetch user wallet to match sender
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
        # POST /api/login
        elif parsed.path == '/api/login':
            email = body.get('email', '') or body.get('email_or_wallet', '') or body.get('wallet_address', '')
            credential = body.get('credential', '') or body.get('password', '')

            try:
                user = matrix_service.login_user(email_or_wallet=email, credential=credential)
                self.send_json_response({'success': True, 'data': user})
            except Exception as e:
                self.send_json_response({'success': False, 'error': str(e)}, status=400)
            return

        # POST /api/withdraw
        elif parsed.path == '/api/withdraw':
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

        # POST /api/admin/verify-4factor (MASTER 4-FACTOR VAULT GATE)
        elif parsed.path == '/api/admin/verify-4factor':
            pass1 = body.get('pass1', '')
            pass2 = body.get('pass2', '')
            pin = body.get('pin', '')
            fav = body.get('fav', '')

            ok, token_or_err = matrix_service.verify_admin_4factor_credentials(pass1, pass2, pin, fav)
            if ok:
                self.send_json_response({'success': True, 'token': token_or_err})
            else:
                self.send_json_response({'success': False, 'error': token_or_err}, status=401)
            return

        # POST /api/admin/verify-pin
        elif parsed.path == '/api/admin/verify-pin':
            pin = body.get('admin_pin', '')
            if matrix_service.verify_admin_pin(pin):
                self.send_json_response({'success': True, 'verified': True})
            else:
                self.send_json_response({'success': False, 'error': 'Invalid Admin PIN'}, status=401)
            return

        # POST /api/admin/process-withdrawal (PROTECTED BY ADMIN PIN)
        elif parsed.path == '/api/admin/process-withdrawal':
            admin_pin = self.headers.get('X-Admin-Pin') or body.get('admin_pin')
            if not matrix_service.verify_admin_pin(admin_pin):
                self.send_json_response({'success': False, 'error': 'Unauthorized: Valid Admin PIN required.'}, status=401)
                return

            withdrawal_id = body.get('withdrawal_id', '')
            status = body.get('status', 'COMPLETED')
            tx_hash = body.get('tx_hash', None)
            admin_note = body.get('admin_note', None)

            if not withdrawal_id:
                self.send_json_response({'success': False, 'error': 'Missing withdrawal_id'}, status=400)
                return

            try:
                res = matrix_service.admin_process_withdrawal(
                    withdrawal_id=withdrawal_id,
                    status=status,
                    tx_hash=tx_hash,
                    admin_note=admin_note
                )
                self.send_json_response({'success': True, 'data': res})
            except Exception as e:
                self.send_json_response({'success': False, 'error': str(e)}, status=400)
            return

        else:
            self.send_json_response({'error': 'API Route Not Found'}, status=404)

def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Matrix8RequestHandler) as httpd:
        print(f"Matrix8 BEP-20 Backend listening on port {PORT}...")
        httpd.serve_forever()

if __name__ == '__main__':
    run_server()
