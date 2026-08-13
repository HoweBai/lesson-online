/**
 * ShareModal component - Social sharing dialog for tutorials.
 */

import React, { useState, useEffect } from 'react';
import { useToast } from '../hooks/useToast';

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  tutorialId: string;
  tutorialTitle: string;
  tutorialDescription: string;
}

const ShareModal = ({ isOpen, onClose, tutorialId, tutorialTitle, tutorialDescription }: ShareModalProps) => {
  const toast = useToast();
  const [shareUrl, setShareUrl] = useState('');

  useEffect(() => {
    if (isOpen && tutorialId) {
      const baseUrl = window.location.origin;
      setShareUrl(`${baseUrl}/tutorial/${tutorialId}`);
    }
  }, [isOpen, tutorialId]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      toast.success('Link copied to clipboard!');
    } catch {
      toast.error('Failed to copy link');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 animate-scale-in">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-gray-900">Share Tutorial</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Preview Card */}
        <div className="bg-gradient-to-br from-primary-50 to-accent-50 rounded-xl p-4 mb-6">
          <h4 className="font-bold text-gray-900 mb-2">{tutorialTitle}</h4>
          <p className="text-sm text-gray-600 line-clamp-2">{tutorialDescription || 'AI-powered personalized learning tutorial'}</p>
        </div>

        {/* Share Link */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">Share Link</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={shareUrl}
              readOnly
              className="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-600"
            />
            <button
              onClick={handleCopy}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
            >
              Copy
            </button>
          </div>
        </div>

        {/* Social Buttons */}
        <div className="flex justify-center gap-4">
          <button
            onClick={() => {
              window.open(
                `https://twitter.com/intent/tweet?text=${encodeURIComponent(tutorialTitle)}&url=${encodeURIComponent(shareUrl)}`,
                '_blank'
              );
            }}
            className="w-10 h-10 rounded-full bg-sky-500 text-white flex items-center justify-center hover:bg-sky-600 transition-colors"
            title="Share on Twitter"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z" />
            </svg>
          </button>
          <button
            onClick={() => {
              const linkedInUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`;
              window.open(linkedInUrl, '_blank');
            }}
            className="w-10 h-10 rounded-full bg-blue-700 text-white flex items-center justify-center hover:bg-blue-800 transition-colors"
            title="Share on LinkedIn"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
            </svg>
          </button>
          <button
            onClick={() => {
              const wechatUrl = `https://api.wechat.com/scan?url=${encodeURIComponent(shareUrl)}`;
              window.open(wechatUrl, '_blank');
            }}
            className="w-10 h-10 rounded-full bg-green-500 text-white flex items-center justify-center hover:bg-green-600 transition-colors"
            title="Share on WeChat"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 01.213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.326.326 0 00.167-.054l1.903-1.114a.864.864 0 01.717-.098 10.16 10.16 0 002.837.403c.276 0 .543-.027.811-.05a6.127 6.127 0 01-.253-1.735c0-3.672 3.381-6.654 7.56-6.654.22 0 .437.011.653.03C16.643 4.988 13.035 2.188 8.691 2.188zm-2.6 4.408c.56 0 1.016.454 1.016 1.016 0 .562-.456 1.016-1.016 1.016-.56 0-1.016-.454-1.016-1.016 0-.562.456-1.016 1.016-1.016zm5.22 0c.56 0 1.016.454 1.016 1.016 0 .562-.456 1.016-1.016 1.016-.56 0-1.016-.454-1.016-1.016 0-.562.456-1.016 1.016-1.016zm4.49 3.376c-3.74 0-6.774 2.722-6.774 6.08 0 3.357 3.034 6.08 6.774 6.08.947 0 1.86-.163 2.69-.46a.744.744 0 01.616.084l1.464.858a.272.272 0 00.139.045c.133 0 .241-.108.241-.241 0-.06-.023-.118-.038-.176l-.3-1.14a.486.486 0 01.175-.545C22.887 17.21 24 15.468 24 13.46c0-3.358-3.034-6.08-6.774-6.08h-.025zm-2.6 3.512c.46 0 .833.373.833.833s-.373.833-.833.833-.833-.373-.833-.833.373-.833.833-.833zm5.187 0c.46 0 .833.373.833.833s-.373.833-.833.833-.833-.373-.833-.833.373-.833.833-.833z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ShareModal;
