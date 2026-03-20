import { api } from './api';

/**
 * AI模拟账户API服务
 */
export const aiSimulationApi = {
  /**
   * 创建AI模拟账户
   * @param {Object} data - { source_account_id, name, description }
   */
  createAccount: (data) => {
    return api.post('/ai-simulation/accounts', data);
  },

  /**
   * 获取AI模拟账户列表
   * @param {number} sourceAccountId - 源账户ID（可选）
   */
  getAccounts: (sourceAccountId) => {
    const params = sourceAccountId ? { source_account_id: sourceAccountId } : {};
    return api.get('/ai-simulation/accounts', { params });
  },

  /**
   * 获取AI模拟账户详情
   * @param {number} aiAccountId - AI账户ID
   * @param {Object} options - 查询选项
   * @param {boolean} options.include_positions - 是否包含持仓数据（默认true）
   * @param {boolean} options.include_trades - 是否包含交易记录（默认true）
   * @param {boolean} options.include_history - 是否包含历史走势（默认true）
   * @param {number} options.trades_limit - 交易记录数量限制（默认20）
   * @param {number} options.history_days - 历史数据天数限制（默认90）
   */
  getAccountDetail: (aiAccountId, options = {}) => {
    const params = {
      include_positions: options.include_positions !== false,
      include_trades: options.include_trades !== false,
      include_history: options.include_history !== false,
      trades_limit: options.trades_limit || 20,
      history_days: options.history_days || 90
    };
    return api.get(`/ai-simulation/accounts/${aiAccountId}`, { params });
  },

  /**
   * 执行每周审视和调仓
   * @param {number} aiAccountId - AI账户ID
   */
  performReview: (aiAccountId) => {
    return api.post(`/ai-simulation/accounts/${aiAccountId}/review`, {}, {
      timeout: 300000  // 5分钟超时，AI分析需要较长时间
    });
  },

  /**
   * 记录每日资产
   * @param {number} aiAccountId - AI账户ID
   */
  /**
   * 手动更新持仓价格和收益
   * @param {number} aiAccountId - AI账户ID
   */
  updatePrices: (aiAccountId) => {
    return api.post(`/ai-simulation/accounts/${aiAccountId}/update-prices`);
  },

  /**
   * 删除AI模拟账户
   * @param {number} aiAccountId - AI账户ID
   */
  deleteAccount: (aiAccountId) => {
    return api.delete(`/ai-simulation/accounts/${aiAccountId}`);
  },

  /**
   * 更新AI模拟账户信息
   * @param {number} aiAccountId - AI账户ID
   * @param {Object} data - 更新数据
   */
  updateAccount: (aiAccountId, data) => {
    return api.put(`/ai-simulation/accounts/${aiAccountId}`, data);
  },

  /**
   * 获取账户对比数据
   * @param {number} aiAccountId - AI账户ID
   */
  getComparison: (aiAccountId) => {
    return api.get(`/ai-simulation/accounts/${aiAccountId}/comparison`);
  },

  /**
   * 更新AI账户持仓
   * @param {number} aiAccountId - AI账户ID
   * @param {Object} data - 持仓数据
   */
  updatePosition: (aiAccountId, data) => {
    return api.put(`/ai-simulation/accounts/${aiAccountId}/positions`, data);
  }
};

export default aiSimulationApi;
