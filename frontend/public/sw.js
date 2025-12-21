/**
 * Service Worker for Commander Push Notifications
 * 
 * Handles receiving push notifications and showing them to the user.
 */

// Handle incoming push notifications
self.addEventListener('push', (event) => {
  console.log('[SW] Push received:', event);
  
  let data = {
    title: 'Commander',
    body: 'New notification',
    url: '/',
    icon: '/commander.png',
  };
  
  // Parse the notification data if available
  if (event.data) {
    try {
      data = { ...data, ...event.data.json() };
    } catch (e) {
      console.error('[SW] Error parsing push data:', e);
      data.body = event.data.text();
    }
  }
  
  const options = {
    body: data.body,
    icon: data.icon || '/commander.png',
    badge: '/commander.png',
    tag: data.tag || 'commander-notification',
    data: {
      url: data.url || '/',
    },
    // These options help ensure system-level notification
    requireInteraction: true,  // Keep notification until user interacts
    renotify: true,            // Show notification even if tag matches previous
    // Note: 'silent: false' is default, notifications will make sound if system allows
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event);
  
  event.notification.close();
  
  const urlToOpen = event.notification.data?.url || '/';
  
  // Focus existing window or open new one
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((windowClients) => {
        // Check if there's already a window open
        for (const client of windowClients) {
          if (client.url.includes(self.location.origin)) {
            // Focus and navigate existing window
            client.focus();
            client.navigate(urlToOpen);
            return;
          }
        }
        // No existing window, open a new one
        return clients.openWindow(urlToOpen);
      })
  );
});

// Handle service worker activation
self.addEventListener('activate', (event) => {
  console.log('[SW] Service worker activated');
  event.waitUntil(clients.claim());
});

// Handle service worker installation
self.addEventListener('install', (event) => {
  console.log('[SW] Service worker installed');
  self.skipWaiting();
});

