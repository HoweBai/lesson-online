/**
 * User Profile Page - Modern dashboard design
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import { User, UserProfile } from '../types';
import { useToast } from '../hooks/useToast';
import { LearningChart } from '../components/LearningChart';

const ProfilePage = () => {
  const { t } = useTranslation('tutorials');
  const toast = useToast();
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [progress, setProgress] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [knowledgeMap, setKnowledgeMap] = useState<Record<string, string>>({});
  const [formData, setFormData] = useState({
    programming_level: 1,
    math_background: '',
    learning_goal: 'general',
    available_hours_per_day: 2,
    preferred_style: 'text'
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // User info
      try {
        const userRes = await api.getMe();
        if (userRes.success) setUser(userRes.data);
      } catch {}

      // Profile
      try {
        const profileRes = await api.getProfile();
        if (profileRes.success) {
          setProfile(profileRes.data?.profile);
          if (profileRes.data?.knowledge_mapping?.mastery_map) {
            setKnowledgeMap(profileRes.data.knowledge_mapping.mastery_map);
          }
          if (profileRes.data?.profile) {
            setFormData({
              programming_level: profileRes.data.profile.programming_level || 1,
              math_background: profileRes.data.profile.math_background || '',
              learning_goal: profileRes.data.profile.learning_goal || 'general',
              available_hours_per_day: profileRes.data.profile.available_hours_per_day || 2,
              preferred_style: profileRes.data.profile.preferred_style || 'text'
            });
          }
        }
      } catch {}

      // Progress
      try {
        const progressRes = await api.getLearningProgress();
        if (progressRes.success) setProgress(progressRes.data);
      } catch {}

      // Stats
      try {
        const statsRes = await api.getLearningStats();
        if (statsRes.success) setStats(statsRes.data);
      } catch {}

    } catch (error) {
      toast.error('Failed to load profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    const result = await api.updateProfile(formData);
    if (result.success) {
      setEditing(false);
      loadData();
    }
  };

  const handleInferKnowledge = async () => {
    const result = await api.inferKnowledge();
    if (result.success) {
      toast.success('Knowledge mapping updated!');
      loadData();
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-20 h-20 mx-auto mb-4">
            <div className="absolute inset-0 border-4 border-primary-200 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-primary-600 rounded-full border-t-transparent animate-spin"></div>
          </div>
          <p className="text-gray-600 font-medium">{t('loading')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        {/* Page header */}
        <div className="mb-8 animate-fade-in">
          <h1 className="text-3xl font-bold text-gray-900">{t('learning_profile')}</h1>
          <p className="text-gray-600 mt-1">{t('manage_profile')}</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* User Info Card */}
          <div className="card p-6 animate-slide-up">
            <div className="text-center">
              {/* Avatar */}
              <div className="relative inline-block mb-4">
                <div className="w-24 h-24 bg-gradient-to-br from-primary-500 to-accent-500 rounded-full flex items-center justify-center shadow-lg">
                  <span className="text-white text-3xl font-bold">
                    {user?.username?.charAt(0).toUpperCase() || 'U'}
                  </span>
                </div>
                <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-success-500 rounded-full border-4 border-white flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>
              <h2 className="text-xl font-bold text-gray-900">{user?.username || 'User'}</h2>
              <p className="text-gray-500 text-sm">{user?.email || ''}</p>
              <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-success-50 text-success-700 rounded-full text-sm font-medium">
                <span className="w-2 h-2 bg-success-500 rounded-full animate-pulse"></span>
                Member since {new Date(user?.created_at || Date.now()).toLocaleDateString()}
              </div>
            </div>

            {/* Quick stats */}
            <div className="mt-6 pt-6 border-t border-gray-100 grid grid-cols-2 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-primary-600">{progress?.total_tutorials || 0}</div>
                <div className="text-xs text-gray-500">{t('tutorials')}</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-accent-600">{progress?.streak_days || 0}</div>
                <div className="text-xs text-gray-500">{t('day_streak')}</div>
              </div>
            </div>
          </div>

          {/* Learning Progress Card */}
          <div className="card p-6 animate-slide-up" style={{ animationDelay: '0.1s' }}>
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <span>📊</span> {t('learning_preferences')}
            </h3>
            {progress ? (
              <div className="space-y-4">
                <StatRow label={t('profile_stat_total_tutorials')} value={progress.total_tutorials || 0} icon="📚" color="primary" />
                <StatRow label={t('profile_stat_completed_chapters')} value={progress.completed_chapters || 0} icon="✅" color="success" />
                <StatRow label={t('profile_stat_in_progress')} value={progress.in_progress_chapters || 0} icon="⏳" color="warning" />
                <StatRow label={t('profile_stat_study_time')} value={`${Math.round((progress.total_study_time_minutes || 0) / 60)}h`} icon="⏱️" color="accent" />
                <StatRow label={t('profile_stat_streak')} value={`${progress.streak_days || 0} ${t('profile_stat_days_suffix')}`} icon="🔥" color="orange" />

                {/* Progress bar */}
                <div className="mt-6">
                  <div className="flex justify-between text-sm text-gray-600 mb-2">
                    <span>{t('overall_progress')}</span>
                    <span>{Math.round(((progress.completed_chapters || 0) / (progress.total_chapters || 1)) * 100)}%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-primary-500 to-accent-500 h-3 rounded-full transition-all duration-500"
                      style={{ width: `${((progress.completed_chapters || 0) / (progress.total_chapters || 1)) * 100}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">{t('no_progress')}</p>
            )}
          </div>

          {/* Statistics Card */}
          <div className="card p-6 animate-slide-up md:col-span-2" style={{ animationDelay: '0.2s' }}>
            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <span>📈</span> Learning Statistics
            </h3>
            {stats ? (
              <LearningChart
                tutorialStats={stats.tutorial_stats || null}
                chapterStats={stats.chapter_stats || null}
              />
            ) : (
              <p className="text-gray-500 text-center py-8">{t('no_stats')}</p>
            )}
          </div>

          {/* Knowledge Map Card */}
          {Object.keys(knowledgeMap).length > 0 && (
            <div className="card p-6 animate-slide-up" style={{ animationDelay: '0.15s' }}>
              <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                <span>🧠</span> Knowledge Map
              </h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(knowledgeMap).map(([topic, level]) => (
                  <span
                    key={topic}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium ${
                      level === 'advanced' ? 'bg-green-100 text-green-700' :
                      level === 'intermediate' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {topic.replace(/_/g, ' ')} · {level}
                  </span>
                ))}
              </div>
              <p className="text-xs text-gray-400 mt-3">
                Auto-inferred from your learning profile
              </p>
            </div>
          )}
        </div>

        {/* Profile Edit Section */}
        <div className="card p-6 mt-6 animate-slide-up" style={{ animationDelay: '0.3s' }}>
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <span>⚙️</span> Learning Preferences
            </h3>
            <div className="flex gap-2">
              <button
                onClick={handleInferKnowledge}
                className="px-4 py-2 text-sm bg-gradient-to-r from-purple-600 to-accent-600 text-white rounded-xl hover:from-purple-700 hover:to-accent-700 transition-all font-medium shadow-soft"
              >
                Update Knowledge Map
              </button>
              <button
                onClick={() => editing ? handleSave() : setEditing(true)}
                className="px-4 py-2 text-sm bg-primary-600 text-white rounded-xl hover:bg-primary-700 transition-all font-medium shadow-soft"
              >
                {editing ? '💾 Save Changes' : '✏️ Edit Profile'}
              </button>
            </div>
          </div>

          {editing ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  {t('programming_level_label')}
                </label>
                <select
                  value={formData.programming_level}
                  onChange={(e) => setFormData({...formData, programming_level: parseInt(e.target.value)})}
                  className="input"
                >
                  {[1, 2, 3, 4, 5].map(n => (
                    <option key={n} value={n}>{n} - {n === 1 ? t('level_beginner') : n === 2 ? t('level_elementary') : n === 3 ? t('level_intermediate') : n === 4 ? t('level_advanced') : t('level_expert')}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  {t('learning_goal_label')}
                </label>
                <select
                  value={formData.learning_goal}
                  onChange={(e) => setFormData({...formData, learning_goal: e.target.value})}
                  className="input"
                >
                  <option value="general">📚 General Learning</option>
                  <option value="job_search">💼 Job Preparation</option>
                  <option value="self_study">🧠 Self Improvement</option>
                  <option value="academic">🎓 Academic Research</option>
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  {t('math_background_label')}
                </label>
                <textarea
                  value={formData.math_background}
                  onChange={(e) => setFormData({...formData, math_background: e.target.value})}
                  className="input"
                  rows={3}
                  placeholder={t('math_background_placeholder')}
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  {t('study_time_label')}
                </label>
                <input
                  type="number"
                  min="0.5"
                  max="24"
                  step="0.5"
                  value={formData.available_hours_per_day}
                  onChange={(e) => setFormData({...formData, available_hours_per_day: parseFloat(e.target.value)})}
                  className="input"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  {t('learning_style_label')}
                </label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {['text', 'visual', 'code', 'exercise'].map(style => (
                    <button
                      key={style}
                      type="button"
                      onClick={() => setFormData({...formData, preferred_style: style})}
                      className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                        formData.preferred_style === style
                          ? 'bg-gradient-to-r from-primary-600 to-accent-600 text-white shadow-soft'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {style.charAt(0).toUpperCase() + style.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : profile ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InfoRow label={t('programming_level_label')} value={[t('level_beginner'), t('level_elementary'), t('level_intermediate'), t('level_advanced'), t('level_expert')][profile.programming_level - 1] || t('not_set')} />
              <InfoRow label={t('learning_goal_label')} value={profile.learning_goal || t('not_set')} />
              <InfoRow label={t('math_background_label')} value={profile.math_background || t('not_set')} />
              <InfoRow label={t('study_time_label')} value={`${profile.available_hours_per_day || 0} ${t('hours_per_day_suffix')}`} />
              <InfoRow label={t('learning_style_label')} value={profile.preferred_style || t('not_set')} />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

// Helper components
const StatRow = ({ label, value, icon, color }: { label: string; value: string | number; icon: string; color: string }) => {
  const colorClasses: Record<string, string> = {
    primary: 'text-primary-600',
    success: 'text-success-600',
    warning: 'text-yellow-600',
    accent: 'text-accent-600',
    orange: 'text-orange-600',
  };
  return (
    <div className="flex justify-between items-center p-3 bg-gray-50 rounded-xl">
      <span className="text-gray-600 flex items-center gap-2">
        <span>{icon}</span> {label}
      </span>
      <span className={`font-bold ${colorClasses[color] || 'text-gray-900'}`}>{value}</span>
    </div>
  );
};

const InfoRow = ({ label, value }: { label: string; value: string }) => (
  <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl">
    <span className="text-gray-500 text-sm w-32 flex-shrink-0">{label}:</span>
    <span className="font-medium text-gray-900">{value}</span>
  </div>
);

export default ProfilePage;
