/** Main application component for the Online Learning Platform. */
import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useParams } from 'react-router-dom';
import AuthPage from './pages/AuthPage';
import TutorialListPage from './pages/TutorialListPage';
import TutorialDisplayPage from './pages/TutorialDisplayPage';
import ProfilePage from './pages/ProfilePage';
import ClaudeConfigPage from './pages/ClaudeConfigPage';
import AdminLoginPage from './pages/AdminLoginPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import AuthCallbackPage from './pages/AuthCallbackPage';
import AdminUsersPage from './pages/AdminUsersPage';
import AdminCatalogPage from './pages/AdminCatalogPage';
import AdminGuard from './components/AdminGuard';
import CourseWizard from './components/CourseWizard';
import { GlobalErrorHandler } from './components/GlobalErrorHandler';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import { api } from './api/client';
import './App.css';

const App = () => {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [showWizard, setShowWizard] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('auth_token');

    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    api.getMe().then((result) => {
      if (result.success && result.data?.user) {
        setUser({ token, ...result.data.user });
      } else {
        localStorage.removeItem('auth_token');
        setUser(null);
      }
      setLoading(false);
    }).catch(() => {
      localStorage.removeItem('auth_token');
      setUser(null);
      setLoading(false);
    });
  }, []);

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('auth_token');
  };

  const ResetPasswordRoute = () => {
    const { token } = useParams<{ token: string }>();
    return <AuthPage mode="reset-password" resetToken={token} />;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-accent-50">
        <div className="text-center">
          <div className="relative">
            <div className="w-16 h-16 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin mx-auto"></div>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xl font-bold text-primary-600">OL</span>
            </div>
          </div>
          <p className="mt-4 text-gray-600 font-medium">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <ThemeProvider>
    <GlobalErrorHandler>
      <BrowserRouter>
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
        {user && (
          <header className="sticky top-0 z-40 glass border-b border-white/30 dark:border-gray-700 shadow-sm">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between items-center h-16">
                <div className="flex items-center space-x-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-primary-600 to-accent-600 rounded-xl flex items-center justify-center shadow-lg">
                    <span className="text-white font-bold text-lg">OL</span>
                  </div>
                  <div>
                    <h1 className="text-xl font-bold text-gray-900">LearnHub</h1>
                    <p className="text-xs text-gray-500">AI Learning Platform</p>
                  </div>
                </div>
                <div className="flex items-center space-x-4">
                  <NavLink href="/" icon="📚" label="Tutorials" />
                  <NavLink href="/wizard" icon="✨" label="Create" />
                  <NavLink href="/profile" icon="👤" label="Profile" />
                  {user?.is_admin && <NavLink href="/admin" icon="🛡️" label="Admin" />}
                  <button onClick={handleLogout} className="text-gray-600 hover:text-red-600">Logout</button>
                  <ThemeToggle />
                </div>
              </div>
            </div>
          </header>
        )}
        <main className="flex-1">
          <Routes>
            {/* Admin routes — always accessible */}
            <Route path="/admin/login" element={<AdminLoginPage />} />
            <Route path="/admin" element={
              <AdminGuard>
                <AdminDashboardPage />
              </AdminGuard>
            } />
            <Route path="/admin/users" element={
              <AdminGuard>
                <AdminUsersPage />
              </AdminGuard>
            } />
            <Route path="/admin/catalog" element={
              <AdminGuard>
                <AdminCatalogPage />
              </AdminGuard>
            } />
            {!user ? (
              <>
                <Route path="/login" element={<AuthPage mode="login" />} />
                <Route path="/register" element={<AuthPage mode="register" />} />
                <Route path="/forgot-password" element={<AuthPage mode="forgot-password" />} />
                <Route path="/reset-password/:token" element={<ResetPasswordRoute />} />
                <Route path="/auth/callback" element={<AuthCallbackPage />} />
                <Route path="*" element={<Navigate to="/login" replace />} />
              </>
            ) : (
              <>
                <Route path="/wizard" element={<CourseWizard onClose={() => setShowWizard(false)} />} />
                <Route path="/" element={<TutorialListPage />} />
                <Route path="/tutorial/share/:shareCode" element={<ShareRedirect />} />
                <Route path="/tutorial/:id" element={<TutorialDisplayPage />} />
                <Route path="/profile" element={<ProfilePage />} />
                <Route path="/claude-config" element={<ClaudeConfigPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </>
            )}
          </Routes>
        </main>
        </div>
      </BrowserRouter>
    </GlobalErrorHandler>
    </ThemeProvider>
  );
};

const NavLink = ({ href, icon, label }: { href: string; icon: string; label: string }) => {
  const navigate = useNavigate();
  return (
    <button onClick={() => navigate(href)} className="flex items-center space-x-2 px-4 py-2 text-gray-600 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-primary-50 dark:hover:bg-gray-700 rounded-xl transition-all">
      <span className="text-lg">{icon}</span>
      <span className="font-medium">{label}</span>
    </button>
  );
};

const ThemeToggle = () => {
  const { theme, toggleTheme } = useTheme();
  return (
    <button
      onClick={toggleTheme}
      className="w-9 h-9 rounded-xl flex items-center justify-center text-lg transition-all hover:bg-gray-100 dark:hover:bg-gray-700"
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      {theme === 'dark' ? '☀️' : '🌙'}
    </button>
  );
};

const ShareRedirect = () => {
  const { shareCode } = useParams<{ shareCode: string }>();
  const navigate = useNavigate();

  useEffect(() => {
    if (!shareCode) {
      navigate('/');
      return;
    }
    const redirect = async () => {
      try {
        const result = await api.getTutorialByShareCode(shareCode);
        if (result.success && result.data?.data?.id) {
          navigate(`/tutorial/${result.data.data.id}`);
        } else {
          navigate('/');
        }
      } catch {
        navigate('/');
      }
    };
    redirect();
  }, [shareCode, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="relative w-16 h-16 mx-auto mb-4">
          <div className="absolute inset-0 border-4 border-primary-200 rounded-full"></div>
          <div className="absolute inset-0 border-4 border-primary-600 rounded-full border-t-transparent animate-spin"></div>
        </div>
        <p className="text-gray-600 font-medium">Loading tutorial...</p>
      </div>
    </div>
  );
};

export default App;
