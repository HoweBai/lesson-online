/**
 * Tutorial Card component - Beautiful modern card design
 */

import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { Tutorial } from '../types';

interface TutorialCardProps {
  tutorial: Tutorial;
  onClick: (id: string) => void;
  onLike?: (e: React.MouseEvent) => void;
  isBookmarked?: boolean;
  onBookmark?: (e: React.MouseEvent) => void;
}

const TutorialCard = ({ tutorial, onClick, onLike, isBookmarked, onBookmark }: TutorialCardProps) => {
  return (
    <div
      className="card p-6 cursor-pointer group hover:-translate-y-1 transition-all duration-300 hover:shadow-hover"
      onClick={() => onClick(tutorial.id)}
    >
      {/* Header with gradient accent */}
      <div className="relative mb-4">
        <div className="absolute inset-0 bg-gradient-to-r from-primary-600 to-accent-600 rounded-xl opacity-0 group-hover:opacity-10 transition-opacity duration-300"></div>
        <div className="flex justify-between items-start mb-3">
          <h3 className="text-lg font-bold text-gray-900 line-clamp-1 group-hover:text-primary-600 transition-colors duration-300">
            {tutorial.title}
          </h3>
          {tutorial.is_public && (
            <span className="badge badge-success flex-shrink-0 ml-2">
              <span className="mr-1">🌍</span> Public
            </span>
          )}
        </div>
        {/* Gradient border at top */}
        <div className="h-1 w-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full mb-4 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
      </div>

      {/* Description */}
      <p className="text-gray-600 text-sm mb-4 line-clamp-2 min-h-[2.5em] group-hover:text-gray-700 transition-colors duration-300">
        {tutorial.description || 'No description available'}
      </p>

      {/* Meta information */}
      <div className="flex flex-wrap gap-3 text-xs text-gray-500 mb-4">
        <span className="flex items-center gap-1 bg-blue-50 text-blue-700 px-2 py-1 rounded-lg group-hover:bg-blue-100 transition-colors duration-300">
          <span>📖</span> {tutorial.total_chapters || 0} chapters
        </span>
        <span className="flex items-center gap-1 bg-purple-50 text-purple-700 px-2 py-1 rounded-lg group-hover:bg-purple-100 transition-colors duration-300">
          <span>👁️</span> {tutorial.views || 0} views
        </span>
        <span className="flex items-center gap-1 bg-pink-50 text-pink-700 px-2 py-1 rounded-lg group-hover:bg-pink-100 transition-colors duration-300">
          <span>❤️</span> {tutorial.likes || 0} likes
        </span>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-100 group-hover:border-primary-200 transition-colors duration-300">
        <span className="text-xs text-gray-400">
          Created {formatDistanceToNow(new Date(tutorial.created_at), { addSuffix: true })}
        </span>
        {onLike && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onLike(e);
            }}
            className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-primary-600 hover:bg-primary-50 rounded-lg transition-all duration-200 hover:scale-105"
          >
            <span>❤️</span> Like
          </button>
        )}
        {onBookmark && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onBookmark(e);
            }}
            className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-primary-600 hover:bg-primary-50 rounded-lg transition-all duration-200 hover:scale-105"
          >
            <span>{isBookmarked ? '🔖' : '📑'}</span> {isBookmarked ? 'Bookmarked' : 'Bookmark'}
          </button>
        )}
      </div>
    </div>
  );
};

export default TutorialCard;
