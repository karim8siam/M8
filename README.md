# Matrix8 - Decentralized 8-Level Crypto Network Marketing Platform

A complete, non-custodial Web3 network marketing platform where users join with **3.4 USDT**, earning multi-level commissions across 8 tiers distributed instantly to their crypto wallets.

---

## 💎 Commission Breakdown (3.4 USDT Entry)

| Level | Percentage | Payout per Join | Recipient |
| :--- | :--- | :--- | :--- |
| **Level 1** | **21%** | **$0.7140 USDT** | Direct Sponsor |
| **Level 2** | **16%** | **$0.5440 USDT** | Level 2 Upline |
| **Level 3** | **13%** | **$0.4420 USDT** | Level 3 Upline |
| **Level 4** | **9%** | **$0.3060 USDT** | Level 4 Upline |
| **Level 5** | **6%** | **$0.2040 USDT** | Level 5 Upline |
| **Level 6** | **3%** | **$0.1020 USDT** | Level 6 Upline |
| **Level 7** | **2%** | **$0.0680 USDT** | Level 7 Upline |
| **Level 8** | **1%** | **$0.0340 USDT** | Level 8 Upline |
| **Upline Total** | **71%** | **$2.4140 USDT** | Distributed across upline chain |
| **System Pool** | **29%** | **$0.9860 USDT** | System Treasury Base |
| **Total** | **100%** | **$3.4000 USDT** | Fully balanced (0% lost funds) |

### 🛡️ Dynamic Orphan Fallback Rule
If a user joins under a shorter upline chain (e.g. only 3 uplines exist):
- Uplines 1, 2, 3 receive their respective $0.714, $0.544, $0.442 USDT ($1.700 total).
- The remaining unallocated levels (Levels 4 through 8 = 21% / $0.714 USDT) automatically route into the **System Account**.
- The System Account receives $0.986 (29% base) + $0.714 = $1.700 USDT.
- **Zero dust is lost, and 100% of every 3.4 USDT is strictly accounted for.**

---

## 🚀 Key Features

1. **100% Anonymous & Privacy-First**:
   - No Email, No Phone Number, No Real Name, Zero KYC.
   - Generates a **Unique ID** (e.g. `NX-489201`).
   - Secure Access Password / PIN for cross-device authentication.
2. **Instant Web3 Commission Routing**:
   - Payouts are pushed directly and instantly to uplines upon registration.
3. **Built-in Crypto Wallet, Swap & Hold Module**:
   - Multi-asset balance tracking (USDT, BNB, ETH, TRX, MATIC, SOL).
   - In-app DEX token swap router with live exchange rates.
   - Deposit USDT via QR code or direct address.
   - Instant withdrawal to external Trust Wallet / MetaMask.
4. **8-Level Real-Time Analytics & Network Tree**:
   - Individual cards for Levels 1 through 8 showing active members and USDT earned.
   - Interactive visual downline tree explorer.
   - Live transaction ledger with blockchain hash simulation.
5. **Referral Hub & QR Code Generator**:
   - 1-click copy shareable link `https://matrix8.io/?ref=NX-XXXXXX`.
   - High-resolution dynamic QR code for Trust Wallet DApp camera scanner.
   - Instant social sharing (Telegram, WhatsApp).
6. **Live Interactive Simulator**:
   - Includes one-click test buttons to simulate new members joining at Level 1, 2, 3, etc. to watch live balances and matrix cards update in real time.

---

## 📂 Project Structure

```
crypto-matrix-mlm/
├── contracts/
│   └── NetworkMatrix8.sol     # Production Solidity Smart Contract
├── css/
│   └── styles.css             # Obsidian dark Web3 glassmorphism design system
├── js/
│   ├── matrixEngine.js        # 8-Tier commission calculations & recursive tree
│   ├── walletService.js       # Crypto wallet, DEX swap, deposit/hold vault
│   ├── authService.js         # Web3 connection & cross-device password sync
│   └── app.js                 # UI controller, event handlers & real-time feed
├── tests/
│   └── test_matrix_math.py    # Unit tests for mathematical accuracy
├── index.html                 # Master Web3 application interface
├── server.py                  # Lightweight Python local dev server
└── README.md                  # Documentation
```

---

## 🛠️ How to Run Locally

1. Open your terminal in this directory:
   ```bash
   cd /Users/karimsiam/.gemini/antigravity/scratch/crypto-matrix-mlm
   ```
2. Start the local server:
   ```bash
   python3 server.py
   ```
3. Open your browser or Trust Wallet DApp browser at:
   ```
   http://localhost:8080
   ```

---

## ⛓️ Smart Contract Deployment (BSC / Polygon / EVM)

The contract `contracts/NetworkMatrix8.sol` is ready for deployment via Remix, Hardhat, or Foundry:
1. Compile using Solidity `^0.8.20`.
2. Pass the **USDT ERC20 Token Address** and your **System Treasury Address** in the constructor:
   ```solidity
   constructor(address _usdtTokenAddress, address _systemTreasury)
   ```
3. Call `register(referrerAddress)` to onboard new users with 3.4 USDT fee.
