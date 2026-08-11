/**
 * Course Generation Wizard - Multi-step form for creating personalized tutorials.
 */

import React, { useState } from 'react';
import { useToast } from '../hooks/useToast';
import ProfileFormStep from './WizardSteps/ProfileFormStep';
import ClaudeConfigStep from './WizardSteps/ClaudeConfigStep';
import OutlineEditorStep from './WizardSteps/OutlineEditorStep';
import ConfirmGenerationStep from './WizardSteps/ConfirmGenerationStep';

interface WizardStepProps {
  formData: Record<string, any>;
  updateFormData: (key: string, value: any) => void;
}

interface WizardStep {
  id: string;
  title: string;
  component: React.FC<WizardStepProps>;
  validate: (formData: any) => boolean | string;
}

export const CourseWizard = ({ onClose }: { onClose?: () => void }) => {
  const toast = useToast();
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [error, setError] = useState('');
  const [wizardSteps, setWizardSteps] = useState<WizardStep[]>([
    {
      id: 'profile',
      title: 'Step 1: Understand Your Learning Situation',
      component: ProfileFormStep,
      validate: (data) => !!data.professional_level && !!data.learning_goal
    },
    {
      id: 'claude-config',
      title: 'Step 2: Configure Claude API',
      component: ClaudeConfigStep,
      validate: (data) => !!data.base_url && !!data.api_key && !!data.model_name
    },
    {
      id: 'outline-draft',
      title: 'Step 3: Review and Modify Draft Outline',
      component: OutlineEditorStep,
      validate: (data) => !!data.outline_content && !!data.selected_sections
    },
    {
      id: 'confirm',
      title: 'Step 4: Confirm Generation',
      component: ConfirmGenerationStep,
      validate: (data) => true
    }
  ]);

  const currentStep = wizardSteps[currentStepIndex];

  const handleNext = () => {
    const validation = currentStep.validate(formData);
    if (typeof validation === 'string') {
      setError(validation);
      return;
    }
    if (currentStepIndex < wizardSteps.length - 1) {
      setCurrentStepIndex(currentStepIndex + 1);
    } else {
      submitGeneration(formData);
    }
  };

  const handleBack = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(currentStepIndex - 1);
    }
  };

  const updateFormData = (key: string, value: any) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const submitGeneration = async (data: any) => {
    try {
      // Call backend API to start tutorial generation
      const response = await fetch('/api/v1/tutorials/generate-outline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });

      if (!response.ok) throw new Error('Failed to generate outline');

      const result = await response.json();
      toast.success(`Tutorial generated successfully! ID: ${result.tutorialId}`);
      onClose?.();
    } catch (err: any) {
      setError(err.message || 'Failed to generate tutorial');
      toast.error(err.message || 'Failed to generate tutorial');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b bg-gradient-to-r from-blue-600 to-indigo-600 text-white">
          <div className="flex justify-between items-center">
            <h2 className="text-2xl font-bold">{currentStep.title}</h2>
            <button onClick={onClose} className="text-white hover:text-opacity-80">✕</button>
          </div>
          {/* Progress bar */}
          <div className="mt-4 bg-white bg-opacity-20 rounded-full h-2">
            <div
              className="bg-white h-2 rounded-full transition-all duration-300"
              style={{ width: `${((currentStepIndex + 1) / wizardSteps.length) * 100}%` }}
            ></div>
          </div>
        </div>

        {/* Step Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {currentStep.component({
            formData,
            updateFormData
          })}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700">
              {error}
            </div>
          )}
        </div>

        {/* Footer Buttons */}
        <div className="p-6 border-t bg-gray-50 flex justify-between items-center">
          {currentStepIndex > 0 && (
            <button
              onClick={handleBack}
              className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
            >
              ← Back
            </button>
          )}

          {currentStepIndex < wizardSteps.length - 1 ? (
            <button
              onClick={handleNext}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              Next →
            </button>
          ) : (
            <button
              onClick={() => submitGeneration(formData)}
              className="px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 transition"
            >
              🚀 Start Generating Tutorial
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// Default export for use in App.tsx
export default CourseWizard;
