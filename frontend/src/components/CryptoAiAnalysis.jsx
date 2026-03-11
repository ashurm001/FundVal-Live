import React, { useState } from 'react';
import { Bot, Sparkles, RefreshCcw } from 'lucide-react';
import { api } from '../services/api';

export const CryptoAiAnalysis = ({ positions, summary }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAnalyze = async () => {
    if (!positions || positions.length === 0) {
      setError('暂无持仓数据，请先添加持仓');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      // 构建数字货币持仓分析数据
      const portfolioData = {
        positions: positions.map(pos => ({
          symbol: pos.symbol,
          name: pos.name,
          cost: pos.cost,
          amount: pos.amount,
          current_price: pos.current_price,
          change_24h: pos.change_24h,
          market_value: pos.market_value,
          total_income: pos.total_income,
          total_return_rate: pos.total_return_rate,
          day_income: pos.day_income,
        })),
        summary: {
          total_market_value: summary?.total_market_value || 0,
          total_cost: summary?.total_cost || 0,
          total_income: summary?.total_income || 0,
          total_return_rate: summary?.total_return_rate || 0,
          total_day_income: summary?.total_day_income || 0,
        },
        type: 'crypto' // 标记为数字货币类型
      };

      const response = await api.post('/ai/analyze_portfolio', portfolioData);
      
      // 分析完成后自动跳转到消息中心
      window.location.href = '#/messages';
    } catch (err) {
      setError('分析请求失败，请稍后重试');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gradient-to-br from-indigo-50 to-white rounded-2xl p-4 shadow-sm border border-indigo-100">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-indigo-600" />
          <h3 className="text-sm font-bold text-slate-800">AI 持仓诊断</h3>
        </div>
        
        {positions && positions.length > 0 && (
          <div className="text-xs text-slate-500">
            {positions.length} 种数字货币
          </div>
        )}
      </div>
      
      <div className="mt-3">
        <button 
          onClick={handleAnalyze}
          disabled={!positions || positions.length === 0 || loading}
          className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-medium transition-all shadow-md shadow-indigo-200 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <RefreshCcw className="w-4 h-4 animate-spin" />
              分析中...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              开始分析
            </>
          )}
        </button>
      </div>
      
      {error && (
        <div className="mt-3 p-2 bg-red-50 border border-red-100 rounded-lg">
          <p className="text-xs text-red-600">{error}</p>
        </div>
      )}
      
      <div className="mt-3 text-xs text-slate-500 leading-relaxed">
        <p>AI 将分析您的数字货币持仓结构、风险分布和收益情况，并提供优化建议。</p>
      </div>
    </div>
  );
};
