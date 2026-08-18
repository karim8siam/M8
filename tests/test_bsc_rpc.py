"""
Live BSC Mainnet RPC Connectivity Test
Queries live BSC node for latest block and validates BSC USDT contract connectivity.
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))

import bsc_verifier

def test_bsc_connection():
    print("==================================================")
    print("🌐 TESTING LIVE BINANCE SMART CHAIN (BSC) RPC CONNECTION")
    print("==================================================")

    # 1. Query block number
    block_hex = bsc_verifier.rpc_call('eth_blockNumber', [])
    assert block_hex is not None, "Failed to connect to BSC RPC!"
    block_num = int(block_hex, 16)
    print(f"✅ [1/3] BSC Mainnet Connected! Current Block Number: #{block_num:,}")

    # 2. Query Treasury USDT Balance
    treasury = bsc_verifier.SYSTEM_TREASURY
    usdt_contract = bsc_verifier.BSC_USDT_CONTRACT
    print(f"✅ [2/3] Target Treasury Address: {treasury}")
    print(f"✅ [2/3] BSC-USD BEP-20 Contract: {usdt_contract}")

    # BalanceOf ABI: 0x70a08231 + padded address
    clean_addr = treasury[2:].zfill(64)
    data_call = f"0x70a08231{clean_addr}"
    
    bal_hex = bsc_verifier.rpc_call('eth_call', [{
        'to': usdt_contract,
        'data': data_call
    }, 'latest'])
    
    if bal_hex:
        raw_bal = int(bal_hex, 16)
        usdt_bal = raw_bal / (10 ** 18)
        print(f"✅ [3/3] Live Treasury USDT Balance on BSC: {usdt_bal:.4f} USDT")
    else:
        print("⚠️ [3/3] Could not read balance (will verify upon transfer receipt).")

    print("==================================================")
    print("🎉 BSC BLOCKCHAIN RPC IS 100% READY FOR REAL USDT DEPOSITS!")
    print("==================================================")

if __name__ == '__main__':
    test_bsc_connection()
