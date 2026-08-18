"""
Authentication & Login Test Suite for Matrix8
Tests Login with Email + Password, Login with Email + BEP-20 Wallet, and Security Boundaries.
"""

import sys
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))

import database
import matrix_service

def test_auth_system():
    print("==================================================")
    print("🔐 TESTING MEMBER AUTHENTICATION & LOGIN SYSTEM")
    print("==================================================")

    database.init_db()

    test_email = f"crypto_trader_{int(time.time())}@gmail.com"
    test_password = "SecurePassword@2026"
    test_wallet = f"0x{os.urandom(20).hex()}"
    test_sponsor = "M8-ADMIN"

    # 1. Register new member
    reg_user = matrix_service.register_user(
        email=test_email,
        password=test_password,
        sponsor_id=test_sponsor,
        wallet_address=test_wallet,
        telegram_handle="@real_tester"
    )
    user_id = reg_user['unique_id']
    print(f"✅ [1/5] Registered Member: {user_id} ({test_email})")

    # 2. Test Login with Email + Password
    login_pw = matrix_service.login_user(test_email, test_password)
    assert login_pw['unique_id'] == user_id, f"Expected {user_id}, got {login_pw['unique_id']}"
    assert login_pw['email'] == test_email, "Email mismatch"
    print(f"✅ [2/5] Login via Email + Password: Succeeded for {login_pw['unique_id']}")

    # 3. Test Login with Email + BEP-20 Wallet Address
    login_wallet = matrix_service.login_user(test_email, test_wallet)
    assert login_wallet['unique_id'] == user_id, f"Expected {user_id}, got {login_wallet['unique_id']}"
    print(f"✅ [3/5] Login via Email + BEP-20 Address: Succeeded for {login_wallet['unique_id']}")

    # 4. Test Login with Wrong Password/Credential (Should Fail)
    try:
        matrix_service.login_user(test_email, "WrongPassword123")
        assert False, "Should have raised ValueError for wrong password"
    except ValueError as e:
        print(f"✅ [4/5] Invalid Credential Protection: Successfully rejected wrong password ({e})")

    # 5. Test Login with Non-existent Email (Should Fail)
    try:
        matrix_service.login_user("nobody_exists@gmail.com", test_password)
        assert False, "Should have raised ValueError for unknown email"
    except ValueError as e:
        print(f"✅ [5/5] Unknown User Protection: Successfully rejected non-existent email ({e})")

    print("==================================================")
    print("🎉 ALL 5 AUTHENTICATION TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == '__main__':
    test_auth_system()
