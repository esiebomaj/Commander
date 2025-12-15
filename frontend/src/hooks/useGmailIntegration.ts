import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getGmailStatus,
  getGmailAuthUrl,
  completeGmailAuth,
  disconnectGmail,
  syncGmail,
  processNewGmailEmails,
} from '@/services/api'

export function useGmailStatus() {
  return useQuery({
    queryKey: ['gmail', 'status'],
    queryFn: getGmailStatus,
  })
}

export function useGmailConnect() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async () => {
      // Get the auth URL
      const { auth_url } = await getGmailAuthUrl(
        `${window.location.origin}/integrations?gmail_callback=true`
      )
      
      // Open in new window
      const width = 600
      const height = 700
      const left = window.screenX + (window.outerWidth - width) / 2
      const top = window.screenY + (window.outerHeight - height) / 2
      
      const popup = window.open(
        auth_url,
        'Gmail Auth',
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
          if (event.data.type === 'gmail_auth_complete') {
            cleanup()
            
            try {
              await completeGmailAuth(event.data.code, event.data.state)
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
      queryClient.invalidateQueries({ queryKey: ['gmail', 'status'] })
    },
  })
}

export function useGmailDisconnect() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: disconnectGmail,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gmail', 'status'] })
    },
  })
}

export function useGmailSync() {
  return useMutation({
    mutationFn: (maxResults: number = 20) => syncGmail(maxResults),
  })
}

export function useGmailProcessNew() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: processNewGmailEmails,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] })
    },
  })
}
