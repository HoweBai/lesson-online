/**
 * CommentSection component - Displays comments and allows creating new ones.
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../api/client';
import { useToast } from '../hooks/useToast';

interface Comment {
  id: string;
  content: string;
  user: { id: string; username: string } | null;
  created_at: string;
  is_reply: boolean;
  like_count: number;
  replies: Comment[];
}

interface CommentSectionProps {
  tutorialId: string;
}

const CommentSection = ({ tutorialId }: CommentSectionProps) => {
  const { t } = useTranslation('tutorials');
  const toast = useToast();
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [newComment, setNewComment] = useState('');

  useEffect(() => {
    loadComments();
  }, [tutorialId]);

  const loadComments = async () => {
    setLoading(true);
    try {
      const result = await api.getComments(tutorialId);
      if (result.success) {
        setComments(result.data?.data || []);
      }
    } catch (error) {
      console.error('Failed to load comments:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;

    const result = await api.createComment(tutorialId, newComment.trim());
    if (result.success) {
      setNewComment('');
      loadComments();
    } else {
      toast.error(result.error || t('write_comment'));
    }
  };

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-soft p-6 mt-8">
      <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
        <span>💬</span> {t('comments')} ({comments.length})
      </h3>

      {/* Comment form */}
      <form onSubmit={handleSubmit} className="mb-8">
        <textarea
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder={t('write_comment')}
          rows={3}
          className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
        />
        <div className="mt-2 flex justify-end">
          <button
            type="submit"
            disabled={!newComment.trim()}
            className="px-5 py-2 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium"
          >
            {t('write_comment')}
          </button>
        </div>
      </form>

      {/* Comments list */}
      {comments.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p className="text-lg">{t('no_comments')}</p>
          <p className="text-sm">{t('be_first')}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {comments.map((comment) => (
            <CommentItem key={comment.id} comment={comment} tutorialId={tutorialId} onRefresh={loadComments} />
          ))}
        </div>
      )}
    </div>
  );
};

// Single comment item component
const CommentItem = ({
  comment,
  tutorialId,
  onRefresh
}: {
  comment: Comment;
  tutorialId: string;
  onRefresh: () => void;
}) => {
  const { t } = useTranslation('tutorials');
  const toast = useToast();
  const [replyText, setReplyText] = useState('');
  const [showReply, setShowReply] = useState(false);

  const handleReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim()) return;

    const result = await api.createComment(tutorialId, replyText.trim(), comment.id);
    if (result.success) {
      setReplyText('');
      setShowReply(false);
      onRefresh();
    } else {
      toast.error('Failed to post reply');
    }
  };

  const timeAgo = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  return (
    <div className="border-b border-gray-100 pb-4 last:border-0">
      <div className="flex gap-3">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
          {comment.user?.username?.charAt(0).toUpperCase() || '?'}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-sm text-gray-900">
              {comment.user?.username || 'Unknown'}
            </span>
            <span className="text-xs text-gray-400">{timeAgo(comment.created_at)}</span>
          </div>
          <p className="text-gray-700 text-sm">{comment.content}</p>
          <button
            onClick={() => setShowReply(!showReply)}
            className="mt-2 text-xs text-primary-600 hover:text-primary-700 font-medium"
          >
            {t('write_reply')}
          </button>
        </div>
      </div>

      {/* Reply form */}
      {showReply && (
        <form onSubmit={handleReply} className="mt-3 ml-11 flex gap-2">
          <input
            type="text"
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder={t('write_reply')}
            className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          <button
            type="submit"
            disabled={!replyText.trim()}
            className="px-3 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            {t('write_reply')}
          </button>
          <button
            type="button"
            onClick={() => setShowReply(false)}
            className="px-3 py-2 text-gray-500 text-sm hover:text-gray-700"
          >
            {t('retry')}
          </button>
        </form>
      )}

      {/* Replies */}
      {comment.replies && comment.replies.length > 0 && (
        <div className="mt-3 ml-11 space-y-2">
          {comment.replies.map((reply) => (
            <div key={reply.id} className="border-l-2 border-gray-200 pl-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-semibold text-xs text-gray-900">
                  {reply.user?.username || 'Unknown'}
                </span>
                <span className="text-xs text-gray-400">{timeAgo(reply.created_at)}</span>
              </div>
              <p className="text-sm text-gray-700">{reply.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CommentSection;
