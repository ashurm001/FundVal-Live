import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, RefreshCw, TrendingUp, TrendingDown, ChevronRight, X, Calendar } from 'lucide-react';
import { aiSimulationApi } from '../services/aiSimulationApi';
import { getAccounts, getCryptoAccounts } from '../services/api';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, ReferenceDot } from 'recharts';

const AISimulation = () => {
  const [accounts, setAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [accountDetail, setAccountDetail] = useState(null);
  const [userAccounts, setUserAccounts] = useState([]);
  const [cryptoAccounts, setCryptoAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [reviewLoading, setReviewLoading] = useState(false);
  const [updateLoading, setUpdateLoading] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    source_account_id: '',
    source_type: 'fund',
    name: 'AI模拟账户',
    description: '',
    review_frequency: 'week', // daily, weekly, monthly
    review_day: 0, // 星期几 (0-6) 或 日期 (1-31)
    review_hour: 18
  });
  const [editForm, setEditForm] = useState({
    id: '',
    name: '',
    description: '',
    review_frequency: 'week', // daily, weekly, monthly
    review_day: 0, // 星期几 (0-6) 或 日期 (1-31)
    review_hour: 18
  });
  const [activeTab, setActiveTab] = useState('overview');
  const [timeRange, setTimeRange] = useState('all');
  const [error, setError] = useState(null);

  const fetchAccounts = useCallback(async () => {
    try {
      setError(null);
      const response = await aiSimulationApi.getAccounts();
      const accountsData = Array.isArray(response?.data) ? response.data : [];
      setAccounts(accountsData);
      return accountsData;
    } catch (err) {
      console.error('获取AI账户失败:', err);
      setError('获取AI账户失败');
      setAccounts([]);
      return [];
    }
  }, []);

  const fetchUserAccounts = async () => {
    try {
      const [fundData, cryptoData] = await Promise.all([
        getAccounts(),
        getCryptoAccounts()
      ]);
      const fundAccounts = Array.isArray(fundData) ? fundData : [];
      const cryptoAccountsData = Array.isArray(cryptoData) ? cryptoData : [];
      setUserAccounts(fundAccounts);
      setCryptoAccounts(cryptoAccountsData);
      
      // 只在第一次加载时设置默认账户
      if (!createForm.source_account_id) {
        let targetType = 'fund';
        let defaultAccountId = '';
        
        if (fundAccounts.length > 0) {
          targetType = 'fund';
          defaultAccountId = fundAccounts[0]?.id || '';
        } else if (cryptoAccountsData.length > 0) {
          targetType = 'crypto';
          defaultAccountId = cryptoAccountsData[0]?.id || '';
        }
        
        if (defaultAccountId) {
          setCreateForm(prev => ({
            ...prev,
            source_type: targetType,
            source_account_id: defaultAccountId
          }));
        }
      }
    } catch (err) {
      console.error('获取用户账户失败:', err);
      setUserAccounts([]);
      setCryptoAccounts([]);
    }
  };

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      const accountsData = await fetchAccounts();
      await fetchUserAccounts();
      if (accountsData.length > 0) {
        setSelectedAccount(accountsData[0]);
      }
      setLoading(false);
    };
    init();
  }, [fetchAccounts]);

  useEffect(() => {
    if (selectedAccount) {
      // 首次加载：只加载基本信息和持仓（不加载历史数据）
      fetchAccountDetail(selectedAccount.id, { 
        include_history: false, 
        include_trades: false 
      });
    }
  }, [selectedAccount]);

  const fetchAccountDetail = async (accountId, options = {}) => {
    setDetailLoading(true);
    try {
      const response = await aiSimulationApi.getAccountDetail(accountId, options);
      setAccountDetail(response?.data || null);
    } catch (err) {
      console.error('获取账户详情失败:', err);
      setAccountDetail(null);
    } finally {
      setDetailLoading(false);
    }
  };

  // 加载交易记录
  const fetchTrades = async (accountId) => {
    try {
      const response = await aiSimulationApi.getAccountDetail(accountId, {
        include_positions: false,
        include_trades: true,
        include_history: false,
        trades_limit: 20
      });
      const trades = response?.data?.trades || [];
      setAccountDetail(prev => prev ? { ...prev, trades } : null);
    } catch (err) {
      console.error('获取交易记录失败:', err);
    }
  };

  // 加载历史走势
  const fetchHistory = async (accountId) => {
    try {
      const response = await aiSimulationApi.getAccountDetail(accountId, {
        include_positions: false,
        include_trades: false,
        include_history: true,
        history_days: 90
      });
      const valueHistory = response?.data?.value_history || [];
      setAccountDetail(prev => prev ? { ...prev, value_history: valueHistory } : null);
    } catch (err) {
      console.error('获取历史走势失败:', err);
    }
  };

  const handleCreateAccount = async () => {
    if (!createForm.source_account_id) {
      alert('请选择源账户');
      return;
    }
    if (!createForm.name) {
      alert('请输入账户名称');
      return;
    }
    
    // 防止重复点击
    if (createLoading) return;
    
    try {
      setCreateLoading(true);
      // 转换为后端需要的格式
      const intervalMap = {
        'daily': 'day',
        'weekly': 'week',
        'monthly': 'month'
      };
      
      await aiSimulationApi.createAccount({
        source_account_id: parseInt(createForm.source_account_id),
        source_type: createForm.source_type,
        name: createForm.name,
        description: createForm.description,
        review_interval_type: intervalMap[createForm.review_frequency],
        review_interval: 1, // 默认间隔为1
        review_day_of_week: createForm.review_frequency === 'weekly' ? createForm.review_day : 0
      });
      setShowCreateModal(false);
      setCreateForm({ 
        source_account_id: '', 
        source_type: 'fund', 
        name: 'AI模拟账户', 
        description: '',
        review_frequency: 'week',
        review_day: 0,
        review_hour: 18
      });
      const accountsData = await fetchAccounts();
      if (accountsData.length > 0) {
        setSelectedAccount(accountsData[0]);
      }
    } catch (err) {
      console.error('创建AI账户失败:', err);
      alert('创建失败: ' + (err.response?.data?.detail || err.message));
    } finally {
      setCreateLoading(false);
    }
  };

  const handlePerformReview = async () => {
    if (!selectedAccount) return;
    setReviewLoading(true);
    try {
      const response = await aiSimulationApi.performReview(selectedAccount.id);
      const data = response?.data || {};
      alert(`审视完成！\n市场分析: ${(data.market_analysis || '').substring(0, 50)}...\n执行交易: ${data.trades_executed || 0} 笔`);
      fetchAccountDetail(selectedAccount.id);
    } catch (err) {
      console.error('执行审视失败:', err);
      alert('审视失败: ' + (err.response?.data?.detail || err.message));
    } finally {
      setReviewLoading(false);
    }
  };

  const handleDeleteAccount = async (accountId) => {
    if (!confirm('确定要删除这个AI模拟账户吗？')) {
      return;
    }
    try {
      await aiSimulationApi.deleteAccount(accountId);
      setAccounts(prev => prev.filter(acc => acc.id !== accountId));
      if (selectedAccount?.id === accountId) {
        const remainingAccounts = accounts.filter(acc => acc.id !== accountId);
        if (remainingAccounts.length > 0) {
          setSelectedAccount(remainingAccounts[0]);
        } else {
          setSelectedAccount(null);
          setAccountDetail(null);
        }
      }
    } catch (error) {
      console.error('删除失败:', error);
      alert('删除失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleEditAccount = (account) => {
    // 转换为新的格式
    const frequencyMap = {
      'day': 'daily',
      'week': 'weekly',
      'month': 'monthly'
    };
    
    setEditForm({
      id: account.id,
      name: account.name,
      description: account.description || '',
      review_frequency: frequencyMap[account.review_interval_type] || 'weekly',
      review_day: account.review_day_of_week || 0,
      review_hour: 18
    });
    setShowEditModal(true);
  };

  const handleUpdateAccount = async () => {
    if (!editForm.name) {
      alert('请输入账户名称');
      return;
    }
    try {
      // 转换为后端需要的格式
      const intervalMap = {
        'daily': 'day',
        'weekly': 'week',
        'monthly': 'month'
      };
      
      await aiSimulationApi.updateAccount(editForm.id, {
        name: editForm.name,
        description: editForm.description,
        review_day_of_week: editForm.review_frequency === 'weekly' ? editForm.review_day : 0,
        review_interval_type: intervalMap[editForm.review_frequency],
        review_interval: 1 // 默认间隔为1
      });
      setShowEditModal(false);
      await fetchAccounts();
      if (selectedAccount?.id === editForm.id) {
        await fetchAccountDetail(editForm.id);
      }
      alert('账户更新成功');
    } catch (err) {
      console.error('更新账户失败:', err);
      alert('更新失败: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleUpdatePrices = async () => {
    if (!selectedAccount) return;
    setUpdateLoading(true);
    try {
      await aiSimulationApi.updatePrices(selectedAccount.id);
      await fetchAccountDetail(selectedAccount.id);
      alert('价格和收益已更新');
    } catch (err) {
      console.error('更新价格失败:', err);
      alert('更新失败: ' + (err.response?.data?.detail || err.message));
    } finally {
      setUpdateLoading(false);
    }
  };

  const getCurrencySymbol = () => {
    return accountDetail?.source_type === 'crypto' ? '$' : '¥';
  };

  const getFilteredData = () => {
    if (!accountDetail?.value_history) return [];
    const data = accountDetail.value_history;
    if (timeRange === 'all') return data;
    
    const now = new Date();
    const days = {
      '7d': 7,
      '30d': 30,
      '90d': 90,
      '1y': 365
    }[timeRange] || data.length;
    
    return data.slice(-days);
  };

  const SimpleLineChart = ({ type = 'value' }) => {
    const data = getFilteredData();
    if (!data || data.length === 0) return <div className="text-center py-8 text-slate-400">暂无数据</div>;

    return (
      <div className="w-full">
        <div className="h-64 w-full" style={{ minHeight: '256px', minWidth: '100%' }}>
          <ResponsiveContainer width="100%" height={256} minWidth={0} minHeight={0}>
            <AreaChart
              data={data}
              margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="colorAI" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorSource" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis
                dataKey="record_date"
                tick={{fontSize: 10, fill: '#94a3b8'}}
                tickLine={false}
                axisLine={false}
                tickFormatter={(str) => str?.slice(5) || ''}
                minTickGap={30}
              />
              <YAxis
                domain={['auto', 'auto']}
                tick={{fontSize: 10, fill: '#94a3b8'}}
                tickLine={false}
                axisLine={false}
                width={40}
                tickFormatter={(value) => {
                  if (type === 'value') {
                    return `${(value / 1000).toFixed(0)}K`;
                  }
                  return `${value.toFixed(1)}%`;
                }}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div style={{ 
                        borderRadius: '8px', 
                        border: 'none', 
                        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                        padding: '8px 12px',
                        backgroundColor: 'white'
                      }}>
                        {payload.map((entry, index) => (
                          <div key={index} style={{ 
                            color: '#1e293b', 
                            fontSize: '12px', 
                            fontWeight: 'bold',
                            marginBottom: index < payload.length - 1 ? '4px' : '0'
                          }}>
                            <span style={{ color: entry.color === '#10b981' ? '#10b981' : '#3b82f6' }}>
                              ●
                            </span>
                            {' '}
                            {entry.name === 'AI账户' ? 'AI账户' : '用户账户'}: {' '}
                            {type === 'value' 
                              ? `${entry.value.toFixed(2)}元`
                              : `${entry.value.toFixed(2)}%`
                            }
                          </div>
                        ))}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Area
                type="monotone"
                dataKey={type === 'value' ? 'ai_value' : 'ai_return_rate'}
                stroke="#10b981"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorAI)"
                animationDuration={500}
                name="AI账户"
              />
              <Area
                type="monotone"
                dataKey={type === 'value' ? 'source_value' : 'source_return_rate'}
                stroke="#3b82f6"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorSource)"
                animationDuration={500}
                name="用户账户"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="flex justify-end mt-2 gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-emerald-500 rounded-full"></div>
            <span className="text-slate-600">AI账户</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
            <span className="text-slate-600">用户账户</span>
          </div>
        </div>
      </div>
    );
  };

  const SimplePieChart = ({ positions }) => {
    if (!positions || positions.length === 0) return <div className="text-center py-8 text-slate-400">暂无持仓</div>;

    const validPositions = positions.filter(p => p.weight > 0);
    const totalWeight = validPositions.reduce((sum, p) => sum + p.weight, 0);

    if (totalWeight === 0) return <div className="text-center py-8 text-slate-400">暂无持仓</div>;

    let currentAngle = 0;
    const colors = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

    return (
      <svg viewBox="0 0 200 200" className="w-full max-w-[200px] h-auto mx-auto">
        {validPositions.map((pos, i) => {
          const angle = (pos.weight / totalWeight) * 360;
          const startAngle = currentAngle;
          const endAngle = currentAngle + angle;
          currentAngle += angle;

          const startRad = (startAngle * Math.PI) / 180;
          const endRad = (endAngle * Math.PI) / 180;

          const x1 = 100 + 80 * Math.cos(startRad);
          const y1 = 100 + 80 * Math.sin(startRad);
          const x2 = 100 + 80 * Math.cos(endRad);
          const y2 = 100 + 80 * Math.sin(endRad);

          const largeArc = angle > 180 ? 1 : 0;

          return (
            <path
              key={pos.code || i}
              d={`M 100 100 L ${x1} ${y1} A 80 80 0 ${largeArc} 1 ${x2} ${y2} Z`}
              fill={colors[i % colors.length]}
              stroke="white"
              strokeWidth="2"
            />
          );
        })}
        <circle cx="100" cy="100" r="40" fill="white" />
      </svg>
    );
  };

  const getRateColor = (rate) => {
    if (rate > 0) return 'text-red-600';
    if (rate < 0) return 'text-green-600';
    return 'text-slate-600';
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
          <span className="ml-2 text-slate-600">加载中...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center justify-between">
          <span className="text-red-600">{error}</span>
          <button onClick={fetchAccounts} className="text-sm text-red-600 hover:text-red-700 underline">重试</button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* AI账户选择器 */}
      {accounts.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
          <div className="flex flex-wrap gap-2 items-center justify-between">
            <div className="flex flex-wrap gap-2 items-center">
              {accounts.map(account => (
                <div key={account.id} className={`flex items-center justify-between px-4 py-2 rounded-lg border transition-colors ${
                  selectedAccount?.id === account.id
                    ? 'bg-blue-100 border-blue-200'
                    : 'bg-slate-50 border-slate-200 hover:bg-slate-100'
                }`}>
                  <button
                    onClick={() => setSelectedAccount(account)}
                    className={`flex-1 text-left text-sm font-medium ${
                      selectedAccount?.id === account.id
                        ? 'text-blue-700'
                        : 'text-slate-600'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      {/* 币/基标签显示在前面 */}
                      <span className="text-xs px-1.5 py-0.5 rounded bg-slate-200 text-slate-500">
                        {account.source_type === 'crypto' ? '币' : '基'}
                      </span>
                      <span>{account.name}</span>
                      <span className={`text-xs ${account.total_return_rate >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                        ({account.total_return_rate >= 0 ? '+' : ''}{account.total_return_rate?.toFixed(2)}%)
                      </span>
                    </div>
                  </button>
                </div>
              ))}
            </div>
            {/* 创建按钮靠右显示 */}
            <button
              className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors text-sm font-medium whitespace-nowrap"
              onClick={async () => {
                await fetchUserAccounts();
                setShowCreateModal(true);
              }}
            >
              <Plus className="w-4 h-4" />
              创建AI模拟账户
            </button>
          </div>
        </div>
      )}

      {/* 空状态 */}
      {accounts.length === 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 text-center">
          <div className="text-slate-400 mb-4">暂无AI模拟账户</div>
          <button
            onClick={async () => {
              await fetchUserAccounts();
              setShowCreateModal(true);
            }}
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors text-sm font-medium"
          >
            <Plus className="w-4 h-4" />
            创建第一个AI账户
          </button>
        </div>
      )}

      {/* 账户详情 */}
      {selectedAccount && accountDetail && (
        <>
          {/* 概览卡片 */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4">
            <div className="flex flex-col md:flex-row md:justify-between md:items-start gap-4 mb-4">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-slate-800">{accountDetail.name}</h2>
                <button
                  onClick={() => handleEditAccount(accountDetail)}
                  className="text-slate-400 hover:text-slate-600 p-1"
                  title="编辑账户"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button
                  onClick={() => handleDeleteAccount(accountDetail.id)}
                  className="text-slate-400 hover:text-red-600 p-1"
                  title="删除账户"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleUpdatePrices}
                  disabled={updateLoading}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white px-4 py-2 rounded-lg transition-colors text-sm font-medium whitespace-nowrap"
                >
                  {updateLoading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      更新中...
                    </>
                  ) : (
                    <>
                      <TrendingUp className="w-4 h-4" />
                      更新价格
                    </>
                  )}
                </button>
                <button
                  onClick={handlePerformReview}
                  disabled={reviewLoading}
                  className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-400 text-white px-4 py-2 rounded-lg transition-colors text-sm font-medium whitespace-nowrap"
                >
                  {reviewLoading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      审视中...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-4 h-4" />
                      手动审视
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* 关键指标 */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-slate-50 rounded-lg p-3">
                <div className="text-xs text-slate-500 mb-1">初始资金</div>
                <div className="text-lg font-bold text-slate-800">{getCurrencySymbol()}{accountDetail.initial_capital?.toLocaleString()}</div>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <div className="text-xs text-slate-500 mb-1">AI市值</div>
                <div className="text-lg font-bold text-slate-800">{getCurrencySymbol()}{accountDetail.current_value?.toLocaleString()}</div>
                <div className={`text-xs ${getRateColor(accountDetail.total_return_rate)}`}>
                  {accountDetail.total_return_rate >= 0 ? '+' : ''}{accountDetail.total_return_rate?.toFixed(2)}%
                </div>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <div className="text-xs text-slate-500 mb-1">现金账户</div>
                <div className="text-lg font-bold text-slate-800">{getCurrencySymbol()}{accountDetail.cash?.toLocaleString()}</div>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <div className="text-xs text-slate-500 mb-1">用户市值</div>
                <div className="text-lg font-bold text-slate-800">{getCurrencySymbol()}{accountDetail.source_current_value?.toLocaleString()}</div>
                <div className={`text-xs ${getRateColor(accountDetail.source_return_rate)}`}>
                  {accountDetail.source_return_rate >= 0 ? '+' : ''}{accountDetail.source_return_rate?.toFixed(2)}%
                </div>
              </div>
            </div>
          </div>

          {/* Tab导航 */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="flex border-b border-slate-200 overflow-x-auto">
              {[
                { key: 'overview', label: '走势对比' },
                { key: 'returns', label: '收益率对比' },
                { key: 'positions', label: 'AI持仓' },
                { key: 'trades', label: '调仓记录' }
              ].map(tab => (
                <button
                  key={tab.key}
                  onClick={() => {
                    setActiveTab(tab.key);
                    // 懒加载数据
                    if (tab.key === 'trades' && selectedAccount && (!accountDetail?.trades || accountDetail.trades.length === 0)) {
                      fetchTrades(selectedAccount.id);
                    }
                    if ((tab.key === 'overview' || tab.key === 'returns') && selectedAccount) {
                      fetchHistory(selectedAccount.id);
                    }
                  }}
                  className={`px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
                    activeTab === tab.key
                      ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/50'
                      : 'text-slate-600 hover:text-slate-800 hover:bg-slate-50'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="p-4">
              {/* 时间周期选择器 */}
              {(activeTab === 'overview' || activeTab === 'returns') && (
                <div className="flex items-center gap-2 mb-4">
                  <Calendar className="w-4 h-4 text-slate-400" />
                  <span className="text-sm text-slate-500">时间周期:</span>
                  <div className="flex gap-1">
                    {[
                      { key: '7d', label: '7天' },
                      { key: '30d', label: '30天' },
                      { key: '90d', label: '90天' },
                      { key: '1y', label: '1年' },
                      { key: 'all', label: '全部' }
                    ].map(range => (
                      <button
                        key={range.key}
                        onClick={() => setTimeRange(range.key)}
                        className={`px-3 py-1 text-xs rounded-lg transition-colors ${
                          timeRange === range.key
                            ? 'bg-blue-100 text-blue-700 border border-blue-200'
                            : 'bg-slate-50 text-slate-600 hover:bg-slate-100 border border-slate-200'
                        }`}
                      >
                        {range.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === 'overview' && (
                <div>
                  <h3 className="text-sm font-bold text-slate-700 mb-4">资产价值走势对比</h3>
                  <SimpleLineChart type="value" />
                </div>
              )}

              {activeTab === 'returns' && (
                <div>
                  <h3 className="text-sm font-bold text-slate-700 mb-4">收益率对比</h3>
                  <SimpleLineChart type="return" />
                </div>
              )}

              {activeTab === 'positions' && (
                <div>
                  <div className="grid md:grid-cols-2 gap-6 mb-6">
                    <div>
                      <h4 className="text-sm font-bold text-slate-700 mb-4">持仓分布</h4>
                      <SimplePieChart positions={accountDetail.positions} />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-slate-700 mb-4">持仓权重</h4>
                      <div className="space-y-2">
                        {accountDetail.positions?.slice(0, 8).map((pos, i) => (
                          <div key={pos.code} className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'][i % 8] }}></div>
                            <span className="text-sm text-slate-600 flex-1 truncate">{pos.name || pos.code}</span>
                            <span className="text-sm font-medium text-slate-800">{pos.weight?.toFixed(1)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* 持仓明细表格 - 桌面端 */}
                  <div className="hidden md:block">
                    <h4 className="text-sm font-bold text-slate-700 mb-4">持仓明细</h4>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-slate-200">
                            <th className="text-left py-2 px-3 text-slate-500 font-medium">代码</th>
                            <th className="text-left py-2 px-3 text-slate-500 font-medium">名称</th>
                            <th className="text-right py-2 px-3 text-slate-500 font-medium">份额</th>
                            <th className="text-right py-2 px-3 text-slate-500 font-medium">成本</th>
                            <th className="text-right py-2 px-3 text-slate-500 font-medium">现价</th>
                            <th className="text-right py-2 px-3 text-slate-500 font-medium">市值</th>
                            <th className="text-right py-2 px-3 text-slate-500 font-medium">收益率</th>
                          </tr>
                        </thead>
                        <tbody>
                          {accountDetail.positions?.map(pos => (
                            <tr key={pos.code} className="border-b border-slate-100 hover:bg-slate-50">
                              <td className="py-2 px-3 font-mono text-slate-600">
                                <div className="flex items-center gap-2">
                                  {pos.code}
                                  {pos.asset_type === 'crypto' && (
                                    <span className="px-1.5 py-0.5 text-xs bg-orange-100 text-orange-700 rounded">币</span>
                                  )}
                                </div>
                              </td>
                              <td className="py-2 px-3 text-slate-800">{pos.name || '-'}</td>
                              <td className="py-2 px-3 text-right font-mono">{pos.shares?.toFixed(4)}</td>
                              <td className="py-2 px-3 text-right font-mono">{pos.cost?.toFixed(4)}</td>
                              <td className="py-2 px-3 text-right font-mono">{pos.current_price?.toFixed(4) || '-'}</td>
                              <td className="py-2 px-3 text-right font-mono">{getCurrencySymbol()}{pos.market_value?.toLocaleString()}</td>
                              <td className={`py-2 px-3 text-right font-medium ${getRateColor(pos.return_rate)}`}>
                                {pos.return_rate >= 0 ? '+' : ''}{pos.return_rate?.toFixed(2)}%
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* 持仓明细 - 移动端卡片 */}
                  <div className="md:hidden space-y-3">
                    {accountDetail.positions?.map(pos => (
                      <div key={pos.code} className="bg-slate-50 rounded-lg p-3">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <div className="font-medium text-slate-800 flex items-center gap-2">
                              {pos.name || pos.code}
                              {pos.asset_type === 'crypto' && (
                                <span className="px-1.5 py-0.5 text-xs bg-orange-100 text-orange-700 rounded">币</span>
                              )}
                            </div>
                            <div className="text-xs text-slate-400 font-mono">{pos.code}</div>
                          </div>
                          <div className={`text-sm font-medium ${getRateColor(pos.return_rate)}`}>
                            {pos.return_rate >= 0 ? '+' : ''}{pos.return_rate?.toFixed(2)}%
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-xs">
                          <div>
                            <div className="text-slate-400">份额</div>
                            <div className="font-mono">{pos.shares?.toFixed(4)}</div>
                          </div>
                          <div>
                            <div className="text-slate-400">成本</div>
                            <div className="font-mono">{pos.cost?.toFixed(4)}</div>
                          </div>
                          <div>
                            <div className="text-slate-400">市值</div>
                            <div className="font-mono">{getCurrencySymbol()}{pos.market_value?.toLocaleString()}</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === 'trades' && (
                <div>
                  <h3 className="text-sm font-bold text-slate-700 mb-4">调仓记录</h3>
                  {!accountDetail.trades ? (
                    <div className="flex items-center justify-center py-8 text-slate-400">
                      <RefreshCw className="w-5 h-5 animate-spin mr-2" />
                      加载中...
                    </div>
                  ) : accountDetail.trades?.length > 0 ? (
                    <>
                      {/* 桌面端表格 */}
                      <div className="hidden md:block overflow-x-auto">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="border-b border-slate-200">
                              <th className="text-left py-2 px-3 text-slate-500 font-medium">日期</th>
                              <th className="text-left py-2 px-3 text-slate-500 font-medium">类型</th>
                              <th className="text-left py-2 px-3 text-slate-500 font-medium">基金</th>
                              <th className="text-right py-2 px-3 text-slate-500 font-medium">交易</th>
                              <th className="text-right py-2 px-3 text-slate-500 font-medium">金额</th>
                              <th className="text-left py-2 px-3 text-slate-500 font-medium w-[40%]">原因</th>
                            </tr>
                          </thead>
                          <tbody>
                            {accountDetail.trades.map(trade => (
                              <tr key={trade.id} className="border-b border-slate-100 hover:bg-slate-50">
                                <td className="py-2 px-3 text-slate-600 whitespace-nowrap">{trade.trade_date}</td>
                                <td className="py-2 px-3">
                                  <span className={`px-2 py-0.5 rounded font-medium whitespace-nowrap ${
                                    trade.trade_type === 'buy' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                                  }`}>
                                    {trade.trade_type === 'buy' ? '买入' : '卖出'}
                                  </span>
                                </td>
                                <td className="py-2 px-3">
                                  <div className="flex items-center gap-2">
                                    <span className="text-slate-800">{trade.name || '-'}</span>
                                    {trade.asset_type === 'crypto' && (
                                      <span className="px-1 py-0.5 text-xs bg-orange-100 text-orange-700 rounded">币</span>
                                    )}
                                  </div>
                                  <div className="text-slate-400 font-mono">{trade.code}</div>
                                </td>
                                <td className="py-2 px-3 text-right">
                                  <div className="font-mono">{trade.shares?.toFixed(4)}份</div>
                                  <div className="font-mono text-slate-400">@{trade.price?.toFixed(4)}</div>
                                </td>
                                <td className="py-2 px-3 text-right font-mono whitespace-nowrap">{getCurrencySymbol()}{trade.amount?.toLocaleString()}</td>
                                <td className="py-2 px-3 text-slate-500 whitespace-normal break-all">{trade.reason || '-'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      {/* 移动端卡片 */}
                      <div className="md:hidden space-y-3">
                        {accountDetail.trades.map(trade => (
                          <div key={trade.id} className="bg-slate-50 rounded-lg p-3">
                            <div className="flex justify-between items-start mb-2">
                              <div className="flex items-center gap-2 flex-shrink-0">
                                <span className={`px-2 py-0.5 rounded font-medium whitespace-nowrap ${
                                  trade.trade_type === 'buy' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                                }`}>
                                  {trade.trade_type === 'buy' ? '买入' : '卖出'}
                                </span>
                                <span className="text-slate-600 text-xs whitespace-nowrap">{trade.trade_date}</span>
                              </div>
                              <span className="font-medium text-slate-800 text-xs whitespace-nowrap">{getCurrencySymbol()}{trade.amount?.toLocaleString()}</span>
                            </div>
                            <div className="flex items-center gap-2 text-xs text-slate-800">
                              {trade.name || trade.code}
                              {trade.asset_type === 'crypto' && (
                                <span className="px-1 py-0.5 text-xs bg-orange-100 text-orange-700 rounded">币</span>
                              )}
                              <span className="text-slate-400 font-mono">({trade.code})</span>
                            </div>
                            <div className="text-xs text-slate-400 font-mono mb-2">{trade.shares?.toFixed(4)}份 @{getCurrencySymbol()}{trade.price?.toFixed(4)}</div>
                            {trade.reason && (
                              <div className="text-xs text-slate-500 bg-white rounded p-2 whitespace-normal break-all">{trade.reason}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div className="text-center py-8 text-slate-400">暂无调仓记录</div>
                  )}
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* 创建账户弹窗 */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md max-h-[90vh] overflow-hidden animate-in fade-in zoom-in duration-200 flex flex-col">
            <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50 shrink-0">
              <h3 className="font-bold text-slate-800">创建AI模拟账户</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              <form onSubmit={(e) => { e.preventDefault(); handleCreateAccount(); }} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">源账户类型</label>
                  <select
                    value={createForm.source_type}
                    onChange={(e) => {
                      const newType = e.target.value;
                      // 检查选择的类型是否有可用账户
                      const hasAccounts = newType === 'fund' 
                        ? userAccounts.length > 0 
                        : cryptoAccounts.length > 0;
                      
                      if (!hasAccounts) {
                        alert(`暂无${newType === 'fund' ? '基金' : '数字货币'}账户，请先创建${newType === 'fund' ? '基金' : '数字货币'}账户`);
                        return;
                      }
                      
                      // 自动选择对应类型的第一个账户
                      const defaultAccountId = newType === 'fund' 
                        ? (userAccounts[0]?.id || '') 
                        : (cryptoAccounts[0]?.id || '');
                      setCreateForm({
                        ...createForm, 
                        source_type: newType, 
                        source_account_id: defaultAccountId
                      });
                    }}
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    <option value="fund">基金账户</option>
                    <option value="crypto">数字货币账户</option>
                  </select>
                </div>

                {createForm.source_type === 'fund' && userAccounts.length > 1 && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">源账户</label>
                    <select
                      value={createForm.source_account_id}
                      onChange={(e) => setCreateForm({...createForm, source_account_id: e.target.value})}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                      required
                    >
                      <option value="">选择源账户</option>
                      {userAccounts.map(acc => (
                        <option key={acc.id} value={acc.id}>{acc.name}</option>
                      ))}
                    </select>
                  </div>
                )}

                {createForm.source_type === 'crypto' && cryptoAccounts.length > 1 && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">源账户</label>
                    <select
                      value={createForm.source_account_id}
                      onChange={(e) => setCreateForm({...createForm, source_account_id: e.target.value})}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                      required
                    >
                      <option value="">选择源账户</option>
                      {cryptoAccounts.map(acc => (
                        <option key={acc.id} value={acc.id}>{acc.name}</option>
                      ))}
                    </select>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">账户名称</label>
                  <input
                    type="text"
                    value={createForm.name}
                    onChange={(e) => setCreateForm({...createForm, name: e.target.value})}
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    placeholder="AI模拟账户"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">描述（可选）</label>
                  <input
                    type="text"
                    value={createForm.description}
                    onChange={(e) => setCreateForm({...createForm, description: e.target.value})}
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    placeholder="账户描述"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">审视频率</label>
                  <select
                    value={createForm.review_frequency}
                    onChange={(e) => setCreateForm({...createForm, review_frequency: e.target.value, review_day: e.target.value === 'week' ? 0 : e.target.value === 'month' ? 1 : 0})}
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    <option value="daily">每日</option>
                    <option value="weekly">每周</option>
                    <option value="monthly">每月</option>
                  </select>
                </div>

                {(createForm.review_frequency === 'weekly' || createForm.review_frequency === 'monthly') && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      {createForm.review_frequency === 'weekly' ? '每周审视日' : '每月审视日'}
                    </label>
                    <select
                      value={createForm.review_day}
                      onChange={(e) => setCreateForm({...createForm, review_day: parseInt(e.target.value)})}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    >
                      {createForm.review_frequency === 'weekly' ? (
                        [
                          {value: 0, label: '周一'},
                          {value: 1, label: '周二'},
                          {value: 2, label: '周三'},
                          {value: 3, label: '周四'},
                          {value: 4, label: '周五'},
                          {value: 5, label: '周六'},
                          {value: 6, label: '周日'}
                        ].map(day => (
                          <option key={day.value} value={day.value}>{day.label}</option>
                        ))
                      ) : (
                        Array.from({length: 31}, (_, i) => i + 1).map(day => (
                          <option key={day} value={day}>{day}日</option>
                        ))
                      )}
                    </select>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">审视时间</label>
                  <select
                    value={createForm.review_hour}
                    onChange={(e) => setCreateForm({...createForm, review_hour: parseInt(e.target.value)})}
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    {Array.from({length: 24}, (_, i) => i).map(hour => (
                      <option key={hour} value={hour}>{hour}:00</option>
                    ))}
                  </select>
                </div>

                <div className="flex gap-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    disabled={createLoading}
                    className="flex-1 px-4 py-2 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    取消
                  </button>
                  <button
                    type="submit"
                    disabled={createLoading}
                    className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {createLoading ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        创建中...
                      </>
                    ) : (
                      '创建'
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
      {/* 编辑账户模态框 */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-lg w-full max-w-md">
            <div className="flex justify-between items-center p-4 border-b border-slate-200">
              <h3 className="text-lg font-bold text-slate-800">编辑AI模拟账户</h3>
              <button onClick={() => setShowEditModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto">
              <form onSubmit={(e) => { e.preventDefault(); handleUpdateAccount(); }} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">账户名称</label>
                  <input
                    type="text"
                    value={editForm.name}
                    onChange={(e) => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="输入账户名称"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">描述</label>
                  <textarea
                    value={editForm.description}
                    onChange={(e) => setEditForm(prev => ({ ...prev, description: e.target.value }))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="输入账户描述"
                    rows={3}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">审视频率</label>
                  <select
                    value={editForm.review_frequency}
                    onChange={(e) => setEditForm({...editForm, review_frequency: e.target.value, review_day: e.target.value === 'weekly' ? 0 : e.target.value === 'monthly' ? 1 : 0})}
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    <option value="daily">每日</option>
                    <option value="weekly">每周</option>
                    <option value="monthly">每月</option>
                  </select>
                </div>

                {(editForm.review_frequency === 'weekly' || editForm.review_frequency === 'monthly') && (
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      {editForm.review_frequency === 'weekly' ? '每周审视日' : '每月审视日'}
                    </label>
                    <select
                      value={editForm.review_day}
                      onChange={(e) => setEditForm({...editForm, review_day: parseInt(e.target.value)})}
                      className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    >
                      {editForm.review_frequency === 'weekly' ? (
                        [
                          {value: 0, label: '周一'},
                          {value: 1, label: '周二'},
                          {value: 2, label: '周三'},
                          {value: 3, label: '周四'},
                          {value: 4, label: '周五'},
                          {value: 5, label: '周六'},
                          {value: 6, label: '周日'}
                        ].map(day => (
                          <option key={day.value} value={day.value}>{day.label}</option>
                        ))
                      ) : (
                        Array.from({length: 31}, (_, i) => i + 1).map(day => (
                          <option key={day} value={day}>{day}日</option>
                        ))
                      )}
                    </select>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">审视时间</label>
                  <select
                    value={editForm.review_hour}
                    onChange={(e) => setEditForm({...editForm, review_hour: parseInt(e.target.value)})}
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                  >
                    {Array.from({length: 24}, (_, i) => i).map(hour => (
                      <option key={hour} value={hour}>{hour}:00</option>
                    ))}
                  </select>
                </div>

                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowEditModal(false)}
                    className="flex-1 px-4 py-2 border border-slate-300 rounded-md text-slate-700 hover:bg-slate-50 transition-colors"
                  >
                    取消
                  </button>
                  <button
                    type="submit"
                    className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
                  >
                    保存
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AISimulation;
