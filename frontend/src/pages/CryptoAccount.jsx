import React, { useState, useEffect } from 'react';
import { Plus, X, Edit2, Trash2, RefreshCw, TrendingUp, TrendingDown } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { getCryptoPositions, createCryptoPosition, updateCryptoPosition, deleteCryptoPosition, buyCrypto, sellCrypto, updateCryptoPrices } from '../services/api';
import { CryptoAiAnalysis } from '../components/CryptoAiAnalysis';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#6366f1', '#14b8a6'];

const CryptoAccount = ({ currentAccount = 1 }) => {
  const [data, setData] = useState({ summary: {}, positions: [] });
  const [loading, setLoading] = useState(false);
  const [updateLoading, setUpdateLoading] = useState(false);
  const [error, setError] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingPos, setEditingPos] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const [formData, setFormData] = useState({ symbol: '', name: '', cost: '', amount: '' });

  const [buyModalOpen, setBuyModalOpen] = useState(false);
  const [sellModalOpen, setSellModalOpen] = useState(false);
  const [tradePos, setTradePos] = useState(null);
  const [tradeData, setTradeData] = useState({ amount: '', price: '' });
  const [tradeSubmitting, setTradeSubmitting] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getCryptoPositions(currentAccount);
      setData(res);
    } catch (e) {
      console.error(e);
      setError('加载数字货币持仓失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [currentAccount]);

  const handleAddPosition = async () => {
    if (!formData.symbol || !formData.name || !formData.cost || !formData.amount) return;

    setSubmitting(true);
    try {
      await createCryptoPosition(formData, currentAccount);
      setModalOpen(false);
      setFormData({ symbol: '', name: '', cost: '', amount: '' });
      fetchData();
    } catch (e) {
      console.error(e);
      alert('添加持仓失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditPosition = async () => {
    if (!formData.symbol || !formData.name || !formData.cost || !formData.amount) return;

    setSubmitting(true);
    try {
      await updateCryptoPosition(editingPos.symbol, formData, currentAccount);
      setModalOpen(false);
      setEditingPos(null);
      setFormData({ symbol: '', name: '', cost: '', amount: '' });
      fetchData();
    } catch (e) {
      console.error(e);
      alert('更新持仓失败');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeletePosition = async (symbol) => {
    if (!confirm('确定要删除这个持仓吗？')) return;

    try {
      await deleteCryptoPosition(symbol, currentAccount);
      fetchData();
    } catch (e) {
      console.error(e);
      alert('删除持仓失败');
    }
  };

  const handleBuy = async () => {
    if (!tradeData.amount || !tradeData.price) return;

    setTradeSubmitting(true);
    try {
      await buyCrypto({
        symbol: tradePos.symbol,
        op_type: 'buy',
        amount: parseFloat(tradeData.amount),
        price: parseFloat(tradeData.price)
      }, currentAccount);
      setBuyModalOpen(false);
      setTradePos(null);
      setTradeData({ amount: '', price: '' });
      fetchData();
    } catch (e) {
      console.error(e);
      alert('买入失败');
    } finally {
      setTradeSubmitting(false);
    }
  };

  const handleSell = async () => {
    if (!tradeData.amount || !tradeData.price) return;

    setTradeSubmitting(true);
    try {
      await sellCrypto({
        symbol: tradePos.symbol,
        op_type: 'sell',
        amount: parseFloat(tradeData.amount),
        price: parseFloat(tradeData.price)
      }, currentAccount);
      setSellModalOpen(false);
      setTradePos(null);
      setTradeData({ amount: '', price: '' });
      fetchData();
    } catch (e) {
      console.error(e);
      alert('卖出失败');
    } finally {
      setTradeSubmitting(false);
    }
  };

  const handleUpdatePrices = async () => {
    setUpdateLoading(true);
    try {
      await updateCryptoPrices();
      fetchData();
    } catch (e) {
      console.error(e);
      alert('更新价格失败');
    } finally {
      setUpdateLoading(false);
    }
  };

  const openAddModal = () => {
    setEditingPos(null);
    setFormData({ symbol: '', name: '', cost: '', amount: '' });
    setModalOpen(true);
  };

  const openEditModal = (pos) => {
    setEditingPos(pos);
    setFormData({
      symbol: pos.symbol,
      name: pos.name,
      cost: pos.cost,
      amount: pos.amount
    });
    setModalOpen(true);
  };

  const getRateColor = (rate) => {
  if (rate > 0) return 'text-red-600';
  if (rate < 0) return 'text-green-600';
  return 'text-gray-600';
};

const getRateBgColor = (rate) => {
  if (rate > 0) return 'bg-red-100 text-red-800';
  if (rate < 0) return 'bg-green-100 text-green-800';
  return 'bg-gray-100 text-gray-800';
};

  // 币种分布数据
  const cryptoDistributionData = data.positions.map(pos => ({
    name: pos.symbol,
    value: pos.market_value
  })).sort((a, b) => b.value - a.value);

  // 自定义标签渲染
  const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, index }) => {
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * Math.PI / 180);
    const y = cy + radius * Math.sin(-midAngle * Math.PI / 180);

    if (percent < 0.05) return null; // 隐藏小标签

    return (
      <text x={x} y={y} fill="white" textAnchor={x > cx ? 'start' : 'end'} dominantBaseline="central" className="text-[10px] font-bold">
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-red-600">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-medium text-red-800">{error}</p>
            </div>
          </div>
          <button
            onClick={fetchData}
            className="text-sm font-medium text-red-600 hover:text-red-700 underline"
          >
            重试
          </button>
        </div>
      )}

      {/* 资产概览 */}
      <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wider">资产概览</h3>
          <button
            onClick={handleUpdatePrices}
            disabled={updateLoading}
            className="p-2 bg-slate-50 border border-slate-200 rounded-full hover:bg-slate-100 transition-colors text-slate-500 hover:text-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
            title="更新价格"
          >
            <RefreshCw className={`w-4 h-4 ${updateLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
        
        {/* 四格信息和币种分布 */}
        <div className="flex flex-col md:flex-row gap-4">
          {/* 左侧：统计数据 */}
          <div className="w-full md:w-1/2 grid grid-cols-2 gap-2">
            <div className="bg-slate-50 p-2 rounded-lg">
              <div className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">总资产</div>
              <div className="text-lg font-bold text-slate-800">
                ${data.summary.total_market_value?.toLocaleString() || '0.00'}
              </div>
            </div>

            <div className="bg-slate-50 p-2 rounded-lg">
              <div className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">总成本</div>
              <div className="text-lg font-bold text-slate-800">
                ${data.summary.total_cost?.toLocaleString() || '0.00'}
              </div>
            </div>

            <div className="bg-slate-50 p-2 rounded-lg">
              <div className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">总盈亏</div>
              <div className={`text-lg font-bold ${getRateColor(data.summary.total_return_rate || 0)}`}>
                {(data.summary.total_income || 0) > 0 ? '+' : ''}${(data.summary.total_income || 0).toLocaleString()}
              </div>
            </div>

            <div className="bg-slate-50 p-2 rounded-lg">
              <div className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">24h盈亏</div>
              <div className={`text-lg font-bold ${getRateColor(data.summary.total_day_income || 0)}`}>
                {(data.summary.total_day_income || 0) > 0 ? '+' : ''}${(data.summary.total_day_income || 0).toLocaleString()}
              </div>
            </div>
          </div>

          {/* 右侧：币种分布 */}
          <div className="w-full md:w-1/2 h-[200px]">
            <h4 className="text-xs font-medium text-slate-600 mb-1">币种分布</h4>
            <ResponsiveContainer width="100%" height="90%">
              <PieChart>
                <Pie
                  data={cryptoDistributionData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={renderCustomizedLabel}
                  outerRadius={70}
                  fill="#8884d8"
                  dataKey="value"
                  paddingAngle={2}
                >
                  {cryptoDistributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Legend layout="horizontal" verticalAlign="bottom" align="center" wrapperStyle={{ fontSize: '10px', marginTop: '0px', marginBottom: '0px' }}/>
                <Tooltip
                  formatter={(value) => `$${value.toLocaleString()}`}
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* AI 持仓分析 */}
      <div className="w-full">
        <CryptoAiAnalysis positions={data.positions} summary={data.summary} />
      </div>

      {/* 标题和操作按钮 */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4">
        <h2 className="text-xl font-bold text-slate-800">持仓列表</h2>
        <div className="flex flex-wrap gap-2 justify-start md:justify-end">
          <button
            onClick={handleUpdatePrices}
            disabled={updateLoading}
            className="flex items-center gap-2 bg-white border border-slate-200 text-slate-600 hover:text-blue-600 hover:border-blue-200 px-4 py-2 rounded-lg transition-colors text-sm font-medium whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw size={16} className={updateLoading ? 'animate-spin' : ''} />
            {updateLoading ? '更新中...' : '更新价格'}
          </button>
          <button
            onClick={openAddModal}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors text-sm font-medium whitespace-nowrap"
          >
            <Plus size={16} />
            添加持仓
          </button>
        </div>
      </div>

      {/* 持仓表格/卡片 */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200">
        {loading ? (
          <div className="p-8 text-center text-gray-500">加载中...</div>
        ) : data.positions.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            暂无持仓，点击"添加持仓"开始
          </div>
        ) : (
          <>
            {/* 桌面端表格 */}
            <div className="hidden md:block overflow-x-auto">
              <div className="min-w-[800px]">
                <table className="w-full text-base text-left border-collapse">
                  <thead className="bg-slate-50 text-slate-500 font-medium text-xs uppercase tracking-wider sticky top-0 z-30 shadow-sm">
                    <tr>
                      <th className="px-4 py-3 text-left border-b border-slate-100 bg-slate-50 rounded-tl-xl">币种</th>
                      <th className="px-4 py-3 text-right border-b border-slate-100 bg-slate-50">数量 | 成本价</th>
                      <th className="px-4 py-3 text-right border-b border-slate-100 bg-slate-50">现价 | 24h涨跌</th>
                      <th className="px-4 py-3 text-right border-b border-slate-100 bg-slate-50">市值 | 盈亏</th>
                      <th className="px-4 py-3 text-right border-b border-slate-100 bg-slate-50">收益率</th>
                      <th className="px-4 py-3 text-center border-b border-slate-100 bg-slate-50 rounded-tr-xl">操作</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-base">
                    {data.positions.map((pos) => (
                      <tr key={pos.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3">
                          <div>
                            <div className="font-bold text-slate-800">{pos.symbol}</div>
                            <div className="text-xs text-slate-400">{pos.name}</div>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="font-mono text-slate-800">{pos.amount.toFixed(4)}</div>
                          <div className="text-xs text-slate-500">${pos.cost.toFixed(2)}</div>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="font-mono text-slate-800">${pos.current_price.toFixed(4)}</div>
                          <div className={`text-xs ${getRateColor(pos.change_24h)}`}>
                            {pos.change_24h >= 0 ? '+' : ''}{pos.change_24h.toFixed(2)}%
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="font-mono text-slate-800">${pos.market_value.toLocaleString()}</div>
                          <div className={`text-xs ${getRateColor(pos.return_rate)}`}>
                            ${pos.income.toLocaleString()}
                          </div>
                        </td>
                        <td className={`px-4 py-3 text-right ${getRateColor(pos.return_rate)}`}>
                          <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getRateBgColor(pos.return_rate)}`}>
                            {pos.return_rate >= 0 ? '+' : ''}{pos.return_rate.toFixed(2)}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <div className="flex justify-center gap-2">
                            <button
                              onClick={() => {
                                setTradePos(pos);
                                setBuyModalOpen(true);
                                setTradeData({ amount: '', price: pos.current_price });
                              }}
                              className="p-1 text-green-600 hover:bg-green-50 rounded"
                              title="买入"
                            >
                              <TrendingUp size={16} />
                            </button>
                            <button
                              onClick={() => {
                                setTradePos(pos);
                                setSellModalOpen(true);
                                setTradeData({ amount: '', price: pos.current_price });
                              }}
                              className="p-1 text-red-600 hover:bg-red-50 rounded"
                              title="卖出"
                            >
                              <TrendingDown size={16} />
                            </button>
                            <button
                              onClick={() => openEditModal(pos)}
                              className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                              title="编辑"
                            >
                              <Edit2 size={16} />
                            </button>
                            <button
                              onClick={() => handleDeletePosition(pos.symbol)}
                              className="p-1 text-gray-600 hover:bg-gray-100 rounded"
                              title="删除"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            
            {/* 移动端卡片 */}
            <div className="md:hidden p-4 space-y-3">
              {data.positions.map((pos) => (
                <div key={pos.id} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                  <div className="p-4 border-b border-slate-100">
                    <div className="flex justify-between items-start">
                      <div className="flex-1 pr-2">
                        <div className="font-bold text-slate-800 break-words leading-tight">{pos.symbol}</div>
                        <div className="text-xs text-slate-400 break-words">{pos.name}</div>
                      </div>
                      <div className={`px-2 py-1 rounded text-xs font-medium shrink-0 ${getRateBgColor(pos.return_rate)}`}>
                        {pos.return_rate >= 0 ? '+' : ''}{pos.return_rate.toFixed(2)}%
                      </div>
                    </div>
                  </div>
                  <div className="p-4 space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <div className="text-xs text-slate-500 font-medium uppercase tracking-wider">数量</div>
                        <div className="font-mono text-slate-800 break-all">{pos.amount.toFixed(4)}</div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-500 font-medium uppercase tracking-wider">成本价</div>
                        <div className="font-mono text-slate-800 break-all">${pos.cost.toFixed(2)}</div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-500 font-medium uppercase tracking-wider">现价</div>
                        <div className="font-mono text-slate-800 break-all">${pos.current_price.toFixed(4)}</div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-500 font-medium uppercase tracking-wider">24h涨跌</div>
                        <div className={`text-sm ${getRateColor(pos.change_24h)}`}>
                          {pos.change_24h >= 0 ? '+' : ''}{pos.change_24h.toFixed(2)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-500 font-medium uppercase tracking-wider">市值</div>
                        <div className="font-mono text-slate-800 break-all">${pos.market_value.toLocaleString()}</div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-500 font-medium uppercase tracking-wider">盈亏</div>
                        <div className={`text-sm ${getRateColor(pos.return_rate)}`}>
                          ${pos.income.toLocaleString()}
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 border-t border-slate-100">
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={() => {
                          setTradePos(pos);
                          setBuyModalOpen(true);
                          setTradeData({ amount: '', price: pos.current_price });
                        }}
                        className="flex items-center justify-center gap-1 bg-white border border-slate-200 text-slate-600 hover:text-green-600 hover:border-green-200 px-2 py-1.5 rounded-lg transition-colors text-xs font-medium"
                        title="买入"
                      >
                        <TrendingUp size={12} />
                        买入
                      </button>
                      <button
                        onClick={() => {
                          setTradePos(pos);
                          setSellModalOpen(true);
                          setTradeData({ amount: '', price: pos.current_price });
                        }}
                        className="flex items-center justify-center gap-1 bg-white border border-slate-200 text-slate-600 hover:text-red-600 hover:border-red-200 px-2 py-1.5 rounded-lg transition-colors text-xs font-medium"
                        title="卖出"
                      >
                        <TrendingDown size={12} />
                        卖出
                      </button>
                      <button
                        onClick={() => openEditModal(pos)}
                        className="flex items-center justify-center gap-1 bg-white border border-slate-200 text-slate-600 hover:text-blue-600 hover:border-blue-200 px-2 py-1.5 rounded-lg transition-colors text-xs font-medium"
                        title="编辑"
                      >
                        <Edit2 size={12} />
                        编辑
                      </button>
                      <button
                        onClick={() => handleDeletePosition(pos.symbol)}
                        className="flex items-center justify-center gap-1 bg-white border border-slate-200 text-slate-600 hover:text-gray-600 hover:border-gray-200 px-2 py-1.5 rounded-lg transition-colors text-xs font-medium"
                        title="删除"
                      >
                        <Trash2 size={12} />
                        删除
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {modalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="p-4 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-lg font-semibold">
                {editingPos ? '编辑持仓' : '添加持仓'}
              </h3>
              <button
                onClick={() => setModalOpen(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">币种符号</label>
                <input
                  type="text"
                  value={formData.symbol}
                  onChange={(e) => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
                  className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="如 BTC, ETH"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">币种名称</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="如 Bitcoin, Ethereum"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">成本价 (USD)</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.cost}
                  onChange={(e) => setFormData({ ...formData, cost: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0.00"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">持仓数量</label>
                <input
                  type="number"
                  step="0.0001"
                  value={formData.amount}
                  onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0.0000"
                />
              </div>
            </div>
            <div className="p-4 border-t border-gray-200 flex justify-end gap-2">
              <button
                onClick={() => setModalOpen(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded transition"
              >
                取消
              </button>
              <button
                onClick={editingPos ? handleEditPosition : handleAddPosition}
                disabled={submitting}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition disabled:opacity-50"
              >
                {submitting ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}

      {buyModalOpen && tradePos && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="p-4 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-lg font-semibold">买入 {tradePos.symbol}</h3>
              <button
                onClick={() => setBuyModalOpen(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">数量</label>
                <input
                  type="number"
                  step="0.0001"
                  value={tradeData.amount}
                  onChange={(e) => setTradeData({ ...tradeData, amount: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0.0000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">价格 (USD)</label>
                <input
                  type="number"
                  step="0.01"
                  value={tradeData.price}
                  onChange={(e) => setTradeData({ ...tradeData, price: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0.00"
                />
              </div>
              {tradeData.amount && tradeData.price && (
                <div className="p-3 bg-blue-50 rounded">
                  <p className="text-sm text-gray-600">
                    总金额: <span className="font-bold">${(parseFloat(tradeData.amount) * parseFloat(tradeData.price)).toFixed(2)}</span>
                  </p>
                </div>
              )}
            </div>
            <div className="p-4 border-t border-gray-200 flex justify-end gap-2">
              <button
                onClick={() => setBuyModalOpen(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded transition"
              >
                取消
              </button>
              <button
                onClick={handleBuy}
                disabled={tradeSubmitting}
                className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition disabled:opacity-50"
              >
                {tradeSubmitting ? '买入中...' : '买入'}
              </button>
            </div>
          </div>
        </div>
      )}

      {sellModalOpen && tradePos && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="p-4 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-lg font-semibold">卖出 {tradePos.symbol}</h3>
              <button
                onClick={() => setSellModalOpen(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">数量</label>
                <input
                  type="number"
                  step="0.0001"
                  max={tradePos.amount}
                  value={tradeData.amount}
                  onChange={(e) => setTradeData({ ...tradeData, amount: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0.0000"
                />
                <p className="text-xs text-gray-500 mt-1">最大可卖: {tradePos.amount.toFixed(4)}</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">价格 (USD)</label>
                <input
                  type="number"
                  step="0.01"
                  value={tradeData.price}
                  onChange={(e) => setTradeData({ ...tradeData, price: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0.00"
                />
              </div>
              {tradeData.amount && tradeData.price && (
                <div className="p-3 bg-red-50 rounded">
                  <p className="text-sm text-gray-600">
                    总金额: <span className="font-bold">${(parseFloat(tradeData.amount) * parseFloat(tradeData.price)).toFixed(2)}</span>
                  </p>
                </div>
              )}
            </div>
            <div className="p-4 border-t border-gray-200 flex justify-end gap-2">
              <button
                onClick={() => setSellModalOpen(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded transition"
              >
                取消
              </button>
              <button
                onClick={handleSell}
                disabled={tradeSubmitting}
                className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition disabled:opacity-50"
              >
                {tradeSubmitting ? '卖出中...' : '卖出'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CryptoAccount;
