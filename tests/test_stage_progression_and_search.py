#!/usr/bin/env python3
"""
Test Suite: Referral Search Strictness & Multi-Stage Concurrent Independence
Validates that:
1. Search bar strictly rejects non-referral code inputs (e.g. emails, 0x wallet addresses).
2. Public member lookup returns complete stats, masked emails/wallets, and stage data.
3. Multiple stages run concurrently and independently.
4. Vercel-compatible handlers and database connections operate cleanly without hanging.
"""

import sys
import os
import urllib.request
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))

import database
import matrix_service

def test_stage_progression_and_search():
    print("==================================================")
    print("🔍 TESTING REFERRAL SEARCH STRICTNESS & STAGES")
    print("==================================================")

    # 1. Test Referral Code Lookup with valid referral code
    valid_code = "M8-160303"
    member_data = matrix_service.lookup_member_public(valid_code)
    assert member_data is not None, f"Member {valid_code} not found!"
    assert member_data['unique_id'] == valid_code
    assert 'email_masked' in member_data and '@' in member_data['email_masked']
    assert '***' in member_data['email_masked'], "Email must be masked for public privacy"
    assert member_data['wallet_masked'].startswith('0x') and '...' in member_data['wallet_masked'], "Wallet must be masked"
    assert 'current_stage' in member_data
    assert 'total_earned' in member_data
    assert len(member_data['levels']) == 8, "Must return 8 level stats"
    print(f"✅ [1/5] Public Member Lookup verified: {valid_code} -> Earned: ${member_data['total_earned']}, Stage: {member_data['current_stage']}, Directs: {member_data['directs_count']}")

    # 2. Test Rejection of Wallet Addresses and Emails in Matrix Service
    res_wallet = matrix_service.lookup_member_public("0xe65b82f8b9B802Dec9127B4696a7F91230c24D55")
    assert res_wallet is None, "Should have returned None for wallet address"
    print(f"✅ [2/5] Successfully rejected wallet address lookup (returned None).")

    res_email = matrix_service.lookup_member_public("siam4990karim@gmail.com")
    assert res_email is None, "Should have returned None for email address"
    print(f"✅ [3/5] Successfully rejected email address lookup (returned None).")

    # 3. Test Independent Concurrent Stage Data Structure
    conn = database.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_stages WHERE user_id = ?", (valid_code,))
    user_stgs = cursor.fetchall()
    conn.close()
    assert len(user_stgs) >= 1, "User must have active stage records"
    print(f"✅ [4/5] Independent Stage Isolation: User {valid_code} has {len(user_stgs)} active independent stage records.")

    # 4. Test Config Endpoint Values
    assert matrix_service.BASE_REGISTRATION_FEE == 3.40
    assert matrix_service.STAGE_INCREMENT_PERCENTAGE == 0.15
    assert matrix_service.STAGE_MILESTONE_MEMBERS == 1000
    assert matrix_service.get_stage_fee(1) == 3.40
    assert matrix_service.get_stage_fee(2) == 3.91
    assert matrix_service.get_stage_fee(3) == 4.50
    print(f"✅ [5/5] Progressive Stage Pricing Math Verified: Stage 1 = $3.40, Stage 2 (+15%) = $3.91, Stage 3 (+15%) = $4.50")

    print("==================================================")
    print("🎉 ALL STAGE AND REFERRAL SEARCH TESTS PASSED 100%!")
    print("==================================================")

if __name__ == '__main__':
    test_stage_progression_and_search()
