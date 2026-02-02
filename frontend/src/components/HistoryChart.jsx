import React, { useEffect, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { getFundHistory } from '../services/api';

const RANGES = [
  { label: '近1周', val: 5 },
  { label: '近1月', val: 22 },
  { label: '近3月', val: 66 },
  { label: '近半年', val: 130 },
  { label: '近1年', val: 250 },
  { label: '成立来', val: 9999 },
];

export const HistoryChart = ({ fundId }) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [range, setRange] = useState(22); // Default 1M

  useEffect(() => {
    if (!fundId) return;
    
    const fetchHistory = async () => {
      setLoading(true);
      try {
        const history = await getFundHistory(fundId, range);
        setData(history);
      } catch (e) {
        console.error("Failed to load history", e);
      } finally {
        setLoading(false);
      }
    };
    
    fetchHistory();
  }, [fundId, range]);

  if (loading) return <div className="h-64 flex items-center justify-center text-slate-400">加载走势中...</div>;
  if (!data || data.length === 0) return <div className="h-64 flex items-center justify-center text-slate-400">暂无历史数据</div>;

  return (
    <div className="w-full">
      <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
        {RANGES.map((r) => (
          <button
            key={r.label}
            onClick={() => setRange(r.val)}
            className={`px-3 py-1 text-xs rounded-full whitespace-nowrap transition-colors ${
              range === r.val 
                ? 'bg-blue-600 text-white font-medium' 
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>
      
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="colorNav" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis 
              dataKey="date" 
              tick={{fontSize: 10, fill: '#94a3b8'}} 
              tickLine={false}
              axisLine={false}
              tickFormatter={(str) => str.slice(5)} // Show MM-DD
              minTickGap={30}
            />
            <YAxis 
              domain={['auto', 'auto']} 
              tick={{fontSize: 10, fill: '#94a3b8'}} 
              tickLine={false}
              axisLine={false}
              width={40}
            />
            <Tooltip 
              contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
              itemStyle={{ color: '#1e293b', fontSize: '12px', fontWeight: 'bold' }}
              labelStyle={{ color: '#64748b', fontSize: '10px', marginBottom: '4px' }}
            />
            <Area 
              type="monotone" 
              dataKey="nav" 
              stroke="#3b82f6" 
              strokeWidth={2}
              fillOpacity={1} 
              fill="url(#colorNav)" 
              animationDuration={500}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
