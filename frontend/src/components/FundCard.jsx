import React, { useState } from 'react';
import { AlertCircle, Bell, Trash2, Clock, Activity } from 'lucide-react';
import { StatCard, getRateColor } from './StatCard';

export const FundCard = ({ fund, onClick, onRemove, onSubscribe }) => {
  const [removing, setRemoving] = useState(false);

  const handleRemove = (e) => {
    e.stopPropagation();
    if (removing) return; // Prevent duplicate clicks
    setRemoving(true);
    onRemove(fund.id);
  };

  return (
    <div 
      onClick={() => {
        console.log("Card clicked:", fund.id);
        onClick(fund.id);
      }}
      className="bg-white rounded-xl p-5 border border-slate-100 shadow-sm hover:shadow-md hover:border-blue-200 transition-all cursor-pointer relative overflow-hidden group"
    >
      {/* Card Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="font-bold text-slate-800 line-clamp-1 text-lg group-hover:text-blue-600 transition-colors">
            {fund.name}
          </h3>
          <div className="flex items-center gap-2 mt-1">
            <span className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-xs font-mono">{fund.id}</span>
            {/* Warning if data looks stale/mock */}
            {(!fund.estimate && fund.estRate === 0) && (
              <span className="flex items-center gap-1 text-orange-500 text-xs bg-orange-50 px-1.5 py-0.5 rounded">
                <AlertCircle className="w-3 h-3" /> 数据待更新
              </span>
            )}
          </div>
        </div>
        <div className="flex gap-1">
          <button 
            onClick={(e) => { e.stopPropagation(); onSubscribe(fund); }}
            className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-full transition-colors z-10"
            title="订阅提醒"
          >
            <Bell className="w-5 h-5" />
          </button>
          <button
            onClick={handleRemove}
            disabled={removing}
            className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-full transition-colors z-10 disabled:opacity-50 disabled:cursor-not-allowed"
            title="删除"
          >
            <Trash2 className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Data Grid */}
      <div className="grid grid-cols-3 gap-4 items-end pointer-events-none">
        <div className="col-span-1">
          <span className="text-xs text-slate-400 block mb-1">盘中估算</span>
          <div className={`text-3xl font-bold tracking-tight ${getRateColor(fund.estRate)}`}>
            {fund.estRate > 0 ? '+' : ''}{fund.estRate}%
          </div>
        </div>
        <div className="col-span-2 flex justify-between items-end pl-4 border-l border-slate-100">
          <StatCard label="估算净值" value={fund.estimate ? fund.estimate.toFixed(4) : '--'} />
          <StatCard label="昨日净值" value={fund.nav ? fund.nav.toFixed(4) : '--'} />
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-50 flex justify-between items-center pointer-events-none">
        <div className="flex items-center gap-1.5 text-xs text-slate-400">
          <Clock className="w-3 h-3" />
          {(() => {
            if (!fund.time) return '--:--';
            // 处理时间字符串，转换为本地时间
            const parts = fund.time.split(/[- :]/);
            const utcDate = new Date(Date.UTC(parts[0], parts[1]-1, parts[2], parts[3], parts[4], parts[5]));
            return utcDate.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
          })()}
        </div>
      </div>
      
      {/* Decorative Line */}
      <div className={`absolute bottom-0 left-0 w-full h-1 ${getRateColor(fund.estRate).replace('text', 'bg')} opacity-50`}></div>
    </div>
  );
};
