import React, { useState, useRef } from 'react';
import { Download, Upload, FileJson, FileSpreadsheet, AlertCircle, CheckCircle, X } from 'lucide-react';
import { exportPositionsJson, exportPositionsCsv, importPositionsJson, importPositionsCsv } from '../services/api';

const DataTransfer = ({ onClose, onSuccess }) => {
  const [activeTab, setActiveTab] = useState('export');
  const [exportFormat, setExportFormat] = useState('json');
  const [importFormat, setImportFormat] = useState('json');
  const [mergeStrategy, setMergeStrategy] = useState('replace');
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  // 导出数据
  const handleExport = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      if (exportFormat === 'json') {
        await exportPositionsJson();
      } else {
        await exportPositionsCsv();
      }
      setResult({
        success: true,
        message: `数据已成功导出为 ${exportFormat.toUpperCase()} 格式`
      });
    } catch (err) {
      setError(err.response?.data?.detail || '导出失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 选择文件
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      // 验证文件类型
      const expectedExtension = importFormat === 'json' ? '.json' : '.csv';
      if (!file.name.endsWith(expectedExtension)) {
        setError(`请选择 ${expectedExtension} 格式的文件`);
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
      setError(null);
      setResult(null);
    }
  };

  // 导入数据
  const handleImport = async () => {
    if (!selectedFile) {
      setError('请先选择要导入的文件');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      let response;
      if (importFormat === 'json') {
        response = await importPositionsJson(selectedFile, 1, mergeStrategy);
      } else {
        response = await importPositionsCsv(selectedFile, 1, mergeStrategy);
      }

      setResult({
        success: true,
        message: '数据导入成功',
        stats: response.stats
      });

      // 清空文件选择
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      // 通知父组件刷新数据
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      setError(err.response?.data?.detail || '导入失败，请检查文件格式');
    } finally {
      setLoading(false);
    }
  };

  // 渲染导入结果统计
  const renderStats = (stats) => {
    if (!stats) return null;

    return (
      <div className="mt-4 p-4 bg-slate-50 rounded-lg text-sm">
        <h4 className="font-medium text-slate-700 mb-2">导入统计</h4>
        <div className="grid grid-cols-2 gap-2">
          {stats.positions_added > 0 && (
            <div className="flex justify-between">
              <span className="text-slate-500">新增基金持仓:</span>
              <span className="text-green-600 font-medium">+{stats.positions_added}</span>
            </div>
          )}
          {stats.positions_updated > 0 && (
            <div className="flex justify-between">
              <span className="text-slate-500">更新基金持仓:</span>
              <span className="text-blue-600 font-medium">{stats.positions_updated}</span>
            </div>
          )}
          {stats.positions_skipped > 0 && (
            <div className="flex justify-between">
              <span className="text-slate-500">跳过基金持仓:</span>
              <span className="text-slate-600 font-medium">{stats.positions_skipped}</span>
            </div>
          )}
          {stats.transactions_added > 0 && (
            <div className="flex justify-between">
              <span className="text-slate-500">新增基金交易:</span>
              <span className="text-green-600 font-medium">+{stats.transactions_added}</span>
            </div>
          )}
          {stats.crypto_positions_added > 0 && (
            <div className="flex justify-between">
              <span className="text-slate-500">新增数字货币:</span>
              <span className="text-green-600 font-medium">+{stats.crypto_positions_added}</span>
            </div>
          )}
          {stats.crypto_positions_updated > 0 && (
            <div className="flex justify-between">
              <span className="text-slate-500">更新数字货币:</span>
              <span className="text-blue-600 font-medium">{stats.crypto_positions_updated}</span>
            </div>
          )}
          {stats.crypto_transactions_added > 0 && (
            <div className="flex justify-between">
              <span className="text-slate-500">新增数字货币交易:</span>
              <span className="text-green-600 font-medium">+{stats.crypto_transactions_added}</span>
            </div>
          )}
          {stats.ai_accounts_added > 0 && (
            <div className="flex justify-between">
              <span className="text-slate-500">新增AI账户:</span>
              <span className="text-green-600 font-medium">+{stats.ai_accounts_added}</span>
            </div>
          )}
          {stats.ai_positions_added > 0 && (
            <div className="flex justify-between">
              <span className="text-slate-500">新增AI持仓:</span>
              <span className="text-green-600 font-medium">+{stats.ai_positions_added}</span>
            </div>
          )}
          {stats.ai_trades_added > 0 && (
            <div className="flex justify-between">
              <span className="text-slate-500">新增AI交易:</span>
              <span className="text-green-600 font-medium">+{stats.ai_trades_added}</span>
            </div>
          )}
          {stats.ai_value_history_added > 0 && (
            <div className="flex justify-between">
              <span className="text-slate-500">新增AI历史:</span>
              <span className="text-green-600 font-medium">+{stats.ai_value_history_added}</span>
            </div>
          )}
          {stats.ai_reviews_added > 0 && (
            <div className="flex justify-between">
              <span className="text-slate-500">新增AI审视:</span>
              <span className="text-green-600 font-medium">+{stats.ai_reviews_added}</span>
            </div>
          )}
        </div>
        {stats.errors && stats.errors.length > 0 && (
          <div className="mt-3">
            <span className="text-red-500 text-xs">错误 ({stats.errors.length}个):</span>
            <ul className="mt-1 text-xs text-red-400 space-y-1 max-h-20 overflow-y-auto">
              {stats.errors.slice(0, 5).map((err, idx) => (
                <li key={idx}>{err}</li>
              ))}
              {stats.errors.length > 5 && (
                <li>...还有 {stats.errors.length - 5} 个错误</li>
              )}
            </ul>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-100">
          <h2 className="text-lg font-semibold text-slate-800">数据备份与恢复</h2>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-100">
          <button
            onClick={() => {
              setActiveTab('export');
              setError(null);
              setResult(null);
            }}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              activeTab === 'export'
                ? 'text-indigo-600 border-b-2 border-indigo-600'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <Download className="w-4 h-4 inline mr-1" />
            导出数据
          </button>
          <button
            onClick={() => {
              setActiveTab('import');
              setError(null);
              setResult(null);
            }}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              activeTab === 'import'
                ? 'text-indigo-600 border-b-2 border-indigo-600'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <Upload className="w-4 h-4 inline mr-1" />
            导入数据
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {activeTab === 'export' ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  选择导出格式
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => setExportFormat('json')}
                    className={`flex items-center gap-3 p-3 rounded-lg border-2 transition-all ${
                      exportFormat === 'json'
                        ? 'border-indigo-500 bg-indigo-50'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <FileJson className={`w-6 h-6 ${exportFormat === 'json' ? 'text-indigo-600' : 'text-slate-400'}`} />
                    <div className="text-left">
                      <div className={`font-medium ${exportFormat === 'json' ? 'text-indigo-700' : 'text-slate-700'}`}>
                        JSON
                      </div>
                      <div className="text-xs text-slate-500">完整数据备份</div>
                    </div>
                  </button>
                  <button
                    onClick={() => setExportFormat('csv')}
                    className={`flex items-center gap-3 p-3 rounded-lg border-2 transition-all ${
                      exportFormat === 'csv'
                        ? 'border-indigo-500 bg-indigo-50'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <FileSpreadsheet className={`w-6 h-6 ${exportFormat === 'csv' ? 'text-indigo-600' : 'text-slate-400'}`} />
                    <div className="text-left">
                      <div className={`font-medium ${exportFormat === 'csv' ? 'text-indigo-700' : 'text-slate-700'}`}>
                        CSV
                      </div>
                      <div className="text-xs text-slate-500">仅基金持仓</div>
                    </div>
                  </button>
                </div>
              </div>

              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-700">
                  <strong>提示:</strong> {exportFormat === 'json'
                    ? 'JSON格式包含完整的持仓数据、交易记录和数字货币信息，适合完整备份。'
                    : 'CSV格式仅包含基金持仓数据，适合在Excel中查看或编辑。'}
                </p>
              </div>

              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 text-red-600 rounded-lg text-sm">
                  <AlertCircle className="w-4 h-4" />
                  {error}
                </div>
              )}

              {result?.success && (
                <div className="flex items-center gap-2 p-3 bg-green-50 text-green-600 rounded-lg text-sm">
                  <CheckCircle className="w-4 h-4" />
                  {result.message}
                </div>
              )}

              <button
                onClick={handleExport}
                disabled={loading}
                className="w-full py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    导出中...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" />
                    导出数据
                  </>
                )}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  选择导入格式
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => {
                      setImportFormat('json');
                      setSelectedFile(null);
                      setError(null);
                    }}
                    className={`flex items-center gap-3 p-3 rounded-lg border-2 transition-all ${
                      importFormat === 'json'
                        ? 'border-indigo-500 bg-indigo-50'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <FileJson className={`w-6 h-6 ${importFormat === 'json' ? 'text-indigo-600' : 'text-slate-400'}`} />
                    <div className="text-left">
                      <div className={`font-medium ${importFormat === 'json' ? 'text-indigo-700' : 'text-slate-700'}`}>
                        JSON
                      </div>
                      <div className="text-xs text-slate-500">完整数据恢复</div>
                    </div>
                  </button>
                  <button
                    onClick={() => {
                      setImportFormat('csv');
                      setSelectedFile(null);
                      setError(null);
                    }}
                    className={`flex items-center gap-3 p-3 rounded-lg border-2 transition-all ${
                      importFormat === 'csv'
                        ? 'border-indigo-500 bg-indigo-50'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <FileSpreadsheet className={`w-6 h-6 ${importFormat === 'csv' ? 'text-indigo-600' : 'text-slate-400'}`} />
                    <div className="text-left">
                      <div className={`font-medium ${importFormat === 'csv' ? 'text-indigo-700' : 'text-slate-700'}`}>
                        CSV
                      </div>
                      <div className="text-xs text-slate-500">仅基金持仓</div>
                    </div>
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  合并策略
                </label>
                <select
                  value={mergeStrategy}
                  onChange={(e) => setMergeStrategy(e.target.value)}
                  className="w-full p-2.5 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                >
                  <option value="replace">替换 - 覆盖现有数据</option>
                  <option value="merge">合并 - 累加数量和加权平均成本</option>
                  <option value="skip">跳过 - 保留现有数据，跳过重复</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  选择文件
                </label>
                <div className="relative">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept={importFormat === 'json' ? '.json' : '.csv'}
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full p-3 border-2 border-dashed border-slate-300 rounded-lg hover:border-indigo-400 hover:bg-indigo-50 transition-colors text-left"
                  >
                    {selectedFile ? (
                      <div className="flex items-center gap-2">
                        {importFormat === 'json' ? (
                          <FileJson className="w-5 h-5 text-indigo-600" />
                        ) : (
                          <FileSpreadsheet className="w-5 h-5 text-green-600" />
                        )}
                        <span className="text-slate-700">{selectedFile.name}</span>
                        <span className="text-xs text-slate-400">
                          ({(selectedFile.size / 1024).toFixed(1)} KB)
                        </span>
                      </div>
                    ) : (
                      <div className="text-center py-4">
                        <Upload className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                        <span className="text-slate-500">点击选择 {importFormat.toUpperCase()} 文件</span>
                      </div>
                    )}
                  </button>
                </div>
              </div>

              <div className="p-3 bg-amber-50 rounded-lg">
                <p className="text-sm text-amber-700">
                  <strong>注意:</strong> 导入操作会修改您的持仓数据，建议在导入前先导出备份。
                </p>
              </div>

              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 text-red-600 rounded-lg text-sm">
                  <AlertCircle className="w-4 h-4" />
                  {error}
                </div>
              )}

              {result?.success && (
                <div className="flex items-center gap-2 p-3 bg-green-50 text-green-600 rounded-lg text-sm">
                  <CheckCircle className="w-4 h-4" />
                  {result.message}
                </div>
              )}

              {result?.stats && renderStats(result.stats)}

              <button
                onClick={handleImport}
                disabled={loading || !selectedFile}
                className="w-full py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    导入中...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    导入数据
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DataTransfer;
