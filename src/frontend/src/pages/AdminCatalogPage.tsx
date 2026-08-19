import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../hooks/useToast';
import { useTranslation } from 'react-i18next';

interface PendingTutorial {
  id: string;
  title: string;
  description?: string;
  owner_id: string;
  status: string;
  total_chapters?: number;
  view_count?: number;
  like_count?: number;
  reported_count?: number;
  created_at: string;
}

const AdminCatalogPage = () => {
  const { t } = useTranslation('admin');
  const toast = useToast();
  const [tutorials, setTutorials] = useState<PendingTutorial[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [reviewingId, setReviewingId] = useState<string | null>(null);

  useEffect(() => {
    loadTutorials();
  }, [page]);

  const loadTutorials = async () => {
    setLoading(true);
    try {
      const result = await api.adminListPendingTutorials(page, 20);
      if (result.success && result.data) {
        setTutorials(result.data.data || []);
        setTotalPages(result.data.pagination?.pages || 1);
        setTotalItems(result.data.pagination?.total || 0);
      }
    } catch {
      toast.error(t('load_pending_failed'));
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async (tutorialId: string, action: 'approve' | 'reject') => {
    setReviewingId(tutorialId);
    try {
      const reason = action === 'reject'
        ? prompt(t('enter_rejection_reason')) || ''
        : '';
      const result = await api.adminReviewTutorial(tutorialId, action, reason || undefined);
      if (result.success) {
        toast.success(`Tutorial ${action}d successfully`);
        loadTutorials();
      } else {
        toast.error(result.error || t('review_failed'));
      }
    } catch (e: any) {
      toast.error(e.message || t('review_failed'));
    } finally {
      setReviewingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('tutorial_review')}</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{totalItems} tutorials pending review</p>
            </div>
            <Link to="/admin" className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-xl hover:bg-gray-200 dark:hover:bg-gray-600 text-sm font-medium">
              {t('back_to_dashboard')}
            </Link>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
          </div>
        ) : tutorials.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-12 text-center shadow-soft border border-gray-100 dark:border-gray-700">
            <div className="text-5xl mb-4">🎉</div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">{t('all_caught_up')}</h3>
            <p className="text-gray-500 dark:text-gray-400 mt-2">{t('no_tutorials_pending_review')}</p>
          </div>
        ) : (
          <>
            <div className="space-y-4">
              {tutorials.map((tutorial) => (
                <div key={tutorial.id} className="bg-white dark:bg-gray-800 rounded-2xl p-4 sm:p-6 shadow-soft border border-gray-100 dark:border-gray-700">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="text-base sm:text-lg font-bold text-gray-900 dark:text-white">{tutorial.title}</h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                        {tutorial.description || 'No description'}
                      </p>
                      <div className="flex flex-wrap items-center gap-2 mt-3 text-xs text-gray-400 dark:text-gray-500">
                        <span className="hidden sm:inline">👤 Owner: {tutorial.owner_id.slice(0, 8)}...</span>
                        <span className="sm:hidden">👤 {tutorial.owner_id.slice(0, 6)}...</span>
                        <span>📖 {tutorial.total_chapters || 0}ch</span>
                        <span>👁️ {tutorial.view_count || 0}</span>
                        <span>❤️ {tutorial.like_count || 0}</span>
                        {tutorial.reported_count && tutorial.reported_count > 0 && (
                          <span className="text-red-500">⚠️{tutorial.reported_count}</span>
                        )}
                        <span className="ml-auto">📅 {new Date(tutorial.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <div className="flex gap-2 ml-4 shrink-0">
                      <button
                        onClick={() => handleReview(tutorial.id, 'approve')}
                        disabled={reviewingId === tutorial.id}
                        className="hidden sm:flex px-4 py-2 bg-green-500 text-white rounded-xl hover:bg-green-600 text-sm font-medium disabled:opacity-50"
                      >
                        {reviewingId === tutorial.id ? '...' : `✓ ${t('approve_btn')}`}
                      </button>
                      <button
                        onClick={() => handleReview(tutorial.id, 'approve')}
                        disabled={reviewingId === tutorial.id}
                        className="sm:hidden w-9 h-9 flex items-center justify-center rounded-lg bg-green-500 text-white text-sm disabled:opacity-50"
                        title={t('approve_btn')}
                        aria-label={t('approve_btn')}
                      >
                        ✓
                      </button>
                      <button
                        onClick={() => handleReview(tutorial.id, 'reject')}
                        disabled={reviewingId === tutorial.id}
                        className="hidden sm:flex px-4 py-2 bg-red-500 text-white rounded-xl hover:bg-red-600 text-sm font-medium disabled:opacity-50"
                      >
                        {reviewingId === tutorial.id ? '...' : `✗ ${t('reject_btn')}`}
                      </button>
                      <button
                        onClick={() => handleReview(tutorial.id, 'reject')}
                        disabled={reviewingId === tutorial.id}
                        className="sm:hidden w-9 h-9 flex items-center justify-center rounded-lg bg-red-500 text-white text-sm disabled:opacity-50"
                        title={t('reject_btn')}
                        aria-label={t('reject_btn')}
                      >
                        ✗
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-6">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                >
                  {t('previous')}
                </button>
                <span className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
                  {t('page_of', { page, totalPages })}
                </span>
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-4 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                >
                  {t('next')}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default AdminCatalogPage;
