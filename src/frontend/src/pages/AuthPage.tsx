/**
 * Authentication page - Beautiful login/register with gradient design
 */

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../hooks/useToast';

interface AuthPageProps {
  mode: 'login' | 'register' | 'forgot-password' | 'reset-password';
  resetToken?: string;
}

const AuthPage = ({ mode, resetToken }: AuthPageProps) => {
  const navigate = useNavigate();
  const toast = useToast();
  const [formData, setFormData] = useState({ email: '', password: '', username: '' });
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    if (error) setError('');
  };

  const handleConfirmChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setConfirmPassword(e.target.value);
    if (error) setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (mode === 'forgot-password') {
        const result = await api.forgotPassword(formData.email);
        if (!result.success) throw new Error(result.error || 'Request failed');
        toast.success('Password reset link sent to your email');
        navigate('/login');
        return;
      }

      if (mode === 'reset-password') {
        if (!resetToken) {
          throw new Error('Invalid reset token');
        }
        if (formData.password !== confirmPassword) {
          throw new Error('Passwords do not match');
        }
        const result = await api.resetPassword(resetToken, formData.password);
        if (!result.success) throw new Error(result.error || 'Password reset failed');
        toast.success('Password reset successful');
        navigate('/login');
        return;
      }

      if (mode === 'register') {
        const result = await api.register(formData.username, formData.email, formData.password);
        if (!result.success) throw new Error(result.error || 'Registration failed');
        if (result.data?.token) api.setToken(result.data.token);
        toast.success('Account created successfully!');
        window.location.href = '/';
        return;
      }

      // LOGIN
      const result = await api.login(formData.email, formData.password);

      if (!result.success) {
        throw new Error(result.error || 'Login failed');
      }

      if (result.data?.token) {
        api.setToken(result.data.token);
      } else {
        throw new Error('No token received from server');
      }

      toast.success('Login successful!');
      window.location.href = '/';
    } catch (err: any) {
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const isLoginOrRegister = mode === 'login' || mode === 'register';

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary-600 via-primary-700 to-accent-700">
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-0 left-0 w-96 h-96 bg-white rounded-full mix-blend-multiply filter blur-3xl animate-pulse-slow"></div>
          <div className="absolute top-0 right-0 w-96 h-96 bg-accent-300 rounded-full mix-blend-multiply filter blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }}></div>
          <div className="absolute bottom-0 left-1/2 w-96 h-96 bg-primary-300 rounded-full mix-blend-multiply filter blur-3xl animate-pulse-slow" style={{ animationDelay: '2s' }}></div>
        </div>
      </div>

      {/* Main card */}
      <div className="relative w-full max-w-md animate-slide-up">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-white rounded-2xl shadow-lg mb-4">
            <span className="text-3xl font-bold gradient-text">OL</span>
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">
            {mode === 'login' ? 'Welcome Back' : mode === 'register' ? 'Join Us' : mode === 'forgot-password' ? 'Reset Password' : 'Set New Password'}
          </h1>
          <p className="text-primary-100">
            {mode === 'login' ? 'Sign in to continue your learning journey' : mode === 'register' ? 'Create your account to start learning' : mode === 'forgot-password' ? 'Enter your email to receive a reset link' : 'Enter your new password below'}
          </p>
        </div>

        {/* Form card */}
        <div className="bg-white rounded-3xl shadow-2xl p-8">
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-2">
              <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {isLoginOrRegister && mode === 'register' && (
              <div className="space-y-2">
                <label className="block text-sm font-semibold text-gray-700">
                  Username
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                  <input
                    type="text"
                    name="username"
                    required
                    value={formData.username}
                    onChange={handleChange}
                    className="input pl-11"
                    placeholder="Enter your username"
                  />
                </div>
              </div>
            )}

            {(isLoginOrRegister || mode === 'forgot-password') && (
              <div className="space-y-2">
                <label className="block text-sm font-semibold text-gray-700">
                  Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <input
                    type="email"
                    name="email"
                    required
                    value={formData.email}
                    onChange={handleChange}
                    className="input pl-11"
                    placeholder="you@example.com"
                  />
                </div>
              </div>
            )}

            {mode === 'reset-password' && (
              <>
                <div className="space-y-2">
                  <label className="block text-sm font-semibold text-gray-700">
                    New Password
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                      </svg>
                    </div>
                    <input
                      type="password"
                      name="password"
                      required
                      minLength={8}
                      value={formData.password}
                      onChange={handleChange}
                      className="input pl-11"
                      placeholder="••••••••"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="block text-sm font-semibold text-gray-700">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                      <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                      </svg>
                    </div>
                    <input
                      type="password"
                      name="confirmPassword"
                      required
                      minLength={8}
                      value={confirmPassword}
                      onChange={handleConfirmChange}
                      className="input pl-11"
                      placeholder="••••••••"
                    />
                  </div>
                </div>
              </>
            )}

            {(mode === 'login' || mode === 'register') && (
              <div className="space-y-2">
                <label className="block text-sm font-semibold text-gray-700">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    name="password"
                    required
                    value={formData.password}
                    onChange={handleChange}
                    className="input pl-11 pr-11"
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? (
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                      </svg>
                    ) : (
                      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* OAuth Divider */}
            {mode === 'login' && (
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200 dark:border-gray-600"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-4 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                    Or continue with
                  </span>
                </div>
              </div>
            )}

            {/* OAuth Buttons */}
            {mode === 'login' && (
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={async () => {
                    const result = await api.oauthGoogleInit();
                    if (result.success && result.data?.authorize_url) {
                      window.location.href = result.data.authorize_url;
                    }
                  }}
                  className="flex items-center justify-center gap-2 px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-200">Google</span>
                </button>
                <button
                  onClick={async () => {
                    const result = await api.oauthGithubInit();
                    if (result.success && result.data?.authorize_url) {
                      window.location.href = result.data.authorize_url;
                    }
                  }}
                  className="flex items-center justify-center gap-2 px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-7.29 0-.166.042-.327.042-.327.056-.092.195-.136.352-.136h.003c.157 0 .296.044.352.136.042.12.083.282.083.472 0 3.133-1.513 4.476-3.087 4.955.262.216.52.638.52 1.287v3.609c0 .318.192.694.703.577 4.765-1.589 8.199-6.085 8.199-11.387 0-6.627-5.373-12-12-12z"/>
                  </svg>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-200">GitHub</span>
                </button>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary py-4 text-lg"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Processing...
                </span>
              ) : mode === 'login' ? 'Sign In' : mode === 'register' ? 'Create Account' : mode === 'forgot-password' ? 'Send Reset Link' : 'Reset Password'}
            </button>
          </form>

          {/* Footer links based on mode */}
          {mode === 'login' && (
            <div className="mt-4 text-center">
              <Link to="/forgot-password" className="text-sm text-primary-600 hover:text-primary-700 font-medium">
                Forgot Password?
              </Link>
            </div>
          )}

          {(mode === 'forgot-password' || mode === 'reset-password') && (
            <div className="mt-8 text-center">
              <Link to="/login" className="text-primary-600 hover:text-primary-700 font-semibold">
                Back to Login
              </Link>
            </div>
          )}

          {mode === 'register' && (
            <div className="mt-8 text-center">
              <Link to="/forgot-password" className="text-sm text-primary-600 hover:text-primary-700 font-medium block mb-4">
                Forgot Password?
              </Link>
              <Link
                to="/login"
                className="text-primary-600 hover:text-primary-700 font-semibold"
              >
                Already have an account? Sign in
              </Link>
            </div>
          )}

          {mode === 'login' && (
            <div className="mt-8 text-center">
              <Link
                to="/register"
                className="text-primary-600 hover:text-primary-700 font-semibold"
              >
                Don't have an account? Sign up
              </Link>
            </div>
          )}
        </div>

        {/* Footer */}
        <p className="mt-8 text-center text-primary-100 text-sm">
          By continuing, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>
    </div>
  );
};

export default AuthPage;
