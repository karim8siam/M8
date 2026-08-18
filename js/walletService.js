/**
 * WalletService - Built-in Crypto Wallet, DEX Swap & Staking/Hold Vault
 */

class WalletService {
  constructor(matrixEngine) {
    this.matrixEngine = matrixEngine;
    this.RATES = {
      USDT: 1.0,
      BNB: 620.45,
      ETH: 3350.80,
      TRX: 0.148,
      MATIC: 0.58,
      SOL: 188.20
    };
  }

  getRates() {
    return this.RATES;
  }

  calculateSwap(fromToken, toToken, fromAmount) {
    const fromRate = this.RATES[fromToken] || 1.0;
    const toRate = this.RATES[toToken] || 1.0;
    
    // Total value in USD
    const usdValue = fromAmount * fromRate;
    // Minus 0.25% DEX router fee
    const effectiveUsd = usdValue * 0.9975;
    const toAmount = effectiveUsd / toRate;

    return {
      fromAmount: +fromAmount,
      fromToken,
      toAmount: +toAmount.toFixed(6),
      toToken,
      exchangeRate: +(fromRate / toRate).toFixed(6),
      feeUsd: +(usdValue * 0.0025).toFixed(4)
    };
  }

  executeSwap(userId, fromToken, toToken, fromAmount) {
    const user = this.matrixEngine.getUserById(userId);
    if (!user) throw new Error('User not found');

    if (!user.cryptoBalances) {
      user.cryptoBalances = {
        USDT: user.walletBalance || 0,
        BNB: 0.05,
        ETH: 0.015,
        TRX: 120,
        MATIC: 50,
        SOL: 0.8
      };
    }

    const currentFromBal = user.cryptoBalances[fromToken] || 0;
    if (currentFromBal < fromAmount) {
      throw new Error(`Insufficient ${fromToken} balance. You have ${currentFromBal.toFixed(4)} ${fromToken}.`);
    }

    const swapResult = this.calculateSwap(fromToken, toToken, fromAmount);

    user.cryptoBalances[fromToken] = +(user.cryptoBalances[fromToken] - fromAmount).toFixed(6);
    user.cryptoBalances[toToken] = +((user.cryptoBalances[toToken] || 0) + swapResult.toAmount).toFixed(6);

    // Sync primary USDT balance if USDT was swapped
    if (fromToken === 'USDT') user.walletBalance = user.cryptoBalances.USDT;
    if (toToken === 'USDT') user.walletBalance = user.cryptoBalances.USDT;

    const allUsers = this.matrixEngine.getAllUsers();
    allUsers[userId] = user;
    this.matrixEngine.saveAllUsers(allUsers);

    this.matrixEngine.addTransaction({
      type: 'SWAP_EXECUTED',
      fromId: userId,
      note: `Swapped ${fromAmount} ${fromToken} ➔ ${swapResult.toAmount} ${toToken}`
    });

    return swapResult;
  }

  depositUSDT(userId, amount) {
    const user = this.matrixEngine.getUserById(userId);
    if (!user) throw new Error('User not found');

    user.walletBalance = +((user.walletBalance || 0) + amount).toFixed(4);
    if (!user.cryptoBalances) user.cryptoBalances = { USDT: user.walletBalance };
    user.cryptoBalances.USDT = user.walletBalance;

    const allUsers = this.matrixEngine.getAllUsers();
    allUsers[userId] = user;
    this.matrixEngine.saveAllUsers(allUsers);

    this.matrixEngine.addTransaction({
      type: 'USDT_DEPOSIT',
      fromId: userId,
      amount: amount,
      note: `Deposited +$${amount} USDT`
    });

    return user.walletBalance;
  }

  withdrawUSDT(userId, destinationAddress, amount) {
    const user = this.matrixEngine.getUserById(userId);
    if (!user) throw new Error('User not found');

    if ((user.walletBalance || 0) < amount) {
      throw new Error('Insufficient wallet balance to withdraw.');
    }

    user.walletBalance = +(user.walletBalance - amount).toFixed(4);
    if (user.cryptoBalances) user.cryptoBalances.USDT = user.walletBalance;

    const allUsers = this.matrixEngine.getAllUsers();
    allUsers[userId] = user;
    this.matrixEngine.saveAllUsers(allUsers);

    this.matrixEngine.addTransaction({
      type: 'WITHDRAWAL_PROCESSED',
      fromId: userId,
      toWallet: destinationAddress,
      amount: amount,
      note: `Withdrawal of $${amount} USDT to ${destinationAddress.slice(0, 6)}...`
    });

    return user.walletBalance;
  }

  transferToHold(userId, amount) {
    const user = this.matrixEngine.getUserById(userId);
    if (!user) throw new Error('User not found');

    if ((user.walletBalance || 0) < amount) {
      throw new Error('Insufficient wallet balance');
    }

    user.walletBalance = +(user.walletBalance - amount).toFixed(4);
    user.holdBalance = +((user.holdBalance || 0) + amount).toFixed(4);
    if (user.cryptoBalances) user.cryptoBalances.USDT = user.walletBalance;

    const allUsers = this.matrixEngine.getAllUsers();
    allUsers[userId] = user;
    this.matrixEngine.saveAllUsers(allUsers);

    return { walletBalance: user.walletBalance, holdBalance: user.holdBalance };
  }
}

window.WalletService = WalletService;
