import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Bell, Trash2, CheckCheck, ChevronRight, AlertTriangle, Lightbulb, X, BarChart3, PieChart, Bot, TrendingUp } from 'lucide-react';
import { getMessages, getMessage, markMessageAsRead, markAllMessagesAsRead, deleteMessage } from '../services/api';

const Messages = () => {
  const [messages, setMessages] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [messageCache, setMessageCache] = useState({});
  const [activeType, setActiveType] = useState('all');
  const pageSize = 20;

  // 消息类型配置
  const messageTypes = [
    { key: 'all', label: '全部', icon: Bell },
    { key: 'portfolio_analysis', label: '持仓分析', icon: PieChart },
    { key: 'fund_analysis', label: '基金分析', icon: BarChart3 },
    { key: 'ai_review', label: 'AI审视', icon: Bot },
  ];

  const fetchMessages = useCallback(async (pageNum = 0, msgType = activeType) => {
    setLoading(true);
    try {
      // 根据类型获取消息
      const typeParam = msgType === 'all' ? null : msgType;
      const data = await getMessages(typeParam, pageSize, pageNum * pageSize);
      setMessages(data.messages || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('Failed to fetch messages', err);
    } finally {
      setLoading(false);
    }
  }, [activeType]);

  useEffect(() => {
    fetchMessages(page);
  }, [page, fetchMessages, activeType]);

  // 切换消息类型
  const handleTypeChange = useCallback((type) => {
    setActiveType(type);
    setPage(0);
  }, []);

  const handleViewMessage = useCallback(async (msg) => {
    setDetailLoading(true);
    try {
      const data = await getMessage(msg.id);
      setSelectedMessage(data);
      
      // 缓存消息详情
      setMessageCache(prev => ({ ...prev, [msg.id]: data }));
      
      // Mark as read
      if (!msg.read) {
        await markMessageAsRead(msg.id);
        setMessages(prev => 
          prev.map(m => m.id === msg.id ? { ...m, read: true } : m)
        );
      }
    } catch (err) {
      console.error('Failed to fetch message detail', err);
    } finally {
      setDetailLoading(false);
    }
  }, [messageCache]);

  const handleDeleteMessage = useCallback(async (e, messageId) => {
    e.stopPropagation();
    if (!confirm('确定删除这条消息吗？')) return;
    
    try {
      await deleteMessage(messageId);
      setMessages(prev => prev.filter(m => m.id !== messageId));
      setTotal(prev => prev - 1);
      if (selectedMessage?.id === messageId) {
        setSelectedMessage(null);
      }
      // 从缓存中删除
      setMessageCache(prev => {
        const newCache = { ...prev };
        delete newCache[messageId];
        return newCache;
      });
    } catch (err) {
      console.error('Failed to delete message', err);
    }
  }, [selectedMessage]);

  const handleMarkAllRead = useCallback(async () => {
    try {
      await markAllMessagesAsRead('portfolio_analysis');
      setMessages(prev => prev.map(m => ({ ...m, read: true })));
    } catch (err) {
      console.error('Failed to mark all as read', err);
    }
  }, []);

  const formatDate = useCallback((dateStr) => {
    // 处理UTC时间字符串，转换为本地时间
    let date;
    if (dateStr.includes('T') || dateStr.includes('Z')) {
      // ISO格式，需要转换为本地时间
      date = new Date(dateStr);
    } else {
      // 无时区的日期字符串，假设为UTC时间，需要转换为本地时间
      // 先解析为UTC时间，然后转换为本地时间
      const parts = dateStr.split(/[- :]/);
      date = new Date(Date.UTC(parts[0], parts[1]-1, parts[2], parts[3], parts[4], parts[5]));
    }
    
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return '刚刚';
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays < 7) return `${diffDays}天前`;
    return date.toLocaleDateString('zh-CN');
  }, []);

  const getScoreColor = useCallback((score) => {
    if (score >= 80) return 'text-green-500 bg-green-50';
    if (score >= 60) return 'text-yellow-500 bg-yellow-50';
    if (score >= 40) return 'text-orange-500 bg-orange-50';
    return 'text-red-500 bg-red-50';
  }, []);

  const getRiskColor = useCallback((level) => {
    if (!level) return 'text-slate-500 bg-slate-100';
    if (level.includes('灾难') || level.includes('自杀')) return 'text-red-600 bg-red-100';
    if (level.includes('激进')) return 'text-orange-600 bg-orange-50';
    if (level.includes('平衡')) return 'text-blue-600 bg-blue-50';
    if (level.includes('稳健')) return 'text-green-600 bg-green-50';
    if (level.includes('保守')) return 'text-slate-600 bg-slate-100';
    return 'text-slate-500 bg-slate-100';
  }, []);

  const totalPages = useMemo(() => Math.ceil(total / pageSize), [total, pageSize]);
  const hasUnreadMessages = useMemo(() => messages.some(m => !m.read), [messages]);

  return (
    <div className="space-y-6">
      {/* 消息类型筛选标签 */}
      <div className="flex flex-wrap gap-2 mb-4">
        {messageTypes.map((type) => {
          const Icon = type.icon;
          return (
            <button
              key={type.key}
              onClick={() => handleTypeChange(type.key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeType === type.key
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-slate-600 hover:bg-slate-50 border border-slate-200'
              }`}
            >
              <Icon className="w-4 h-4" />
              {type.label}
            </button>
          );
        })}
      </div>

      <div className="flex justify-end mb-6">
        {hasUnreadMessages && (
          <button
            onClick={handleMarkAllRead}
            className="flex items-center gap-2 text-sm text-indigo-600 hover:text-indigo-700 px-3 py-2 rounded-lg hover:bg-indigo-50 transition-colors"
          >
            <CheckCheck className="w-4 h-4" />
            全部已读
          </button>
        )}
      </div>

      <div className="flex gap-6">
        {/* Message List */}
        <div className="flex-1">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
          ) : messages.length === 0 ? (
            <div className="bg-white rounded-2xl p-12 text-center shadow-sm border border-slate-100">
              <Bell className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p className="text-slate-500">暂无消息</p>
              <p className="text-sm text-slate-400 mt-1">持仓分析结果将保存在这里</p>
            </div>
          ) : (
            <div className="space-y-3">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  onClick={() => handleViewMessage(msg)}
                  className={`bg-white rounded-xl p-4 shadow-sm border cursor-pointer transition-all hover:shadow-md ${
                    msg.read ? 'border-slate-100' : 'border-indigo-200 bg-indigo-50/30'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        {!msg.read && (
                          <span className="w-2 h-2 bg-indigo-500 rounded-full"></span>
                        )}
                        <h3 className="font-semibold text-slate-800">{msg.title}</h3>
                      </div>
                      
                      {msg.summary && (
                        <p className="text-sm text-slate-500 line-clamp-2 mb-2">{msg.summary}</p>
                      )}
                      
                      <div className="flex items-center gap-3 text-xs">
                        {msg.risk_level && (
                          <span className={`px-2 py-0.5 rounded font-medium ${getRiskColor(msg.risk_level)}`}>
                            {msg.risk_level}
                          </span>
                        )}
                        <span className="text-slate-400">{formatDate(msg.created_at)}</span>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => handleDeleteMessage(e, msg.id)}
                        className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <ChevronRight className="w-5 h-5 text-slate-300" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1.5 text-sm rounded-lg border border-slate-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50"
              >
                上一页
              </button>
              <span className="text-sm text-slate-500">
                第 {page + 1} / {totalPages} 页
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="px-3 py-1.5 text-sm rounded-lg border border-slate-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50"
              >
                下一页
              </button>
            </div>
          )}
        </div>

        {/* Message Detail Modal */}
        {selectedMessage && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
              <div className="sticky top-0 bg-white border-b border-slate-100 p-4 flex items-center justify-between flex-shrink-0">
                <h2 className="font-bold text-slate-800">分析详情</h2>
                <button
                  onClick={() => setSelectedMessage(null)}
                  className="p-1 hover:bg-slate-100 rounded-lg"
                >
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>
              <div className="overflow-y-auto flex-1 p-4">
                {detailLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                  </div>
                ) : selectedMessage.error ? (
                  <div className="text-red-500">{selectedMessage.error}</div>
                ) : (
                  <div className="space-y-4">
                    {/* Risk Level */}
                    {selectedMessage.risk_level && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-slate-500">风险评级:</span>
                        <span className={`px-2 py-1 rounded text-sm font-medium ${getRiskColor(selectedMessage.risk_level)}`}>
                          {selectedMessage.risk_level}
                        </span>
                      </div>
                    )}

                    {/* Fund Analysis Detail - 单个基金分析详情 */}
                    {selectedMessage.msg_type === 'fund_analysis' && selectedMessage.content && (
                      <>
                        {/* 基金信息 */}
                        <div className="bg-indigo-50 rounded-xl p-4">
                          <h4 className="text-sm font-semibold text-indigo-900 mb-2">
                            {selectedMessage.content.fund_name} ({selectedMessage.content.fund_code})
                          </h4>
                          {selectedMessage.content.indicators && (
                            <div className="text-sm text-indigo-700">
                              <span className="font-medium">市场位置:</span> {selectedMessage.content.indicators.status}
                              <p className="text-xs text-indigo-600 mt-1">{selectedMessage.content.indicators.desc}</p>
                            </div>
                          )}
                        </div>

                        {/* 分析报告 */}
                        {selectedMessage.content.analysis_report && (
                          <div className="bg-white border border-slate-200 rounded-xl p-4">
                            <h4 className="text-sm font-semibold text-slate-700 mb-3">AI 分析报告</h4>
                            <div className="prose prose-sm max-w-none text-slate-700 leading-relaxed whitespace-pre-line text-sm">
                              {selectedMessage.content.analysis_report}
                            </div>
                          </div>
                        )}

                        {/* 核心结论 */}
                        {selectedMessage.content.summary && (
                          <div className="bg-amber-50 rounded-xl p-4 border border-amber-100">
                            <h4 className="text-sm font-semibold text-amber-900 mb-2">核心结论</h4>
                            <p className="text-sm text-amber-800">{selectedMessage.content.summary}</p>
                          </div>
                        )}
                      </>
                    )}

                    {/* Overview - 持仓整体概况 (仅 portfolio_analysis 类型显示) */}
                    {selectedMessage.content?.overview && (
                      <div className="bg-slate-50 rounded-xl p-4">
                        <h4 className="text-sm font-semibold text-slate-700 mb-3">持仓整体概况</h4>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-slate-500">总仓位:</span>
                            <span className="font-medium">{selectedMessage.content.overview.total_position}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">行业分布:</span>
                            <span className="font-medium">{selectedMessage.content.overview.industry_distribution?.join(', ')}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">集中度风险:</span>
                            <span className="font-medium">{selectedMessage.content.overview.concentration_risk?.risk_level}</span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Risk Analysis - 收益与风险分析 */}
                    {selectedMessage.content?.risk_analysis && (
                      <div className="bg-blue-50 rounded-xl p-4">
                        <h4 className="text-sm font-semibold text-slate-700 mb-3">收益与风险分析</h4>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-slate-500">总盈亏:</span>
                            <span className={`font-medium ${selectedMessage.content.risk_analysis.total_pnl < 0 ? 'text-red-600' : 'text-green-600'}`}>
                              {selectedMessage.content.risk_analysis.total_pnl}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">盈亏比例:</span>
                            <span className="font-medium">{selectedMessage.content.risk_analysis.pnl_ratio}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">波动率估算:</span>
                            <span className="font-medium">{selectedMessage.content.risk_analysis.volatility_estimate}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">回撤风险:</span>
                            <span className="font-medium">{selectedMessage.content.risk_analysis.drawdown_risk}</span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Fund Analysis - 标的基本面与逻辑 */}
                    {selectedMessage.content?.fund_analysis && selectedMessage.content.fund_analysis.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                          <Lightbulb className="w-4 h-4 text-yellow-500" />
                          标的基本面分析
                        </h4>
                        <div className="space-y-3">
                          {selectedMessage.content.fund_analysis.map((fund, idx) => (
                            <div key={idx} className="bg-white border border-slate-200 p-3 rounded-lg text-sm">
                              <div className="flex items-center justify-between mb-2">
                                <span className="font-medium text-slate-800">{fund.name} ({fund.code})</span>
                                <span className={`text-xs px-2 py-0.5 rounded ${fund.prosperity === '高' ? 'bg-green-100 text-green-700' : fund.prosperity === '低' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'}`}>
                                  景气度: {fund.prosperity}
                                </span>
                              </div>
                              <p className="text-slate-600 mb-2">{fund.logic}</p>
                              <div className="flex gap-4 text-xs text-slate-500">
                                <span>估值: {fund.valuation}</span>
                                <span className="text-red-500">风险: {fund.risks?.join(', ')}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Diagnosis - 持仓问题诊断 */}
                    {selectedMessage.content?.diagnosis && (
                      <div>
                        <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-red-500" />
                          持仓问题诊断
                        </h4>
                        <div className="space-y-2">
                          {selectedMessage.content.diagnosis.structure_issues?.length > 0 && (
                            <div className="bg-red-50 p-3 rounded-lg text-sm">
                              <span className="font-medium text-red-700">结构问题:</span>
                              <p className="text-slate-600 mt-1">{selectedMessage.content.diagnosis.structure_issues.join('; ')}</p>
                            </div>
                          )}
                          {selectedMessage.content.diagnosis.overlap_issues?.length > 0 && (
                            <div className="bg-orange-50 p-3 rounded-lg text-sm">
                              <span className="font-medium text-orange-700">重复持仓:</span>
                              <p className="text-slate-600 mt-1">{selectedMessage.content.diagnosis.overlap_issues.join('; ')}</p>
                            </div>
                          )}
                          {selectedMessage.content.diagnosis.black_swan_risks?.length > 0 && (
                            <div className="bg-purple-50 p-3 rounded-lg text-sm">
                              <span className="font-medium text-purple-700">黑天鹅风险:</span>
                              <p className="text-slate-600 mt-1">{selectedMessage.content.diagnosis.black_swan_risks.join('; ')}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Recommendations - 优化策略与调仓建议 */}
                    {selectedMessage.content?.recommendations && selectedMessage.content.recommendations.length > 0 && (
                      <div>
                        <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                          <Lightbulb className="w-4 h-4 text-green-500" />
                          优化策略与调仓建议
                        </h4>
                        <div className="space-y-2">
                          {selectedMessage.content.recommendations.map((rec, idx) => (
                            <div key={idx} className="bg-green-50 p-3 rounded-lg text-sm">
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-medium text-green-700">{rec.action} - {rec.target_name}</span>
                                <span className={`text-xs px-2 py-0.5 rounded ${rec.priority === '高' ? 'bg-red-100 text-red-700' : rec.priority === '中' ? 'bg-yellow-100 text-yellow-700' : 'bg-blue-100 text-blue-700'}`}>
                                  {rec.priority}优先级
                                </span>
                              </div>
                              <p className="text-slate-600">{rec.proportion}</p>
                              <p className="text-xs text-slate-400 mt-1">{rec.logic}</p>
                              {rec.buy_sell_points && (
                                <p className="text-xs text-blue-600 mt-1">买卖点: {rec.buy_sell_points}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* AI Review - AI审视报告详情 */}
                    {selectedMessage.msg_type === 'ai_review' && selectedMessage.content && (
                      <>
                        {/* 账户信息 */}
                        <div className="bg-indigo-50 rounded-xl p-4">
                          <h4 className="text-sm font-semibold text-indigo-900 mb-2">
                            {selectedMessage.content.account_type} - 审视日期: {selectedMessage.content.review_date}
                          </h4>
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <span className="text-indigo-600">AI账户收益率: </span>
                              <span className={`font-medium ${selectedMessage.content.ai_return_rate >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                                {selectedMessage.content.ai_return_rate >= 0 ? '+' : ''}{selectedMessage.content.ai_return_rate?.toFixed(2)}%
                              </span>
                            </div>
                            <div>
                              <span className="text-indigo-600">用户账户收益率: </span>
                              <span className={`font-medium ${selectedMessage.content.source_return_rate >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                                {selectedMessage.content.source_return_rate >= 0 ? '+' : ''}{selectedMessage.content.source_return_rate?.toFixed(2)}%
                              </span>
                            </div>
                            <div>
                              <span className="text-indigo-600">AI总资产: </span>
                              <span className="font-medium">{selectedMessage.content.ai_total_value?.toLocaleString('zh-CN')} 元</span>
                            </div>
                            <div>
                              <span className="text-indigo-600">执行交易: </span>
                              <span className="font-medium">{selectedMessage.content.trades_executed} 笔</span>
                            </div>
                          </div>
                        </div>

                        {/* 市场分析 */}
                        {selectedMessage.content.market_analysis && (
                          <div className="bg-gradient-to-br from-slate-50 to-blue-50 border border-slate-200 rounded-xl p-4">
                            <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                              <TrendingUp className="w-4 h-4 text-blue-500" />
                              市场分析
                            </h4>
                            <div className="bg-white/80 rounded-lg p-3 border border-slate-100">
                              <div className="text-slate-700 text-sm leading-relaxed whitespace-pre-line">
                                {selectedMessage.content.market_analysis}
                              </div>
                            </div>
                          </div>
                        )}

                        {/* 组合分析 */}
                        {selectedMessage.content.portfolio_analysis && (
                          <div className="bg-gradient-to-br from-white to-green-50 border border-slate-200 rounded-xl p-4">
                            <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                              <PieChart className="w-4 h-4 text-green-500" />
                              组合分析
                            </h4>
                            <div className="bg-white/80 rounded-lg p-3 border border-slate-100">
                              <div className="text-slate-700 text-sm leading-relaxed whitespace-pre-line">
                                {selectedMessage.content.portfolio_analysis}
                              </div>
                            </div>
                          </div>
                        )}

                        {/* 收益对比 */}
                        {selectedMessage.content.performance_comparison && (
                          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4">
                            <h4 className="text-sm font-semibold text-blue-900 mb-3 flex items-center gap-2">
                              <BarChart3 className="w-4 h-4 text-blue-600" />
                              收益对比分析
                            </h4>
                            <div className="bg-white/80 rounded-lg p-3 border border-blue-100">
                              <div className="text-blue-800 text-sm leading-relaxed whitespace-pre-line">
                                {selectedMessage.content.performance_comparison}
                              </div>
                            </div>
                          </div>
                        )}

                        {/* 调仓策略 */}
                        {selectedMessage.content.adjustment_strategy && (
                          <div className="bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-200 rounded-xl p-4">
                            <h4 className="text-sm font-semibold text-amber-900 mb-3 flex items-center gap-2">
                              <Lightbulb className="w-4 h-4 text-amber-600" />
                              调仓策略
                            </h4>
                            <div className="space-y-4">
                              {/* 核心目标 */}
                              {selectedMessage.content.adjustment_strategy.includes('核心目标：') && (
                                <div className="bg-white/80 rounded-lg p-3 border border-amber-100">
                                  <div className="font-semibold text-amber-900 mb-2">核心目标：</div>
                                  <div className="text-amber-800 text-sm">
                                    {selectedMessage.content.adjustment_strategy.split('核心目标：')[1].split('具体策略：')[0]}
                                  </div>
                                </div>
                              )}
                              
                              {/* 具体策略 */}
                              {selectedMessage.content.adjustment_strategy.includes('具体策略：') && (
                                <div>
                                  <div className="font-semibold text-amber-900 mb-2">具体策略：</div>
                                  <div className="space-y-3">
                                    {selectedMessage.content.adjustment_strategy.split('具体策略：')[1].split(/\d+）/).filter(item => item.trim()).map((strategy, index) => {
                                      if (strategy.trim()) {
                                        return (
                                          <div key={index} className="bg-white/80 rounded-lg p-3 border border-amber-100">
                                            <div className="text-amber-800 text-sm">
                                              {strategy.trim()}
                                            </div>
                                          </div>
                                        );
                                      }
                                      return null;
                                    })}
                                  </div>
                                </div>
                              )}
                              
                              {/* 普通文本格式 */}
                              {!selectedMessage.content.adjustment_strategy.includes('核心目标：') && !selectedMessage.content.adjustment_strategy.includes('具体策略：') && (
                                <div className="bg-white/80 rounded-lg p-3 border border-amber-100">
                                  <div className="text-amber-800 text-sm whitespace-pre-line">
                                    {selectedMessage.content.adjustment_strategy}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                        {/* 交易记录 */}
                        {selectedMessage.content.trades && selectedMessage.content.trades.length > 0 && (
                          <div>
                            <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                              <Lightbulb className="w-4 h-4 text-green-500" />
                              执行的交易
                            </h4>
                            <div className="space-y-2">
                              {selectedMessage.content.trades.map((trade, idx) => (
                                <div key={idx} className="bg-green-50 p-3 rounded-lg text-sm">
                                  <div className="flex items-center justify-between mb-1">
                                    <span className="font-medium text-green-700">
                                      {trade.trade_type === 'buy' ? '买入' : '卖出'} - {trade.name} ({trade.code})
                                    </span>
                                    <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">
                                      {trade.shares} 份 @ {trade.price?.toFixed(4)}
                                    </span>
                                  </div>
                                  <p className="text-slate-600">金额: {trade.amount?.toLocaleString('zh-CN')} 元</p>
                                  <p className="text-xs text-slate-400 mt-1">理由: {trade.reason}</p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </>
                    )}

                    {/* Conclusion - 总结性结论 */}
                    {selectedMessage.content?.conclusion && (
                      <div className="bg-slate-800 rounded-xl p-4 text-white">
                        <h4 className="text-sm font-semibold mb-2 text-slate-300">分析结论</h4>
                        <p className="text-sm leading-relaxed whitespace-pre-line">
                          {selectedMessage.content.conclusion}
                        </p>
                      </div>
                    )}

                    {/* Created At */}
                    <div className="text-xs text-slate-400 pt-2 border-t border-slate-100">
                      生成时间: {(() => {
                        const dateStr = selectedMessage.created_at;
                        // 假设数据库中的时间是UTC时间，需要转换为本地时间
                        // 先创建一个UTC时间对象，然后转换为本地时间
                        const parts = dateStr.split(/[- :]/);
                        const utcDate = new Date(Date.UTC(parts[0], parts[1]-1, parts[2], parts[3], parts[4], parts[5]));
                        return utcDate.toLocaleString('zh-CN');
                      })()}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Messages;
