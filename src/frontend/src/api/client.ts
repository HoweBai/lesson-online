/** API client for the Online Learning Platform */

const API_BASE = process.env.REACT_APP_API_URL || 'http://tlcw.yobeeo.com';

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('auth_token');
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('auth_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('auth_token');
  }

  getToken(): string | null {
    return this.token;
  }

  private getHeaders(extra: Record<string, string> = {}): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...extra
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async request<T>(method: string, path: string, data?: any): Promise<ApiResponse<T>> {
    const url = `${API_BASE}${path}`;
    const options: RequestInit = {
      method,
      headers: this.getHeaders(),
    };

    if (data && method !== 'GET') {
      options.body = JSON.stringify(data);
    }

    const response = await fetch(url, options);
    const result = await response.json();

    if (!response.ok) {
      return {
        success: false,
        error: result?.detail || result?.message || 'Request failed',
      };
    }

    return { success: true, data: result };
  }

  // Auth endpoints
  async login(email: string, password: string) {
    return this.request<any>('POST', '/api/v1/auth/login', { email, password });
  }

  async register(username: string, email: string, password: string) {
    return this.request<any>('POST', '/api/v1/auth/register', { username, email, password });
  }

  async forgotPassword(email: string) {
    return this.request<any>('POST', '/api/v1/auth/forgot-password', { email });
  }

  async resetPassword(token: string, newPassword: string) {
    return this.request<any>('POST', '/api/v1/auth/reset-password', { token, new_password: newPassword });
  }

  async logout() {
    this.clearToken();
    return { success: true };
  }

  async getMe() {
    return this.request<any>('GET', '/api/v1/auth/me');
  }

  // Tutorial endpoints
  async getTutorials(page = 1, limit = 20) {
    return this.request<any>('GET', `/api/v1/tutorials/?public_only=true&page=${page}&limit=${limit}`);
  }

  async getMyTutorials(page = 1, limit = 20) {
    return this.request<any>('GET', `/api/v1/tutorials/?public_only=false&page=${page}&limit=${limit}`);
  }

  async getTutorial(id: string) {
    return this.request<any>('GET', `/api/v1/tutorials/${id}`);
  }

  async createTutorial(data: any) {
    return this.request<any>('POST', '/api/v1/tutorials', data);
  }

  async updateTutorial(id: string, data: any) {
    return this.request<any>('PUT', `/api/v1/tutorials/${id}`, data);
  }

  async deleteTutorial(id: string) {
    return this.request<any>('DELETE', `/api/v1/tutorials/${id}`);
  }

  // Outline endpoints
  async generateOutline(claudeConfigId: string, topics: string[]) {
    return this.request<any>('POST', '/api/v1/tutorials/generate-outline', {
      claude_config_id: claudeConfigId,
      topics
    });
  }

  async getOutlineStatus(outlineId: string) {
    return this.request<any>('GET', `/api/v1/tutorials/outlines/${outlineId}`);
  }

  async confirmOutline(outlineId: string, data: any) {
    return this.request<any>('PUT', `/api/v1/tutorials/outlines/${outlineId}/confirm`, data);
  }

  // Chapter endpoints
  async generateNextChapter(tutorialId: string) {
    return this.request<any>('POST', `/api/v1/tutorials/${tutorialId}/generate-next`);
  }

  async getTutorialChapters(tutorialId: string) {
    return this.request<any>('GET', `/api/v1/tutorials/${tutorialId}/chapters`);
  }

  async getChapterStatus(tutorialId: string, chapterNumber: number) {
    return this.request<any>('GET', `/api/v1/tutorials/${tutorialId}/chapters/${chapterNumber}/status`);
  }

  async getChapterContent(tutorialId: string, chapterNumber: number) {
    return this.request<any>('GET', `/api/v1/tutorials/${tutorialId}/chapters/${chapterNumber}`);
  }

  // Catalog endpoints
  async getCatalog(search?: string, sort_by = 'publish_time', order = 'desc') {
    let url = '/api/v1/catalog/?';
    if (search) url += `search=${encodeURIComponent(search)}&`;
    url += `sort_by=${sort_by}&order=${order}`;
    return this.request<any>('GET', url);
  }

  async getCatalogTutorial(id: string) {
    return this.request<any>('GET', `/api/v1/catalog/${id}`);
  }

  async likeTutorial(id: string) {
    return this.request<any>('POST', `/api/v1/catalog/${id}/like`);
  }

  async bookmarkTutorial(id: string) {
    return this.request<any>('POST', `/api/v1/bookmarks/${id}/bookmark`);
  }

  async unbookmarkTutorial(id: string) {
    return this.request<any>('DELETE', `/api/v1/bookmarks/${id}/bookmark`);
  }

  async reportTutorial(id: string, reason: string) {
    return this.request<any>('POST', `/api/v1/catalog/${id}/report`, { reason });
  }

  async getComments(tutorialId: string) {
    return this.request<any>('GET', `/api/v1/tutorials/${tutorialId}/comments`);
  }

  async createComment(tutorialId: string, content: string, parentId?: string) {
    return this.request<any>('POST', `/api/v1/tutorials/${tutorialId}/comments`, {
      content,
      parent_id: parentId
    });
  }

  async getPopularTutorials() {
    return this.request<any>('GET', '/api/v1/catalog/popular');
  }

  // Claude Config endpoints
  async getClaudeConfigs() {
    return this.request<any>('GET', '/api/v1/tutorials/claude-configs');
  }

  async saveClaudeConfig(data: any) {
    return this.request<any>('POST', '/api/v1/tutorials/claude-configs', data);
  }

  async deleteClaudeConfig(id: string) {
    return this.request<any>('DELETE', `/api/v1/tutorials/claude-configs/${id}`);
  }

  // Profile endpoints
  async getProfile() {
    return this.request<any>('GET', '/api/v1/users/profile');
  }

  async updateProfile(data: any) {
    return this.request<any>('PUT', '/api/v1/users/profile', data);
  }

  async getLearningProgress() {
    return this.request<any>('GET', '/api/v1/users/profile/progress');
  }

  async getLearningStats() {
    return this.request<any>('GET', '/api/v1/users/profile/stats');
  }

  async inferKnowledge() {
    return this.request<any>('POST', '/api/v1/users/profile/infer-knowledge');
  }

  // Export endpoints
  async exportMarkdown(tutorialId: string) {
    const response = await fetch(`${API_BASE}/api/v1/tutorials/${tutorialId}/export/markdown`, {
      headers: this.getHeaders()
    });
    return response.text();
  }

  async exportJSON(tutorialId: string) {
    return this.request<any>('GET', `/api/v1/tutorials/${tutorialId}/export/json`);
  }

  async exportOutline(tutorialId: string) {
    return this.request<any>('GET', `/api/v1/tutorials/${tutorialId}/export/outline`);
  }
}

export const api = new ApiClient();
export default ApiClient;
