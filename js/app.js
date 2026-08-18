/**
 * Matrix8 Application Controller
 * Production BEP-20 Matrix Engine, User Dashboard, Automated On-Chain Detection, and Strict Member Isolation.
 * 100% AUTOMATED: Auto-detects BSC USDT transfers on-chain without requiring users to manually copy/paste hashes.
 * STRICT SECURITY: Unactivated accounts can NEVER access the Dashboard.
 */

class AppController {
  constructor() {
    this.matrixEngine = new window.MatrixEngine();
    this.walletService = new window.WalletService(this.matrixEngine);
    this.authService = new window.AuthService(this.matrixEngine);
    this.telegramService = new window.TelegramService(this.matrixEngine);

    this.pendingUser = null;
    this.authMode = 'register'; // 'register' or 'login'
    this.autoPollInterval = null;

    this.init();
  }

  init() {
    this.bindEvents();
    this.checkUrlReferral();
    this.renderView();
  }

  bindEvents() {
    // Navigation tabs
    document.querySelectorAll('.nav-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = btn.dataset.tab;
        if (tab === 'tab-overview') {
          this.showUserDashboard();
        } else if (tab) {
          this.switchTab(tab);
        }
      });
    });

    // Copy Referral Link
    const btnCopyRefLink = document.getElementById('btnCopyRefLink');
    if (btnCopyRefLink) {
      btnCopyRefLink.addEventListener('click', () => this.copyReferralLink());
    }
  }

  switchAuthMode(mode) {
    this.authMode = mode;
    const regContainer = document.getElementById('authRegisterContainer');
    const loginContainer = document.getElementById('authLoginContainer');
    const tabReg = document.getElementById('toggleTabRegister');
    const tabLogin = document.getElementById('toggleTabLogin');

    if (mode === 'login') {
      if (regContainer) regContainer.style.display = 'none';
      if (loginContainer) loginContainer.style.display = 'block';

      if (tabLogin) {
        tabLogin.style.background = 'var(--primary-cyan)';
        tabLogin.style.color = '#fff';
      }
      if (tabReg) {
        tabReg.style.background = 'transparent';
        tabReg.style.color = 'var(--text-secondary)';
      }
    } else {
      if (regContainer) regContainer.style.display = 'block';
      if (loginContainer) loginContainer.style.display = 'none';

      if (tabReg) {
        tabReg.style.background = 'var(--primary-emerald)';
        tabReg.style.color = '#fff';
      }
      if (tabLogin) {
        tabLogin.style.background = 'transparent';
        tabLogin.style.color = 'var(--text-secondary)';
      }
    }
  }

  checkUrlReferral() {
    const urlParams = new URLSearchParams(window.location.search);
    const ref = urlParams.get('ref');
    if (ref) {
      const inputSponsor = document.getElementById('regSponsorId');
      if (inputSponsor) {
        inputSponsor.value = ref.trim().toUpperCase();
      }
    }
    this.checkSponsorVipStatus();
  }

  checkSponsorVipStatus() {
    const inputSponsor = document.getElementById('regSponsorId');
    const vipContainer = document.getElementById('vipFreeBadgeContainer');
    const feeBadge = document.getElementById('regFeeBadge');
    const btnText = document.getElementById('btnRegisterText');

    if (!inputSponsor) return;
    const sponsorVal = inputSponsor.value.trim().toUpperCase();
    const isAdmin = ['M8-ADMIN', 'ADMIN', 'M8-VIP001'].includes(sponsorVal);

    if (isAdmin) {
      if (vipContainer) vipContainer.style.display = 'block';
      if (feeBadge) feeBadge.textContent = '0.00 USDT (FREE VIP)';
      if (btnText) btnText.textContent = '🚀 Free Instant VIP Activation (0 USDT) ➔';
    } else {
      if (vipContainer) vipContainer.style.display = 'none';
      if (feeBadge) feeBadge.textContent = '3.40 USDT (BEP20)';
      if (btnText) btnText.textContent = 'Pay 3.4 USDT & Activate Membership';
    }
  }

  renderView() {
    const urlParams = new URLSearchParams(window.location.search);
    const ref = urlParams.get('ref');
    const savedUserId = localStorage.getItem(this.authService.SESSION_KEY);

    if (savedUserId) {
      // Real member/owner session exists -> Open Dashboard
      this.showUserDashboard();
    } else {
      // Guest visitor -> Open Landing / Registration & Login Page
      if (ref) {
        this.switchAuthMode('register');
      }
      this.showRegistrationPage();
    }
  }

  showRegistrationPage() {
    const onboardingView = document.getElementById('onboardingView');
    const dashboardView = document.getElementById('dashboardView');
    const navTabs = document.getElementById('navTabs');
    const navGuestBar = document.getElementById('navGuestBar');
    const navUserBar = document.getElementById('navUserBar');

    if (onboardingView) onboardingView.style.display = 'block';
    if (dashboardView) dashboardView.style.display = 'none';
    if (navTabs) navTabs.style.display = 'none';
    if (navGuestBar) navGuestBar.style.display = 'flex';
    if (navUserBar) navUserBar.style.display = 'none';

    this.checkSponsorVipStatus();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async showUserDashboard(passedUser = null) {
    const onboardingView = document.getElementById('onboardingView');
    const dashboardView = document.getElementById('dashboardView');
    const navTabs = document.getElementById('navTabs');
    const navGuestBar = document.getElementById('navGuestBar');
    const navUserBar = document.getElementById('navUserBar');

    let user = passedUser || this.authService.getCurrentUser();
    let userId = user ? (user.unique_id || user.uniqueId) : localStorage.getItem(this.authService.SESSION_KEY);
    
    // Guard: Guests or unauthenticated visitors must never see the dashboard
    if (!userId) {
      this.showRegistrationPage();
      return;
    }

    try {
      const res = await fetch(`/api/user-dashboard?user_id=${userId}&t=${Date.now()}`);
      if (res.ok) {
        const liveData = await res.json();

        // STRICT SECURITY GUARD: If user is not ACTIVE, block dashboard and prompt payment
        if (liveData.status === 'PENDING_DEPOSIT' || liveData.requires_activation) {
          this.showToast('⚠️ Account pending activation. Please complete 3.40 USDT deposit to access dashboard.', 'warning');
          this.pendingUser = { unique_id: userId };
          this.showRegistrationPage();
          this.openModal('modalPaymentVerify');
          this.startAutoDepositPolling(userId);
          return;
        }

        if (onboardingView) onboardingView.style.display = 'none';
        if (dashboardView) dashboardView.style.display = 'block';
        if (navTabs) navTabs.style.display = 'flex';
        if (navGuestBar) navGuestBar.style.display = 'none';
        if (navUserBar) navUserBar.style.display = 'flex';

        document.querySelectorAll('.nav-tab-btn').forEach(b => {
          b.classList.toggle('active', b.dataset.tab === 'tab-overview');
        });

        this.renderLiveDashboardData(liveData);
        this.switchTab('tab-overview');
        this.startDashboardLiveRefresh(userId);
        return;
      } else {
        this.showRegistrationPage();
      }
    } catch (e) {
      console.warn('Backend live dashboard fetch error:', e);
    }
  }

  renderLiveDashboardData(data) {
    if (!data) return;
    this.currentDashboardData = data;

    const elBalance = document.getElementById('kpiWalletBalance');
    const elEarned = document.getElementById('kpiTotalEarned');
    const elWithdrawn = document.getElementById('kpiTotalWithdrawnLabel');
    const elTotal = document.getElementById('kpiTotalMembers');
    const elDirect = document.getElementById('kpiDirectCount');
    const elNavId = document.getElementById('navUserUniqueId');
    const elNavWallet = document.getElementById('navWalletAddressShort');
    const elRefId = document.getElementById('refCardUniqueId');
    const elRefInput = document.getElementById('refLinkInput');
    const elKpiWallet = document.getElementById('kpiWalletAddressShort');

    const bal = Number(data.wallet_balance || 0);
    const earned = Number(data.total_earned || 0);
    const withdrawn = Number(data.total_withdrawn || 0);
    const directs = Number(data.directs_count || 0);
    const totalDown = Number(data.total_downlines || 0);

    if (elBalance) elBalance.textContent = `$${bal.toFixed(4)} USDT`;
    if (elEarned) elEarned.textContent = `$${earned.toFixed(4)} USDT`;
    if (elWithdrawn) elWithdrawn.textContent = `Paid Out: $${withdrawn.toFixed(2)}`;
    if (elTotal) elTotal.textContent = totalDown;
    if (elDirect) elDirect.textContent = directs;

    if (elNavId) elNavId.textContent = data.unique_id;
    if (elRefId) elRefId.textContent = data.unique_id;

    if (data.wallet_address) {
      const shortAddr = `${data.wallet_address.slice(0, 6)}...${data.wallet_address.slice(-4)}`;
      if (elNavWallet) elNavWallet.textContent = shortAddr;
      if (elKpiWallet) elKpiWallet.textContent = `${data.wallet_address.slice(0, 8)}...${data.wallet_address.slice(-6)}`;
    }

    if (elRefInput) {
      elRefInput.value = `${window.location.origin}/?ref=${data.unique_id}`;
    }

    // Render 8 level cards from backend levels data
    const container = document.getElementById('matrixGridCards');
    if (container && data.levels && Array.isArray(data.levels)) {
      const levelPcts = [21, 16, 13, 9, 6, 3, 2, 1];
      const levelAmounts = [0.714, 0.544, 0.442, 0.306, 0.204, 0.102, 0.068, 0.034];

      container.innerHTML = data.levels.map((lvl, idx) => {
        const isTier1 = lvl.level_num === 1;
        const mCount = Number(lvl.member_count || 0);
        const eAmt = Number(lvl.earned_amount || 0);
        return `
          <div class="level-card ${isTier1 ? 'tier-1' : ''}">
            <div class="level-card-header">
              <span class="level-tag">LEVEL ${lvl.level_num}</span>
              <span class="level-percentage">${levelPcts[idx]}%</span>
            </div>
            <div class="level-amount-per-join">+$${levelAmounts[idx].toFixed(3)} USDT per member</div>
            <div class="level-stats-row">
              <div class="level-stat-box">
                <span class="level-stat-num mono">${mCount}</span>
                <span class="level-stat-lbl">Members</span>
              </div>
              <div class="level-stat-box">
                <span class="level-stat-num mono" style="color: var(--primary-emerald);">$${eAmt.toFixed(2)}</span>
                <span class="level-stat-lbl">Earned</span>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

    // Render Recent Commission Transactions
    const feedContainer = document.getElementById('activityFeedList');
    if (feedContainer && data.transactions) {
      const commTxs = data.transactions.filter(tx => tx.tx_type.includes('COMMISSION') || tx.tx_type === 'BSC_DEPOSIT');
      if (commTxs.length === 0) {
        feedContainer.innerHTML = `
          <div style="text-align: center; color: var(--text-muted); padding: 1.5rem; font-size: 0.82rem;">
            No commission earnings yet. Share your referral link to earn instant 21% Level 1 commissions!
          </div>
        `;
      } else {
        feedContainer.innerHTML = commTxs.map(tx => {
          const isDeposit = tx.tx_type === 'BSC_DEPOSIT';
          const icon = isDeposit ? '⚡' : '💰';
          const amountColor = isDeposit ? 'var(--primary-cyan)' : 'var(--primary-emerald)';
          const amountText = isDeposit ? '$3.4000 USDT' : `+$${(tx.amount_usdt || 0).toFixed(4)} USDT`;
          const title = isDeposit ? '3.40 USDT Activation Confirmed on BSC' : (tx.note || 'Commission Payout');

          return `
            <div class="feed-item">
              <div class="feed-left">
                <div class="feed-icon ${isDeposit ? 'join' : 'commission'}">
                  ${icon}
                </div>
                <div>
                  <div class="feed-title">${title}</div>
                  <div class="feed-desc mono">${new Date((tx.timestamp || Date.now()/1000) * 1000).toLocaleTimeString()} • ${tx.tx_hash ? tx.tx_hash.slice(0, 12) + '...' : ''}</div>
                </div>
              </div>
              <div class="feed-amount mono" style="color: ${amountColor}; font-weight: 700;">
                ${amountText}
              </div>
            </div>
          `;
        }).join('');
      }
    }

    // Render Withdrawal History List
    const wdContainer = document.getElementById('withdrawalHistoryList');
    if (wdContainer) {
      const wds = data.withdrawals || [];
      if (wds.length === 0) {
        wdContainer.innerHTML = `
          <div style="text-align: center; color: var(--text-muted); padding: 1.5rem; font-size: 0.82rem;">
            No withdrawal requests yet. Click "Withdraw Funds" anytime to cash out your available balance!
          </div>
        `;
      } else {
        wdContainer.innerHTML = wds.map(w => {
          const isPending = w.status === 'PENDING';
          const isCompleted = w.status === 'COMPLETED';
          const statusBadge = isPending 
            ? `<span style="background: rgba(245, 158, 11, 0.15); color: #F59E0B; padding: 2px 8px; border-radius: 99px; font-size: 0.72rem; font-weight: 700;">🟡 PENDING</span>`
            : isCompleted 
            ? `<span style="background: rgba(16, 185, 129, 0.15); color: #10B981; padding: 2px 8px; border-radius: 99px; font-size: 0.72rem; font-weight: 700;">🟢 COMPLETED</span>`
            : `<span style="background: rgba(239, 68, 68, 0.15); color: #EF4444; padding: 2px 8px; border-radius: 99px; font-size: 0.72rem; font-weight: 700;">🔴 REJECTED</span>`;

          return `
            <div class="feed-item">
              <div class="feed-left">
                <div class="feed-icon" style="background: rgba(16, 185, 129, 0.15); color: #10B981;">💸</div>
                <div>
                  <div class="feed-title" style="display: flex; align-items: center; gap: 6px;">
                    <span>${w.withdrawal_id}</span>
                    ${statusBadge}
                  </div>
                  <div class="feed-desc mono">
                    ${new Date((w.request_timestamp || Date.now()/1000) * 1000).toLocaleDateString()} • To: ${w.wallet_address ? (w.wallet_address.slice(0, 6) + '...' + w.wallet_address.slice(-4)) : ''}
                  </div>
                </div>
              </div>
              <div class="feed-amount mono" style="color: #10B981; font-weight: 700;">
                $${(w.amount_usdt || 0).toFixed(2)} USDT
              </div>
            </div>
          `;
        }).join('');
      }
    }

    // QR code
    this.renderReferralQr(data.unique_id);
    this.renderTelegramLogs();
  }

  renderDashboardData(user) {
    if (!user) return;
    const elBalance = document.getElementById('kpiWalletBalance');
    const elEarned = document.getElementById('kpiTotalEarned');
    const elWithdrawn = document.getElementById('kpiTotalWithdrawnLabel');
    const elTotal = document.getElementById('kpiTotalMembers');
    const elDirect = document.getElementById('kpiDirectCount');
    const elNavId = document.getElementById('navUserUniqueId');
    const elNavWallet = document.getElementById('navWalletAddressShort');
    const elRefId = document.getElementById('refCardUniqueId');
    const elKpiWallet = document.getElementById('kpiWalletAddressShort');

    const bal = (typeof user.wallet_balance !== 'undefined') ? user.wallet_balance : (user.walletBalance || 0);
    const earned = (typeof user.total_earned !== 'undefined') ? user.total_earned : (user.totalEarned || 0);
    const withdrawn = (typeof user.total_withdrawn !== 'undefined') ? user.total_withdrawn : 0;
    const directs = (typeof user.directs_count !== 'undefined') ? user.directs_count : (user.levelMemberCounts ? user.levelMemberCounts[0] : 0);
    const totalDown = (typeof user.total_downlines !== 'undefined') ? user.total_downlines : ((user.levelMemberCounts || []).reduce((a, b) => a + b, 0));
    const wallet = user.wallet_address || user.walletAddress || '';
    const uid = user.unique_id || user.uniqueId || '';

    if (elBalance) elBalance.textContent = `$${Number(bal).toFixed(4)} USDT`;
    if (elEarned) elEarned.textContent = `$${Number(earned).toFixed(4)} USDT`;
    if (elWithdrawn) elWithdrawn.textContent = `Paid Out: $${Number(withdrawn).toFixed(2)}`;
    if (elTotal) elTotal.textContent = totalDown;
    if (elDirect) elDirect.textContent = directs;

    if (elKpiWallet && wallet) {
      elKpiWallet.textContent = `${wallet.slice(0, 8)}...${wallet.slice(-6)}`;
    }
    if (elNavId) elNavId.textContent = uid;
    if (elRefId) elRefId.textContent = uid;
    if (elNavWallet && wallet) {
      elNavWallet.textContent = `${wallet.slice(0, 6)}...${wallet.slice(-4)}`;
    }
  }

  renderMatrixCards(user) {
    const container = document.getElementById('matrixGridCards');
    if (!container || !user) return;

    const levelPcts = [21, 16, 13, 9, 6, 3, 2, 1];
    const levelAmounts = [0.714, 0.544, 0.442, 0.306, 0.204, 0.102, 0.068, 0.034];

    // If user has levels array from backend
    if (user.levels && Array.isArray(user.levels)) {
      container.innerHTML = user.levels.map((lvl, idx) => {
        const isTier1 = lvl.level_num === 1;
        return `
          <div class="level-card ${isTier1 ? 'tier-1' : ''}">
            <div class="level-card-header">
              <span class="level-tag">LEVEL ${lvl.level_num}</span>
              <span class="level-percentage">${levelPcts[idx]}%</span>
            </div>
            <div class="level-amount-per-join">+$${levelAmounts[idx].toFixed(3)} USDT per member</div>
            <div class="level-stats-row">
              <div class="level-stat-box">
                <span class="level-stat-num mono">${lvl.member_count}</span>
                <span class="level-stat-lbl">Members</span>
              </div>
              <div class="level-stat-box">
                <span class="level-stat-num mono" style="color: var(--primary-emerald);">$${Number(lvl.earned_amount || 0).toFixed(2)}</span>
                <span class="level-stat-lbl">Earned</span>
              </div>
            </div>
          </div>
        `;
      }).join('');
      return;
    }

    let html = '';
    for (let i = 0; i < 8; i++) {
      const levelNum = i + 1;
      const count = user.levelMemberCounts ? user.levelMemberCounts[i] : 0;
      const earned = user.levelEarnings ? user.levelEarnings[i] : 0;
      const isTier1 = levelNum === 1;

      html += `
        <div class="level-card ${isTier1 ? 'tier-1' : ''}">
          <div class="level-card-header">
            <span class="level-tag">LEVEL ${levelNum}</span>
            <span class="level-percentage">${levelPcts[i]}%</span>
          </div>
          <div class="level-amount-per-join">+$${levelAmounts[i].toFixed(3)} USDT per member</div>
          <div class="level-stats-row">
            <div class="level-stat-box">
              <span class="level-stat-num mono">${count}</span>
              <span class="level-stat-lbl">Members</span>
            </div>
            <div class="level-stat-box">
              <span class="level-stat-num mono" style="color: var(--primary-emerald);">$${earned.toFixed(2)}</span>
              <span class="level-stat-lbl">Earned</span>
            </div>
          </div>
        </div>
      `;
    }
    container.innerHTML = html;
  }

  renderReferralHub(user) {
    if (!user) return;
    const refInput = document.getElementById('refLinkInput');
    const refUrl = `${window.location.origin}/?ref=${user.uniqueId}`;
    if (refInput) refInput.value = refUrl;
    this.renderReferralQr(user.uniqueId);
  }

  renderReferralQr(uniqueId) {
    const qrContainer = document.getElementById('qrCodeContainer');
    if (!qrContainer) return;
    qrContainer.innerHTML = '';
    try {
      if (window.QRCode) {
        new window.QRCode(qrContainer, {
          text: `${window.location.origin}/?ref=${uniqueId}`,
          width: 130,
          height: 130
        });
      }
    } catch (err) {}
  }

  copyReferralLink() {
    const input = document.getElementById('refLinkInput');
    if (input) {
      input.select();
      navigator.clipboard.writeText(input.value);
      this.showToast('Referral link copied to clipboard!', 'success');
    }
  }

  copyUserBep20Address() {
    const user = this.authService.getCurrentUser();
    if (user && user.walletAddress) {
      navigator.clipboard.writeText(user.walletAddress);
      this.showToast(`BEP-20 Address (${user.walletAddress.slice(0, 10)}...) copied!`, 'info');
    }
  }

  renderRecentActivity() {
    const container = document.getElementById('activityFeedList');
    if (!container) return;
    const logs = this.matrixEngine.getGlobalLogs().slice(0, 10);
    if (logs.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 1.5rem; font-size: 0.82rem;">
          No network transactions yet. Start referring members to see live commissions!
        </div>
      `;
      return;
    }

    const html = logs.map(l => `
      <div class="feed-item">
        <div class="feed-left">
          <div class="feed-icon ${l.type === 'commission' ? 'commission' : 'join'}">
            ${l.type === 'commission' ? '💰' : '👥'}
          </div>
          <div>
            <div class="feed-title">${l.title}</div>
            <div class="feed-desc mono">${new Date(l.timestamp).toLocaleTimeString()} • ${l.details}</div>
          </div>
        </div>
        <div class="feed-amount mono">+$${l.amount.toFixed(4)} USDT</div>
      </div>
    `).join('');
    container.innerHTML = html;
  }

  renderTelegramLogs() {
    const container = document.getElementById('telegramLogsContainer');
    if (!container) return;
    const logs = this.telegramService.getRecentLogs();
    if (logs.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 1.5rem; font-size: 0.82rem;">
          No Telegram alerts received yet. When a commission arrives, instant bot pings stream here.
        </div>
      `;
      return;
    }
    const html = logs.map(l => `
      <div class="feed-item" style="margin-bottom: 0.5rem;">
        <div class="feed-left">
          <div class="feed-icon" style="background: rgba(42, 171, 238, 0.15); color: #2AABEE;">✈️</div>
          <div>
            <div class="feed-title">${l.title}</div>
            <div class="feed-desc mono">${new Date(l.timestamp).toLocaleTimeString()} • ${l.details}</div>
          </div>
        </div>
        <div class="feed-amount mono" style="color: #2AABEE;">+$${l.amount.toFixed(4)} USDT</div>
      </div>
    `).join('');
    container.innerHTML = html;
  }

  renderSystemTreasury() {
    const sysData = this.matrixEngine.getSystemTreasury();
    const elCollected = document.getElementById('sysTreasuryCollected');
    const elVolume = document.getElementById('sysTotalVolume');
    if (elCollected) elCollected.textContent = `$${sysData.totalCollectedUsdt.toFixed(2)} USDT`;
    if (elVolume) elVolume.textContent = `$${sysData.totalVolumeUsdt.toFixed(2)} USDT`;
  }

  switchTab(tabId) {
    document.querySelectorAll('.tab-pane').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.nav-tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    const target = document.getElementById(`tabContent-${tabId.replace('tab-', '')}`);
    if (target) target.style.display = 'block';

    if (tabId === 'tab-tree') {
      this.renderNetworkTree();
    }
  }

  renderNetworkTree() {
    const treeContainer = document.getElementById('downlineTreeContainer');
    if (!treeContainer) return;
    const user = this.authService.getCurrentUser();
    if (!user) return;
    const treeData = this.matrixEngine.getTreeData(user.uniqueId);

    let treeHtml = `
      <div class="tree-node-root">
        <div class="tree-node-id" style="font-size: 1rem;">${treeData.uniqueId} (YOU)</div>
        <div class="tree-node-sub mono">${treeData.walletAddress.slice(0, 8)}...${treeData.walletAddress.slice(-6)}</div>
        <div style="font-size: 0.85rem; color: var(--primary-emerald); font-weight: 700; margin-top: 4px;">Earned: $${treeData.totalEarned.toFixed(2)} USDT</div>
      </div>
    `;

    if (treeData.children && treeData.children.length > 0) {
      treeHtml += `<div class="tree-branches">`;
      treeData.children.forEach(c1 => {
        treeHtml += `
          <div style="display: flex; flex-direction: column; align-items: center;">
            <div class="tree-node-child">
              <div class="tree-node-id">${c1.uniqueId} (L1)</div>
              <div class="tree-node-sub mono">${c1.walletAddress.slice(0, 6)}...</div>
              <div style="font-size: 0.7rem; color: var(--primary-cyan); font-weight: 600;">Earned: $${c1.totalEarned.toFixed(2)}</div>
            </div>
        `;
        if (c1.children && c1.children.length > 0) {
          treeHtml += `<div style="display: flex; gap: 0.5rem; margin-top: 1rem;">`;
          c1.children.forEach(c2 => {
            treeHtml += `
              <div class="tree-node-child" style="min-width: 90px; padding: 0.4rem 0.6rem;">
                <div class="tree-node-id" style="font-size: 0.72rem;">${c2.uniqueId} (L2)</div>
                <div class="tree-node-sub mono">${c2.walletAddress.slice(0, 4)}...</div>
              </div>
            `;
          });
          treeHtml += `</div>`;
        }
        treeHtml += `</div>`;
      });
      treeHtml += `</div>`;
    } else {
      treeHtml += `
        <div style="color: var(--text-muted); font-size: 0.85rem; text-align: center; margin-top: 1rem;">
          No downlines yet. Share your referral link with new members!
        </div>
      `;
    }
    treeContainer.innerHTML = treeHtml;
  }

  // --------------------------------------------------------------------------
  // USER LOGIN & LOGOUT (WITH DEVICE PERSISTENCE)
  // --------------------------------------------------------------------------
  async handleLogin() {
    const ident = (document.getElementById('loginEmail').value || '').trim();
    const credential = (document.getElementById('loginCredential').value || '').trim();
    const remember = document.getElementById('loginRemember') ? document.getElementById('loginRemember').checked : true;

    if (!ident && !credential) {
      this.showToast('Please enter your registered Gmail, Unique ID, or BEP-20 Wallet Address.', 'warning');
      return;
    }

    try {
      this.showToast('Authenticating credentials...', 'info');
      const user = await this.authService.loginWithBackend(ident, credential, remember);

      if (user.status === 'PENDING_DEPOSIT') {
        this.showToast('⚠️ Account registered, but pending 3.40 USDT activation deposit.', 'warning');
        this.pendingUser = { unique_id: user.uniqueId };
        this.openModal('modalPaymentVerify');
        this.startAutoDepositPolling(user.uniqueId);
        return;
      }

      this.showToast(`🎉 Login successful! Welcome back, ${user.uniqueId}.`, 'success');
      this.showUserDashboard(user);
    } catch (err) {
      this.showToast(err.message || 'Login failed. Please verify your credentials.', 'warning');
    }
  }

  handleLogout() {
    this.stopAutoDepositPolling();
    this.authService.logout();
    this.showToast('🚪 Logged out successfully. You can log in or register anytime.', 'info');
    
    // Switch to guest landing page
    this.switchAuthMode('login');
    this.showRegistrationPage();
  }

  // --------------------------------------------------------------------------
  // USER REGISTRATION & AUTOMATED REAL BSC PAYMENT VERIFICATION
  // --------------------------------------------------------------------------
  async handleRegister() {
    const email = (document.getElementById('regEmail').value || '').trim();
    const password = (document.getElementById('regPassword').value || '').trim();
    const sponsorId = (document.getElementById('regSponsorId').value || '').trim();
    const bep20Wallet = (document.getElementById('regBep20Wallet').value || '').trim();
    const telegram = (document.getElementById('regTelegram').value || '').trim();

    if (!sponsorId) {
      this.showToast('Please enter a valid Sponsor / Referrer ID.', 'warning');
      return;
    }
    if (!email || !email.includes('@')) {
      this.showToast('Please enter a valid Gmail / Email Address.', 'warning');
      return;
    }
    if (!password) {
      this.showToast('Please enter a Security Password.', 'warning');
      return;
    }
    if (!bep20Wallet || !this.matrixEngine.isValidBep20Address(bep20Wallet)) {
      this.showToast('Please enter a valid BEP-20 Wallet Address (42 characters starting with 0x).', 'warning');
      return;
    }

    try {
      // 1. Register with backend API
      const res = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          password,
          sponsor_id: sponsorId,
          wallet_address: bep20Wallet,
          telegram_handle: telegram
        })
      });

      const json = await res.json();
      if (!json.success) {
        throw new Error(json.error || 'Registration failed');
      }

      this.pendingUser = json.data;

      // Check if Admin Free VIP Join
      if (json.data.is_free_vip || ['M8-ADMIN', 'ADMIN', 'M8-VIP001'].includes(sponsorId.toUpperCase())) {
        this.authService.saveSession(json.data.unique_id, true);
        this.showToast(`🎉 VIP Activation Complete! Unique ID: ${json.data.unique_id} (100% FREE via Admin Link)`, 'success');
        this.showUserDashboard(json.data);
        return;
      }

      // Render Payment QR Code for MetaMask Treasury Address
      const qrBox = document.getElementById('paymentQrBox');
      if (qrBox) {
        qrBox.innerHTML = '';
        try {
          if (window.QRCode) {
            new window.QRCode(qrBox, {
              text: `ethereum:0x9ff36bB1b16F1421b2CeBFFE311aCB8D5800AE43@56?value=3.4`,
              width: 120,
              height: 120
            });
          }
        } catch (e) {}
      }

      // Open BSC Payment & Auto-Detection Modal
      this.openModal('modalPaymentVerify');
      this.showToast(`Account Created (${this.pendingUser.unique_id})! Send 3.40 USDT from your wallet — verification is 100% automatic!`, 'info');

      // START AUTOMATIC BACKGROUND ON-CHAIN SCANNER
      this.startAutoDepositPolling(this.pendingUser.unique_id);

    } catch (err) {
      this.showToast(err.message || 'Registration error occurred.', 'warning');
    }
  }

  // --------------------------------------------------------------------------
  // AUTOMATIC BSC BLOCKCHAIN AUTO-POLLING LISTENER
  // --------------------------------------------------------------------------
  startAutoDepositPolling(userId) {
    this.stopAutoDepositPolling();
    if (!userId) return;

    const radarText = document.getElementById('autoScanRadarText');
    let dotCount = 1;

    this.autoPollInterval = setInterval(async () => {
      dotCount = (dotCount % 3) + 1;
      const dots = '.'.repeat(dotCount);
      if (radarText) {
        radarText.textContent = `⚡ Auto-detecting transfer on Binance Smart Chain${dots}`;
      }

      try {
        const res = await fetch(`/api/auto-check-deposit?user_id=${userId}`);
        if (res.ok) {
          const data = await res.json();
          if (data.verified === true) {
            this.stopAutoDepositPolling();
            this.closeModal('modalPaymentVerify');
            this.authService.saveSession(userId, true);
            this.showToast(`🎉 3.40 USDT Verified Automatically on BSC! Welcome to Matrix8!`, 'success');
            this.showUserDashboard();
          }
        }
      } catch (err) {
        // Silent retry
      }
    }, 3500);
  }

  startDashboardLiveRefresh(userId) {
    this.stopDashboardLiveRefresh();
    if (!userId) return;

    this.dashboardPollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/user-dashboard?user_id=${userId}&t=${Date.now()}`);
        if (res.ok) {
          const liveData = await res.json();
          this.renderLiveDashboardData(liveData);
        }
      } catch (err) {
        // Silent retry
      }
    }, 3000);
  }

  stopDashboardLiveRefresh() {
    if (this.dashboardPollInterval) {
      clearInterval(this.dashboardPollInterval);
      this.dashboardPollInterval = null;
    }
  }

  stopAutoDepositPolling() {
    if (this.autoPollInterval) {
      clearInterval(this.autoPollInterval);
      this.autoPollInterval = null;
    }
  }

  copyTreasuryAddress() {
    const addr = document.getElementById('payTreasuryAddressInput').value;
    navigator.clipboard.writeText(addr);
    this.showToast('System Treasury BEP-20 address copied to clipboard!', 'info');
  }

  async handleVerifyDeposit() {
    const txHash = (document.getElementById('depositTxHashInput').value || '').trim();
    if (!txHash || !txHash.startsWith('0x')) {
      this.showToast('Please enter a valid 66-character BSC Transaction Hash (0x...) or wait for automatic detection.', 'warning');
      return;
    }

    const userId = this.pendingUser ? this.pendingUser.unique_id : null;
    if (!userId) {
      this.showToast('No pending registration found. Please register first.', 'warning');
      return;
    }

    this.showToast('🔍 Checking Binance Smart Chain for 3.40 USDT transfer...', 'info');

    try {
      const res = await fetch('/api/verify-deposit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          tx_hash: txHash
        })
      });

      const json = await res.json();
      if (!json.success) {
        throw new Error(json.error || 'On-chain verification failed');
      }

      this.stopAutoDepositPolling();
      this.closeModal('modalPaymentVerify');
      this.authService.saveSession(userId, true);
      this.showToast(`🎉 3.40 USDT Verified on BSC! 8-Level Commissions Distributed!`, 'success');
      this.showUserDashboard();

    } catch (err) {
      this.showToast(`⚠️ Verification Failed: ${err.message}`, 'warning');
    }
  }

  // --------------------------------------------------------------------------
  // MEMBER WITHDRAWAL & PAYOUT SYSTEM (OPTION 2)
  // --------------------------------------------------------------------------
  openWithdrawModal() {
    const data = this.currentDashboardData;
    const balance = data ? (data.wallet_balance || 0.0) : 0.0;
    const wallet = data ? (data.wallet_address || '0x...') : '0x...';

    const elBal = document.getElementById('withdrawModalAvailableBal');
    const elWallet = document.getElementById('withdrawModalTargetWallet');
    const elInput = document.getElementById('withdrawAmountInput');

    if (elBal) elBal.textContent = `$${balance.toFixed(4)} USDT`;
    if (elWallet) elWallet.value = wallet;
    if (elInput) {
      elInput.value = '';
      elInput.max = balance;
    }

    this.openModal('modalWithdraw');
  }

  setWithdrawMax() {
    const data = this.currentDashboardData;
    const balance = data ? (data.wallet_balance || 0.0) : 0.0;
    const elInput = document.getElementById('withdrawAmountInput');
    if (elInput) {
      elInput.value = balance.toFixed(4);
    }
  }

  async handleWithdrawSubmit() {
    const elInput = document.getElementById('withdrawAmountInput');
    const amount = parseFloat(elInput ? elInput.value : 0);
    const user = this.authService.getCurrentUser();
    const userId = user ? (user.unique_id || user.uniqueId) : localStorage.getItem(this.authService.SESSION_KEY);

    if (!userId) {
      this.showToast('Please log in to request a withdrawal.', 'warning');
      return;
    }

    if (isNaN(amount) || amount < 5.0) {
      this.showToast('Minimum withdrawal amount is $5.00 USDT.', 'warning');
      return;
    }

    const availableBal = this.currentDashboardData ? (this.currentDashboardData.wallet_balance || 0.0) : 0.0;
    if (amount > availableBal) {
      this.showToast(`Insufficient balance. You have $${availableBal.toFixed(4)} USDT available.`, 'warning');
      return;
    }

    try {
      this.showToast('Submitting payout request...', 'info');
      const res = await fetch('/api/withdraw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          amount: amount
        })
      });

      const json = await res.json();
      if (!json.success) {
        throw new Error(json.error || 'Withdrawal request failed');
      }

      this.closeModal('modalWithdraw');
      this.showToast(`🎉 Withdrawal request of $${amount.toFixed(2)} USDT submitted! (Ref: ${json.data.withdrawal_id})`, 'success');
      
      // Refresh dashboard immediately
      this.showUserDashboard();

    } catch (err) {
      this.showToast(err.message || 'Failed to submit withdrawal.', 'warning');
    }
  }

  // --------------------------------------------------------------------------
  // 4-FACTOR ADMIN MASTER SECURITY VAULT & PAYOUT MANAGER
  // --------------------------------------------------------------------------
  openAdminAuthGate() {
    const elP1 = document.getElementById('adminPass1Input');
    const elP2 = document.getElementById('adminPass2Input');
    const elPin = document.getElementById('adminPinInput');
    const elFav = document.getElementById('adminFavInput');

    if (elP1) elP1.value = '';
    if (elP2) elP2.value = '';
    if (elPin) elPin.value = '';
    if (elFav) elFav.value = '';

    this.openModal('modalAdminAuthGate');
  }

  async handleAdmin4FactorSubmit() {
    const elP1 = document.getElementById('adminPass1Input');
    const elP2 = document.getElementById('adminPass2Input');
    const elPin = document.getElementById('adminPinInput');
    const elFav = document.getElementById('adminFavInput');

    const pass1 = (elP1 ? elP1.value : '').trim();
    const pass2 = (elP2 ? elP2.value : '').trim();
    const pin = (elPin ? elPin.value : '').trim();
    const fav = (elFav ? elFav.value : '').trim();

    if (!pass1 || !pass2 || !pin || !fav) {
      this.showToast('Please enter all 4 master security credentials.', 'warning');
      return;
    }

    try {
      this.showToast('Authenticating 4-Factor Master Vault...', 'info');
      const res = await fetch('/api/admin/verify-4factor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pass1,
          pass2,
          pin,
          fav
        })
      });

      const json = await res.json();
      if (!json.success) {
        throw new Error(json.error || 'Access Denied: 4-Factor Authentication Failed');
      }

      sessionStorage.setItem('matrix8_admin_token', json.token);
      this.closeModal('modalAdminAuthGate');
      
      const navBtn = document.getElementById('navAdminPayoutsBtn');
      if (navBtn) navBtn.style.display = 'inline-flex';

      this.showToast('🔓 4-Factor Vault Verified! Master Payout Control Granted.', 'success');
      this.openAdminWithdrawals();

    } catch (err) {
      this.showToast(`⛔ ${err.message || 'Access Denied.'}`, 'warning');
    }
  }

  // --------------------------------------------------------------------------
  // DUAL-MODE ADMIN PAYOUT MANAGER (1-CLICK METAMASK + MANUAL PATH)
  // --------------------------------------------------------------------------
  switchAdminPayoutTab(tabName) {
    this.adminPayoutTab = tabName;

    // Update Tab Buttons UI
    document.querySelectorAll('.admin-tab-toggle').forEach(btn => {
      btn.classList.remove('active');
      btn.style.background = 'transparent';
      btn.style.borderColor = 'var(--border-subtle)';
      btn.style.color = 'var(--text-secondary)';
    });

    const activeBtn = document.getElementById(
      tabName === 'metamask' ? 'adminTabBtnMetaMask' :
      tabName === 'manual' ? 'adminTabBtnManual' : 'adminTabBtnHistory'
    );

    if (activeBtn) {
      activeBtn.classList.add('active');
      if (tabName === 'metamask') {
        activeBtn.style.background = 'rgba(245, 158, 11, 0.15)';
        activeBtn.style.borderColor = 'rgba(245, 158, 11, 0.4)';
        activeBtn.style.color = '#F59E0B';
      } else if (tabName === 'manual') {
        activeBtn.style.background = 'rgba(6, 182, 212, 0.15)';
        activeBtn.style.borderColor = 'rgba(6, 182, 212, 0.4)';
        activeBtn.style.color = 'var(--primary-cyan)';
      } else {
        activeBtn.style.background = 'rgba(16, 185, 129, 0.15)';
        activeBtn.style.borderColor = 'rgba(16, 185, 129, 0.4)';
        activeBtn.style.color = '#10B981';
      }
    }

    // Update Banner Instructions
    const banner = document.getElementById('adminModeBanner');
    if (banner) {
      if (tabName === 'metamask') {
        banner.innerHTML = `<span style="color: #F59E0B; font-weight: 700;">🦊 MetaMask Web3 Mode:</span> Click "1-Click Disburse" to trigger a direct BEP-20 USDT transfer from your connected wallet without copy-pasting. Once confirmed, it automatically marks completed across all queues!`;
      } else if (tabName === 'manual') {
        banner.innerHTML = `<span style="color: var(--primary-cyan); font-weight: 700;">📋 Manual Transfer Mode:</span> Copy the member's verified BEP-20 address, transfer USDT from Binance / Trust Wallet / any exchange, and click "Mark Paid". Once approved, it removes from both queues!`;
      } else {
        banner.innerHTML = `<span style="color: #10B981; font-weight: 700;">🟢 Completed Archive:</span> Chronological record of all settled and refunded payouts with BSCScan transaction proofs.`;
      }
    }

    this.renderAdminWithdrawalsList();
  }

  async openAdminWithdrawals() {
    const adminToken = sessionStorage.getItem('matrix8_admin_token');
    if (!adminToken) {
      this.openAdminAuthGate();
      return;
    }

    if (!this.adminPayoutTab) {
      this.adminPayoutTab = 'metamask';
    }

    this.openModal('modalAdminWithdrawals');
    const container = document.getElementById('adminWithdrawalsTableContainer');
    if (container) {
      container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading live withdrawal queue...</div>`;
    }

    try {
      const res = await fetch(`/api/admin/withdrawals?t=${Date.now()}`, {
        headers: {
          'X-Admin-Pin': adminToken
        }
      });

      if (res.status === 401) {
        sessionStorage.removeItem('matrix8_admin_token');
        this.closeModal('modalAdminWithdrawals');
        this.showToast('Admin session expired. Please re-authenticate.', 'warning');
        this.openAdminAuthGate();
        return;
      }

      this.adminWithdrawalsCache = await res.json();
      this.renderAdminWithdrawalsList();

    } catch (err) {
      if (container) {
        container.innerHTML = `<div style="color: #EF4444; padding: 1rem;">Failed to load queue: ${err.message}</div>`;
      }
    }
  }

  renderAdminWithdrawalsList() {
    const container = document.getElementById('adminWithdrawalsTableContainer');
    const elPendingStats = document.getElementById('adminPendingStats');
    const elCompletedStats = document.getElementById('adminCompletedStats');
    const elNavBadge = document.getElementById('navPendingBadge');

    if (!container) return;

    const list = this.adminWithdrawalsCache || [];
    const pendingList = list.filter(w => w.status === 'PENDING');
    const completedList = list.filter(w => w.status === 'COMPLETED' || w.status === 'REJECTED');
    const pendingSum = pendingList.reduce((acc, w) => acc + (Number(w.amount_usdt) || 0), 0);
    const completedSum = completedList.filter(w => w.status === 'COMPLETED').reduce((acc, w) => acc + (Number(w.amount_usdt) || 0), 0);

    if (elPendingStats) elPendingStats.textContent = `${pendingList.length} Requests ($${pendingSum.toFixed(2)} USDT)`;
    if (elCompletedStats) elCompletedStats.textContent = `${completedList.length} Requests ($${completedSum.toFixed(2)} USDT)`;
    if (elNavBadge) elNavBadge.textContent = pendingList.length;

    // ----------------------------------------------------
    // TAB 1: 1-CLICK METAMASK PAYOUTS
    // ----------------------------------------------------
    if (this.adminPayoutTab === 'metamask') {
      if (pendingList.length === 0) {
        container.innerHTML = `
          <div style="text-align: center; color: var(--text-muted); padding: 3rem 1rem;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎉</div>
            <div style="font-weight: 700; color: #fff; margin-bottom: 0.25rem;">MetaMask Queue is Clear!</div>
            <div style="font-size: 0.8rem;">All member payouts are currently settled. New withdrawal requests will appear here instantly.</div>
          </div>
        `;
        return;
      }

      let html = `
        <table style="width: 100%; border-collapse: collapse; font-size: 0.82rem;">
          <thead>
            <tr style="border-bottom: 1px solid var(--border-subtle); color: var(--text-muted); text-align: left;">
              <th style="padding: 8px;">Ticket ID</th>
              <th style="padding: 8px;">Member / BEP-20 Wallet</th>
              <th style="padding: 8px;">Amount (USDT)</th>
              <th style="padding: 8px; text-align: right;">1-Click Web3 Action</th>
            </tr>
          </thead>
          <tbody>
      `;

      pendingList.forEach(w => {
        const dateStr = new Date((w.request_timestamp || Date.now()/1000) * 1000).toLocaleString();
        html += `
          <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); background: rgba(245, 158, 11, 0.04);">
            <td class="mono" style="padding: 10px 8px;">
              <div style="font-weight: 700; color: #F59E0B;">${w.withdrawal_id}</div>
              <div style="font-size: 0.7rem; color: var(--text-muted);">${dateStr}</div>
            </td>
            <td class="mono" style="padding: 10px 8px;">
              <div style="font-weight: 700; color: var(--primary-cyan);">${w.user_id}</div>
              <div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 2px;">
                ${w.wallet_address.slice(0, 10)}...${w.wallet_address.slice(-8)}
              </div>
            </td>
            <td class="mono" style="padding: 10px 8px; color: var(--primary-emerald); font-weight: 800; font-size: 0.95rem;">
              $${Number(w.amount_usdt).toFixed(4)} USDT
            </td>
            <td style="padding: 10px 8px; text-align: right;">
              <div style="display: flex; gap: 6px; justify-content: flex-end;">
                <button class="btn btn-primary btn-sm" style="background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%); color: #000; font-weight: 800; padding: 5px 12px; font-size: 0.75rem;" onclick="if(window.App) window.App.disburseViaMetaMask('${w.withdrawal_id}', '${w.wallet_address}', ${w.amount_usdt});">
                  🦊 1-Click Disburse
                </button>
                <button class="btn btn-secondary btn-sm" style="padding: 5px 8px; font-size: 0.75rem; color: #EF4444;" onclick="if(window.App) window.App.processAdminWithdrawal('${w.withdrawal_id}', 'REJECTED');" title="Reject and Refund">
                  ✕ Refund
                </button>
              </div>
            </td>
          </tr>
        `;
      });

      html += `</tbody></table>`;
      container.innerHTML = html;
      return;
    }

    // ----------------------------------------------------
    // TAB 2: MANUAL TRANSFER & CONFIRM
    // ----------------------------------------------------
    if (this.adminPayoutTab === 'manual') {
      if (pendingList.length === 0) {
        container.innerHTML = `
          <div style="text-align: center; color: var(--text-muted); padding: 3rem 1rem;">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎉</div>
            <div style="font-weight: 700; color: #fff; margin-bottom: 0.25rem;">Manual Queue is Clear!</div>
            <div style="font-size: 0.8rem;">All member payouts are currently settled. New withdrawal requests will appear here instantly.</div>
          </div>
        `;
        return;
      }

      let html = `
        <table style="width: 100%; border-collapse: collapse; font-size: 0.82rem;">
          <thead>
            <tr style="border-bottom: 1px solid var(--border-subtle); color: var(--text-muted); text-align: left;">
              <th style="padding: 8px;">Ticket ID</th>
              <th style="padding: 8px;">Member / Address to Copy</th>
              <th style="padding: 8px;">Amount</th>
              <th style="padding: 8px; text-align: right;">Manual Action</th>
            </tr>
          </thead>
          <tbody>
      `;

      pendingList.forEach(w => {
        const dateStr = new Date((w.request_timestamp || Date.now()/1000) * 1000).toLocaleString();
        html += `
          <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); background: rgba(6, 182, 212, 0.03);">
            <td class="mono" style="padding: 10px 8px;">
              <div style="font-weight: 700; color: #fff;">${w.withdrawal_id}</div>
              <div style="font-size: 0.7rem; color: var(--text-muted);">${dateStr}</div>
            </td>
            <td class="mono" style="padding: 10px 8px;">
              <div style="font-weight: 700; color: var(--primary-cyan);">${w.user_id}</div>
              <div style="display: flex; align-items: center; gap: 4px; font-size: 0.72rem; color: var(--text-secondary); margin-top: 2px;">
                <span>${w.wallet_address.slice(0, 8)}...${w.wallet_address.slice(-6)}</span>
                <button type="button" class="btn btn-secondary btn-sm" style="padding: 1px 6px; font-size: 0.65rem;" onclick="navigator.clipboard.writeText('${w.wallet_address}'); if(window.App) window.App.showToast('BEP-20 address copied to clipboard!', 'info');">
                  📋 Copy
                </button>
              </div>
            </td>
            <td class="mono" style="padding: 10px 8px; color: var(--primary-emerald); font-weight: 800; font-size: 0.95rem;">
              $${Number(w.amount_usdt).toFixed(4)} USDT
            </td>
            <td style="padding: 10px 8px; text-align: right;">
              <div style="display: flex; gap: 6px; justify-content: flex-end;">
                <button class="btn btn-emerald btn-sm" style="padding: 5px 12px; font-size: 0.75rem; font-weight: 700;" onclick="if(window.App) window.App.processAdminWithdrawal('${w.withdrawal_id}', 'COMPLETED');">
                  ✓ Mark Paid
                </button>
                <button class="btn btn-secondary btn-sm" style="padding: 5px 8px; font-size: 0.75rem; color: #EF4444;" onclick="if(window.App) window.App.processAdminWithdrawal('${w.withdrawal_id}', 'REJECTED');">
                  ✕ Refund
                </button>
              </div>
            </td>
          </tr>
        `;
      });

      html += `</tbody></table>`;
      container.innerHTML = html;
      return;
    }

    // ----------------------------------------------------
    // TAB 3: COMPLETED ARCHIVE
    // ----------------------------------------------------
    if (this.adminPayoutTab === 'history') {
      if (completedList.length === 0) {
        container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 2rem;">No processed withdrawals in archive.</div>`;
        return;
      }

      let html = `
        <table style="width: 100%; border-collapse: collapse; font-size: 0.82rem;">
          <thead>
            <tr style="border-bottom: 1px solid var(--border-subtle); color: var(--text-muted); text-align: left;">
              <th style="padding: 8px;">Ticket ID</th>
              <th style="padding: 8px;">Member / Wallet</th>
              <th style="padding: 8px;">Amount</th>
              <th style="padding: 8px;">Status / On-Chain Proof</th>
            </tr>
          </thead>
          <tbody>
      `;

      completedList.forEach(w => {
        const isCompleted = w.status === 'COMPLETED';
        const dateStr = new Date((w.processed_timestamp || w.request_timestamp || Date.now()/1000) * 1000).toLocaleString();
        html += `
          <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
            <td class="mono" style="padding: 8px;">
              <div style="font-weight: 700; color: #fff;">${w.withdrawal_id}</div>
              <div style="font-size: 0.68rem; color: var(--text-muted);">${dateStr}</div>
            </td>
            <td class="mono" style="padding: 8px;">
              <div style="font-weight: 700; color: var(--primary-cyan);">${w.user_id}</div>
              <div style="font-size: 0.7rem; color: var(--text-secondary);">${w.wallet_address.slice(0, 8)}...${w.wallet_address.slice(-6)}</div>
            </td>
            <td class="mono" style="padding: 8px; color: ${isCompleted ? 'var(--primary-emerald)' : '#EF4444'}; font-weight: 700;">
              $${Number(w.amount_usdt).toFixed(4)} USDT
            </td>
            <td style="padding: 8px;">
              <span style="font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 99px; ${isCompleted ? 'background: rgba(16,185,129,0.2); color: #10B981;' : 'background: rgba(239,68,68,0.2); color: #EF4444;'}">
                ${w.status}
              </span>
              ${w.tx_hash ? `
                <div class="mono" style="font-size: 0.68rem; color: var(--text-muted); margin-top: 3px;">
                  <a href="https://bscscan.com/tx/${w.tx_hash}" target="_blank" rel="noopener noreferrer" style="color: var(--primary-cyan); text-decoration: none;">
                    Tx: ${w.tx_hash.slice(0, 12)}... ↗
                  </a>
                </div>
              ` : ''}
            </td>
          </tr>
        `;
      });

      html += `</tbody></table>`;
      container.innerHTML = html;
    }
  }

  // --------------------------------------------------------------------------
  // 1-CLICK METAMASK WEB3 DIRECT DISBURSEMENT
  // --------------------------------------------------------------------------
  async disburseViaMetaMask(withdrawalId, recipientAddress, amountUsdt) {
    if (typeof window.ethereum === 'undefined') {
      alert('MetaMask is not detected in your browser. Please switch to the "Manual Transfer" tab to disburse via Binance / exchange, or install MetaMask extension.');
      return;
    }

    try {
      this.showToast('Connecting to MetaMask...', 'info');
      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
      if (!accounts || accounts.length === 0) {
        throw new Error('No MetaMask account selected.');
      }
      const adminAddress = accounts[0];

      // Ensure connected to BSC Mainnet (ChainID 56 = 0x38)
      try {
        await window.ethereum.request({
          method: 'wallet_switchEthereumChain',
          params: [{ chainId: '0x38' }]
        });
      } catch (switchError) {
        if (switchError.code === 4902) {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [{
              chainId: '0x38',
              chainName: 'Binance Smart Chain Mainnet',
              nativeCurrency: { name: 'BNB', symbol: 'BNB', decimals: 18 },
              rpcUrls: ['https://bsc-dataseed.binance.org/'],
              blockExplorerUrls: ['https://bscscan.com']
            }]
          });
        }
      }

      // Encode BEP-20 transfer(address to, uint256 amount)
      // Method signature: transfer(address,uint256) -> a9059cbb
      const cleanTo = recipientAddress.toLowerCase().replace('0x', '').padStart(64, '0');
      // USDT on BSC has 18 decimals
      const amountWeiBigInt = BigInt(Math.floor(amountUsdt * 1e18));
      const amountWeiHex = amountWeiBigInt.toString(16).padStart(64, '0');
      const transferCalldata = '0xa9059cbb' + cleanTo + amountWeiHex;

      this.showToast(`Please confirm $${amountUsdt} USDT transfer in MetaMask...`, 'info');

      const txHash = await window.ethereum.request({
        method: 'eth_sendTransaction',
        params: [{
          from: adminAddress,
          to: '0x55d398326f99059ff775485246999027b3197955', // BSC USDT Contract
          data: transferCalldata
        }]
      });

      this.showToast(`⚡ Transaction Broadcast! TxID: ${txHash.slice(0, 10)}... Updating system...`, 'info');

      // Update backend record to COMPLETED
      const adminToken = sessionStorage.getItem('matrix8_admin_token');
      const res = await fetch('/api/admin/process-withdrawal', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Pin': adminToken
        },
        body: JSON.stringify({
          withdrawal_id: withdrawalId,
          status: 'COMPLETED',
          tx_hash: txHash,
          admin_pin: adminToken,
          admin_note: 'Paid via 1-Click MetaMask Web3'
        })
      });

      const json = await res.json();
      if (!json.success) throw new Error(json.error || 'Failed to update withdrawal status.');

      this.showToast(`🎉 Payout for ${withdrawalId} COMPLETED via MetaMask!`, 'success');
      
      // Instantly re-fetch and refresh state across BOTH tabs
      await this.openAdminWithdrawals();
      this.showUserDashboard();

    } catch (err) {
      console.error('MetaMask disburse error:', err);
      this.showToast(err.message || 'MetaMask transaction cancelled.', 'warning');
    }
  }

  async processAdminWithdrawal(withdrawalId, status) {
    const adminToken = sessionStorage.getItem('matrix8_admin_token');
    if (!adminToken) {
      this.openAdminAuthGate();
      return;
    }

    let txHash = '';
    if (status === 'COMPLETED') {
      txHash = prompt(`Enter BSC / Binance TxID (or leave blank to auto-confirm):`, '') || '';
    } else {
      if (!confirm(`Are you sure you want to REJECT and REFUND withdrawal ${withdrawalId}? 100% of USDT will be returned to user's balance.`)) return;
    }

    try {
      this.showToast('Updating withdrawal status...', 'info');
      const res = await fetch('/api/admin/process-withdrawal', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Admin-Pin': adminToken
        },
        body: JSON.stringify({
          withdrawal_id: withdrawalId,
          status: status,
          tx_hash: txHash,
          admin_pin: adminToken,
          admin_note: status === 'COMPLETED' ? 'Approved & Paid by Admin (Manual)' : 'Refunded by Admin'
        })
      });

      const json = await res.json();
      if (!json.success) throw new Error(json.error || 'Failed to update withdrawal');

      this.showToast(`🎉 Withdrawal ${withdrawalId} marked as ${status}!`, 'success');
      
      // Instantly re-fetch and refresh state across BOTH tabs
      await this.openAdminWithdrawals();
      this.showUserDashboard();

    } catch (err) {
      this.showToast(err.message || 'Action failed.', 'warning');
    }
  }

  openModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.add('active');
  }

  closeModal(modalId) {
    if (modalId === 'modalPaymentVerify') {
      this.stopAutoDepositPolling();
    }
    const el = document.getElementById(modalId);
    if (el) el.classList.remove('active');
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 4500);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.App = new AppController();
});

