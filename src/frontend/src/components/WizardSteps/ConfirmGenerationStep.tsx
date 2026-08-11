/** Step component: Final confirmation before generation */

import React from 'react';

interface ConfirmGenerationStepProps {
  formData: any;
  updateFormData: (key: string, value: any) => void;
}

export const ConfirmGenerationStep = ({ formData, updateFormData }: ConfirmGenerationStepProps) => {
  return (
    <div className="space-y-4">
      <div className="bg-green-50 rounded-lg p-6 border border-green-200">
        <h3 className="text-lg font-semibold text-green-800 mb-2">Review Your Configuration</h3>
        <div className="space-y-2 text-sm text-green-900">
          <p><strong>Learning Profile:</strong></p>
          <ul className="list-disc list-inside ml-4 space-y-1">
            <li>Programming Level: {formData.professional_level || 'Not set'}</li>
            <li>Learning Goal: {formData.learning_goal || 'Not set'}</li>
            <li>Study Time: {formData.available_hours_per_day ? formData.available_hours_per_day + ' hours/day' : 'Not set'}</li>
          </ul>
          <p className="mt-2"><strong>Claude API Configuration:</strong></p>
          <ul className="list-disc list-inside ml-4 space-y-1">
            <li>Model: {formData.model_name || 'Not set'}</li>
            <li>Base URL: {formData.base_url ? 'Set' : 'Using default'}</li>
          </ul>
        </div>
      </div>

      <div className="p-4 bg-yellow-50 rounded-md border border-yellow-200">
        <h4 className="font-semibold text-yellow-800 mb-2">Important Notes</h4>
        <ul className="text-sm text-yellow-900 space-y-1 list-disc list-inside">
          <li>Your API key will be securely encrypted before storage</li>
          <li>Chapters are generated one-at-a-time - click "Generate Next Chapter" to continue</li>
          <li>You can modify the outline using Claude Chat at any time</li>
          <li>All content belongs to you until you choose to publish it publicly</li>
        </ul>
      </div>

      <div className="pt-4 border-t border-gray-200">
        <label className="flex items-center">
          <input
            type="checkbox"
            className="form-checkbox text-blue-600 h-4 w-4"
            id="confirm_terms"
          />
          <span className="ml-2 text-sm text-gray-700">I confirm that I want to proceed with tutorial generation</span>
        </label>
      </div>
    </div>
  );
};

export default ConfirmGenerationStep;
