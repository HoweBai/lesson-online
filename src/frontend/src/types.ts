/** TypeScript type definitions for the Online Learning Platform frontend. */

export interface User {
  id: string;
  username: string;
  email: string;
  created_at: string;
  is_admin: boolean;
}

export interface UserProfile {
  id: string;
  user_id: string;
  programming_level?: number;
  math_background?: string;
  learning_goal?: string;
  available_hours_per_day?: number;
  preferred_style?: string;
}

export interface ClaudeConfig {
  id: string;
  user_id: string;
  base_url: string;
  model_name?: string;
  system_prompt?: string;
  created_at: string;
  last_used_at?: string;
  is_default: boolean;
}

export interface Tutorial {
  id: string;
  owner_id: string;
  title: string;
  description?: string;
  is_public: boolean;
  status: 'draft' | 'reviewing' | 'published' | 'retired';
  outline?: Record<string, any>;
  total_chapters?: number;
  current_chapter?: number;
  created_at: string;
  updated_at: string;
  views?: number;
  likes?: number;
}

export interface Chapter {
  id: string;
  tutorial_id: string;
  chapter_number: number;
  title: string;
  content: SectionContent[];
  status: 'draft' | 'ready' | 'in_progress' | 'completed' | 'failed';
  prerequisite_check_passed: boolean;
  generated_at: string;
  completed_at?: string;
  version: number;
}

export interface SectionContent {
  id: string;
  title: string;
  order: number;
  type: 'theory' | 'formula' | 'code' | 'exercise';
  content: {
    overview?: string;
    theoreticalExplanation?: string;
    diagrams?: Array<{ caption: string; url: string }>;
    mathematicalFormulas?: Array<{
      latex: string;
      derivation: string;
      explanation: string;
    }>;
    codeSamples?: Array<{
      language: string;
      code: string;
      explanation: string;
      complexityAnalysis?: { time: string; space: string };
    }>;
    practiceExercises?: Array<{
      question: string;
      difficulty: 'easy' | 'medium' | 'hard';
      hint?: string;
      solutionReference?: string;
    }>;
  };
}

export interface OutlineDraft {
  id: string;
  tutorialId: string;
  chapters: Array<{
    number: number;
    title: string;
  }>;
  createdAt: string;
  updatedAt: string;
}

export interface AuthToken {
  access_token: string;
  expires_in: number;
  token_type: string;
}

export interface APIResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  content: string;
  timestamp: number;
  isProcessing?: boolean;
}
