/**
 * DigitalProductsService - Real Digital Marketing & Digital Products Hub
 * Every member paying 3.4 USDT receives full commercial access to these digital products.
 */

class DigitalProductsService {
  constructor(matrixEngine) {
    this.matrixEngine = matrixEngine;
    this.PRODUCTS = [
      {
        id: 'ai_marketing_vault',
        title: 'AI Viral Marketing & Copywriting Vault 2026',
        category: 'Digital Marketing / AI',
        valueUsd: 149.00,
        badge: 'UNLOCKED',
        icon: '🤖',
        description: 'Complete suite of 500+ engineered AI prompts, viral hooks, and high-converting sales scripts for crypto & affiliate marketing.',
        downloadUrl: '#',
        features: ['500+ High-Conversion AI Prompts', 'Crypto Ad Copy Templates', 'Video Sales Letter (VSL) Scripts']
      },
      {
        id: 'seo_traffic_funnels',
        title: 'Web3 Organic Traffic & SEO Domination',
        category: 'Traffic Generation',
        valueUsd: 199.00,
        badge: 'UNLOCKED',
        icon: '📈',
        description: 'Step-by-step masterclass on generating 10,000+ targeted monthly crypto visitors without paid advertising.',
        downloadUrl: '#',
        features: ['Google SEO Ranking Blueprints', 'YouTube Crypto Keyword Engine', 'Backlink Outreach Automation']
      },
      {
        id: 'telegram_automation_bot',
        title: 'Telegram Affiliate & Community Growth Bot',
        category: 'Software & Tools',
        valueUsd: 299.00,
        badge: 'UNLOCKED',
        icon: '⚡',
        description: 'Production-ready Python/Node.js Telegram bot that auto-onboards leads, answers FAQs, and tracks referrals 24/7.',
        downloadUrl: '#',
        features: ['Full Bot Source Code', 'Auto-Responder & Broadcast Engine', 'Instant Referral Link Embedder']
      },
      {
        id: 'web3_growth_toolkit',
        title: 'Crypto Network Marketing Scale Blueprint',
        category: 'Academy & Masterclass',
        valueUsd: 249.00,
        badge: 'UNLOCKED',
        icon: '🌐',
        description: 'The exact step-by-step roadmap to scale your 8-level downline to 1,000+ active members across 15+ countries.',
        downloadUrl: '#',
        features: ['Team Duplication Strategies', 'Webinar Slide Decks', 'Multi-Language Marketing Assets']
      }
    ];
  }

  getProducts() {
    return this.PRODUCTS;
  }

  getTotalDigitalValue() {
    return this.PRODUCTS.reduce((sum, p) => sum + p.valueUsd, 0);
  }

  claimProduct(userId, productId) {
    const user = this.matrixEngine.getUserById(userId);
    if (!user) throw new Error('User not found');
    
    return {
      success: true,
      product: this.PRODUCTS.find(p => p.id === productId),
      downloadKey: `DL-${Math.random().toString(36).substring(2, 10).toUpperCase()}`
    };
  }
}

window.DigitalProductsService = DigitalProductsService;
