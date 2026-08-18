/** Step component: Outline review and editing */

import React from 'react';
import { useTranslation } from 'react-i18next';

interface OutlineEditorStepProps {
  formData: any;
  updateFormData: (key: string, value: any) => void;
}

export const OutlineEditorStep = ({ formData, updateFormData }: OutlineEditorStepProps) => {
  const { t } = useTranslation('wizard');
  return (
    <div className="space-y-4">
      <p className="text-gray-600 mb-4">{t('review_outline')}</p>

      <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
        <h4 className="font-semibold mb-2">{t('outline_generated')}:</h4>
        <div className="text-sm text-gray-700 space-y-2">
          {/* Display the outline content - would normally come from AI response */}
          <p>{formData.outline_content || 'The AI will generate your course outline here after clicking "Next". Once generated, you can edit it using the Claude Chat Sidebar.'}</p>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">{t('select_sections')}</label>
        <div className="flex flex-wrap gap-2 mt-2">
          {[1, 2, 3, 4, 5].map(num => (
            <button
              key={num}
              type="button"
              onClick={() => {
                const selected = formData.selected_sections || [];
                const newSelected = selected.includes(num)
                  ? selected.filter((n: number) => n !== num)
                  : [...selected, num];
                updateFormData('selected_sections', newSelected);
              }}
              className={`px-3 py-1 rounded-full text-sm ${
                formData.selected_sections?.includes(num)
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {t('chapter_n', { n: num })}
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-1">{t('continue_generating')}</p>
      </div>

      <div className="mt-4 p-3 bg-blue-50 rounded-md border border-blue-200">
        <p className="text-sm text-blue-800">
          {t('tip_chat')}
        </p>
      </div>
    </div>
  );
};

export default OutlineEditorStep;
