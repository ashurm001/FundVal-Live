import React, { useState, useMemo, useEffect } from 'react';
import { Search, Activity, Filter, ArrowUpDown } from 'lucide-react';
import { FundCard } from '../components/FundCard';
import { getFundCategories } from '../services/api';

export const FundList = ({ watchlist, setWatchlist, onSelectFund, onSubscribe, onRemove }) => {
  const [filterSector, setFilterSector] = useState("全部");
  const [sortType, setSortType] = useState("default"); // default, rate_desc, rate_asc
  const [categories, setCategories] = useState(["全部"]);

  // Load categories from backend
  useEffect(() => {
    getFundCategories().then(cats => {
      if (cats.length > 0) {
        setCategories(["全部", ...cats]);
      }
    });
  }, []);

  // Process list
  const processedList = useMemo(() => {
    let result = [...watchlist];

    // 1. Filter
    if (filterSector !== "全部") {
        result = result.filter(f => {
            // Use fuzzy matching for major categories
            // e.g. "股票型" matches "股票型", "混合型-偏股"
            return f.type && f.type.includes(filterSector.replace("型", ""));
        });
    }

    // 2. Sort
    if (sortType === "rate_desc") {
        result.sort((a, b) => (b.estRate || 0) - (a.estRate || 0));
    } else if (sortType === "rate_asc") {
        result.sort((a, b) => (a.estRate || 0) - (b.estRate || 0));
    }

    return result;
  }, [watchlist, filterSector, sortType]);

  return (
    <>
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
        {/* Header / Stats */}
        <div className="text-xs text-slate-500 px-1">
          <span className="font-bold text-slate-700 text-sm">我的关注 ({watchlist.length})</span>
          <span className="ml-3 inline-flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            实时更新
          </span>
        </div>

        {/* Controls */}
        <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
            {/* Sort Toggle - Now placed before category filter */}
            <button 
                onClick={() => setSortType(prev => prev === 'rate_desc' ? 'rate_asc' : 'rate_desc')}
                className="flex items-center gap-1 bg-white border border-slate-200 text-slate-600 px-3 py-1 rounded-lg text-xs hover:bg-slate-50 transition-colors whitespace-nowrap"
            >
                <ArrowUpDown className="w-3 h-3" />
                {sortType === 'default' ? '排序' : sortType === 'rate_desc' ? '涨幅 ↓' : '涨幅 ↑'}
            </button>

            {/* Sector Filter */}
            <div className="flex bg-white border border-slate-200 rounded-lg p-1">
                {categories.map(s => (
                    <button
                        key={s}
                        onClick={() => setFilterSector(s)}
                        className={`px-3 py-1 text-xs rounded-md transition-colors whitespace-nowrap ${
                            filterSector === s
                            ? 'bg-blue-100 text-blue-700 font-medium'
                            : 'text-slate-500 hover:bg-slate-50'
                        }`}
                    >
                        {s}
                    </button>
                ))}
            </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {processedList.map((fund) => (
          <FundCard 
            key={fund.id} 
            fund={fund} 
            onClick={onSelectFund}
            onRemove={onRemove}
            onSubscribe={onSubscribe}
          />
        ))}

        {watchlist.length === 0 && (
          <div className="col-span-1 md:col-span-2 py-12 text-center text-slate-400 border-2 border-dashed border-slate-200 rounded-xl">
            <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>暂无关注基金，请在上方搜索添加代码</p>
          </div>
        )}
        
        {watchlist.length > 0 && processedList.length === 0 && (
             <div className="col-span-1 md:col-span-2 py-12 text-center text-slate-400">
                <p>没有找到匹配板块的基金</p>
                <button onClick={() => setFilterSector("全部")} className="text-blue-600 text-xs mt-2 hover:underline">清除筛选</button>
             </div>
        )}
      </div>
    </>
  );
};
