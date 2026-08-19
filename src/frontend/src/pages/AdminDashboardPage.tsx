import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../hooks/useToast';
import { useTranslation } from 'react-i18next';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

const AdminDashboardPage = () => {
  const { t } = useTranslation('admin');
  const toast = useToast();
  const [stats, setStats] = useState<any>(null);
  const [userGrowth, setUserGrowth] = useState<any[]>([]);
  const [tutorialStats, setTutorialStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    setLoading(true);
    try {
      const [statsRes, userRes, tutorialRes] = await Promise.all([
        api.adminGetStatsOverview(),
        api.adminGetUserStats('30d'),
        api.adminGetTutorialStats('30d'),
      ]);
      if (statsRes.success) setStats(statsRes.data);
      if (userRes.success) setUserGrowth(userRes.data?.growth || []);
      if (tutorialRes.success) setTutorialStats(tutorialRes.data);
    } catch {
      toast.error(t('load_dashboard_failed'));
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
      </div>
    );
  }

  const statCards = [
    { label: t('total_users'), value: stats?.total_users ?? 0, icon: '👥', color: 'from-blue-500 to-cyan-500' },
    { label: t('total_tutorials'), value: stats?.total_tutorials ?? 0, icon: '📚', color: 'from-purple-500 to-pink-500' },
    { label: t('published'), value: stats?.published_tutorials ?? 0, icon: '✅', color: 'from-green-500 to-emerald-500' },
    { label: t('pending_review'), value: stats?.pending_tutorials ?? 0, icon: '⏳', color: 'from-yellow-500 to-orange-500' },
    { label: t('new_7days'), value: stats?.new_users_last_7_days ?? 0, icon: '📈', color: 'from-indigo-500 to-violet-500' },
    { label: t('published_month'), value: stats?.published_this_month ?? 0, icon: '🆕', color: 'from-rose-500 to-red-500' },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('admin_dashboard')}</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{t('platform_overview')}</p>
            </div>
            <div className="flex items-center gap-3">
              <Link to="/admin/users" className="px-4 py-2 bg-primary-600 text-white rounded-xl hover:bg-primary-700 text-sm font-medium">
                {t('manage_users')}
              </Link>
              <Link to="/admin/catalog" className="px-4 py-2 bg-purple-600 text-white rounded-xl hover:bg-purple-700 text-sm font-medium">
                {t('review_tutorials')}
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Stat Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
          {statCards.map((card) => (
            <div key={card.label} className={`bg-white dark:bg-gray-800 rounded-2xl p-4 shadow-soft border border-gray-100 dark:border-gray-700`}>
              <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${card.color} flex items-center justify-center text-xl mb-3`}>
                {card.icon}
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">{card.value}</div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{card.label}</div>
            </div>
          ))}
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* User Growth */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-soft border border-gray-100 dark:border-gray-700 overflow-x-auto">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">{t('user_growth')}</h3>
            {userGrowth.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={userGrowth}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} tickLine={false} />
                  <YAxis tick={{ fontSize: 12 }} tickLine={false} />
                  <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }} />
                  <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-400">{t('no_data')}</div>
            )}
          </div>

          {/* Tutorial Stats */}
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-soft border border-gray-100 dark:border-gray-700 overflow-x-auto">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">{t('tutorial_status_distribution')}</h3>
            {tutorialStats && (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={Object.entries(tutorialStats.by_status ?? {}).map(([k, v]) => ({ name: k, value: v }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} tickLine={false} />
                  <YAxis tick={{ fontSize: 12 }} tickLine={false} />
                  <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }} />
                  <Bar dataKey="value" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboardPage;
