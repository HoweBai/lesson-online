/** Progress indicator shown during tutorial outline generation. */

import React from 'react';
import { useTranslation } from 'react-i18next';

interface GenerationProgressProps {
  status: 'idle' | 'generating' | 'completed' | 'failed';
  progress?: number;
  message?: string;
  tutorialId?: string;
  onNavigate?: () => void;
  onRetry?: () => void;
}

export const GenerationProgress: React.FC<GenerationProgressProps> = ({
  status,
  progress = 0,
  message,
  tutorialId,
  onNavigate,
  onRetry,
}) => {
  const { t } = useTranslation('wizard');
  if (status === 'idle') return null;

  return (
    <div className="flex flex-col items-center justify-center py-12 space-y-6">
      {status === 'generating' && (
        <>
          <div className="relative">
            <div className="w-20 h-20 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-blue-600 font-bold text-sm">{progress}%</span>
            </div>
          </div>
          <div className="text-center space-y-1">
            <p className="text-lg font-semibold text-gray-800">{t('processing_outline')}</p>
            {message && <p className="text-sm text-gray-500">{message}</p>}
          </div>
          <div className="w-64 bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </>
      )}

      {status === 'completed' && (
        <div className="text-center space-y-4">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
            <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <div>
            <p className="text-lg font-semibold text-gray-800">{t('tutorial_generated')}</p>
            <p className="text-sm text-gray-500 mt-1">{t('tutorial_id')}: <span className="font-mono text-gray-700">{tutorialId}</span></p>
          </div>
          {onNavigate && (
            <button
              onClick={onNavigate}
              className="px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 transition"
            >
              {t('view_tutorial')}
            </button>
          )}
        </div>
      )}

      {status === 'failed' && (
        <div className="text-center space-y-4">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto">
            <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <div>
            <p className="text-lg font-semibold text-gray-800">{t('generation_failed')}</p>
            {message && <p className="text-sm text-red-600 mt-1">{message}</p>}
          </div>
          {onRetry && (
            <button
              onClick={onRetry}
              className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
            >
              {t('try_again')}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default GenerationProgress;
