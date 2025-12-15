import { useEffect } from 'react'
import { IntegrationCard } from '@/components/integrations/IntegrationCard'
import {
  useGmailStatus,
  useGmailConnect,
  useGmailDisconnect,
  useGmailSync,
} from '@/hooks/useGmailIntegration'
import { useToast } from '@/components/ui/use-toast'
import { useSearchParams } from 'react-router-dom'

export function IntegrationsPage() {
  const [searchParams] = useSearchParams()
  const { toast } = useToast()
  
  const { data: gmailStatus, isLoading } = useGmailStatus()
  const connectMutation = useGmailConnect()
  const disconnectMutation = useGmailDisconnect()
  const syncMutation = useGmailSync()
  
  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')
    const isCallback = searchParams.get('gmail_callback')
    
    if (code && isCallback) {
      console.log('code', code);
      console.log('state', state);
      console.log('isCallback', isCallback);
      console.log('window.opener', window.opener);
      console.log('window.location.origin', window.location.origin);

      if (window.opener) {
        window.opener.postMessage(
          { type: 'gmail_auth_complete', code, state },
          window.location.origin
        )
        window.close()
      }
    }
  }, [searchParams])
  
  const handleConnect = async () => {
    try {
      await connectMutation.mutateAsync()
      toast({
        title: "Connected",
        description: "Gmail integration is now connected.",
      })
    } catch (error) {
      toast({
        title: "Connection failed",
        description: error instanceof Error ? error.message : "Failed to connect Gmail.",
        variant: "destructive",
      })
    }
  }
  
  const handleDisconnect = async () => {
    try {
      await disconnectMutation.mutateAsync()
      toast({
        title: "Disconnected",
        description: "Gmail integration has been disconnected.",
      })
    } catch {
      toast({
        title: "Error",
        description: "Failed to disconnect Gmail.",
        variant: "destructive",
      })
    }
  }
  
  const handleSync = async () => {
    try {
      const result = await syncMutation.mutateAsync(20)
      toast({
        title: "Sync complete",
        description: result.message,
      })
    } catch {
      toast({
        title: "Sync failed",
        description: "Failed to sync Gmail.",
        variant: "destructive",
      })
    }
  }
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin" />
      </div>
    )
  }
  
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Integrations</h1>
        <p className="text-sm text-gray-500 mt-1">
          Connect your accounts to automate your workflow
        </p>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2">
        <IntegrationCard
          name="Gmail"
          description="Read and send emails automatically"
          connected={gmailStatus?.connected || false}
          email={gmailStatus?.email}
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
          onSync={handleSync}
          loading={
            connectMutation.isPending ||
            disconnectMutation.isPending ||
            syncMutation.isPending
          }
        />
        
        <IntegrationCard
          name="Slack"
          description="Send and receive Slack messages"
          connected={false}
          onConnect={() => toast({
            title: "Coming soon",
            description: "Slack integration is not yet available.",
          })}
        />
      </div>
    </div>
  )
}
