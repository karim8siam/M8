"""
Automated Test Suite for Option 2: Dashboard Balance & 1-Click Withdrawals
"""

import sys
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))

import database
import matrix_service

def test_full_withdrawal_cycle():
    print("==================================================")
    print("🧪 TESTING OPTION 2: DASHBOARD BALANCE & WITHDRAWALS")
    print("==================================================")

    database.init_db()

    sponsor_id = 'M8-160303'
    conn = database.get_db()
    conn.cursor().execute('UPDATE users SET wallet_balance = 0.7140, total_withdrawn = 0.0 WHERE unique_id = ?', (sponsor_id,))
    conn.commit()
    conn.close()

    dashboard_before = matrix_service.get_user_dashboard(sponsor_id)
    initial_balance = dashboard_before['wallet_balance']
    print(f"1. Initial Sponsor ({sponsor_id}) Available Balance: ${initial_balance:.4f} USDT")

    # Step 1: Submit a withdrawal request of $0.50 USDT
    test_amount = 0.50
    print(f"2. Submitting withdrawal request for ${test_amount:.2f} USDT...")
    wd_res = matrix_service.request_withdrawal(sponsor_id, test_amount)
    wd_id = wd_res['withdrawal_id']
    print(f"   ✅ Created Withdrawal: {wd_id}, Remaining Balance: ${wd_res['remaining_balance']:.4f} USDT")

    assert wd_res['status'] == 'PENDING'
    assert round(wd_res['remaining_balance'] + test_amount, 4) == round(initial_balance, 4)

    # Step 2: Test overdraw protection
    print("3. Testing Overdraw Protection (attempting to withdraw $9999.00)...")
    try:
        matrix_service.request_withdrawal(sponsor_id, 9999.0)
        print("   ❌ Error: Overdraw was allowed!")
        sys.exit(1)
    except ValueError as e:
        print(f"   ✅ Overdraw successfully blocked: {e}")

    # Step 3: Check user withdrawal history
    wds = matrix_service.get_user_withdrawals(sponsor_id)
    assert any(w['withdrawal_id'] == wd_id for w in wds)
    print(f"   ✅ Withdrawal {wd_id} successfully listed in user history!")

    # Step 4: Test Admin Approval
    print(f"4. Testing Admin Payout Approval for {wd_id}...")
    mock_payout_hash = f"0xmock{os.urandom(28).hex()}"
    proc_res = matrix_service.admin_process_withdrawal(wd_id, 'COMPLETED', tx_hash=mock_payout_hash, admin_note='Verified BSC Payout')
    assert proc_res['status'] == 'COMPLETED'
    print(f"   ✅ Admin marked {wd_id} as COMPLETED with Tx: {mock_payout_hash[:16]}...")

    # Step 5: Test Refund on Reject
    print("5. Testing Refund Logic (Create new WD -> Reject & Refund)...")
    # Add temporary commission so user has balance >= 0.50
    conn = database.get_db()
    conn.cursor().execute('UPDATE users SET wallet_balance = wallet_balance + 1.0 WHERE unique_id = ?', (sponsor_id,))
    conn.commit()
    conn.close()

    wd_res_2 = matrix_service.request_withdrawal(sponsor_id, 0.50)
    wd_id_2 = wd_res_2['withdrawal_id']
    bal_after_wd2 = wd_res_2['remaining_balance']

    matrix_service.admin_process_withdrawal(wd_id_2, 'REJECTED', admin_note='Incorrect Wallet Info')
    dashboard_refunded = matrix_service.get_user_dashboard(sponsor_id)
    assert round(dashboard_refunded['wallet_balance'], 4) == round(bal_after_wd2 + 0.50, 4)
    print(f"   ✅ Rejection successfully refunded $0.50 USDT back to user balance (${dashboard_refunded['wallet_balance']:.4f} USDT)")

    print("==================================================")
    print("🎉 ALL OPTION 2 WITHDRAWAL TESTS PASSED 100%!")
    print("==================================================")

if __name__ == '__main__':
    test_full_withdrawal_cycle()
