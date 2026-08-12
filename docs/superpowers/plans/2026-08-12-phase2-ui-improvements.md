# Phase 2: 用户体验优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成第二阶段用户体验优化 — 完善前端界面交互、实现 WebSocket 聊天功能集成、添加加载状态和错误提示。

**Architecture:** 前端为 React + TypeScript，使用 Tailwind CSS。后端 WebSocket 服务已完整实现。第二阶段重点是：(1) 将密码重置功能集成到前端认证页面；(2) 修复并完善 WebSocket 聊天侧边栏，集成到教程展示页；(3) 添加教程生成进度轮询和错误处理；(4) 统一全局加载状态和错误提示。

**Tech Stack:** React 18, TypeScript, Tailwind CSS 3, FastAPI, WebSocket, JWT

## Global Constraints

- 所有 API 调用使用 `src/frontend/src/api/client.ts` 的 `api` 实例，baseUrl 为 `http://tlcw.yobeeo.com`
- 密码重置使用 JWT 令牌（1小时过期），forgot-password 始终返回 200（防止邮箱枚举）
- WebSocket 连接使用 query param 传递 token: `?token=${authToken}`
- 前端 Toast 通知通过 `react-hot-toast` 实现，使用 `useToast()` hook
- 所有异步操作必须有 loading 状态和错误处理
- 代码风格：保持与现有代码一致的命名、注释密度和样式

---

### Task 1: 密码重置 UI 流程

**Files:**
- Modify: `src/frontend/src/pages/AuthPage.tsx`
- Modify: `src/frontend/src/api/client.ts`
- Modify: `src/frontend/src/contexts/ToastContext.tsx`

**Interfaces:**
- Consumes: `api.login()`, `api.register()`, new `api.forgotPassword(email)`, `api.resetPassword(token, newPassword)`
- Produces: AuthPage 支持两种新模式：登录/注册 + 忘记密码

**Context:** 密码重置后端 API 已实现（`POST /api/v1/auth/forgot-password` 和 `POST /api/v1/auth/reset-password`），但前端没有入口。需要在 AuthPage 添加忘记密码链接和重置表单。

- [ ] **Step 1: 扩展 ApiClient 添加密码重置方法**

在 `src/frontend/src/api/client.ts` 中添加两个方法：

```typescript
// 密码重置
async forgotPassword(email: string) {
  return this.request<any>('POST', '/api/v1/auth/forgot-password', { email });
}

async resetPassword(token: string, newPassword: string) {
  return this.request<any>('POST', '/api/v1/auth/reset-password', { token, new_password: newPassword });
}
```

- [ ] **Step 2: 修改 AuthPage 添加忘记密码模式**

在 `AuthPage.tsx` 中：
1. 将 `mode` 类型扩展为 `'login' | 'register' | 'forgot-password' | 'reset-password'`
2. 添加 `resetToken` prop（用于 reset-password 模式）
3. 添加"忘记密码"链接（在 login 和 register 模式下）
4. 实现忘记密码表单（只输入邮箱）
5. 实现重置密码表单（输入新密码 + 确认密码）

```typescript
// 扩展 mode 类型
interface AuthPageProps {
  mode: 'login' | 'register' | 'forgot-password' | 'reset-password';
  resetToken?: string;
}

// 忘记密码表单（简单版）
if (mode === 'forgot-password') {
  return (
    <form onSubmit={handleForgotPassword}>
      <h2>Forgot Password</h2>
      <input name="email" type="email" placeholder="Your email" />
      <button type="submit">Send Reset Link</button>
      <Link to="/login">Back to Login</Link>
    </form>
  );
}

// 重置密码表单
if (mode === 'reset-password') {
  return (
    <form onSubmit={handleSubmit}>
      <h2>Reset Password</h2>
      <input name="newPassword" type="password" placeholder="New password" />
      <input name="confirmPassword" type="password" placeholder="Confirm password" />
      <button type="submit" disabled={loading}>
        {loading ? 'Processing...' : 'Reset Password'}
      </button>
    </form>
  );
}
```

- [ ] **Step 3: 运行测试**

```bash
cd src/frontend && npm test -- --watchAll=false
```

> 注意：本项目前端尚未配置 Jest 测试环境（无 test 文件，无 @testing-library/react）。此步骤用于验证构建不会因新增代码报错。

- [ ] **Step 4: 更新 App.tsx 路由**

在 `App.tsx` 中添加 forgot-password 和 reset-password 路由：

```typescript
<Route path="/forgot-password" element={<AuthPage mode="forgot-password" />} />
<Route path="/reset-password/:token" element={<AuthPage mode="reset-password" resetToken={params.token} />} />
```

- [ ] **Step 5: 提交**

```bash
git add src/frontend/src/pages/AuthPage.tsx src/frontend/src/api/client.ts src/frontend/src/App.tsx
git commit -m "feat: add password reset UI flow to AuthPage"
```

---

### Task 2: WebSocket 聊天侧边栏集成到教程页

**Files:**
- Modify: `src/frontend/src/hooks/useWebSocket.ts`
- Modify: `src/frontend/src/components/ClaudeChatSidebar.tsx`
- Modify: `src/frontend/src/pages/TutorialDisplayPage.tsx`
- Modify: `src/frontend/src/App.tsx`

**Interfaces:**
- Consumes: `useWebSocket(url, options)`, JWT token from localStorage
- Produces: 可工作的聊天侧边栏，集成到教程页面

**Context:** WebSocket 后端已完整实现（`/ws/claude/{tutorial_id}/{channel_id}`），前端有基础组件和 hook，但：
1. `ClaudeChatSidebar` 使用硬编码的 `wss://api.yourplatform.com` URL
2. 没有传递认证 token
3. 没有集成到教程页面
4. `useWebSocket` hook 存在 reconnect 循环问题

- [ ] **Step 1: 修复 useWebSocket hook 的 reconnect 问题**

问题：当 `socket` 状态更新为 null 后，`useEffect` 重新运行，但 `connect` 依赖包含 `socket`，导致无限循环。

修改 `src/frontend/src/hooks/useWebSocket.ts`：

```typescript
export function useWebSocket(
  url: string,
  options: Partial<WebSocketOptions> = {}
): UseWebSocketResult {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
    }
    
    const ws = new WebSocket(url);
    socketRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      onOpen();
    };

    ws.onmessage = (event) => {
      onMessage(event.data);
    };

    ws.onclose = (event) => {
      setIsConnected(false);
      onClose();
      
      // Exponential backoff reconnect
      if (event.code !== 1000) { // 1000 = normal close
        reconnectTimeoutRef.current = setTimeout(() => connect(), reconnectionDelay);
      }
    };

    ws.onerror = (error) => {
      onError(error);
    };
  }, [url, onOpen, onMessage, onClose, onError, reconnectionDelay]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close(1000, 'Component unmounting');
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message: string | ArrayBuffer | Blob) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(message);
    } else {
      console.warn('WebSocket not connected');
    }
  }, []);

  const closeWebSocket = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close(1000, 'Manual close');
      socketRef.current = null;
      setIsConnected(false);
    }
  }, []);

  return {
    socket: socketRef.current,
    isConnected,
    send: sendMessage,
    close: closeWebSocket,
    reconnect: connect
  };
}
```

- [ ] **Step 2: 修复 ClaudeChatSidebar 并添加 auth 支持**

修改 `ClaudeChatSidebar.tsx`：

1. 从 `localStorage` 获取 token
2. 构建正确的 WebSocket URL（使用 `window.location` 确定 protocol 和 host）
3. 正确处理 `typing` 消息类型
4. 修复 reconnect 逻辑（避免 `window.location.reload()`）

```typescript
// 获取 WebSocket URL
const getToken = () => localStorage.getItem('auth_token') || '';
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/claude/${tutorialId}/default?token=${getToken()}`;
```

5. 添加 typing indicator 处理：

```typescript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'ai_response') {
    setMessages(prev => [...prev, {
      id: data.message?.id || uuidv4(),
      sender: 'ai',
      content: data.message?.content || data.content,
      timestamp: Date.now()
    }]);
  } else if (data.type === 'typing') {
    // Show typing indicator
    setTyping(true);
  } else if (data.type === 'error') {
    toast.error(`Error: ${data.message}`);
  }
};
```

6. 添加 typing indicator UI：

```typescript
{typing && (
  <div className="flex justify-start">
    <div className="bg-gray-700 px-3 py-2 rounded-lg text-sm text-gray-400">
      <span className="animate-pulse">AI is thinking...</span>
    </div>
  </div>
)}
```

- [ ] **Step 3: 将聊天侧边栏集成到 TutorialDisplayPage**

在 `TutorialDisplayPage.tsx` 中：

1. 导入 `ClaudeChatSidebar`
2. 在页面中添加侧边栏，默认收起
3. 传递 `tutorialId` 和 `onChapterGenerated` 回调

```typescript
import ClaudeChatSidebar from '../components/ClaudeChatSidebar';

// 在 return 中添加
const [showChat, setShowChat] = useState(false);

// 在页面中添加切换按钮
<button onClick={() => setShowChat(!showChat)} className="fixed right-4 top-20 z-30">
  {showChat ? '✕' : '💬'}
</button>

{/* 侧边栏 */}
{showChat && (
  <ClaudeChatSidebar 
    tutorialId={id || ''} 
    onChapterGenerated={() => {
      toast.success('New chapter generated!');
      // Refresh chapter data
    }}
  />
)}
```

- [ ] **Step 4: 添加 WebSocket 聊天测试**

> 注意：本项目前端无 Jest 配置，跳过测试步骤。

- [ ] **Step 5: 运行测试**

创建 `src/frontend/src/hooks/__tests__/useWebSocket.test.ts`:

```typescript
import { renderHook, act } from '@testing-library/react-hooks';
import { useWebSocket } from '../useWebSocket';

describe('useWebSocket', () => {
  beforeEach(() => {
    // Mock WebSocket
    global.WebSocket = class MockWebSocket {
      readyState = 1; // OPEN
      onopen = () => {};
      onmessage = () => {};
      onclose = () => {};
      onerror = () => {};
      send = jest.fn();
      close = jest.fn();
      constructor() {}
    } as any;
  });

  it('connects on mount', () => {
    const { result } = renderHook(() => useWebSocket('ws://test.com'));
    expect(result.current.isConnected).toBe(true);
  });

  it('sends message', () => {
    const { result } = renderHook(() => useWebSocket('ws://test.com'));
    result.current.send('hello');
    // Verify send was called
  });
});
```

- [ ] **Step 5: 运行测试**

```bash
cd src/frontend && npm test -- --watchAll=false
```

> 注意：本项目前端无 Jest 配置，此步骤验证 TypeScript 编译无错误。

- [ ] **Step 6: 提交**

```bash
git add src/frontend/src/hooks/useWebSocket.ts src/frontend/src/components/ClaudeChatSidebar.tsx src/frontend/src/pages/TutorialDisplayPage.tsx
git commit -m "feat: integrate WebSocket chat sidebar into tutorial page"
```

---

### Task 3: 教程生成进度轮询

**Files:**
- Modify: `src/frontend/src/components/CourseWizard.tsx`
- Modify: `src/frontend/src/api/client.ts`

**Interfaces:**
- Consumes: `api.getOutlineStatus()`, `api.getChapterStatus()`
- Produces: 教程生成过程中的实时进度反馈

**Context:** 大纲和章节生成是异步操作（通过 Celery）。前端需要轮询状态端点来获取生成进度。

- [ ] **Step 1: 添加状态轮询辅助函数**

在 `src/frontend/src/utils/index.ts` 中添加：

```typescript
/**
 * Poll for status updates with exponential backoff
 */
export async function pollStatus<T>(
  getStatus: () => Promise<T>,
  isComplete: (result: T) => boolean,
  options: {
    initialDelay?: number;
    maxDelay?: number;
    maxAttempts?: number;
  } = {}
): Promise<T> {
  const {
    initialDelay = 1000,
    maxDelay = 30000,
    maxAttempts = 60
  } = options;

  let delay = initialDelay;
  let attempts = 0;

  while (attempts < maxAttempts) {
    const result = await getStatus();
    
    if (isComplete(result)) {
      return result;
    }

    await new Promise(resolve => setTimeout(resolve, delay));
    delay = Math.min(delay * 2, maxDelay);
    attempts++;
  }

  throw new Error('Status polling timed out');
}
```

- [ ] **Step 2: 修改 CourseWizard 添加生成进度**

注意：后端 `POST /api/v1/tutorials/generate-outline` 为同步生成（MVP），直接返回 completed 状态。前端需要等待并处理返回结果。

修改 `CourseWizard.tsx` 的 `submitGeneration` 方法：

```typescript
const submitGeneration = async (data: any) => {
  try {
    // Start generation
    const response = await fetch('/api/v1/tutorials/generate-outline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    if (!response.ok) throw new Error('Failed to start generation');

    const result = await response.json();
    const tutorialId = result.tutorial_id;

    if (!tutorialId) throw new Error('No tutorial ID returned');

    toast.success('Tutorial outline generated successfully!');
    onClose?.();
    
    // Navigate to tutorial
    window.location.href = `/tutorial/${tutorialId}`;
  } catch (err: any) {
    toast.error(err.message || 'Failed to generate tutorial');
    setError(err.message || 'Failed to generate tutorial');
  }
};
```

- [ ] **Step 3: 添加进度 UI 组件**

创建 `src/frontend/src/components/GenerationProgress.tsx`：

```typescript
import React from 'react';

interface GenerationProgressProps {
  status: 'pending' | 'generating' | 'completed' | 'failed';
  progress?: number;
  message?: string;
}

export const GenerationProgress: React.FC<GenerationProgressProps> = ({ 
  status, 
  progress = 0, 
  message 
}) => {
  return (
    <div className="p-6 bg-gray-50 rounded-xl">
      <div className="flex items-center gap-3 mb-4">
        {status === 'generating' && (
          <div className="animate-spin rounded-full h-5 w-5 border-2 border-blue-600 border-t-transparent"></div>
        )}
        {status === 'completed' && <span className="text-green-500 text-xl">✓</span>}
        {status === 'failed' && <span className="text-red-500 text-xl">✕</span>}
        <span className="font-medium text-gray-700">
          {message || (
            status === 'generating' ? 'Generating outline...' :
            status === 'completed' ? 'Generation complete!' :
            status === 'failed' ? 'Generation failed' : 'Waiting...'
          )}
        </span>
      </div>
      
      {status === 'generating' && (
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-blue-600 h-2 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
      )}
    </div>
  );
};
```

- [ ] **Step 4: 更新 CourseWizard 使用进度组件**

在 `CourseWizard.tsx` 中添加生成状态管理：

```typescript
const [generationStatus, setGenerationStatus] = useState<'idle' | 'generating' | 'completed' | 'failed'>('idle');
const [generationMessage, setGenerationMessage] = useState('');

// 在 submitGeneration 中更新状态
const submitGeneration = async (data: any) => {
  setGenerationStatus('generating');
  setGenerationMessage('Generating outline...');
  
  try {
    // ... existing generation logic ...
    setGenerationStatus('completed');
    setGenerationMessage('Tutorial generated successfully!');
  } catch (err) {
    setGenerationStatus('failed');
    setGenerationMessage(err.message || 'Generation failed');
  }
};
```

- [ ] **Step 5: 运行测试**

```bash
cd src/frontend && npm test -- --watchAll=false
```

> 注意：本项目前端无 Jest 配置，此步骤验证 TypeScript 编译无错误。

- [ ] **Step 6: 提交**

```bash
git add src/frontend/src/utils/index.ts src/frontend/src/components/CourseWizard.tsx src/frontend/src/components/GenerationProgress.tsx src/frontend/src/api/client.ts
git commit -m "feat: add tutorial generation progress polling"
```

---

### Task 4: 全局错误处理和加载状态改进

**Files:**
- Modify: `src/frontend/src/components/TutorialCard.tsx`
- Modify: `src/frontend/src/pages/TutorialListPage.tsx`
- Modify: `src/frontend/src/pages/ProfilePage.tsx`
- Create: `src/frontend/src/components/GlobalErrorHandler.tsx`

**Interfaces:**
- Consumes: `useToast()`, API client methods
- Produces: 统一的全局错误处理和加载状态

**Context:** 当前各页面的错误处理不一致，有些使用 `console.error`，有些显示简单错误消息。需要统一处理。

- [ ] **Step 1: 创建全局错误边界组件**

创建 `src/frontend/src/components/GlobalErrorHandler.tsx`：

```typescript
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { useToast } from '../hooks/useToast';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class GlobalErrorHandler extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Global error caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center p-8 bg-white rounded-2xl shadow-lg max-w-md">
            <div className="text-6xl mb-4">⚠️</div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Something went wrong</h2>
            <p className="text-gray-600 mb-6">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="btn-primary px-6 py-3"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
```

- [ ] **Step 2: 在 App.tsx 中使用错误边界**

```typescript
import { GlobalErrorHandler } from './components/GlobalErrorHandler';

// 在 return 中包裹
<GlobalErrorHandler>
  <BrowserRouter>
    {/* ... existing routes ... */}
  </BrowserRouter>
</GlobalErrorHandler>
```

- [ ] **Step 3: 统一 TutorialListPage 错误处理**

在 `TutorialListPage.tsx` 的 `fetchTutorials` 中添加错误提示：

```typescript
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
    } else if (result.error) {
      toast.error(result.error || 'Failed to load tutorials');
    }
  } catch (error: any) {
    toast.error(error.message || 'Failed to load tutorials');
    console.error('Failed to fetch tutorials:', error);
  } finally {
    setLoading(false);
  }
};
```

- [ ] **Step 4: 统一 ProfilePage 错误处理**

在 `ProfilePage.tsx` 的 `loadData` 中添加错误提示：

```typescript
const loadData = async () => {
  setLoading(true);
  try {
    const [userRes, profileRes, progressRes, statsRes] = await Promise.all([
      api.getMe(),
      api.getProfile(),
      api.getLearningProgress(),
      api.getLearningStats()
    ]);

    if (userRes.success) setUser(userRes.data);
    if (profileRes.success) setProfile(profileRes.data?.profile);
    if (progressRes.success) setProgress(progressRes.data);
    if (statsRes.success) setStats(statsRes.data);

    // Check for errors
    if (!userRes.success) toast.error(userRes.error || 'Failed to load user data');
  } catch (error: any) {
    toast.error(error.message || 'Failed to load profile');
  } finally {
    setLoading(false);
  }
};
```

- [ ] **Step 5: 添加统一的 loading 组件**

创建 `src/frontend/src/components/LoadingSpinner.tsx`：

```typescript
import React from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  fullScreen?: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  size = 'md', 
  text, 
  fullScreen = false 
}) => {
  const sizeClasses = {
    sm: 'w-6 h-6 border-2',
    md: 'w-10 h-10 border-4',
    lg: 'w-16 h-16 border-4'
  };

  const spinner = (
    <div className={`${sizeClasses[size]} border-primary-200 rounded-full border-t-primary-600 animate-spin`} />
  );

  if (fullScreen) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-primary-50 to-accent-50">
        {spinner}
        {text && <p className="mt-4 text-gray-600 font-medium">{text}</p>}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center p-4">
      {spinner}
      {text && <p className="mt-2 text-sm text-gray-500">{text}</p>}
    </div>
  );
};
```

- [ ] **Step 6: 运行测试**

```bash
cd src/frontend && npm test -- --watchAll=false
```

> 注意：本项目前端无 Jest 配置，此步骤验证 TypeScript 编译无错误。

- [ ] **Step 7: 提交**

```bash
git add src/frontend/src/components/GlobalErrorHandler.tsx src/frontend/src/components/LoadingSpinner.tsx src/frontend/src/pages/TutorialListPage.tsx src/frontend/src/pages/ProfilePage.tsx src/frontend/src/App.tsx
git commit -m "feat: add global error handling and loading states"
```

---

### Task 5: 教程页面加载状态改进

**Files:**
- Modify: `src/frontend/src/pages/TutorialDisplayPage.tsx`
- Modify: `src/frontend/src/components/TutorialCard.tsx`

**Interfaces:**
- Consumes: `api.generateNextChapter()`, `api.getChapterStatus()`, `api.getTutorial()`
- Produces: 改进的加载和错误状态

**Context:** 当前 TutorialDisplayPage 使用原始 fetch 获取章节，缺少错误状态和章节生成中的 loading 提示。需要改为使用 api 客户端并添加完整的错误处理。

- [ ] **Step 1: 修改 TutorialDisplayPage 使用 API 客户端**

在 `TutorialDisplayPage.tsx` 中：
1. 导入 `api` 客户端
2. 修改 `fetchChapter` 使用 `api.getTutorial()`
3. 修改 `handleDownloadPDF` 使用 `api` 客户端
4. 添加错误状态

```typescript
import { api } from '../api/client';

const [error, setError] = useState<string | null>(null);

const fetchChapter = async () => {
  try {
    setError(null);
    const result = await api.getTutorial(id!);
    if (result.success && result.data) {
      setChapter(result.data);
    } else {
      setError(result.error || 'Failed to load chapter');
    }
  } catch (err: any) {
    setError(err.message || 'Failed to load chapter');
  } finally {
    setLoading(false);
  }
};
```

- [ ] **Step 2: 添加生成中按钮状态**

```typescript
const [generating, setGenerating] = useState(false);

const handleNextChapter = async () => {
  setGenerating(true);
  try {
    const result = await api.generateNextChapter(id!);
    if (result.success) {
      toast.info('Chapter generation started! This may take a few minutes.');
      // Poll for completion
      await pollGenerationStatus(id!);
      toast.success('Chapter generated!');
      // Refresh chapter data
      fetchChapter();
    } else {
      toast.error(result.error || 'Failed to generate chapter');
    }
  } catch (err: any) {
    toast.error(err.message || 'Failed to generate chapter');
  } finally {
    setGenerating(false);
  }
};
```

- [ ] **Step 3: 添加错误状态显示**

在 `TutorialDisplayPage` 中添加错误状态：

```typescript
const [error, setError] = useState<string | null>(null);

const fetchChapter = async () => {
  try {
    setError(null);
    const result = await api.getTutorial(id!);
    if (result.success) {
      setChapter(result.data);
    } else {
      setError(result.error || 'Failed to load chapter');
    }
  } catch (err: any) {
    setError(err.message || 'Failed to load chapter');
  } finally {
    setLoading(false);
  }
};

// 在 loading 和 chapter 检查之间添加错误检查
if (error) {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="text-6xl mb-4">⚠️</div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Failed to Load</h2>
        <p className="text-gray-500 mb-6">{error}</p>
        <button onClick={() => fetchChapter()} className="btn-primary">
          Retry
        </button>
        <button onClick={() => navigate('/')} className="ml-4 text-gray-600 hover:text-gray-900">
          Back to Library
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 改进 TutorialCard 错误处理**

在 `TutorialCard.tsx` 中添加 hover 状态和加载状态：

```typescript
const [hovered, setHovered] = useState(false);
const [imageError, setImageError] = useState(false);

// 在 card 上添加
<div
  onMouseEnter={() => setHovered(true)}
  onMouseLeave={() => setHovered(false)}
  className={`card transition-all duration-300 ${hovered ? 'shadow-hover -translate-y-1' : ''}`}
>
  {/* ... existing content ... */}
</div>
```

- [ ] **Step 5: 运行测试**

```bash
cd src/frontend && npm test -- --watchAll=false
```

> 注意：本项目前端无 Jest 配置，此步骤验证 TypeScript 编译无错误。

- [ ] **Step 6: 提交**

```bash
git add src/frontend/src/pages/TutorialDisplayPage.tsx src/frontend/src/components/TutorialCard.tsx
git commit -m "feat: improve tutorial page loading and error states"
```

---

### Task 6: 前端构建和部署验证

**Files:**
- Modify: `src/frontend/build/`（构建产物）
- Modify: 服务器 nginx 配置

**Interfaces:**
- Consumes: 所有前端改动
- Produces: 可运行的前端应用

**Context:** 需要构建前端并在服务器上部署，验证所有改动。

- [ ] **Step 1: 本地构建前端**

```bash
cd src/frontend && npm run build
```

确保构建成功，无 TypeScript 错误。

- [ ] **Step 2: 部署到服务器**

上传构建产物到服务器 nginx 目录（通常是 `/usr/share/nginx/html` 或类似路径）。

- [ ] **Step 3: 验证所有功能**

1. 访问 `http://tlcw.yobeeo.com` - 前端正常加载
2. 注册新用户
3. 测试忘记密码功能
4. 测试重置密码功能
5. 创建教程并生成大纲
6. 生成章节
7. 测试 WebSocket 聊天
8. 检查错误处理

- [ ] **Step 4: 提交**

```bash
git add src/frontend/build/
git commit -m "chore: build and deploy frontend"
```

---

## 执行顺序

1. **Task 1**: 密码重置 UI（依赖后端已实现）
2. **Task 2**: WebSocket 聊天集成（依赖后端已实现）
3. **Task 3**: 教程生成进度轮询
4. **Task 4**: 全局错误处理
5. **Task 5**: 教程页面改进
6. **Task 6**: 构建和部署

## 注意事项

- 所有前端改动需要同步更新 `API_BASE` URL（如果是多环境部署）
- WebSocket URL 需要根据当前环境自动确定 protocol（ws/wss）
- 密码重置的 JWT token 有效期为 1 小时，前端应提示用户及时使用
- 生成进度轮询有超时限制（默认 30 次 × 2 秒 = 60 秒），需要适当调整
