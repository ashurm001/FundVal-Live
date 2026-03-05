import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Bell, Trash2, CheckCheck, ChevronRight, AlertTriangle, Lightbulb, X } from 'lucide-react';
import { getMessages, getMessage, markMessageAsRead, markAllMessagesAsRead, deleteMessage } from '../services/api';

const Messages = () => {
  const [messages, setMessages] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [messageCache, setMessageCache] = useState({});
  const pageSize = 20;

  const fetchMessages = useCallback(async (pageNum = 0) => {
    setLoading(true);
    try {
      const data = await getMessages('portfolio_analysis', pageSize, pageNum * pageSize);
      setMessages(data.messages || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('Failed to fetch messages', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMessages(page);
  }, [page, fetchMessages]);

  const handleViewMessage = useCallback(async (msg) => {
    // 检查缓存
    if (messageCache[msg.id]) {
      setSelectedMessage(messageCache[msg.id]);
      
      // Mark as read if needed
      if (!msg.read) {
        try {
          await markMessageAsRead(msg.id);
          setMessages(prev => 
            prev.map(m => m.id === msg.id ? { ...m, read: true } : m)
          );
        } catch (err) {
          console.error('Failed to mark as read', err);
        }
      }
      return;
    }

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
    const date = new Date(dateStr);
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
    <div className="max-w-6xl mx-auto p-4 md:p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-100 p-2 rounded-lg">
            <Bell className="w-6 h-6 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">消息中心</h1>
            <p className="text-sm text-slate-500">持仓分析历史记录</p>
          </div>
        </div>
        
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
                        {msg.score !== null && msg.score !== undefined && (
                          <span className={`px-2 py-0.5 rounded font-medium ${getScoreColor(msg.score)}`}>
                            评分: {msg.score}
                          </span>
                        )}
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

        {/* Message Detail */}
        {selectedMessage && (
          <div className="w-[480px] bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden sticky top-4 h-fit max-h-[calc(100vh-2rem)] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-slate-100 p-4 flex items-center justify-between">
              <h2 className="font-bold text-slate-800">分析详情</h2>
              <button
                onClick={() => setSelectedMessage(null)}
                className="p-1 hover:bg-slate-100 rounded-lg"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>
            
            {detailLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
              </div>
            ) : selectedMessage.error ? (
              <div className="p-4 text-red-500">{selectedMessage.error}</div>
            ) : (
              <div className="p-4 space-y-4">
                {/* Score */}
                {selectedMessage.score !== undefined && (
                  <div className="bg-slate-50 rounded-xl p-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-600">健康度评分</span>
                      <span className={`text-3xl font-bold ${getScoreColor(selectedMessage.score).split(' ')[0]}`}>
                        {selectedMessage.score}
                      </span>
                    </div>
                  </div>
                )}

                {/* Risk Level */}
                {selectedMessage.risk_level && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-500">风险评级:</span>
                    <span className={`px-2 py-1 rounded text-sm font-medium ${getRiskColor(selectedMessage.risk_level)}`}>
                      {selectedMessage.risk_level}
                    </span>
                  </div>
                )}

                {/* Problems */}
                {selectedMessage.content?.problems && selectedMessage.content.problems.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-red-500" />
                      发现的问题 ({selectedMessage.content.problems.length}个)
                    </h4>
                    <div className="space-y-2">
                      {selectedMessage.content.problems.map((problem, idx) => (
                        <div key={idx} className="bg-red-50 p-3 rounded-lg text-sm">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-red-700">{problem.type}</span>
                            {problem.fund_code && (
                              <span className="text-xs text-slate-500">{problem.fund_code}</span>
                            )}
                          </div>
                          <p className="text-slate-600">{problem.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Suggestions */}
                {selectedMessage.content?.suggestions && selectedMessage.content.suggestions.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
                      <Lightbulb className="w-4 h-4 text-yellow-500" />
                      优化建议
                    </h4>
                    <div className="space-y-2">
                      {selectedMessage.content.suggestions.map((suggestion, idx) => (
                        <div key={idx} className="bg-green-50 p-3 rounded-lg text-sm">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-green-700">{suggestion.action}</span>
                            <span className="text-xs text-slate-400">{suggestion.priority}优先级</span>
                          </div>
                          <p className="text-slate-600">{suggestion.target}</p>
                          <p className="text-xs text-slate-400 mt-1">{suggestion.logic}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Critique */}
                {selectedMessage.content?.critique && (
                  <div className="bg-slate-800 rounded-xl p-4 text-white">
                    <h4 className="text-sm font-semibold mb-2 text-slate-300">Linus 的总结</h4>
                    <p className="text-sm leading-relaxed whitespace-pre-line">
                      {selectedMessage.content.critique}
                    </p>
                  </div>
                )}

                {/* Created At */}
                <div className="text-xs text-slate-400 pt-2 border-t border-slate-100">
                  生成时间: {new Date(selectedMessage.created_at).toLocaleString('zh-CN')}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Messages;
