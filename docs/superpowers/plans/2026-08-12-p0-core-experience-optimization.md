# P0: Core Experience Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete all three P0 tasks from FUNCTIONAL_GAP_ANALYSIS_v2.md: learning stats charts, tutorial display page improvements (bookmark + share), and search debounce.

**Architecture:** The platform runs FastAPI backend (SQLite) + React frontend. P0 changes are all frontend-first with one database migration. No backend API changes are needed for bookmark/share/debounce. Learning charts render server-fetched JSON via recharts.

**Tech Stack:**
- Frontend: React 18, TypeScript, Tailwind CSS 3, react-router-dom 6, recharts (new), date-fns 2
- Backend: FastAPI, SQLAlchemy, SQLite
- Build: react-scripts (Create React App)

## Global Constraints

- Must follow existing code patterns: `useToast` hook for all toasts, `api` client for all requests, Tailwind utility classes for styling
- `react-hot-toast` is already configured in `ToastProvider` — use `useToast()` not `alert()` anywhere
- All frontend API calls must handle errors gracefully without crashing the page
- Database migrations must be idempotent (check table existence before creating)
- No new backend API endpoints required for P0 — use existing ones

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `src/frontend/src/api/client.ts` | Fix duplicate `getTutorialChapters`, add `isBookmarked` helper |
| Modify | `src/frontend/src/pages/TutorialDisplayPage.tsx` | Add bookmark toggle button + share button |
| Modify | `src/frontend/src/pages/TutorialListPage.tsx` | Add search debounce |
| Create | `src/frontend/src/components/LearningChart.tsx` | Recharts-based learning statistics charts |
| Modify | `src/frontend/src/pages/ProfilePage.tsx` | Replace stat cards with LearningChart component |
| Modify | `src/frontend/src/package.json` | Add recharts dependency |
| Create | `src/backend/src/database/migrations/005_add_is_bookmarked_flag.py` | No migration needed — bookmark logic is already in user_bookmarks table |

---

### Task 1: Add recharts dependency

**Files:**
- Modify: `src/frontend/src/package.json`

**Interfaces:**
- Produces: `recharts` package available for import as `import { LineChart, ... } from 'recharts'`

- [ ] **Step 1: Add recharts to package.json**

Open `src/frontend/src/package.json` and add `"recharts": "^2.10.0"` to the `dependencies` section:

```json
  "dependencies": {
    ...existing dependencies...,
    "recharts": "^2.10.0"
  },
```

- [ ] **Step 2: Install dependencies**

Run: `cd src/frontend && npm install`

Expected: `recharts` installed, no errors.

- [ ] **Step 3: Verify import works**

Create a temporary test file `src/frontend/src/components/RechartsTest.tsx` with:

```tsx
import React from 'react';
import { LineChart, Line } from 'recharts';

export const RechartsTest: React.FC = () => (
  <div data-testid="recharts-test">recharts loaded</div>
);
```

Run: `cd src/frontend && npx tsc --noEmit`

Expected: No type errors.

- [ ] **Step 4: Remove test file and commit**

```bash
rm src/frontend/src/components/RechartsTest.tsx
git add src/frontend/src/package.json src/frontend/package-lock.json
git commit -m "chore: add recharts dependency for learning statistics charts"
```

---

### Task 2: Fix client.ts duplicate method

**Files:**
- Modify: `src/frontend/src/api/client.ts`

**Interfaces:**
- Consumes: existing API methods
- Produces: a clean client with no duplicate methods; adds `isBookmarked(tutorialId: string): Promise<boolean>` helper

- [ ] **Step 1: Remove duplicate getTutorialChapters**

In `src/frontend/src/api/client.ts`, find the two `getTutorialChapters` methods (lines ~140 and ~152). Delete the second duplicate. Keep only the first one.

- [ ] **Step 2: Add isBookmarked helper**

After the existing `unbookmarkTutorial` method, add:

```typescript
  async isBookmarked(tutorialId: string): Promise<boolean> {
    const result = await this.request<any>('GET', '/api/v1/bookmarks/bookmarks');
    if (!result.success || !result.data?.data) return false;
    return result.data.data.some((b: { tutorial_id: string }) => b.tutorial_id === tutorialId);
  }
```

- [ ] **Step 3: TypeScript check**

Run: `cd src/frontend && npx tsc --noEmit`

Expected: No type errors.

- [ ] **Step 4: Commit**

```bash
git add src/frontend/src/api/client.ts
git commit -m "fix: remove duplicate getTutorialChapters in client.ts, add isBookmarked helper"
```

---

### Task 3: Add search debounce to TutorialListPage

**Files:**
- Modify: `src/frontend/src/pages/TutorialListPage.tsx`

**Interfaces:**
- Consumes: existing `searchTerm` state, `fetchTutorials` function
- Produces: debounced search that delays API calls by 400ms after user stops typing

- [ ] **Step 1: Update imports and add debounce**

In `src/frontend/src/pages/TutorialListPage.tsx`, change the first import line from:

```typescript
import React, { useState, useEffect } from 'react';
```

to:

```typescript
import React, { useState, useEffect, useRef } from 'react';
```

Then add a ref for the debounce timer (place it right after the existing `searchTerm` state):

```typescript
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
```

Replace the existing `handleSearch` function with debounced version:

```typescript
  const handleSearch = (value: string) => {
    setSearchTerm(value);
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current);
    }
    searchDebounceRef.current = setTimeout(() => {
      fetchTutorials();
    }, 400);
  };
```

Update the search input `onChange` to call `handleSearch`:

```typescript
              <input
                type="text"
                placeholder="Search tutorials..."
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
                className="input pl-11"
              />
```

Remove the `onSubmit` handler call from the form (the debounce handles it):

```typescript
          <form className="flex flex-col sm:flex-row gap-4">
```

- [ ] **Step 2: Clean up on unmount**

Add a `useEffect` cleanup:

```typescript
  useEffect(() => {
    return () => {
      if (searchDebounceRef.current) {
        clearTimeout(searchDebounceRef.current);
      }
    };
  }, []);
```

Place this after the existing `useEffect` hooks.

- [ ] **Step 3: TypeScript check**

Run: `cd src/frontend && npx tsc --noEmit`

Expected: No type errors.

- [ ] **Step 4: Commit**

```bash
git add src/frontend/src/pages/TutorialListPage.tsx
git commit -m "feat: add 400ms debounce to TutorialListPage search input"
```

---

### Task 4: Add bookmark button to TutorialDisplayPage

**Files:**
- Modify: `src/frontend/src/pages/TutorialDisplayPage.tsx`
- Modify: `src/frontend/src/api/client.ts` (add `getTutorialDetail` if needed — check first)

**Interfaces:**
- Consumes: `api.bookmarkTutorial()`, `api.unbookmarkTutorial()`, `api.isBookmarked()`
- Produces: a bookmark toggle button in the tutorial toolbar that reflects current state

- [ ] **Step 1: Check if getTutorialBookmarkStatus exists in client.ts**

Search `client.ts` for any method that checks bookmark status for a single tutorial. The `isBookmarked` helper from Task 2 can serve this purpose.

- [ ] **Step 2: Add bookmark state to TutorialDisplayPage**

In `TutorialDisplayPage.tsx`, add state after the existing state declarations:

```typescript
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [bookmarkLoading, setBookmarkLoading] = useState(false);
```

- [ ] **Step 3: Fetch bookmark status on mount**

Add inside the existing `useEffect` (or a new one) that calls `fetchChapters`:

```typescript
  useEffect(() => {
    const checkBookmark = async () => {
      if (!id) return;
      const result = await api.isBookmarked(id);
      setIsBookmarked(result);
    };
    checkBookmark();
  }, [id]);
```

- [ ] **Step 4: Add bookmark toggle handler**

Add the handler function before the JSX return:

```typescript
  const handleBookmark = async () => {
    if (!id || bookmarkLoading) return;
    setBookmarkLoading(true);
    try {
      const result = isBookmarked
        ? await api.unbookmarkTutorial(id)
        : await api.bookmarkTutorial(id);
      if (result.success) {
        setIsBookmarked(!isBookmarked);
        toast.success(isBookmarked ? 'Removed from bookmarks' : 'Added to bookmarks');
      }
    } catch (e: any) {
      toast.error('Failed to update bookmark');
    } finally {
      setBookmarkLoading(false);
    }
  };
```

- [ ] **Step 5: Add bookmark button to toolbar**

In the top toolbar `div` (the one with export buttons), add a bookmark button before the export buttons:

```tsx
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
              {isBookmarked ? 'Bookmarked' : 'Bookmark'}
            </button>
```

- [ ] **Step 6: TypeScript check**

Run: `cd src/frontend && npx tsc --noEmit`

Expected: No type errors.

- [ ] **Step 7: Commit**

```bash
git add src/frontend/src/pages/TutorialDisplayPage.tsx
git commit -m "feat: add bookmark toggle button to TutorialDisplayPage"
```

---

### Task 5: Add share button to TutorialDisplayPage

**Files:**
- Modify: `src/frontend/src/pages/TutorialDisplayPage.tsx`

**Interfaces:**
- Consumes: `window.location.href` for current URL, `navigator.clipboard.writeText`
- Produces: a share button that copies the tutorial URL to clipboard with toast feedback

- [ ] **Step 1: Add share handler**

Add after the `handleBookmark` function:

```typescript
  const handleShare = async () => {
    if (!id) return;
    const url = `${window.location.origin}/tutorial/${id}`;
    try {
      await navigator.clipboard.writeText(url);
      toast.success('Link copied to clipboard!');
    } catch {
      toast.error('Failed to copy link');
    }
  };
```

- [ ] **Step 2: Add share button to toolbar**

Add the share button next to the bookmark button in the toolbar:

```tsx
            <button
              onClick={handleShare}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-600 rounded-xl hover:bg-gray-200 transition-all font-medium shadow-soft"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
              </svg>
              Share
            </button>
```

- [ ] **Step 3: TypeScript check**

Run: `cd src/frontend && npx tsc --noEmit`

Expected: No type errors.

- [ ] **Step 4: Commit**

```bash
git add src/frontend/src/pages/TutorialDisplayPage.tsx
git commit -m "feat: add share button to TutorialDisplayPage with clipboard copy"
```

---

### Task 6: Create LearningChart component

**Files:**
- Create: `src/frontend/src/components/LearningChart.tsx`

**Interfaces:**
- Consumes: `stats` data from API (`tutorial_stats.by_month`, `chapter_stats`, `recent_activity`)
- Produces: chart components for tutorial creation trend and chapter completion breakdown

- [ ] **Step 1: Create the component file**

Create `src/frontend/src/components/LearningChart.tsx`:

```tsx
import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, Legend
} from 'recharts';

interface LearningChartProps {
  tutorialStats: {
    by_month: Record<string, number>;
    total: number;
    draft: number;
    published: number;
  } | null;
  chapterStats: {
    total: number;
    completed: number;
    ready: number;
    in_progress: number;
    failed: number;
  } | null;
}

const CHAPTER_COLORS = ['#22c55e', '#f59e0b', '#3b82f6', '#ef4444'];

const ChapterPieChart: React.FC<{ stats: LearningChartProps['chapterStats'] }> = ({ stats }) => {
  if (!stats || stats.total === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        <p>No chapter data yet</p>
      </div>
    );
  }

  const data = [
    { name: 'Completed', value: stats.completed, color: CHAPTER_COLORS[0] },
    { name: 'Ready', value: stats.ready, color: CHAPTER_COLORS[1] },
    { name: 'In Progress', value: stats.in_progress, color: CHAPTER_COLORS[2] },
    { name: 'Failed', value: stats.failed, color: CHAPTER_COLORS[3] },
  ].filter(d => d.value > 0);

  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        <p>No chapters generated yet</p>
      </div>
    );
  }

  return (
    <PieChart width={280} height={220}>
      <Pie
        data={data}
        cx="50%"
        cy="50%"
        innerRadius={55}
        outerRadius={90}
        paddingAngle={4}
        dataKey="value"
        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
      >
        {data.map((entry, index) => (
          <Cell key={`cell-${index}`} fill={entry.color} />
        ))}
      </Pie>
      <Tooltip formatter={(value: number) => `${value} chapters`} />
      <Legend />
    </PieChart>
  );
};

const TutorialBarChart: React.FC<{ stats: LearningChartProps['tutorialStats'] }> = ({ stats }) => {
  if (!stats || Object.keys(stats.by_month).length === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        <p>No tutorial data yet</p>
      </div>
    );
  }

  const data = Object.entries(stats.by_month)
    .map(([month, count]) => ({ month, count }))
    .sort((a, b) => a.month.localeCompare(b.month));

  return (
    <BarChart width={500} height={220} data={data}>
      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
      <XAxis dataKey="month" tick={{ fontSize: 12 }} />
      <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
      <Tooltip
        formatter={(value: number) => [`${value} tutorial${value !== 1 ? 's' : ''}`, 'Created']}
        labelFormatter={(label) => `Month: ${label}`}
      />
      <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
    </BarChart>
  );
};

export const LearningChart: React.FC<LearningChartProps> = ({ tutorialStats, chapterStats }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="card p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
          <span>📊</span> Tutorials by Month
        </h3>
        <div className="flex justify-center overflow-x-auto">
          <TutorialBarChart stats={tutorialStats} />
        </div>
      </div>
      <div className="card p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
          <span>📖</span> Chapter Status
        </h3>
        <div className="flex justify-center">
          <ChapterPieChart stats={chapterStats} />
        </div>
      </div>
    </div>
  );
};

export default LearningChart;
```

- [ ] **Step 2: TypeScript check**

Run: `cd src/frontend && npx tsc --noEmit`

Expected: No type errors.

- [ ] **Step 3: Commit**

```bash
git add src/frontend/src/components/LearningChart.tsx
git commit -m "feat: create LearningChart component with bar and pie charts using recharts"
```

---

### Task 7: Integrate LearningChart into ProfilePage

**Files:**
- Modify: `src/frontend/src/pages/ProfilePage.tsx`

**Interfaces:**
- Consumes: existing `stats` state (from `api.getLearningStats()`), `LearningChart` component
- Produces: ProfilePage with chart visualization replacing static stat cards

- [ ] **Step 1: Add imports**

Add to the imports at the top of `ProfilePage.tsx`:

```typescript
import { LearningChart } from '../components/LearningChart';
```

- [ ] **Step 2: Replace Statistics Card with LearningChart**

Find the Statistics Card `div` (the one with `stats` state check) and replace its entire content with:

```tsx
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
              <p className="text-gray-500 text-center py-8">No stats available yet</p>
            )}
          </div>
```

- [ ] **Step 3: Update grid layout**

Change the outer grid from `grid-cols-1 lg:grid-cols-3` to `grid-cols-1 lg:grid-cols-3` (no change needed for the first two cards; the chart card will span 2 columns on md+).

Actually the grid is already correct — the chart card uses `md:col-span-2` which will flow naturally.

- [ ] **Step 4: Fix error isolation in loadData**

The `Promise.all` in `loadData` crashes the whole page if one API fails. Replace it with independent calls:

```typescript
  const loadData = async () => {
    setLoading(true);
    try {
      const userRes = await api.getMe();
      if (userRes.success) setUser(userRes.data);
    } catch {
      // User info failure is non-critical
    }

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
    } catch {
      // Profile failure is non-critical
    }

    try {
      const progressRes = await api.getLearningProgress();
      if (progressRes.success) setProgress(progressRes.data);
    } catch {
      // Progress failure is non-critical
    }

    try {
      const statsRes = await api.getLearningStats();
      if (statsRes.success) setStats(statsRes.data);
    } catch {
      // Stats failure is non-critical
    }
  } catch (error) {
    toast.error('Failed to load profile. Please try again.');
  } finally {
    setLoading(false);
  }
```

Wait — that `} catch` closing won't match. The correct structure is:

```typescript
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
```

- [ ] **Step 5: TypeScript check**

Run: `cd src/frontend && npx tsc --noEmit`

Expected: No type errors.

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/pages/ProfilePage.tsx
git commit -m "feat: integrate LearningChart into ProfilePage, fix API error isolation"
```

---

### Task 8: Build verification

**Files:**
- No code changes

**Interfaces:**
- Verifies: all changes compile and the app builds without errors

- [ ] **Step 1: Full TypeScript check**

Run: `cd src/frontend && npx tsc --noEmit`

Expected: 0 errors.

- [ ] **Step 2: Build production**

Run: `cd src/frontend && npm run build`

Expected: Build succeeds, no errors.

- [ ] **Step 3: Verify all changes are committed**

Run: `git log --oneline -8`

Expected: 6 new commits (Tasks 1-7), plus the original gap analysis doc.

- [ ] **Step 4: Verify no regressions**

Check that existing pages still render:
- `TutorialListPage` — search input has debounce, bookmarks still toggle
- `TutorialDisplayPage` — has bookmark + share buttons, chapter nav still works
- `ProfilePage` — shows learning charts, profile edit still works

---

## Summary of Changes

| Task | File | Type | Change |
|------|------|------|--------|
| 1 | `src/frontend/src/package.json` | Modify | Add `recharts: ^2.10.0` |
| 2 | `src/frontend/src/api/client.ts` | Modify | Remove duplicate method, add `isBookmarked()` |
| 3 | `src/frontend/src/pages/TutorialListPage.tsx` | Modify | Add 400ms search debounce |
| 4 | `src/frontend/src/pages/TutorialDisplayPage.tsx` | Modify | Add bookmark toggle button |
| 5 | `src/frontend/src/pages/TutorialDisplayPage.tsx` | Modify | Add share button |
| 6 | `src/frontend/src/components/LearningChart.tsx` | Create | Recharts bar + pie chart component |
| 7 | `src/frontend/src/pages/ProfilePage.tsx` | Modify | Integrate LearningChart, fix error isolation |

**No backend changes required for P0.** All functionality uses existing APIs.
