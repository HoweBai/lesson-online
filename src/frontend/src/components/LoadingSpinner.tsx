import React from 'react';

type SpinnerSize = 'sm' | 'md' | 'lg';

interface LoadingSpinnerProps {
  size?: SpinnerSize;
  text?: string;
  fullScreen?: boolean;
}

const sizeClasses: Record<SpinnerSize, string> = {
  sm: 'w-8 h-8 border-2',
  md: 'w-12 h-12 border-4',
  lg: 'w-20 h-20 border-4',
};

const textSizes: Record<SpinnerSize, string> = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg',
};

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  text,
  fullScreen = false,
}) => {
  const containerClass = fullScreen
    ? 'min-h-screen flex items-center justify-center'
    : 'flex items-center justify-center py-8';

  return (
    <div className={containerClass}>
      <div className="text-center">
        <div className={`relative mx-auto mb-4 ${sizeClasses[size]}`}>
          <div className="absolute inset-0 border-current border-primary-200 rounded-full opacity-30"></div>
          <div className="absolute inset-0 border-current border-primary-600 rounded-full border-t-transparent animate-spin"></div>
        </div>
        {text && (
          <p className={`${textSizes[size]} text-gray-600 font-medium`}>{text}</p>
        )}
      </div>
    </div>
  );
};

export default LoadingSpinner;
