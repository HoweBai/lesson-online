/** Utility functions for the frontend application. */

export const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

export const formatTimeAgo = (dateString: string): string => {
  const seconds = Math.floor((Date.now() - new Date(dateString).getTime()) / 1000);
  let interval = seconds / 31536000;
  if (interval > 1) return Math.floor(interval) + " years ago";
  interval = seconds / 2592000;
  if (interval > 1) return Math.floor(interval) + " months ago";
  interval = seconds / 86400;
  if (interval > 1) return Math.floor(interval) + " days ago";
  interval = seconds / 3600;
  if (interval > 1) return Math.floor(interval) + " hours ago";
  interval = seconds / 60;
  if (interval > 1) return Math.floor(interval) + " minutes ago";
  return Math.floor(seconds) + " seconds ago";
};

export const generateId = (): string => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

export const checkRole = (user: any, roles: string[]): boolean => {
  return roles.some(r => user?.roles?.includes(r));
};

export async function pollStatus<T>(
  getStatus: () => Promise<T>,
  isComplete: (result: T) => boolean,
  options: { initialDelay?: number; maxDelay?: number; maxAttempts?: number } = {}
): Promise<T> {
  const { initialDelay = 1000, maxDelay = 30000, maxAttempts = 60 } = options;
  let delay = initialDelay;
  let attempts = 0;
  while (attempts < maxAttempts) {
    const result = await getStatus();
    if (isComplete(result)) return result;
    await new Promise(resolve => setTimeout(resolve, delay));
    delay = Math.min(delay * 2, maxDelay);
    attempts++;
  }
  throw new Error('Status polling timed out');
}
