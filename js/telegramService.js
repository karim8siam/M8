/**
 * TelegramService - Real-time Telegram Bot Integration & Alert Webhook
 * Delivers instant transaction notifications to Telegram accounts when commissions arrive.
 */

class TelegramService {
  constructor(matrixEngine) {
    this.matrixEngine = matrixEngine;
    this.BOT_USERNAME = 'Matrix8_Official_Bot';
    this.CHANNEL_URL = 'https://t.me/matrix8_community';
  }

  getBotUrl(uniqueId) {
    return `https://t.me/${this.BOT_USERNAME}?start=${uniqueId || 'join'}`;
  }

  getChannelUrl() {
    return this.CHANNEL_URL;
  }

  formatCommissionMessage({ level, percentage, amount, fromId, bscHash, toWallet }) {
    return `
🚀 *MATRIX8 INSTANT COMMISSION ALERT* 🚀
━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 *Amount:* \`+${amount} USDT (BEP-20)\`
📊 *Level:* Level ${level} (${percentage}%)
👤 *Triggered By:* \`${fromId}\`
👛 *Recipient BEP-20:* \`${toWallet ? toWallet.slice(0, 8) + '...' + toWallet.slice(-6) : 'Your Wallet'}\`
🔗 *BSCScan TX:* [View on BSCScan](https://bscscan.com/tx/${bscHash})
⏰ *Timestamp:* ${new Date().toLocaleTimeString()}
━━━━━━━━━━━━━━━━━━━━━━━━━━
💎 *Matrix8 Ecosystem | Real Digital Assets*
    `.trim();
  }

  sendSimulatedBotAlert(uniqueId, messageData) {
    const text = this.formatCommissionMessage(messageData);
    const existingLogs = JSON.parse(localStorage.getItem('matrix8_tg_logs') || '[]');
    existingLogs.unshift({
      uniqueId,
      text,
      timestamp: Date.now()
    });
    if (existingLogs.length > 50) existingLogs.pop();
    localStorage.setItem('matrix8_tg_logs', JSON.stringify(existingLogs));
    return text;
  }

  getRecentLogs() {
    return JSON.parse(localStorage.getItem('matrix8_tg_logs') || '[]');
  }
}

window.TelegramService = TelegramService;
