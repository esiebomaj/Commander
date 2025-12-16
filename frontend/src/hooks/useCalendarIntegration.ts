import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getCalendarStatus,
  getCalendarAuthUrl,
  completeCalendarAuth,
  disconnectCalendar,
} from '@/services/api'

export function useCalendarStatus() {
  return useQuery({
    queryKey: ['calendar', 'status'],
    queryFn: getCalendarStatus,
  })
}

export function useCalendarConnect() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async () => {
      // Get the auth URL
      const { auth_url } = await getCalendarAuthUrl(
        `${window.location.origin}/integrations?calendar_callback=true`
      )
      
      // Open in new window
      const width = 600
      const height = 700
      const left = window.screenX + (window.outerWidth - width) / 2
      const top = window.screenY + (window.outerHeight - height) / 2
      
      const popup = window.open(
        auth_url,
        'Calendar Auth',
        `width=${width},height=${height},left=${left},top=${top}`
      )
      
      // Wait for the OAuth callback
      return new Promise<void>((resolve, reject) => {
        let checkClosed: ReturnType<typeof setInterval>
        
        const cleanup = () => {
          clearInterval(checkClosed)
          window.removeEventListener('message', handleMessage)
        }
        
        const handleMessage = async (event: MessageEvent) => {
          if (event.data.type === 'calendar_auth_complete') {
            cleanup()
            
            try {
              await completeCalendarAuth(event.data.code, event.data.state)
              resolve()
            } catch (error) {
              reject(error)
            } finally {
              popup?.close()
            }
          }
        }
        
        window.addEventListener('message', handleMessage)
        
        // Check if popup was closed without completing auth
        checkClosed = setInterval(() => {
          if (popup?.closed) {
            cleanup()
            reject(new Error('Authentication window was closed'))
          }
        }, 1000)
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar', 'status'] })
    },
  })
}

export function useCalendarDisconnect() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: disconnectCalendar,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calendar', 'status'] })
    },
  })
}
