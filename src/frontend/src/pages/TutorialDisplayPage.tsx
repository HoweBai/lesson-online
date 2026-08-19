/**
 * Tutorial Display Page - Beautiful tutorial reading experience
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useTranslation } from 'react-i18next';
import CodeBlock from '../components/CodeBlock';
import ClaudeChatSidebar from '../components/ClaudeChatSidebar';
import CommentSection from '../components/CommentSection';
import ShareModal from '../components/ShareModal';
import { api } from '../api/client';
import { useToast } from '../hooks/useToast';

interface ChapterContent {
  title: string;
  sections: Array<{
    id: string;
    title: string;
    order: number;
    type: 'theory' | 'formula' | 'code' | 'exercise';
    content: any;
  }>;
  chapter_number?: number;
  totalChapters?: number;
  prerequisiteTopicsCovered?: string[];
  keyConceptsLearned?: string[];
  estimatedReadingTimeMin?: number;
}

const TutorialDisplayPage = () => {
  const { t } = useTranslation('tutorials');
  const toast = useToast();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [chapter, setChapter] = useState<ChapterContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  const [refreshing, setRefreshing] = useState(false);
  const [chapters, setChapters] = useState<Array<{ chapter_number: number; title: string; status: string; id: string }>>([]);
  const [showChapterList, setShowChapterList] = useState(false);
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [bookmarkLoading, setBookmarkLoading] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);

  const fetchChapters = useCallback(async () => {
    if (!id) return;
    const result = await api.getTutorialChapters(id);
    if (result.success && result.data?.data) {
      setChapters(result.data.data);
    }
  }, [id]);

  const fetchChapter = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.getChapterContent(id!, 1);
      if (result.success) {
        setChapter(result.data);
      } else {
        throw new Error(result.error || t('errors.load_chapter', { ns: 'common' }));
      }
    } catch (err: any) {
      console.error('Error loading chapter:', err);
      setError(err?.message || t('errors.load_chapter', { ns: 'common' }));
      toast.error(t('errors.load_chapter', { ns: 'common' }));
    } finally {
      setLoading(false);
    }
  }, [id, toast, t]);

  useEffect(() => {
    fetchChapter();
    fetchChapters();
  }, [fetchChapter, fetchChapters]);

  useEffect(() => {
    const checkBookmark = async () => {
      if (!id) return;
      const result = await api.isBookmarked(id);
      setIsBookmarked(result);
    };
    checkBookmark();
  }, [id]);

  const handleRetry = useCallback(() => {
    fetchChapter();
  }, [fetchChapter]);

  const handleChapterGenerated = useCallback(async () => {
    if (id) {
      setRefreshing(true);
      try {
        const result = await api.getChapterContent(id, 1);
        if (result.success) {
          setChapter(result.data);
        } else {
          toast.error(t('errors.refresh_chapter', { ns: 'common' }));
        }
      } catch (err: any) {
        toast.error(t('errors.refresh_chapter', { ns: 'common' }));
        console.error('Error refreshing chapter:', err);
      } finally {
        setRefreshing(false);
      }
    }
  }, [id, toast, t]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="relative w-20 h-20 mx-auto mb-4">
            <div className="absolute inset-0 border-4 border-primary-200 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-primary-600 rounded-full border-t-transparent animate-spin"></div>
          </div>
          <p className="text-gray-600 font-medium">{t('loading_tutorial')}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">{t('failed_to_load_tutorial')}</h2>
          <p className="text-gray-500 mb-2">{error}</p>
          <p className="text-gray-400 text-sm mb-6">{t('please_check_connection')}</p>
          <button onClick={handleRetry} className="btn-primary">
            {t('retry')}
          </button>
        </div>
      </div>
    );
  }

  if (!chapter) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">📭</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">{t('tutorial_not_found')}</h2>
          <p className="text-gray-500 mb-6">{t('tutorial_removed')}</p>
          <button onClick={() => navigate('/')} className="btn-primary">
            {t('back_to_library')}
          </button>
        </div>
      </div>
    );
  }

  const handleExportMarkdown = async () => {
    try {
      const text = await api.exportMarkdown(id!);
      if (text) {
        const blob = new Blob([text], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${chapter?.title || 'tutorial'}.md`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success(t('export_markdown_success'));
      }
    } catch (e: any) {
      toast.error(t('errors.export_markdown', { ns: 'common' }));
    }
  };

  const handleExportJSON = async () => {
    try {
      const result = await api.exportJSON(id!);
      if (result.success) {
        const blob = new Blob([JSON.stringify(result.data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${chapter?.title || 'tutorial'}.json`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success(t('export_json_success'));
      }
    } catch (e: any) {
      toast.error(t('errors.export_json', { ns: 'common' }));
    }
  };

  const handleExportOutline = async () => {
    try {
      const result = await api.exportOutline(id!);
      if (result.success) {
        const blob = new Blob([JSON.stringify(result.data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${chapter?.title || 'tutorial'}-outline.json`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success(t('export_outline_success'));
      }
    } catch (e: any) {
      toast.error(t('errors.export_outline', { ns: 'common' }));
    }
  };

  const handleExportPDF = async () => {
    try {
      const blob = await api.exportPDF(id!);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${chapter?.title || 'tutorial'}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success(t('export_pdf_success'));
    } catch (e: any) {
      toast.error(t('errors.export_pdf', { ns: 'common' }));
    }
  };

  const handleBookmark = async () => {
    if (!id || bookmarkLoading) return;
    setBookmarkLoading(true);
    try {
      const result = isBookmarked
        ? await api.unbookmarkTutorial(id)
        : await api.bookmarkTutorial(id);
      if (result.success) {
        setIsBookmarked(!isBookmarked);
        toast.success(isBookmarked ? t('removed_from_bookmarks') : t('added_to_bookmarks'));
      }
    } catch (e: any) {
      toast.error(t('errors.update_bookmark', { ns: 'common' }));
    } finally {
      setBookmarkLoading(false);
    }
  };

  const handleShare = () => {
    if (!id) return;
    setShowShareModal(true);
  };

  const handleNextChapter = async () => {
    setGenerating(true);
    try {
      const result = await api.generateNextChapter(id!);
      if (result.success) {
        toast.info(t('generating_next_chapter_wait'));
      } else {
        toast.error(t('errors.generate_chapter', { ns: 'common' }));
      }
    } catch (e: any) {
      toast.error(t('errors.generate_chapter', { ns: 'common' }));
    } finally {
      setGenerating(false);
    }
  };

  const renderSection = (section: any) => {
    switch (section.type) {
      case 'theory':
        return (
          <div
            key={section.id}
            className={`theory-section mb-8 rounded-2xl border-l-4 transition-all duration-300 ${
              activeSection === section.id
                ? 'bg-gradient-to-r from-primary-50 to-accent-50 border-primary-500 shadow-soft'
                : 'bg-white border-gray-200 hover:border-primary-300'
            }`}
            onClick={() => setActiveSection(activeSection === section.id ? null : section.id)}
          >
            <div className="p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <span className="w-8 h-8 bg-primary-100 rounded-lg flex items-center justify-center text-primary-600 text-sm">
                  📖
                </span>
                {section.title}
              </h3>
              {section.content.theoreticalExplanation && (
                <div className="prose prose-lg max-w-none text-gray-700">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {section.content.theoreticalExplanation}
                  </ReactMarkdown>
                </div>
              )}
              {section.content.overview && (
                <div className="mt-4 p-4 bg-blue-50 rounded-xl border border-blue-200">
                  <p className="text-gray-700">{section.content.overview}</p>
                </div>
              )}
              {section.content.diagrams && (
                <div className="mt-4 space-y-4">
                  {section.content.diagrams.map((diag: any, i: number) => (
                    <div key={i} className="rounded-xl overflow-hidden shadow-md">
                      <img src={diag.url} alt={diag.caption} className="max-w-full h-auto" />
                      <p className="text-sm text-gray-600 mt-2 text-center px-4">{diag.caption}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        );

      case 'formula':
        return (
          <div
            key={section.id}
            className={`formula-section mb-8 rounded-2xl border-l-4 transition-all duration-300 ${
              activeSection === section.id
                ? 'bg-gradient-to-r from-accent-50 to-primary-50 border-accent-500 shadow-soft'
                : 'bg-white border-gray-200 hover:border-accent-300'
            }`}
            onClick={() => setActiveSection(activeSection === section.id ? null : section.id)}
          >
            <div className="p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <span className="w-8 h-8 bg-accent-100 rounded-lg flex items-center justify-center text-accent-600 text-sm">
                  📐
                </span>
                {section.title}
              </h3>
              {section.content.mathematicalFormulas?.map((formula: any, i: number) => (
                <div key={i} className="formula-card bg-gradient-to-r from-slate-50 to-primary-50 p-5 rounded-xl border border-primary-100 mb-4">
                  <div className="text-center my-4 font-mono text-lg bg-white p-4 rounded-lg shadow-sm">
                    {formula.latex.replace(/\$/g, '')}
                  </div>
                  <div className="space-y-2 text-sm text-gray-700">
                    <p><strong className="text-primary-700">{t('derivation')}:</strong> {formula.derivation}</p>
                    <p><strong className="text-primary-700">{t('explanation')}:</strong> {formula.explanation}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

      case 'code':
        return (
          <div
            key={section.id}
            className={`code-section mb-8 rounded-2xl border-l-4 transition-all duration-300 ${
              activeSection === section.id
                ? 'bg-slate-900 border-green-500 shadow-soft'
                : 'bg-white border-gray-200 hover:border-green-300'
            }`}
            onClick={() => setActiveSection(activeSection === section.id ? null : section.id)}
          >
            <div className="p-6">
              <h3 className={`text-xl font-bold mb-4 flex items-center gap-2 ${
                activeSection === section.id ? 'text-white' : 'text-gray-900'
              }`}>
                <span className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm ${
                  activeSection === section.id ? 'bg-green-600' : 'bg-green-100 text-green-600'
                }`}>
                  💻
                </span>
                {section.title}
              </h3>
              {section.content.code_samples?.map((sample: any, i: number) => (
                <div key={i} className="mb-4">
                  <CodeBlock language={sample.language} code={sample.code} />
                  {sample.explanation && (
                    <p className="mt-2 text-gray-600 text-sm px-2">{sample.explanation}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        );

      case 'exercise':
        return (
          <div
            key={section.id}
            className={`exercise-section mb-8 rounded-2xl border-l-4 transition-all duration-300 ${
              activeSection === section.id
                ? 'bg-gradient-to-r from-yellow-50 to-orange-50 border-yellow-500 shadow-soft'
                : 'bg-white border-gray-200 hover:border-yellow-300'
            }`}
            onClick={() => setActiveSection(activeSection === section.id ? null : section.id)}
          >
            <div className="p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <span className="w-8 h-8 bg-yellow-100 rounded-lg flex items-center justify-center text-yellow-600 text-sm">
                  ✏️
                </span>
                {section.title}
              </h3>
              {section.content.practice_exercises?.map((exercise: any, i: number) => (
                <div key={i} className="bg-gradient-to-r from-yellow-50 to-orange-50 p-5 rounded-xl border border-yellow-200 mb-4">
                  <p className="font-medium text-gray-900 mb-3">{exercise.question}</p>
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <span className={`badge ${
                      exercise.difficulty === 'easy' ? 'badge-success' :
                      exercise.difficulty === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {exercise.difficulty?.charAt(0).toUpperCase() + exercise.difficulty?.slice(1)}
                    </span>
                    {exercise.hint && (
                      <p className="text-sm text-yellow-700">{t('hint')} {exercise.hint}</p>
                    )}
                  </div>
                  <button className="mt-3 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors text-sm font-medium">
                    {t('show_solution')}
                  </button>
                </div>
              ))}
            </div>
          </div>
        );

      default:
        return (
          <div key={section.id} className="mb-8 p-6 bg-white rounded-2xl border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">{section.title}</h3>
            <p className="text-gray-500 text-sm mt-1">{t('section_type_not_supported')}</p>
          </div>
        );
    }
  };

  const progress = chapter.totalChapters
    ? ((chapter.chapter_number || 1) / chapter.totalChapters) * 100
    : 0;

  return (
    <>
      {/* Chapter Navigation */}
      <div className="fixed left-0 top-16 bottom-0 z-30 transition-all duration-300">
        <button
          onClick={() => setShowChapterList(!showChapterList)}
          className="fixed left-0 top-20 z-40 w-10 h-10 bg-white rounded-r-xl shadow-lg flex items-center justify-center text-gray-600 hover:text-primary-600 transition-all"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h10M4 18h7" />
          </svg>
        </button>
        <div className={`bg-white shadow-xl transition-all duration-300 ${showChapterList ? 'w-72' : 'w-0'} overflow-hidden`}>
          <div className="p-4">
            <h3 className="font-bold text-gray-900 mb-3">{t('chapters')}</h3>
            <div className="space-y-1">
              {chapters.map((ch) => (
                <button
                  key={ch.id}
                  onClick={async () => {
                    const result = await api.getChapterContent(id!, ch.chapter_number);
                    if (result.success) {
                      setChapter(result.data);
                      setShowChapterList(false);
                    }
                  }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all ${
                    chapter?.chapter_number === ch.chapter_number
                      ? 'bg-primary-100 text-primary-700 font-semibold'
                      : ch.status === 'ready'
                      ? 'text-gray-700 hover:bg-gray-50'
                      : 'text-gray-400 cursor-not-allowed'
                  }`}
                  disabled={ch.status !== 'ready'}
                >
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-bold">
                      {ch.chapter_number}
                    </span>
                    <span className="truncate">{ch.title}</span>
                    {ch.status === 'ready' && <span className="text-green-500 text-xs ml-auto">✓</span>}
                  </div>
                </button>
              ))}
              {chapters.length === 0 && (
                <p className="text-sm text-gray-500 text-center py-4">{t('no_chapters')}</p>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className={`min-h-screen py-8 px-4 sm:px-6 lg:px-8 transition-all duration-300 ${showChapterList ? 'ml-72' : 'ml-0'}`}>
      <div className="max-w-4xl mx-auto">
        {/* Top toolbar */}
        <div className="bg-white rounded-2xl shadow-soft p-4 mb-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-primary-600 hover:text-primary-700 font-medium px-4 py-2 rounded-xl hover:bg-primary-50 transition-all"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            {t('back_to_library')}
          </button>
          <div className="flex gap-2">
            <button
              onClick={handleBookmark}
              disabled={bookmarkLoading}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all font-medium shadow-soft ${
                isBookmarked
                  ? 'bg-amber-100 text-amber-700 hover:bg-amber-200'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              } disabled:opacity-50`}
            >
              <span>{isBookmarked ? '🔖' : '📑'}</span>
              {isBookmarked ? t('bookmarked') : t('bookmark')}
            </button>
            <button
              onClick={handleShare}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-600 rounded-xl hover:bg-gray-200 transition-all font-medium shadow-soft"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
              </svg>
              {t('share')}
            </button>
            <button
              onClick={handleExportMarkdown}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all font-medium shadow-soft"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {t('export_markdown')}
            </button>
            <button
              onClick={handleExportJSON}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-xl hover:bg-purple-700 transition-all font-medium shadow-soft"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h7" />
              </svg>
              {t('export_json')}
            </button>
            <button
              onClick={handleExportOutline}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-xl hover:bg-green-700 transition-all font-medium shadow-soft"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
              </svg>
              {t('export_outline')}
            </button>
            <button
              onClick={handleExportPDF}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-xl hover:bg-red-700 transition-all font-medium shadow-soft"
              title={t('export_pdf_btn')}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16l-4-4m0 0l4-4m-4 4h18" />
              </svg>
              {t('export_pdf')}
            </button>
          </div>
            <button
              onClick={handleNextChapter}
              disabled={generating || refreshing || !chapter?.chapter_number}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-primary-600 to-accent-600 text-white rounded-xl hover:from-primary-700 hover:to-accent-700 transition-all font-medium shadow-soft hover:shadow-hover disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {generating ? (
                <>
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  {t('generating')}
                </>
              ) : refreshing ? (
                <>
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  {t('refreshing')}
                </>
              ) : (
                <>
                  {t('next_chapter')}
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Chapter header */}
        <div className="bg-white rounded-2xl shadow-soft p-8 mb-6">
          <div className="flex items-center gap-3 mb-4">
            <span className="badge badge-primary text-sm">
              {t('chapter_of', { n: chapter.chapter_number || 1, total: chapter.totalChapters || '?' })}
            </span>
            {chapter.estimatedReadingTimeMin && (
              <span className="badge bg-gray-100 text-gray-600 text-sm">
                ⏱ {Math.round(chapter.estimatedReadingTimeMin)} {t('min_read')}
              </span>
            )}
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">{chapter.title}</h1>
          {chapter.prerequisiteTopicsCovered && (
            <div className="flex flex-wrap gap-2 mt-4">
              {chapter.prerequisiteTopicsCovered.map((topic: string, i: number) => (
                <span key={i} className="px-3 py-1 bg-primary-100 text-primary-700 rounded-full text-sm font-medium">
                  {topic}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Progress bar */}
        <div className="bg-white rounded-2xl shadow-soft p-4 mb-6">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>{t('progress')}</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
            <div
              className="bg-gradient-to-r from-primary-500 to-accent-500 h-3 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <p className="text-xs text-gray-500 mt-2 text-right">
            {t('chapter_of', { n: chapter.chapter_number || 1, total: chapter.totalChapters || '?' })}
          </p>
        </div>

        {/* Content sections */}
        <div className="space-y-2">
          {chapter.sections?.map((section) => renderSection(section))}
        </div>

        {/* Key concepts summary */}
        {chapter.keyConceptsLearned && (
          <div className="mt-12 bg-gradient-to-r from-primary-50 to-accent-50 p-8 rounded-2xl border border-primary-200">
            <h3 className="text-xl font-bold text-primary-900 mb-4 flex items-center gap-2">
              <span className="text-2xl">🎯</span> {t('key_concepts')}
            </h3>
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {chapter.keyConceptsLearned.map((concept: string, i: number) => (
                <li key={i} className="flex items-center gap-2 text-primary-800">
                  <svg className="w-5 h-5 text-primary-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  {concept.replace(/_/g, ' ')}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Bottom navigation */}
        <div className="mt-12 flex justify-between items-center">
          <button
            onClick={() => navigate('/')}
            className="btn-secondary"
          >
            ← {t('back_to_library')}
          </button>
          <button
            onClick={handleNextChapter}
            disabled={generating || !chapter?.chapter_number}
            className="btn-primary"
          >
            {generating ? (
              <>
                <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {t('generating')}
              </>
            ) : refreshing ? (
              <>
                <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {t('refreshing')}
              </>
            ) : (
              t('generate_next')
            )}
          </button>
        </div>
      </div>

      {/* Claude Chat Sidebar */}
      {id && (
        <ClaudeChatSidebar
          tutorialId={id}
          onChapterGenerated={handleChapterGenerated}
        />
      )}

      {/* Comments Section */}
      <CommentSection tutorialId={id} />

      {/* Share Modal */}
      <ShareModal
        isOpen={showShareModal}
        onClose={() => setShowShareModal(false)}
        tutorialId={id!}
        tutorialTitle={chapter?.title || ''}
        tutorialDescription={''}
      />
    </>
  );
};

export default TutorialDisplayPage;
