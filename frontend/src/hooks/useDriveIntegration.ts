import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getDriveStatus,
  getDriveAuthUrl,
  completeDriveAuth,
  disconnectDrive,
  processRecentTranscripts,
} from '@/services/api'

export function useDriveStatus() {
  return useQuery({
    queryKey: ['drive', 'status'],
    queryFn: getDriveStatus,
  })
}

export function useDriveConnect() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async () => {
      // Get the auth URL
      const { auth_url } = await getDriveAuthUrl(
        `${window.location.origin}/integrations?drive_callback=true`
      )
      
      // Open in new window
      const width = 600
      const height = 700
      const left = window.screenX + (window.outerWidth - width) / 2
      const top = window.screenY + (window.outerHeight - height) / 2
      
      const popup = window.open(
        auth_url,
        'Drive Auth',
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
          if (event.data.type === 'drive_auth_complete') {
            cleanup()
            
            try {
              await completeDriveAuth(event.data.code, event.data.state)
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
      queryClient.invalidateQueries({ queryKey: ['drive', 'status'] })
    },
  })
}

export function useDriveDisconnect() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: disconnectDrive,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['drive', 'status'] })
    },
  })
}

export function useDriveSync() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ maxFiles = 5, sinceHours = 24 }: { maxFiles?: number; sinceHours?: number } = {}) => 
      processRecentTranscripts(maxFiles, sinceHours),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] })
    },
  })
}

