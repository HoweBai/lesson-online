/** Step component: Final confirmation before generation */

import React from 'react';
import { useTranslation } from 'react-i18next';

interface ConfirmGenerationStepProps {
  formData: any;
  updateFormData: (key: string, value: any) => void;
}

export const ConfirmGenerationStep = ({ formData, updateFormData }: ConfirmGenerationStepProps) => {
  const { t } = useTranslation('wizard');
  return (
    <div className="space-y-4">
      <div className="bg-green-50 rounded-lg p-6 border border-green-200">
        <h3 className="text-lg font-semibold text-green-800 mb-2">{t('review_config')}</h3>
        <div className="space-y-2 text-sm text-green-900">
          <p><strong>{t('learning_profile_label')}</strong></p>
          <ul className="list-disc list-inside ml-4 space-y-1">
            <li>Programming Level: {formData.professional_level || t('not_set')}</li>
            <li>Learning Goal: {formData.learning_goal || t('not_set')}</li>
            <li>Study Time: {formData.available_hours_per_day ? formData.available_hours_per_day + t('hours_per_day') : t('not_set')}</li>
          </ul>
          <p className="mt-2"><strong>Claude API Configuration:</strong></p>
          <ul className="list-disc list-inside ml-4 space-y-1">
            <li>Model: {formData.model_name || t('not_set')}</li>
            <li>Base URL: {formData.base_url ? t('set') : t('using_default')}</li>
          </ul>
        </div>
      </div>

      <div className="p-4 bg-yellow-50 rounded-md border border-yellow-200">
        <h4 className="font-semibold text-yellow-800 mb-2">{t('important_notes')}</h4>
        <ul className="text-sm text-yellow-900 space-y-1 list-disc list-inside">
          <li>{t('api_key_secure')}</li>
          <li>{t('chapters_generated_one')}</li>
          <li>{t('modify_outline_chat')}</li>
          <li>{t('content_ownership')}</li>
        </ul>
      </div>

      <div className="pt-4 border-t border-gray-200">
        <label className="flex items-center">
          <input
            type="checkbox"
            className="form-checkbox text-blue-600 h-4 w-4"
            id="confirm_terms"
          />
          <span className="ml-2 text-sm text-gray-700">{t('confirm_generation')}</span>
        </label>
      </div>
    </div>
  );
};

export default ConfirmGenerationStep;
