/** Step component: Personal information collection */

import React from 'react';

interface ProfileFormStepProps {
  formData: any;
  updateFormData: (key: string, value: any) => void;
}

export const ProfileFormStep = ({ formData, updateFormData }: ProfileFormStepProps) => {
  return (
    <div className="space-y-4">
      <p className="text-gray-600 mb-4">Please answer these questions to help us create your personalized tutorial:</p>

      <div>
        <label className="block text-sm font-medium text-gray-700">Your programming level (1-5)</label>
        <select
          value={formData.professional_level || ''}
          onChange={(e) => updateFormData('professional_level', parseInt(e.target.value))}
          className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500 sm:text-sm rounded-md"
        >
          <option value="">Select level</option>
          <option value="1">Beginner - I'm just starting out</option>
          <option value="2">Some basic knowledge</option>
          <option value="3">Intermediate - Comfortable with basics</option>
          <option value="4">Advanced - Experienced developer</option>
          <option value="5">Expert - Ready for advanced topics</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Mathematics background</label>
        <textarea
          value={formData.math_background || ''}
          onChange={(e) => updateFormData('math_background', e.target.value)}
          rows={3}
          placeholder="Describe your math knowledge (calculus, linear algebra, probability...)"
          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-3"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Learning goal</label>
        <select
          value={formData.learning_goal || ''}
          onChange={(e) => updateFormData('learning_goal', e.target.value)}
          className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm p-3"
        >
          <option value="">Select goal</option>
          <option value="job_search">Preparing for job interviews</option>
          <option value="self_study">Self-improvement / Interest</option>
          <option value="academic">Academic research / University studies</option>
          <option value="teaching">Preparing to teach others</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">Available study time per day (hours)</label>
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
        <label className="block text-sm font-medium text-gray-700">Preferred learning style</label>
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
              {style.charAt(0).toUpperCase() + style.slice(1)}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ProfileFormStep;
