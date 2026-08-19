import React, { Component, ReactNode, ErrorInfo } from 'react';
import { withTranslation, WithTranslation } from 'react-i18next';

interface GlobalErrorHandlerProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface GlobalErrorHandlerState {
  hasError: boolean;
  error?: Error;
}

class GlobalErrorHandlerInner extends Component<GlobalErrorHandlerProps & WithTranslation, GlobalErrorHandlerState> {
  constructor(props: GlobalErrorHandlerProps & WithTranslation) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): GlobalErrorHandlerState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Global error:', error, errorInfo);
  }

  render() {
    const { t } = this.props;
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
          <div className="text-center px-6">
            <div className="text-8xl mb-6">⚠️</div>
            <h1 className="text-3xl font-bold text-gray-900 mb-3">{t('something_went_wrong', { defaultValue: 'Something went wrong' })}</h1>
            <p className="text-gray-600 mb-8 max-w-md">
              {t('unexpected_error', { defaultValue: 'An unexpected error occurred. Please try reloading the page.' })}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="inline-flex items-center px-6 py-3 bg-primary-600 text-white font-semibold rounded-xl shadow-soft hover:shadow-hover hover:bg-primary-700 transition-all duration-200"
            >
              {t('reload_page', { defaultValue: 'Reload Page' })}
            </button>
            {this.state.error && (
              <details className="mt-6 text-left max-w-lg mx-auto">
                <summary className="text-sm text-gray-500 cursor-pointer hover:text-gray-700">
                  {t('error_details', { defaultValue: 'Error details' })}
                </summary>
                <pre className="mt-2 p-4 bg-white rounded-xl shadow-soft text-xs text-red-600 overflow-auto max-h-48">
                  {this.state.error.stack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export const GlobalErrorHandler = withTranslation('common')(GlobalErrorHandlerInner);
