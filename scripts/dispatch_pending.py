"""
Matrix8 Automated Payout Dispatcher Script
Checks Treasury BNB gas and broadcasts any pending commissions to upline BEP-20 wallets.
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))

import bsc_verifier
import payout_dispatcher
import database

def check_and_dispatch():
    print("==================================================")
    print("⚡ CHECKING TREASURY GAS & ON-CHAIN PAYOUT STATUS")
    print("==================================================")

    treasury = database.SYSTEM_TREASURY_ADDRESS
    print(f"Treasury Address: {treasury}")

    bal_hex = bsc_verifier.rpc_call('eth_getBalance', [treasury, 'latest'])
    bnb_bal = (int(bal_hex, 16) / (10**18)) if bal_hex else 0.0
    print(f"Current BNB Gas Balance: {bnb_bal:.6f} BNB (~${bnb_bal * 650:.2f} USD)")

    if bnb_bal < 0.0005:
        print("⚠️ BNB Gas is currently empty (< 0.0005 BNB).")
        print("👉 Please send $0.50 - $1.00 of BNB to Treasury address for gas:")
        print(f"   {treasury}")
        print("Once BNB arrives, the system will automatically broadcast all BEP-20 USDT payouts on BSC!")
        return

    print("✅ Sufficient BNB Gas detected! Broadcasting pending Level 1 commission ($0.7140 USDT)...")
    res = payout_dispatcher.dispatch_usdt_payout(
        to_wallet="0xe65b82f8b9B802Dec9127B4696a7F91230c24D55",
        amount_usdt=0.7140,
        level_num=1,
        from_user_id="M8-853464",
        to_user_id="M8-160303"
    )
    print("Result:", res)

if __name__ == '__main__':
    check_and_dispatch()
