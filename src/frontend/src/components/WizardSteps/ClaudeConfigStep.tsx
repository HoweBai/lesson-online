/** Step component: Claude API configuration */

import React from 'react';
import { useTranslation } from 'react-i18next';

interface ClaudeConfigStepProps {
  formData: any;
  updateFormData: (key: string, value: any) => void;
}

export const ClaudeConfigStep = ({ formData, updateFormData }: ClaudeConfigStepProps) => {
  const { t } = useTranslation('wizard');
  return (
    <div className="space-y-4">
      <p className="text-gray-600 mb-4">{t('intro_claude_config')}</p>

      <div>
        <label className="block text-sm font-medium text-gray-700">{t('base_url')}</label>
        <input
          type="text"
          value={formData.base_url || ''}
          onChange={(e) => updateFormData('base_url', e.target.value)}
          placeholder="https://api.anthropic.com/v1"
          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-3"
        />
        <p className="text-xs text-gray-500 mt-1">{t('base_url_hint')}</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">{t('api_key')}</label>
        <input
          type="password"
          value={formData.api_key || ''}
          onChange={(e) => updateFormData('api_key', e.target.value)}
          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-3"
        />
        <p className="text-xs text-gray-500 mt-1">{t('api_key_hint')}</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">{t('model_name')}</label>
        <select
          value={formData.model_name || ''}
          onChange={(e) => updateFormData('model_name', e.target.value)}
          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-3"
        >
          <option value="">{t('select_model')}</option>
          <option value="claude-3-opus-20240925">{t('claude_opus')}</option>
          <option value="claude-3-sonnet-20240925">{t('claude_sonnet')}</option>
          <option value="claude-3-haiku-20240925">{t('claude_haiku')}</option>
          <option value="custom">{t('custom_model')}</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">{t('system_prompt_label')}</label>
        <textarea
          value={formData.system_prompt || ''}
          onChange={(e) => updateFormData('system_prompt', e.target.value)}
          rows={4}
          placeholder={t('system_prompt_placeholder')}
          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-3"
        />
      </div>
    </div>
  );
};

export default ClaudeConfigStep;
