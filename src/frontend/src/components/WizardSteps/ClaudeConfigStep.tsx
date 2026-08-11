/** Step component: Claude API configuration */

import React from 'react';

interface ClaudeConfigStepProps {
  formData: any;
  updateFormData: (key: string, value: any) => void;
}

export const ClaudeConfigStep = ({ formData, updateFormData }: ClaudeConfigStepProps) => {
  return (
    <div className="space-y-4">
      <p className="text-gray-600 mb-4">Enter your Claude API configuration. This allows the platform to generate personalized tutorial content using your account.</p>

      <div>
        <label className="block text-sm font-medium text-gray-700">API Base URL</label>
        <input
          type="text"
          value={formData.base_url || ''}
          onChange={(e) => updateFormData('base_url', e.target.value)}
          placeholder="https://api.anthropic.com/v1"
          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-3"
        />
        <p className="text-xs text-gray-500 mt-1">Leave blank for default Anthropic API</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">API Key</label>
        <input
          type="password"
          value={formData.api_key || ''}
          onChange={(e) => updateFormData('api_key', e.target.value)}
          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-3"
        />
        <p className="text-xs text-gray-500 mt-1">Your API key will be encrypted before storage</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Model Name</label>
        <select
          value={formData.model_name || ''}
          onChange={(e) => updateFormData('model_name', e.target.value)}
          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-3"
        >
          <option value="">Select model</option>
          <option value="claude-3-opus-20240925">Claude 3 Opus (fast & intelligent)</option>
          <option value="claude-3-sonnet-20240925">Claude 3 Sonnet (balanced)</option>
          <option value="claude-3-haiku-20240925">Claude 3 Haiku (fast & lightweight)</option>
          <option value="custom">Custom third-party model</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">System Prompt (optional)</label>
        <textarea
          value={formData.system_prompt || ''}
          onChange={(e) => updateFormData('system_prompt', e.target.value)}
          rows={4}
          placeholder="Custom instructions for the AI when generating your tutorial..."
          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-3"
        />
      </div>
    </div>
  );
};

export default ClaudeConfigStep;
