#!/usr/bin/env python3
"""
Unit Test: Verify 8-Level Matrix Commission Distribution and Orphaned Fallback Math
"""
import sys

REGISTRATION_FEE = 3.40
LEVEL_PERCENTAGES = [0.21, 0.16, 0.13, 0.09, 0.06, 0.03, 0.02, 0.01]
SYSTEM_BASE_PERCENTAGE = 0.29

def simulate_distribution(upline_count):
    upline_payouts = []
    orphaned_pct = 0.0
    distributed_sum = 0.0

    for idx, pct in enumerate(LEVEL_PERCENTAGES):
        amount = round(REGISTRATION_FEE * pct, 4)
        if idx < upline_count:
            upline_payouts.append((idx + 1, pct * 100, amount))
            distributed_sum += amount
        else:
            orphaned_pct += pct

    base_system = round(REGISTRATION_FEE * SYSTEM_BASE_PERCENTAGE, 4)
    orphaned_system = round(REGISTRATION_FEE * orphaned_pct, 4)
    total_system = round(base_system + orphaned_system, 4)
    grand_total = round(distributed_sum + total_system, 4)

    return {
        "uplines": upline_payouts,
        "distributed_sum": round(distributed_sum, 4),
        "base_system": base_system,
        "orphaned_system": orphaned_system,
        "total_system": total_system,
        "grand_total": grand_total
    }

def test_full_chain():
    print("Testing Full 8-Upline Chain...")
    res = simulate_distribution(8)
    assert res["grand_total"] == 3.40, f"Expected 3.40, got {res['grand_total']}"
    assert res["distributed_sum"] == 2.414, f"Expected 2.414, got {res['distributed_sum']}"
    assert res["base_system"] == 0.986, f"Expected 0.986, got {res['base_system']}"
    assert res["orphaned_system"] == 0.0, f"Expected 0.0, got {res['orphaned_system']}"
    assert res["total_system"] == 0.986, f"Expected 0.986, got {res['total_system']}"
    print("  ✅ Full 8-upline test passed: $2.414 to uplines + $0.986 to system = $3.400")

def test_partial_chain_3_levels():
    print("\nTesting Partial 3-Upline Chain (5 Orphaned Levels)...")
    res = simulate_distribution(3)
    # L1: 0.714, L2: 0.544, L3: 0.442 = 1.700 (50%)
    # Levels 4-8 = 9+6+3+2+1 = 21% = 0.714
    # Base system = 29% = 0.986
    # Total system = 0.986 + 0.714 = 1.700 (50%)
    assert res["grand_total"] == 3.40, f"Expected 3.40, got {res['grand_total']}"
    assert res["distributed_sum"] == 1.70, f"Expected 1.70, got {res['distributed_sum']}"
    assert res["orphaned_system"] == 0.714, f"Expected 0.714, got {res['orphaned_system']}"
    assert res["total_system"] == 1.70, f"Expected 1.70, got {res['total_system']}"
    print("  ✅ Partial 3-upline test passed: $1.700 to 3 uplines + $1.700 to system ($0.986 base + $0.714 orphans) = $3.400")

def test_single_direct_upline():
    print("\nTesting 1-Upline Chain (7 Orphaned Levels)...")
    res = simulate_distribution(1)
    # L1: 0.714 (21%)
    # Levels 2-8 = 50% = 1.700
    # Base system = 29% = 0.986
    # Total system = 2.686 (79%)
    assert res["grand_total"] == 3.40, f"Expected 3.40, got {res['grand_total']}"
    assert res["distributed_sum"] == 0.714, f"Expected 0.714, got {res['distributed_sum']}"
    assert res["total_system"] == 2.686, f"Expected 2.686, got {res['total_system']}"
    print("  ✅ 1-upline test passed: $0.714 to direct sponsor + $2.686 to system = $3.400")

if __name__ == '__main__':
    test_full_chain()
    test_partial_chain_3_levels()
    test_single_direct_upline()
    print("\n🎉 ALL MATHEMATICAL INTEGRITY TESTS PASSED!")
