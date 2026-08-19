/**
 * AuthService - Production BEP-20 Authentication & Persistent Member Session Management
 * Authenticates users via registered Gmail/Email + (Password OR BEP-20 Wallet Address).
 * Pure member isolation: Guests see only the public Landing/Registration page.
 */

class AuthService {
  constructor(matrixEngine) {
    this.matrixEngine = matrixEngine;
    this.SESSION_KEY = 'matrix8_prod_member_auth_session';
    this.currentUser = null;
    this.connectedWallet = null;

    // Clean legacy test sessions
    localStorage.removeItem('matrix8_active_session_id_prod');
    sessionStorage.removeItem('matrix8_active_session_id_prod');

    this.loadSession();
  }

  loadSession() {
    const savedUserId = localStorage.getItem(this.SESSION_KEY) || sessionStorage.getItem(this.SESSION_KEY);
    if (!savedUserId) {
      this.currentUser = null;
      this.connectedWallet = null;
      return;
    }

    this.currentUser = {
      uniqueId: savedUserId,
      unique_id: savedUserId
    };
  }

  async loginWithBackend(emailOrWallet, credential = '', remember = true) {
    const ident = (emailOrWallet || '').trim();
    const cred = (credential || '').trim();

    if (!ident && !cred) {
      throw new Error('Please enter your registered Gmail, Unique ID, or BEP-20 Wallet Address.');
    }

    const response = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: ident, credential: cred })
    });

    const json = await response.json();
    if (!json.success) {
      throw new Error(json.error || 'Login failed. Invalid credentials.');
    }

    const user = json.data;
    this.currentUser = {
      uniqueId: user.unique_id,
      unique_id: user.unique_id,
      email: user.email,
      walletAddress: user.wallet_address,
      wallet_address: user.wallet_address,
      status: user.status,
      totalEarned: Number(user.total_earned || 0),
      total_earned: Number(user.total_earned || 0),
      walletBalance: Number(user.wallet_balance || 0),
      wallet_balance: Number(user.wallet_balance || 0),
      total_withdrawn: Number(user.total_withdrawn || 0),
      directs_count: Number(user.directs_count || 0),
      referrerId: user.referrer_id,
      isRegistered: true
    };
    this.connectedWallet = user.wallet_address;

    this.saveSession(user.unique_id, remember);

    return this.currentUser;
  }

  saveSession(uniqueId, remember = true) {
    if (!uniqueId) return;
    if (remember) {
      localStorage.setItem(this.SESSION_KEY, uniqueId);
    } else {
      sessionStorage.setItem(this.SESSION_KEY, uniqueId);
    }
  }

  logout() {
    this.currentUser = null;
    this.connectedWallet = null;
    sessionStorage.removeItem(this.SESSION_KEY);
    localStorage.removeItem(this.SESSION_KEY);
    localStorage.removeItem('matrix8_active_session_id_prod');
    sessionStorage.removeItem('matrix8_active_session_id_prod');
  }

  isLoggedIn() {
    const saved = localStorage.getItem(this.SESSION_KEY) || sessionStorage.getItem(this.SESSION_KEY);
    return !!this.currentUser || !!saved;
  }

  getCurrentUser() {
    return this.currentUser;
  }
}

window.AuthService = AuthService;
