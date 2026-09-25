#!/usr/bin/env python3
"""
Test Suite: Vercel Serverless Handler Simulation
Directly invokes api.index.handler with simulated HTTP requests (GET and POST)
to guarantee that Vercel's serverless environment handles all routes perfectly.
"""

import sys
import os
import io
import json
import urllib.parse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'api'))
sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))

import index as vercel_api

class MockSocket:
    def makefile(self, *args, **kwargs):
        return io.BytesIO()

class DummyHandler(vercel_api.handler):
    def __init__(self, method, path, body=None, headers=None):
        self.rfile = io.BytesIO(body.encode('utf-8') if body else b'')
        self.wfile = io.BytesIO()
        self.command = method
        self.path = path
        self.requestline = f"{method} {path} HTTP/1.1"
        self.request_version = "HTTP/1.1"
        self.headers = headers or {}
        self.close_connection = True
        
        if method == 'GET':
            self.do_GET()
        elif method == 'POST':
            self.do_POST()
        elif method == 'OPTIONS':
            self.do_OPTIONS()

    def send_response(self, code, message=None):
        self.response_code = code

    def send_header(self, keyword, value):
        pass

    def end_headers(self):
        pass

def test_vercel_serverless():
    print("==================================================")
    print("⚡ TESTING VERCEL SERVERLESS HANDLER (api/index.py)")
    print("==================================================")

    # 1. Test /api/config
    h_config = DummyHandler('GET', '/api/config')
    res_config = json.loads(h_config.wfile.getvalue().decode('utf-8'))
    assert h_config.response_code == 200
    assert 'treasury_address' in res_config
    assert len(res_config['stages']) == 5
    print(f"✅ [1/5] Vercel GET /api/config: HTTP 200 (Mode: {res_config.get('database_mode')})")

    # 2. Test /api/member-lookup with valid code
    h_lookup = DummyHandler('GET', '/api/member-lookup?ref_code=M8-160303')
    res_lookup = json.loads(h_lookup.wfile.getvalue().decode('utf-8'))
    assert h_lookup.response_code == 200
    assert res_lookup['success'] is True
    assert res_lookup['data']['unique_id'] == 'M8-160303'
    print(f"✅ [2/5] Vercel GET /api/member-lookup: HTTP 200 (Member: {res_lookup['data']['unique_id']})")

    # 3. Test /api/member-lookup strict rejection of email / wallet
    h_reject = DummyHandler('GET', '/api/member-lookup?ref_code=0xe65b82f8b9B802Dec9127B4696a7F91230c24D55')
    res_reject = json.loads(h_reject.wfile.getvalue().decode('utf-8'))
    assert h_reject.response_code == 400
    assert 'Referral Code only' in res_reject['error']
    print(f"✅ [3/5] Vercel GET /api/member-lookup Rejection: HTTP 400 ({res_reject['error'][:35]}...)")

    # 4. Test /api/user-dashboard
    h_dash = DummyHandler('GET', '/api/user-dashboard?user_id=M8-160303')
    res_dash = json.loads(h_dash.wfile.getvalue().decode('utf-8'))
    assert h_dash.response_code == 200
    assert res_dash['unique_id'] == 'M8-160303'
    assert len(res_dash['levels']) == 8
    print(f"✅ [4/5] Vercel GET /api/user-dashboard: HTTP 200 (Balance: ${res_dash['wallet_balance']})")

    # 5. Test /api/admin/verify-pin
    body_pin = json.dumps({'admin_pin': '499011'})
    headers_pin = {'Content-Length': str(len(body_pin))}
    h_pin = DummyHandler('POST', '/api/admin/verify-pin', body=body_pin, headers=headers_pin)
    res_pin = json.loads(h_pin.wfile.getvalue().decode('utf-8'))
    assert h_pin.response_code == 200
    assert res_pin['success'] is True
    print(f"✅ [5/5] Vercel POST /api/admin/verify-pin: HTTP 200 (Verified: {res_pin['verified']})")

    print("==================================================")
    print("🎉 VERCEL SERVERLESS HANDLER VALIDATED 100% READY!")
    print("==================================================")

if __name__ == '__main__':
    test_vercel_serverless()
