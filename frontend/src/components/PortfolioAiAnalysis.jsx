import React, { useState } from 'react';
import { Bot, Sparkles, RefreshCcw } from 'lucide-react';
import { api } from '../services/api';

export const PortfolioAiAnalysis = ({ positions, summary }) => {
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
      // 构建持仓分析数据
      const portfolioData = {
        positions: positions.map(pos => ({
          code: pos.code,
          name: pos.name,
          type: pos.type,
          cost: pos.cost,
          shares: pos.shares,
          nav: pos.nav,
          latest_nav: pos.latest_nav,
          estimate: pos.estimate,
          est_rate: pos.est_rate,
          accumulated_income: pos.accumulated_income,
          accumulated_return_rate: pos.accumulated_return_rate,
          day_income: pos.day_income,
          total_income: pos.total_income,
          total_return_rate: pos.total_return_rate,
          actual_market_value: pos.actual_market_value,
        })),
        summary: {
          total_market_value: summary?.total_market_value || 0,
          total_cost: summary?.total_cost || 0,
          total_income: summary?.total_income || 0,
          total_return_rate: summary?.total_return_rate || 0,
          total_day_income: summary?.total_day_income || 0,
        }
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
            {positions.length} 只基金
          </div>
        )}
      </div>
      
      <div className="mt-3">
        <button 
          onClick={handleAnalyze}
          disabled={!positions || positions.length === 0}
          className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-medium transition-all shadow-md shadow-indigo-200 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <RefreshCcw className="w-4 h-4 animate-spin" /> 诊断中...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" /> 诊断持仓
            </>
          )}
        </button>
        {error && <p className="text-red-500 text-xs mt-2 text-center">{error}</p>}
      </div>
    </div>
  );
};
