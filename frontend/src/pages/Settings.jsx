import React, { useState, useEffect, useCallback, lazy, Suspense } from 'react';
import { Save, AlertCircle, CheckCircle2, Database, Download, Upload } from 'lucide-react';
import { getSettings, updateSettings } from '../services/api';

const DataTransfer = lazy(() => import('../components/DataTransfer'));

export default function Settings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [showDataTransfer, setShowDataTransfer] = useState(false);

  const [settings, setSettings] = useState({
    OPENAI_API_KEY: '',
    OPENAI_API_BASE: '',
    AI_MODEL_NAME: '',
    SMTP_HOST: '',
    SMTP_PORT: '',
    SMTP_USER: '',
    SMTP_PASSWORD: '',
    EMAIL_FROM: '',
    NOTIFICATION_EMAIL: '',
    INTRADAY_COLLECT_INTERVAL: '5'
  });

  const [errors, setErrors] = useState({});

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setMessage({ type: '', text: '' });
    
    try {
      const data = await getSettings();
      setSettings(data.settings || {});
    } catch (error) {
      console.error('Load settings error:', error);
      setMessage({ type: 'error', text: error.message || '加载设置失败，请检查网络连接' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const validateForm = () => {
    const newErrors = {};

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (settings.SMTP_USER && !emailRegex.test(settings.SMTP_USER)) {
      newErrors.SMTP_USER = '邮箱格式不正确';
    }
    if (settings.EMAIL_FROM && !emailRegex.test(settings.EMAIL_FROM)) {
      newErrors.EMAIL_FROM = '邮箱格式不正确';
    }
    if (settings.NOTIFICATION_EMAIL && !emailRegex.test(settings.NOTIFICATION_EMAIL)) {
      newErrors.NOTIFICATION_EMAIL = '邮箱格式不正确';
    }

    // Port validation
    const port = parseInt(settings.SMTP_PORT);
    if (settings.SMTP_PORT && (isNaN(port) || port < 1 || port > 65535)) {
      newErrors.SMTP_PORT = '端口必须在 1-65535 之间';
    }

    // Interval validation
    const interval = parseInt(settings.INTRADAY_COLLECT_INTERVAL);
    if (settings.INTRADAY_COLLECT_INTERVAL && (isNaN(interval) || interval < 1 || interval > 60)) {
      newErrors.INTRADAY_COLLECT_INTERVAL = '采集间隔必须在 1-60 分钟之间';
    }

    // URL validation
    if (settings.OPENAI_API_BASE) {
      try {
        new URL(settings.OPENAI_API_BASE);
      } catch {
        newErrors.OPENAI_API_BASE = 'URL 格式不正确';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validateForm()) {
      setMessage({ type: 'error', text: '请修正表单错误' });
      return;
    }

    setSaving(true);
    setMessage({ type: '', text: '' });

    try {
      // 过滤掉掩码字段
      const filteredSettings = Object.fromEntries(
        Object.entries(settings).filter(([key, value]) => value !== '***')
      );

      await updateSettings(filteredSettings);
      setMessage({ type: 'success', text: '设置已保存' });
    } catch (error) {
      console.error('Save settings error:', error);
      // 如果后端返回字段级错误
      if (error.response?.data?.detail?.errors) {
        setErrors(error.response.data.detail.errors);
        setMessage({ type: 'error', text: '请修正表单错误' });
      } else {
        setMessage({ type: 'error', text: error.message || '保存失败' });
      }
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (field, value) => {
    setSettings(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <div className="flex items-center gap-2 text-gray-500">
          <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
          加载设置中...
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Save className="w-4 h-4" />
          {saving ? '保存中...' : '保存更改'}
        </button>
      </div>

      {message.text && (
        <div className={`flex items-center gap-2 p-4 rounded-lg ${
          message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
        }`}>
          {message.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5" />
          ) : (
            <AlertCircle className="w-5 h-5" />
          )}
          <span>{message.text}</span>
        </div>
      )}

      {/* AI Configuration */}
      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <h2 className="text-xl font-semibold text-gray-900">AI 配置</h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            OpenAI API Key
          </label>
          <input
            type="password"
            value={settings.OPENAI_API_KEY}
            onChange={(e) => handleChange('OPENAI_API_KEY', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="sk-..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            OpenAI API Base URL
          </label>
          <input
            type="text"
            value={settings.OPENAI_API_BASE}
            onChange={(e) => handleChange('OPENAI_API_BASE', e.target.value)}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.OPENAI_API_BASE ? 'border-red-500' : 'border-gray-300'
            }`}
            placeholder="https://api.openai.com/v1"
          />
          {errors.OPENAI_API_BASE && (
            <p className="mt-1 text-sm text-red-600">{errors.OPENAI_API_BASE}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            AI Model Name
          </label>
          <input
            type="text"
            value={settings.AI_MODEL_NAME}
            onChange={(e) => handleChange('AI_MODEL_NAME', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="gpt-4"
          />
        </div>
      </div>

      {/* Email Configuration */}
      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <h2 className="text-xl font-semibold text-gray-900">邮件配置</h2>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              SMTP Host
            </label>
            <input
              type="text"
              value={settings.SMTP_HOST}
              onChange={(e) => handleChange('SMTP_HOST', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="smtp.gmail.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              SMTP Port
            </label>
            <input
              type="number"
              value={settings.SMTP_PORT}
              onChange={(e) => handleChange('SMTP_PORT', e.target.value)}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.SMTP_PORT ? 'border-red-500' : 'border-gray-300'
              }`}
              placeholder="587"
            />
            {errors.SMTP_PORT && (
              <p className="mt-1 text-sm text-red-600">{errors.SMTP_PORT}</p>
            )}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            SMTP User (Email)
          </label>
          <input
            type="email"
            value={settings.SMTP_USER}
            onChange={(e) => handleChange('SMTP_USER', e.target.value)}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.SMTP_USER ? 'border-red-500' : 'border-gray-300'
            }`}
            placeholder="user@example.com"
          />
          {errors.SMTP_USER && (
            <p className="mt-1 text-sm text-red-600">{errors.SMTP_USER}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            SMTP Password
          </label>
          <input
            type="password"
            value={settings.SMTP_PASSWORD}
            onChange={(e) => handleChange('SMTP_PASSWORD', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="••••••••"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            From Email Address
          </label>
          <input
            type="email"
            value={settings.EMAIL_FROM}
            onChange={(e) => handleChange('EMAIL_FROM', e.target.value)}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.EMAIL_FROM ? 'border-red-500' : 'border-gray-300'
            }`}
            placeholder="noreply@example.com"
          />
          {errors.EMAIL_FROM && (
            <p className="mt-1 text-sm text-red-600">{errors.EMAIL_FROM}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            通知接收邮箱
          </label>
          <input
            type="email"
            value={settings.NOTIFICATION_EMAIL}
            onChange={(e) => handleChange('NOTIFICATION_EMAIL', e.target.value)}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.NOTIFICATION_EMAIL ? 'border-red-500' : 'border-gray-300'
            }`}
            placeholder="your@email.com"
          />
          {errors.NOTIFICATION_EMAIL && (
            <p className="mt-1 text-sm text-red-600">{errors.NOTIFICATION_EMAIL}</p>
          )}
          <p className="mt-2 text-sm text-gray-500">
            AI审视报告等系统通知将发送到此邮箱
          </p>
        </div>
      </div>

      {/* Data Collection Configuration */}
      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <h2 className="text-xl font-semibold text-gray-900">数据采集配置</h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            分时数据采集间隔（分钟）
          </label>
          <input
            type="number"
            value={settings.INTRADAY_COLLECT_INTERVAL}
            onChange={(e) => handleChange('INTRADAY_COLLECT_INTERVAL', e.target.value)}
            className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.INTRADAY_COLLECT_INTERVAL ? 'border-red-500' : 'border-gray-300'
            }`}
            placeholder="5"
            min="1"
            max="60"
          />
          {errors.INTRADAY_COLLECT_INTERVAL && (
            <p className="mt-1 text-sm text-red-600">{errors.INTRADAY_COLLECT_INTERVAL}</p>
          )}
          <p className="mt-2 text-sm text-gray-500">
             请注意：分时数据采集仅在系统开启时运行（交易日 09:35-15:05）
          </p>
        </div>
      </div>

      {/* Data Backup & Restore */}
      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <h2 className="text-xl font-semibold text-gray-900">数据备份与恢复</h2>
        <p className="text-sm text-gray-500">
          导出您的持仓数据进行备份，或从备份文件恢复数据。
        </p>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => setShowDataTransfer(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            <Database className="w-4 h-4" />
            打开数据管理
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div className="p-4 bg-slate-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Download className="w-5 h-5 text-green-600" />
              <h3 className="font-medium text-slate-800">导出数据</h3>
            </div>
            <p className="text-sm text-slate-500">
              支持 JSON 和 CSV 两种格式。JSON 包含完整的持仓、交易记录和数字货币数据；CSV 仅包含基金持仓。
            </p>
          </div>

          <div className="p-4 bg-slate-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Upload className="w-5 h-5 text-blue-600" />
              <h3 className="font-medium text-slate-800">导入数据</h3>
            </div>
            <p className="text-sm text-slate-500">
              支持从 JSON 或 CSV 文件恢复数据。提供替换、合并、跳过三种合并策略。
            </p>
          </div>
        </div>
      </div>

      {/* Data Transfer Modal */}
      {showDataTransfer && (
        <Suspense fallback={<div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"><div className="bg-white p-6 rounded-lg">加载中...</div></div>}>
          <DataTransfer
            onClose={() => setShowDataTransfer(false)}
            onSuccess={() => {
              setMessage({ type: 'success', text: '数据导入成功，页面将刷新' });
              setTimeout(() => window.location.reload(), 1500);
            }}
          />
        </Suspense>
      )}
    </div>
  );
}

