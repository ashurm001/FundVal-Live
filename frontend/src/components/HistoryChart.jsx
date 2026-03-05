import React, { useEffect, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, ReferenceDot, Scatter, ScatterChart, Cell } from 'recharts';
import { getFundHistory, getAiAnalysisHistory, getUserNotes, saveUserNote, updateUserNote, deleteUserNote } from '../services/api';
import { Bot, MessageSquare, Plus, X } from 'lucide-react';

const RANGES = [
  { label: '近1周', val: 5 },
  { label: '近1月', val: 22 },
  { label: '近3月', val: 66 },
  { label: '近半年', val: 130 },
  { label: '近1年', val: 250 },
  { label: '成立来', val: 9999 },
];

export const HistoryChart = ({ fundId, fundName }) => {
  const [data, setData] = useState([]);
  const [aiAnalyses, setAiAnalyses] = useState([]);
  const [userNotes, setUserNotes] = useState([]);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [selectedNote, setSelectedNote] = useState(null);
  const [selectedMarker, setSelectedMarker] = useState(null); // For combined marker modal
  const [loading, setLoading] = useState(true);
  const [range, setRange] = useState(22); // Default 1M
  const [showNoteInput, setShowNoteInput] = useState(false);
  const [noteContent, setNoteContent] = useState('');
  const [savingNote, setSavingNote] = useState(false);

  useEffect(() => {
    if (!fundId) return;

    const fetchData = async () => {
      setLoading(true);
      try {
        // Parallel fetch for better performance
        const [history, analyses, notes] = await Promise.all([
          getFundHistory(fundId, range),
          getAiAnalysisHistory(fundId, 50),
          getUserNotes(fundId, 50)
        ]);
        
        setData(history);
        setAiAnalyses(analyses);
        setUserNotes(notes);
      } catch (e) {
        console.error("Failed to load history", e);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [fundId, range]);

  const handleAnalysisClick = (analysis) => {
    setSelectedAnalysis(analysis);
  };

  const closeAnalysisModal = () => {
    setSelectedAnalysis(null);
  };

  const handleNoteClick = (note) => {
    setSelectedNote(note);
  };

  const closeNoteModal = () => {
    setSelectedNote(null);
  };

  const handleMarkerClick = (markerData) => {
    setSelectedMarker(markerData);
  };

  const closeMarkerModal = () => {
    setSelectedMarker(null);
    setEditingNote(null);
  };

  const [editingNote, setEditingNote] = useState(null);
  const [editNoteContent, setEditNoteContent] = useState('');
  const [editNoteColor, setEditNoteColor] = useState('#10b981');

  const handleEditNote = (note) => {
    console.log('handleEditNote called with note:', note);
    setEditingNote(note);
    setEditNoteContent(note.note_content);
    setEditNoteColor(note.note_color || '#10b981');
  };

  const handleSaveEditNote = async () => {
    console.log('handleSaveEditNote called');
    console.log('editingNote:', editingNote);
    console.log('editNoteContent:', editNoteContent);
    console.log('editNoteColor:', editNoteColor);
    
    if (!editingNote || !editNoteContent.trim()) {
      console.log('Validation failed');
      return;
    }
    
    try {
      console.log('Calling updateUserNote with:', editingNote.id, editNoteContent, editNoteColor);
      const result = await updateUserNote(editingNote.id, editNoteContent, editNoteColor);
      console.log('updateUserNote result:', result);
      
      if (result.id) {
        console.log('Update successful, updating local state');
        // Update local state
        setUserNotes(prev => prev.map(n => n.id === editingNote.id ? result : n));
        setEditingNote(null);
        setEditNoteContent('');
        // Update selected marker if needed
        if (selectedMarker) {
          setSelectedMarker(prev => ({
            ...prev,
            notes: prev.notes.map(note => note.id === editingNote.id ? result : note)
          }));
        }
      } else {
        console.log('Update failed, no id in result');
      }
    } catch (e) {
      console.error('Failed to update note', e);
    }
  };

  const handleDeleteNote = async (noteId) => {
    console.log('handleDeleteNote called with noteId:', noteId);
    if (!confirm('确定要删除这条笔记吗？')) return;
    
    try {
      console.log('Calling deleteUserNote with:', noteId);
      const result = await deleteUserNote(noteId);
      console.log('deleteUserNote result:', result);
      
      if (result.success) {
        console.log('Delete successful, updating local state');
        // Update local state
        setUserNotes(prev => prev.filter(n => n.id !== noteId));
        // Close marker modal if no more notes/ai for this date
        if (selectedMarker) {
          const updatedNotes = selectedMarker.notes.filter(n => n.id !== noteId);
          if (updatedNotes.length === 0 && selectedMarker.ai.length === 0) {
            closeMarkerModal();
          } else {
            setSelectedMarker({ ...selectedMarker, notes: updatedNotes });
          }
        }
      } else {
        console.log('Delete failed, success is false');
      }
    } catch (e) {
      console.error('Failed to delete note', e);
    }
  };

  const [noteDate, setNoteDate] = useState(new Date().toISOString().split('T')[0]);
  const [noteColor, setNoteColor] = useState('#10b981');

  const colorOptions = [
    { color: '#10b981', label: '绿色' },
    { color: '#3b82f6', label: '蓝色' },
    { color: '#f59e0b', label: '橙色' },
    { color: '#ef4444', label: '红色' },
    { color: '#8b5cf6', label: '紫色' },
    { color: '#ec4899', label: '粉色' },
  ];

  const handleSaveNote = async () => {
    if (!noteContent.trim()) return;
    
    setSavingNote(true);
    try {
      const result = await saveUserNote(fundId, fundName, noteContent, noteDate || null, noteColor);
      if (result.id) {
        // 直接添加新笔记到列表，不需要重新获取
        setUserNotes(prev => [result, ...prev]);
        setNoteContent('');
        setNoteDate(new Date().toISOString().split('T')[0]);
        setNoteColor('#10b981');
        setShowNoteInput(false);
      }
    } catch (e) {
      console.error('Failed to save note', e);
    } finally {
      setSavingNote(false);
    }
  };

  const getAnalysisMarkers = () => {
    const markers = [];
    if (!data || data.length === 0 || aiAnalyses.length === 0) return markers;

    const analysisMap = {};
    const processedDates = new Set();

    aiAnalyses.forEach(analysis => {
      const date = analysis.analysis_date;
      if (!analysisMap[date]) {
        analysisMap[date] = [];
      }
      analysisMap[date].push(analysis);
    });

    // Get date range of history data
    const historyDates = data.map(item => item.date).sort();
    const earliestDate = historyDates[0];
    const latestDate = historyDates[historyDates.length - 1];

    // Match analyses to history data points
    data.forEach(item => {
      if (analysisMap[item.date]) {
        const nav = item.nav;
        analysisMap[item.date].forEach(analysis => {
          markers.push({
            date: item.date,
            nav: nav,
            analysis: analysis
          });
        });
        processedDates.add(item.date);
      }
    });

    // For analyses with dates outside history range, place them at the nearest edge
    Object.keys(analysisMap).forEach(date => {
      if (processedDates.has(date)) return; // Skip already processed

      const analyses = analysisMap[date];
      let targetItem = null;

      if (date < earliestDate) {
        targetItem = data.find(item => item.date === earliestDate);
      } else if (date > latestDate) {
        targetItem = data.find(item => item.date === latestDate);
      } else {
        // Date is within range but no exact match, find the closest date
        const sortedData = [...data].sort((a, b) => new Date(a.date) - new Date(b.date));
        // Find the date that is closest to the analysis date
        let closestItem = null;
        let minDiff = Infinity;
        
        sortedData.forEach(item => {
          const diff = Math.abs(new Date(item.date) - new Date(date));
          if (diff < minDiff) {
            minDiff = diff;
            closestItem = item;
          }
        });
        
        targetItem = closestItem;
      }

      if (targetItem) {
        analyses.forEach(analysis => {
          markers.push({
            date: targetItem.date,
            nav: targetItem.nav,
            analysis: analysis
          });
        });
      }
    });

    return markers;
  };

  const getNoteMarkers = () => {
    const markers = [];
    if (!data || data.length === 0 || userNotes.length === 0) return markers;

    const noteMap = {};
    const processedDates = new Set();

    userNotes.forEach(note => {
      const date = note.note_date;
      if (!noteMap[date]) {
        noteMap[date] = [];
      }
      noteMap[date].push(note);
    });

    // Get date range of history data
    const historyDates = data.map(item => item.date).sort();
    const earliestDate = historyDates[0];
    const latestDate = historyDates[historyDates.length - 1];

    // Match notes to history data points
    data.forEach(item => {
      if (noteMap[item.date]) {
        const nav = item.nav;
        noteMap[item.date].forEach(note => {
          markers.push({
            date: item.date,
            nav: nav,
            note: note
          });
        });
        processedDates.add(item.date);
      }
    });

    // For notes with dates outside history range, place them at the nearest edge
    Object.keys(noteMap).forEach(date => {
      if (processedDates.has(date)) return;

      const notes = noteMap[date];
      let targetItem = null;

      if (date < earliestDate) {
        targetItem = data.find(item => item.date === earliestDate);
      } else if (date > latestDate) {
        targetItem = data.find(item => item.date === latestDate);
      } else {
        // Date is within range but no exact match, find the closest date
        const sortedData = [...data].sort((a, b) => new Date(a.date) - new Date(b.date));
        // Find the date that is closest to the note date
        let closestItem = null;
        let minDiff = Infinity;
        
        sortedData.forEach(item => {
          const diff = Math.abs(new Date(item.date) - new Date(date));
          if (diff < minDiff) {
            minDiff = diff;
            closestItem = item;
          }
        });
        
        targetItem = closestItem;
      }

      if (targetItem) {
        notes.forEach(note => {
          markers.push({
            date: targetItem.date,
            nav: targetItem.nav,
            note: note
          });
        });
      }
    });

    return markers;
  };

  const analysisMarkers = getAnalysisMarkers();
  const noteMarkers = getNoteMarkers();
  
  console.log('History data first 5 dates:', data.slice(0, 5).map(d => d.date));
  console.log('Analysis markers:', analysisMarkers.length, analysisMarkers.map(m => ({date: m.date, nav: m.nav})));
  console.log('Note markers:', noteMarkers.length, noteMarkers.map(m => ({date: m.date, nav: m.nav})));

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
      
      <div className="h-64 w-full" style={{ minHeight: '256px', minWidth: '100%' }}>
        <ResponsiveContainer width="100%" height={256} minWidth={0} minHeight={0}>
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
            {/* Render markers - one per date with all info */}
            {(() => {
              const allMarkers = [];
              
              // Group markers by date
              const markersByDate = {};
              
              analysisMarkers.forEach((marker) => {
                if (!markersByDate[marker.date]) markersByDate[marker.date] = { ai: [], notes: [] };
                markersByDate[marker.date].ai.push(marker.analysis);
              });
              
              noteMarkers.forEach((marker) => {
                if (!markersByDate[marker.date]) markersByDate[marker.date] = { ai: [], notes: [] };
                markersByDate[marker.date].notes.push(marker.note);
              });
              
              // Render one marker per date
              Object.keys(markersByDate).forEach((date, index) => {
                const { ai, notes } = markersByDate[date];
                const hasAi = ai.length > 0;
                const hasNotes = notes.length > 0;
                
                // Determine color based on content type
                let fillColor = '#10b981'; // Default green for notes only
                if (hasAi && hasNotes) fillColor = '#8b5cf6'; // Purple for both
                else if (hasAi) fillColor = '#f59e0b'; // Orange for AI only
                
                // Get nav from first available marker
                const nav = analysisMarkers.find(m => m.date === date)?.nav || 
                           noteMarkers.find(m => m.date === date)?.nav || 0;
                
                allMarkers.push(
                  <ReferenceDot
                    key={`marker-${date}-${index}`}
                    x={date}
                    y={nav}
                    r={7}
                    fill={fillColor}
                    stroke="white"
                    strokeWidth={2}
                    onClick={() => handleMarkerClick({ date, ai, notes })}
                    cursor="pointer"
                  />
                );
              });
              
              return allMarkers;
            })()}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Add note button */}
      <div className="flex justify-end mt-2">
        <button
          onClick={() => setShowNoteInput(true)}
          className="flex items-center gap-1 px-3 py-1.5 text-xs bg-emerald-50 text-emerald-600 rounded-lg hover:bg-emerald-100 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          添加笔记
        </button>
      </div>

      {/* Note input modal */}
      {showNoteInput && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowNoteInput(false)}>
          <div className="bg-white rounded-2xl p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-slate-800">添加笔记</h3>
              <button onClick={() => setShowNoteInput(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {/* Date selector */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-700 mb-1">日期</label>
              <input
                type="date"
                value={noteDate}
                onChange={(e) => setNoteDate(e.target.value)}
                className="w-full p-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              />
              <p className="text-xs text-slate-400 mt-1">不选择则使用今天日期</p>
            </div>
            
            {/* Color selector */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-700 mb-2">标记颜色</label>
              <div className="flex gap-2 flex-wrap">
                {colorOptions.map((option) => (
                  <button
                    key={option.color}
                    onClick={() => setNoteColor(option.color)}
                    className={`w-8 h-8 rounded-full border-2 transition-all ${
                      noteColor === option.color ? 'border-slate-800 scale-110' : 'border-transparent'
                    }`}
                    style={{ backgroundColor: option.color }}
                    title={option.label}
                  />
                ))}
              </div>
            </div>
            
            <textarea
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
              placeholder="记录你的投资思路..."
              className="w-full h-32 p-3 border border-slate-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setShowNoteInput(false)}
                className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSaveNote}
                disabled={!noteContent.trim() || savingNote}
                className="px-4 py-2 text-sm bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {savingNote ? '保存中...' : '保存'}
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedAnalysis && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={closeAnalysisModal}>
          <div className="bg-white rounded-2xl p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4 border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="bg-indigo-100 p-2 rounded-lg">
                  <Bot className="w-6 h-6 text-indigo-700" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-800">AI 分析报告</h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {selectedAnalysis.analysis_date} {selectedAnalysis.analysis_time}
                  </p>
                </div>
              </div>
              <button
                onClick={closeAnalysisModal}
                className="text-slate-400 hover:text-slate-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div className="bg-slate-50 rounded-xl p-4 text-xs text-slate-600">
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-bold">风险等级:</span>
                  <span className={`px-2 py-1 rounded text-xs font-bold ${
                    selectedAnalysis.risk_level?.includes('高') ? 'bg-red-50 text-red-600' :
                    selectedAnalysis.risk_level?.includes('中') ? 'bg-orange-50 text-orange-600' :
                    'bg-green-50 text-green-600'
                  }`}>
                    {selectedAnalysis.risk_level || '未知'}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-bold">位置:</span>
                  <span>{selectedAnalysis.status || '未知'}</span>
                </div>
              </div>

              {selectedAnalysis.indicators_desc && (
                <div className="bg-slate-50 rounded-xl p-4 text-xs text-slate-600">
                  {selectedAnalysis.indicators_desc}
                </div>
              )}

              <div className="prose prose-sm max-w-none text-slate-700 leading-relaxed whitespace-pre-line">
                {selectedAnalysis.analysis_report}
              </div>

              {selectedAnalysis.summary && (
                <div className="mt-4 p-4 bg-indigo-50 rounded-xl border border-indigo-100">
                  <h4 className="text-indigo-900 font-bold text-sm mb-2">核心结论</h4>
                  <p className="text-indigo-800 text-sm font-medium">
                    {selectedAnalysis.summary}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Note view modal */}
      {selectedNote && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={closeNoteModal}>
          <div className="bg-white rounded-2xl p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4 border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className="bg-emerald-100 p-2 rounded-lg">
                  <MessageSquare className="w-6 h-6 text-emerald-700" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-800">投资笔记</h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {selectedNote.note_date} {selectedNote.note_time}
                  </p>
                </div>
              </div>
              <button
                onClick={closeNoteModal}
                className="text-slate-400 hover:text-slate-600 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="text-slate-700 leading-relaxed whitespace-pre-line">
              {selectedNote.note_content}
            </div>
          </div>
        </div>
      )}

      {/* Combined marker modal - shows AI analysis and notes */}
      {selectedMarker && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={closeMarkerModal}>
          <div className="bg-white rounded-2xl p-6 max-w-lg w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4 border-b border-slate-100 pb-4">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${
                  selectedMarker.ai.length > 0 && selectedMarker.notes.length > 0 ? 'bg-purple-100' :
                  selectedMarker.ai.length > 0 ? 'bg-amber-100' : 'bg-emerald-100'
                }`}>
                  {selectedMarker.ai.length > 0 && selectedMarker.notes.length > 0 ? (
                    <Bot className="w-6 h-6 text-purple-700" />
                  ) : selectedMarker.ai.length > 0 ? (
                    <Bot className="w-6 h-6 text-amber-700" />
                  ) : (
                    <MessageSquare className="w-6 h-6 text-emerald-700" />
                  )}
                </div>
                <div>
                  <h3 className="font-bold text-slate-800">
                    {selectedMarker.ai.length > 0 && selectedMarker.notes.length > 0 ? 'AI分析 & 笔记' :
                     selectedMarker.ai.length > 0 ? 'AI分析' : '投资笔记'}
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">{selectedMarker.date}</p>
                </div>
              </div>
              <button
                onClick={closeMarkerModal}
                className="text-slate-400 hover:text-slate-600 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* AI Analysis Section */}
            {selectedMarker.ai.length > 0 && (
              <div className="mb-6">
                <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                  <Bot className="w-4 h-4 text-amber-600" />
                  AI 分析 ({selectedMarker.ai.length})
                </h4>
                {selectedMarker.ai.map((analysis, idx) => (
                  <div key={idx} className="bg-slate-50 rounded-xl p-4 mb-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        analysis.risk_level === '高风险' ? 'bg-red-100 text-red-700' :
                        analysis.risk_level === '中风险' ? 'bg-yellow-100 text-yellow-700' :
                        analysis.risk_level === '低风险' ? 'bg-green-100 text-green-700' :
                        'bg-slate-100 text-slate-700'
                      }`}>
                        {analysis.risk_level}
                      </span>
                      <span className="text-xs text-slate-400">{analysis.analysis_time}</span>
                    </div>
                    {analysis.summary && (
                      <p className="text-sm text-slate-700 font-medium mb-2">{analysis.summary}</p>
                    )}
                    {analysis.analysis_report && (
                      <div className="text-sm text-slate-600 whitespace-pre-line">{analysis.analysis_report}</div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Notes Section */}
            {selectedMarker.notes.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-emerald-600" />
                  用户笔记 ({selectedMarker.notes.length})
                </h4>
                {selectedMarker.notes.map((note) => (
                  <div key={note.id} className="bg-emerald-50 rounded-xl p-4 mb-3 border-l-4" style={{ borderLeftColor: note.note_color || '#10b981' }}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: note.note_color || '#10b981' }}></div>
                        <span className="text-xs text-slate-400">{note.note_time}</span>
                      </div>
                      <div className="flex gap-1">
                        <button
                          onClick={() => handleEditNote(note)}
                          className="p-1 text-slate-400 hover:text-blue-600 transition-colors"
                          title="编辑"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleDeleteNote(note.id)}
                          className="p-1 text-slate-400 hover:text-red-600 transition-colors"
                          title="删除"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>
                    <div className="text-sm text-slate-700 whitespace-pre-line">{note.note_content}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Edit Note Modal */}
      {editingNote && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4" onClick={() => setEditingNote(null)}>
          <div className="bg-white rounded-2xl p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-slate-800">编辑笔记</h3>
              <button onClick={() => setEditingNote(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {/* Color selector */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-700 mb-2">标记颜色</label>
              <div className="flex gap-2 flex-wrap">
                {colorOptions.map((opt) => (
                  <button
                    key={opt.color}
                    onClick={() => setEditNoteColor(opt.color)}
                    className={`w-8 h-8 rounded-full border-2 transition-all ${
                      editNoteColor === opt.color ? 'border-slate-800 scale-110' : 'border-transparent'
                    }`}
                    style={{ backgroundColor: opt.color }}
                    title={opt.label}
                  />
                ))}
              </div>
            </div>

            {/* Content input */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-700 mb-2">笔记内容</label>
              <textarea
                value={editNoteContent}
                onChange={(e) => setEditNoteContent(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 min-h-[120px] resize-none"
                placeholder="输入您的投资思路..."
              />
            </div>

            {/* Buttons */}
            <div className="flex gap-2">
              <button
                onClick={() => setEditingNote(null)}
                className="flex-1 px-4 py-2 text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSaveEditNote}
                disabled={!editNoteContent.trim()}
                className="flex-1 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
