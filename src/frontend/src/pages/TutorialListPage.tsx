/**
 * Tutorial List Page - Beautiful modern design with grid layout
 */

import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import TutorialCard from '../components/TutorialCard';
import { Tutorial } from '../types';
import { useToast } from '../hooks/useToast';

interface TutorialListPageProps {
  onOpenWizard?: () => void;
}

const TutorialListPage = ({ onOpenWizard }: TutorialListPageProps) => {
  const navigate = useNavigate();
  const toast = useToast();
  const { t } = useTranslation('tutorials');
  const [tutorials, setTutorials] = useState<Tutorial[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('publish_time');
  const [sortOrder, setSortOrder] = useState('desc');
  const [activeTab, setActiveTab] = useState<'public' | 'mine'>('public');
  const [bookmarks, setBookmarks] = useState<Set<string>>(new Set());
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (searchDebounceRef.current) {
        clearTimeout(searchDebounceRef.current);
      }
    };
  }, []);

  useEffect(() => {
    fetchBookmarks();
  }, []);

  useEffect(() => {
    fetchTutorials();
  }, [activeTab, searchTerm, sortBy, sortOrder]);

  const fetchBookmarks = async () => {
    try {
      const result = await api.request<any>('GET', '/api/v1/bookmarks/bookmarks');
      if (result.success && result.data?.data) {
        const bookmarkIds = result.data.data.map((b: any) => b.tutorial_id);
        setBookmarks(new Set(bookmarkIds));
      }
    } catch {
      // Failed to fetch bookmarks, ignore
    }
  };

  const fetchTutorials = async () => {
    setLoading(true);
    try {
      let result;
      if (activeTab === 'public') {
        result = await api.getCatalog(searchTerm, sortBy, sortOrder);
      } else {
        result = await api.getMyTutorials();
      }

      if (result.success && result.data) {
        setTutorials(result.data.data || []);
      }
    } catch (error) {
      toast.error(t('errors.load_tutorials', { ns: 'common' }));
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current);
    }
    searchDebounceRef.current = setTimeout(() => {
      fetchTutorials();
    }, 400);
  };

  const handleBookmark = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const isBookmarked = bookmarks.has(id);
    const result = isBookmarked
      ? await api.unbookmarkTutorial(id)
      : await api.bookmarkTutorial(id);
    if (result.success) {
      setBookmarks(prev => {
        const next = new Set(prev);
        if (isBookmarked) next.delete(id);
        else next.add(id);
        return next;
      });
    }
  };

  const handleLike = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const result = await api.likeTutorial(id);
    if (result.success) {
      fetchTutorials();
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-20 h-20 mx-auto mb-4">
            <div className="absolute inset-0 border-4 border-primary-200 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-primary-600 rounded-full border-t-transparent animate-spin"></div>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl">📚</span>
            </div>
          </div>
          <p className="text-gray-600 font-medium text-lg">{t('loading_tutorials')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Hero Section */}
        <div className="text-center mb-12 animate-fade-in">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            {t('welcome_to_learnhub')}{' '}
            <span className="gradient-text">{t('learnHub_title')}</span>
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Discover AI-powered personalized learning tutorials crafted just for you
          </p>
        </div>

        {/* Tabs and Actions */}
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4 mb-8">
          <div className="flex items-center gap-2 bg-white p-1 rounded-2xl shadow-soft">
            <button
              onClick={() => setActiveTab('public')}
              className={`px-6 py-2.5 rounded-xl font-semibold transition-all duration-200 ${
                activeTab === 'public'
                  ? 'bg-gradient-to-r from-primary-600 to-accent-600 text-white shadow-md'
                  : 'text-gray-600 hover:text-primary-600 hover:bg-primary-50'
              }`}
            >
              <span className="flex items-center gap-2">
                🌍 Public Tutorials
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  activeTab === 'public' ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-500'
                }`}>
                  {tutorials.filter(t => t.is_public).length}
                </span>
              </span>
            </button>
            <button
              onClick={() => setActiveTab('mine')}
              className={`px-6 py-2.5 rounded-xl font-semibold transition-all duration-200 ${
                activeTab === 'mine'
                  ? 'bg-gradient-to-r from-primary-600 to-accent-600 text-white shadow-md'
                  : 'text-gray-600 hover:text-primary-600 hover:bg-primary-50'
              }`}
            >
              <span className="flex items-center gap-2">
                👤 My Tutorials
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  activeTab === 'mine' ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-500'
                }`}>
                  {tutorials.filter(t => !t.is_public).length}
                </span>
              </span>
            </button>
          </div>

          <button
            onClick={() => onOpenWizard?.()}
            className="btn-primary flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Create Tutorial
          </button>
        </div>

        {/* Search and Filter */}
        <div className="bg-white rounded-2xl shadow-soft p-4 mb-8">
          <form className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                placeholder={t('search_tutorials')}
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                className="input pl-11"
              />
            </div>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white text-gray-700"
            >
              <option value="publish_time">📅 {t('sort_latest')}</option>
              <option value="views">👁️ {t('sort_views')}</option>
              <option value="likes">❤️ {t('sort_likes')}</option>
              <option value="created_at">🕐 {t('sort_oldest')}</option>
            </select>
            <button
              type="submit"
              className="btn-primary px-8"
            >
              Search
            </button>
          </form>
        </div>

        {/* Tutorial Grid */}
        {tutorials.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-3xl shadow-soft">
            <div className="text-6xl mb-4">📭</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              {activeTab === 'public' ? 'No public tutorials yet' : 'You haven\'t created any tutorials'}
            </h3>
            <p className="text-gray-500 mb-6 max-w-md mx-auto">
              {activeTab === 'public'
                ? 'Share your knowledge with the community! Create your first AI-powered tutorial.'
                : 'Create your first AI-powered tutorial with our guided wizard.'}
            </p>
            <button
              onClick={() => onOpenWizard?.()}
              className="btn-primary inline-flex items-center gap-2 px-6 py-3"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              {activeTab === 'public' ? 'Create & Publish Tutorial' : 'Create Your First Tutorial'}
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {tutorials.map((tutorial, index) => (
              <div key={tutorial.id} className="animate-slide-up" style={{ animationDelay: `${index * 0.1}s` }}>
                <TutorialCard
                  tutorial={tutorial}
                  onClick={(id) => navigate(`/tutorial/${id}`)}
                  onLike={(e) => handleLike(tutorial.id, e)}
                  isBookmarked={bookmarks.has(tutorial.id)}
                  onBookmark={(e) => handleBookmark(tutorial.id, e)}
                />
              </div>
            ))}
          </div>
        )}

        {/* Stats Footer */}
        <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label={t('stat_total_tutorials')} value={tutorials.length} icon="📚" />
          <StatCard label={t('stat_public_tutorials')} value={tutorials.filter(t => t.is_public).length} icon="🌍" />
          <StatCard label={t('stat_total_views')} value={tutorials.reduce((sum, t) => sum + (t.views || 0), 0)} icon="👁️" />
          <StatCard label={t('stat_bookmarked')} value={bookmarks.size} icon="🔖" />
        </div>
      </div>
    </div>
  );
};

// Stat card component
const StatCard = ({ label, value, icon }: { label: string; value: number; icon: string }) => (
  <div className="bg-white rounded-2xl p-4 shadow-soft text-center hover:shadow-hover transition-shadow">
    <div className="text-3xl mb-2">{icon}</div>
    <div className="text-2xl font-bold text-gray-900">{value}</div>
    <div className="text-sm text-gray-500">{label}</div>
  </div>
);

export default TutorialListPage;
