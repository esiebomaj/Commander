import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getGitHubStatus,
  getGitHubAuthUrl,
  completeGitHubAuth,
  disconnectGitHub,
} from '@/services/api'

export function useGitHubStatus() {
  return useQuery({
    queryKey: ['github', 'status'],
    queryFn: getGitHubStatus,
  })
}

export function useGitHubConnect() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async () => {
      const redirectUri = `${window.location.origin}/integrations?github_callback=true`
      
      // Get the auth URL
      const { auth_url } = await getGitHubAuthUrl(redirectUri)
      
      // Open in new window
      const width = 600
      const height = 700
      const left = window.screenX + (window.outerWidth - width) / 2
      const top = window.screenY + (window.outerHeight - height) / 2
      
      const popup = window.open(
        auth_url,
        'GitHub Auth',
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
          if (event.data.type === 'github_auth_complete') {
            cleanup()
            
            try {
              await completeGitHubAuth(event.data.code, redirectUri, event.data.state)
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
      queryClient.invalidateQueries({ queryKey: ['github', 'status'] })
    },
  })
}

export function useGitHubDisconnect() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: disconnectGitHub,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['github', 'status'] })
    },
  })
}

