/** React application entry point. */

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { ToastProvider } from './contexts/ToastContext';
import './index.css';
import * as serviceWorkerRegistration from './serviceWorkerRegistration';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <ToastProvider>
      <App />
    </ToastProvider>
  </React.StrictMode>
);

// Register service worker for PWA offline support
// DISABLED TEMPORARILY: SW was caching stale API responses causing login redirect loop
// serviceWorkerRegistration.register({
//   onUpdate: () => {
//     console.log('New version available, refresh to update.');
//   },
// });
