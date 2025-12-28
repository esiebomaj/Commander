import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getSlackStatus,
  getSlackAuthUrl,
  completeSlackAuth,
  disconnectSlack,
} from '@/services/api'

export function useSlackStatus() {
  return useQuery({
    queryKey: ['slack', 'status'],
    queryFn: getSlackStatus,
  })
}

export function useSlackConnect() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async () => {
      const redirectUri = `${window.location.origin}/integrations?slack_callback=true`
      
      // Get the auth URL
      const { auth_url } = await getSlackAuthUrl(redirectUri)
      
      // Open in new window
      const width = 600
      const height = 700
      const left = window.screenX + (window.outerWidth - width) / 2
      const top = window.screenY + (window.outerHeight - height) / 2
      
      const popup = window.open(
        auth_url,
        'Slack Auth',
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
          if (event.data.type === 'slack_auth_complete') {
            cleanup()
            
            try {
              await completeSlackAuth(event.data.code, redirectUri, event.data.state)
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
      queryClient.invalidateQueries({ queryKey: ['slack', 'status'] })
    },
  })
}

export function useSlackDisconnect() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: disconnectSlack,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slack', 'status'] })
    },
  })
}

