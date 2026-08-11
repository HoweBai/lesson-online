/**
 * Claude API Configuration Page
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

interface ClaudeConfig {
  id: string;
  base_url: string;
  model_name: string;
  is_default: boolean;
  created_at: string;
}

const ClaudeConfigPage = () => {
  const navigate = useNavigate();
  const [configs, setConfigs] = useState<ClaudeConfig[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({
    base_url: 'https://api.anthropic.com/v1',
    api_key: '',
    model_name: 'claude-3-opus-20240925',
    system_prompt: '',
    is_default: true
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    setLoading(true);
    const result = await api.getClaudeConfigs();
    if (result.success) {
      setConfigs(result.data || []);
    }
    setLoading(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!formData.api_key) {
      setError('API key is required');
      return;
    }

    const result = await api.saveClaudeConfig(formData);
    if (result.success) {
      setSuccess('Configuration saved successfully!');
      setShowForm(false);
      setFormData({
        base_url: 'https://api.anthropic.com/v1',
        api_key: '',
        model_name: 'claude-3-opus-20240925',
        system_prompt: '',
        is_default: true
      });
      loadConfigs();
    } else {
      setError(result.error || 'Failed to save configuration');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this configuration?')) return;

    const result = await api.deleteClaudeConfig(id);
    if (result.success) {
      loadConfigs();
    }
  };

  const handleSetDefault = async (id: string) => {
    const config = configs.find(c => c.id === id);
    if (config) {
      const result = await api.saveClaudeConfig({
        ...config,
        is_default: true,
        api_key: config.base_url ? '' : undefined // Don't require key for update
      });
      if (result.success) {
        loadConfigs();
      }
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Claude API Configuration</h1>
        <button
          onClick={() => setShowForm(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + Add Configuration
        </button>
      </div>

      {success && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
          {success}
        </div>
      )}

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Add Form */}
      {showForm && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Add New Configuration</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">API Base URL</label>
              <input
                type="text"
                value={formData.base_url}
                onChange={(e) => setFormData({...formData, base_url: e.target.value})}
                placeholder="https://api.anthropic.com/v1"
                className="mt-1 block w-full border border-gray-300 rounded-md p-2"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">API Key *</label>
              <input
                type="password"
                value={formData.api_key}
                onChange={(e) => setFormData({...formData, api_key: e.target.value})}
                placeholder="sk-ant-..."
                className="mt-1 block w-full border border-gray-300 rounded-md p-2"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">Model Name</label>
              <select
                value={formData.model_name}
                onChange={(e) => setFormData({...formData, model_name: e.target.value})}
                className="mt-1 block w-full border border-gray-300 rounded-md p-2"
              >
                <option value="claude-3-opus-20240925">Claude 3 Opus</option>
                <option value="claude-3-sonnet-20240925">Claude 3 Sonnet</option>
                <option value="claude-3-haiku-20240925">Claude 3 Haiku</option>
                <option value="claude-2.1">Claude 2.1</option>
                <option value="custom">Custom Model</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">System Prompt (optional)</label>
              <textarea
                value={formData.system_prompt}
                onChange={(e) => setFormData({...formData, system_prompt: e.target.value})}
                placeholder="Enter system prompt..."
                className="mt-1 block w-full border border-gray-300 rounded-md p-2"
                rows={3}
              />
            </div>

            <div className="flex items-center">
              <input
                type="checkbox"
                id="is_default"
                checked={formData.is_default}
                onChange={(e) => setFormData({...formData, is_default: e.target.checked})}
                className="form-checkbox text-blue-600 h-4 w-4"
              />
              <label htmlFor="is_default" className="ml-2 text-sm text-gray-700">Set as default configuration</label>
            </div>

            <div className="flex gap-4 pt-4">
              <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
                Save Configuration
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Configs List */}
      <div className="space-y-3">
        {configs.length === 0 ? (
          <div className="text-center py-8 bg-white rounded-lg shadow">
            <p className="text-gray-500">No configurations found. Add your first Claude API configuration above.</p>
          </div>
        ) : (
          configs.map(config => (
            <div key={config.id} className="bg-white rounded-lg shadow p-4 flex justify-between items-center">
              <div>
                {config.is_default && (
                  <span className="inline-block px-2 py-1 rounded-full text-xs bg-green-100 text-green-800 mr-2">
                    Default
                  </span>
                )}
                <span className="font-mono text-sm">{config.model_name}</span>
                <span className="text-gray-500 text-sm ml-2">{config.base_url}</span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleSetDefault(config.id)}
                  className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
                >
                  Set Default
                </button>
                <button
                  onClick={() => handleDelete(config.id)}
                  className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded"
                >
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Info */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 mb-2">How to get your API key</h3>
        <ol className="list-decimal list-inside text-sm text-blue-800 space-y-1">
          <li>Go to <a href="https://console.anthropic.com" target="_blank" rel="noopener noreferrer" className="underline">console.anthropic.com</a></li>
          <li>Create an account or sign in</li>
          <li>Go to API Keys section</li>
          <li>Create a new API key and copy it</li>
          <li>Paste it in the API Key field above</li>
        </ol>
      </div>
    </div>
  );
};

export default ClaudeConfigPage;
