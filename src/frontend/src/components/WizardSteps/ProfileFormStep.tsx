/** Step component: Personal information collection */

import React from 'react';
import { useTranslation } from 'react-i18next';

interface ProfileFormStepProps {
  formData: any;
  updateFormData: (key: string, value: any) => void;
}

export const ProfileFormStep = ({ formData, updateFormData }: ProfileFormStepProps) => {
  const { t } = useTranslation('wizard');
  return (
    <div className="space-y-4">
      <p className="text-gray-600 mb-4">{t('answer_questions')}</p>

      <div>
        <label className="block text-sm font-medium text-gray-700">{t('programming_level_label')}</label>
        <select
          value={formData.professional_level || ''}
          onChange={(e) => updateFormData('professional_level', parseInt(e.target.value))}
          className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500 sm:text-sm rounded-md"
        >
          <option value="">{t('select_level')}</option>
          <option value="1">{t('beginner_level')}</option>
          <option value="2">{t('basic_knowledge')}</option>
          <option value="3">{t('intermediate_level')}</option>
          <option value="4">{t('advanced_level')}</option>
          <option value="5">{t('expert_level')}</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">{t('math_background_label')}</label>
        <textarea
          value={formData.math_background || ''}
          onChange={(e) => updateFormData('math_background', e.target.value)}
          rows={3}
          placeholder={t('math_background_placeholder')}
          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-3"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">{t('learning_goal')}</label>
        <select
          value={formData.learning_goal || ''}
          onChange={(e) => updateFormData('learning_goal', e.target.value)}
          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-3"
        >
          <option value="">{t('select_goal')}</option>
          <option value="job_search">{t('prepare_job_interviews')}</option>
          <option value="self_study">{t('self_improvement')}</option>
          <option value="academic">{t('academic_research')}</option>
          <option value="teaching">{t('prepare_teach_others')}</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">{t('available_hours_label')}</label>
        <input
          type="number"
          step="0.5"
          value={formData.available_hours_per_day || ''}
          onChange={(e) => updateFormData('available_hours_per_day', parseFloat(e.target.value))}
          min="0"
          max="24"
          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-3"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">{t('preferred_style_label')}</label>
        <div className="flex flex-wrap gap-2 mt-2">
          {['visual', 'text', 'code', 'exercise'].map(style => (
            <button
              key={style}
              type="button"
              onClick={() => updateFormData('preferred_style', style)}
              className={`px-3 py-1 rounded-full text-sm ${
                formData.preferred_style === style
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {t(`style_${style}`)}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ProfileFormStep;
