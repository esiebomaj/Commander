import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getVapidPublicKey,
  subscribeToPush,
  unsubscribeFromPush,
  sendTestNotification,
  getPushStatus,
} from '@/services/api'

/**
 * Check if push notifications are supported in the current browser
 */
export function isPushSupported(): boolean {
  return (
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  )
}

/**
 * Convert a base64 URL-safe string to a Uint8Array for the applicationServerKey
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/')
  
  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  
  return outputArray as Uint8Array<ArrayBuffer>
}

/**
 * Hook to check push notification support status
 */
export function usePushSupport() {
  const [supported, setSupported] = useState(false)
  const [permission, setPermission] = useState<NotificationPermission>('default')
  
  useEffect(() => {
    setSupported(isPushSupported())
    if ('Notification' in window) {
      setPermission(Notification.permission)
    }
  }, [])
  
  return { supported, permission }
}

/**
 * Hook to get push notification status from backend
 */
export function usePushStatus() {
  return useQuery({
    queryKey: ['push', 'status'],
    queryFn: getPushStatus,
    // Refetch when window gains focus in case user changed subscription elsewhere
    refetchOnWindowFocus: true,
  })
}

/**
 * Hook to manage push notification subscriptions
 */
export function usePushSubscription() {
  const queryClient = useQueryClient()
  const [isSubscribed, setIsSubscribed] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  
  // Check current subscription status on mount
  useEffect(() => {
    const checkSubscription = async () => {
      if (!isPushSupported()) {
        setIsLoading(false)
        return
      }
      
      try {
        const registration = await navigator.serviceWorker.ready
        const subscription = await registration.pushManager.getSubscription()
        setIsSubscribed(!!subscription)
      } catch (error) {
        console.error('Error checking push subscription:', error)
      } finally {
        setIsLoading(false)
      }
    }
    
    checkSubscription()
  }, [])
  
  const subscribe = useCallback(async () => {
    if (!isPushSupported()) {
      throw new Error('Push notifications are not supported in this browser')
    }
    
    // Request notification permission
    const permission = await Notification.requestPermission()
    if (permission !== 'granted') {
      throw new Error('Notification permission denied')
    }
    
    // Get VAPID public key from backend
    const { public_key } = await getVapidPublicKey()
    
    // Get service worker registration
    const registration = await navigator.serviceWorker.ready
    
    // Subscribe to push
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(public_key),
    })
    
    // Send subscription to backend
    const subscriptionJSON = subscription.toJSON()
    await subscribeToPush({
      endpoint: subscriptionJSON.endpoint!,
      keys: subscriptionJSON.keys as Record<string, string>,
    })
    
    setIsSubscribed(true)
    queryClient.invalidateQueries({ queryKey: ['push', 'status'] })
    
    return subscription
  }, [queryClient])
  
  const unsubscribe = useCallback(async () => {
    if (!isPushSupported()) {
      return
    }
    
    try {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      
      if (subscription) {
        // Unsubscribe from push service
        await subscription.unsubscribe()
        
        // Remove from backend
        await unsubscribeFromPush(subscription.endpoint)
      }
      
      setIsSubscribed(false)
      queryClient.invalidateQueries({ queryKey: ['push', 'status'] })
    } catch (error) {
      console.error('Error unsubscribing from push:', error)
      throw error
    }
  }, [queryClient])
  
  return {
    isSubscribed,
    isLoading,
    subscribe,
    unsubscribe,
  }
}

/**
 * Hook to send test notifications
 */
export function useTestNotification() {
  return useMutation({
    mutationFn: (params?: { title?: string; body?: string }) => 
      sendTestNotification(params?.title, params?.body),
  })
}

/**
 * Combined hook for all push notification functionality
 */
export function usePushNotifications() {
  const { supported, permission } = usePushSupport()
  const { data: status, isLoading: statusLoading } = usePushStatus()
  const { isSubscribed, isLoading: subscriptionLoading, subscribe, unsubscribe } = usePushSubscription()
  const testNotificationMutation = useTestNotification()
  
  return {
    // Support info
    supported,
    permission,
    
    // Status
    isSubscribed,
    subscriptionCount: status?.subscription_count ?? 0,
    
    // Loading states
    isLoading: statusLoading || subscriptionLoading,
    
    // Actions
    subscribe,
    unsubscribe,
    sendTestNotification: testNotificationMutation.mutateAsync,
    isTestingNotification: testNotificationMutation.isPending,
  }
}

