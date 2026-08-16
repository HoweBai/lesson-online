/**
 * This optional code is used to register a service worker.
 * register() is not called by default. This module registers the SW
 * and provides update notifications.
 */

const isLocalhost = Boolean(
  typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' ||
      window.location.hostname === '[::1]' ||
      window.location.hostname.match(/^127(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}$/))
);

export function register(config?: { onSuccess?: () => void; onUpdate?: () => void }) {
  if ('serviceWorker' in navigator) {
    const swUrl = `${process.env.PUBLIC_URL}/service-worker.js`;

    if (isLocalhost) {
      // Check if service worker exists in development
      checkValidServiceWorker(swUrl, config);
      navigator.serviceWorker.ready.then(() => {
        // Service worker registered
      });
    } else {
      // Register in production
      navigator.serviceWorker
        .register(swUrl)
        .then((registration) => {
          registration.onupdatefound = () => {
            const installingWorker = registration.installing;
            if (installingWorker == null) return;
            installingWorker.onstatechange = () => {
              if (installingWorker.state === 'installed') {
                if (navigator.serviceWorker.controller) {
                  config?.onUpdate?.();
                } else {
                  config?.onSuccess?.();
                }
              }
            };
          };
        })
        .catch((error) => {
          console.error('Error during service worker registration:', error);
        });
    }
  }
}

function checkValidServiceWorker(swUrl: string, config?: { onSuccess?: () => void; onUpdate?: () => void }) {
  fetch(swUrl, { headers: { 'Service-Worker': 'script' } })
    .then((response) => {
      // Ensure service worker exists
      const contentType = response.headers.get('content-type');
      if (
        response.status === 404 ||
        (contentType != null && contentType.indexOf('javascript') === -1)
      ) {
        // No service worker found, unregister
        navigator.serviceWorker.ready.then((registration) => {
          registration.unregister();
        });
        return;
      }
    })
    .then(() => import(/* webpackIgnore: true */ swUrl))
    });
}

export function unregister() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => registration.unregister())
      .catch((error) => console.error(error.message));
  }
}
