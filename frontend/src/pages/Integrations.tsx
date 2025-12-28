import { useEffect } from 'react'
import { IntegrationCard } from '@/components/integrations/IntegrationCard'
import {
  useGmailStatus,
  useGmailConnect,
  useGmailDisconnect,
  useGmailSync,
  useGmailWebhookSetup,
} from '@/hooks/useGmailIntegration'
import {
  useCalendarStatus,
  useCalendarConnect,
  useCalendarDisconnect,
} from '@/hooks/useCalendarIntegration'
import {
  useDriveStatus,
  useDriveConnect,
  useDriveDisconnect,
  useDriveSync,
  useDriveWebhookSetup,
} from '@/hooks/useDriveIntegration'
import {
  useGitHubStatus,
  useGitHubConnect,
  useGitHubDisconnect,
} from '@/hooks/useGithubIntegration'
import {
  useSlackStatus,
  useSlackConnect,
  useSlackDisconnect,
} from '@/hooks/useSlackIntegration'
import { useToast } from '@/components/ui/use-toast'
import { useSearchParams } from 'react-router-dom'

export function IntegrationsPage() {
  const [searchParams] = useSearchParams()
  const { toast } = useToast()
  
  // Gmail hooks
  const { data: gmailStatus, isLoading: gmailLoading } = useGmailStatus()
  const gmailConnectMutation = useGmailConnect()
  const gmailDisconnectMutation = useGmailDisconnect()
  const gmailSyncMutation = useGmailSync()
  const gmailWebhookSetupMutation = useGmailWebhookSetup()
  
  // Calendar hooks
  const { data: calendarStatus, isLoading: calendarLoading } = useCalendarStatus()
  const calendarConnectMutation = useCalendarConnect()
  const calendarDisconnectMutation = useCalendarDisconnect()
  
  // Drive hooks
  const { data: driveStatus, isLoading: driveLoading } = useDriveStatus()
  const driveConnectMutation = useDriveConnect()
  const driveDisconnectMutation = useDriveDisconnect()
  const driveSyncMutation = useDriveSync()
  const driveWebhookSetupMutation = useDriveWebhookSetup()
  
  // GitHub hooks
  const { data: githubStatus, isLoading: githubLoading } = useGitHubStatus()
  const githubConnectMutation = useGitHubConnect()
  const githubDisconnectMutation = useGitHubDisconnect()
  
  // Slack hooks
  const { data: slackStatus, isLoading: slackLoading } = useSlackStatus()
  const slackConnectMutation = useSlackConnect()
  const slackDisconnectMutation = useSlackDisconnect()
  
  // Handle OAuth callbacks
  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')
    const isGmailCallback = searchParams.get('gmail_callback')
    const isCalendarCallback = searchParams.get('calendar_callback')
    
    if (code && isGmailCallback) {
      console.log('Gmail OAuth callback:', { code, state })
      if (window.opener) {
        window.opener.postMessage(
          { type: 'gmail_auth_complete', code, state },
          window.location.origin
        )
        window.close()
      }
    }
    
    if (code && isCalendarCallback) {
      console.log('Calendar OAuth callback:', { code, state })
      if (window.opener) {
        window.opener.postMessage(
          { type: 'calendar_auth_complete', code, state },
          window.location.origin
        )
        window.close()
      }
    }
    
    const isDriveCallback = searchParams.get('drive_callback')
    if (code && isDriveCallback) {
      console.log('Drive OAuth callback:', { code, state })
      if (window.opener) {
        window.opener.postMessage(
          { type: 'drive_auth_complete', code, state },
          window.location.origin
        )
        window.close()
      }
    }
    
    const isGitHubCallback = searchParams.get('github_callback')
    if (code && isGitHubCallback) {
      console.log('GitHub OAuth callback:', { code, state })
      if (window.opener) {
        window.opener.postMessage(
          { type: 'github_auth_complete', code, state },
          window.location.origin
        )
        window.close()
      }
    }
    
    const isSlackCallback = searchParams.get('slack_callback')
    if (code && isSlackCallback) {
      console.log('Slack OAuth callback:', { code, state })
      if (window.opener) {
        window.opener.postMessage(
          { type: 'slack_auth_complete', code, state },
          window.location.origin
        )
        window.close()
      }
    }
  }, [searchParams])
  
  // Gmail handlers
  const handleGmailConnect = async () => {
    try {
      await gmailConnectMutation.mutateAsync()
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
  
  const handleGmailDisconnect = async () => {
    try {
      await gmailDisconnectMutation.mutateAsync()
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
  
  const handleGmailSync = async () => {
    try {
      const result = await gmailSyncMutation.mutateAsync(20)
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
  
  const handleGmailWebhookSetup = async () => {
    try {
      const result = await gmailWebhookSetupMutation.mutateAsync()
      if (result.success) {
        toast({
          title: "Notifications enabled",
          description: "Gmail push notifications are now active.",
        })
      } else {
        toast({
          title: "Setup failed",
          description: result.message,
          variant: "destructive",
        })
      }
    } catch {
      toast({
        title: "Setup failed",
        description: "Failed to enable Gmail notifications.",
        variant: "destructive",
      })
    }
  }
  
  // Calendar handlers
  const handleCalendarConnect = async () => {
    try {
      await calendarConnectMutation.mutateAsync()
      toast({
        title: "Connected",
        description: "Google Calendar integration is now connected.",
      })
    } catch (error) {
      toast({
        title: "Connection failed",
        description: error instanceof Error ? error.message : "Failed to connect Google Calendar.",
        variant: "destructive",
      })
    }
  }
  
  const handleCalendarDisconnect = async () => {
    try {
      await calendarDisconnectMutation.mutateAsync()
      toast({
        title: "Disconnected",
        description: "Google Calendar integration has been disconnected.",
      })
    } catch {
      toast({
        title: "Error",
        description: "Failed to disconnect Google Calendar.",
        variant: "destructive",
      })
    }
  }
  
  // Drive handlers
  const handleDriveConnect = async () => {
    try {
      await driveConnectMutation.mutateAsync()
      toast({
        title: "Connected",
        description: "Google Drive integration is now connected.",
      })
    } catch (error) {
      toast({
        title: "Connection failed",
        description: error instanceof Error ? error.message : "Failed to connect Google Drive.",
        variant: "destructive",
      })
    }
  }
  
  const handleDriveDisconnect = async () => {
    try {
      await driveDisconnectMutation.mutateAsync()
      toast({
        title: "Disconnected",
        description: "Google Drive integration has been disconnected.",
      })
    } catch {
      toast({
        title: "Error",
        description: "Failed to disconnect Google Drive.",
        variant: "destructive",
      })
    }
  }
  
  const handleDriveSync = async () => {
    try {
      const result = await driveSyncMutation.mutateAsync({})
      toast({
        title: "Sync complete",
        description: `Processed ${result.processed_count} transcript(s).`,
      })
    } catch {
      toast({
        title: "Sync failed",
        description: "Failed to sync meeting transcripts.",
        variant: "destructive",
      })
    }
  }
  
  const handleDriveWebhookSetup = async () => {
    try {
      const result = await driveWebhookSetupMutation.mutateAsync()
      if (result.success) {
        toast({
          title: "Notifications enabled",
          description: "Drive push notifications are now active.",
        })
      } else {
        toast({
          title: "Setup failed",
          description: result.message,
          variant: "destructive",
        })
      }
    } catch {
      toast({
        title: "Setup failed",
        description: "Failed to enable Drive notifications.",
        variant: "destructive",
      })
    }
  }
  
  // GitHub handlers
  const handleGitHubConnect = async () => {
    try {
      await githubConnectMutation.mutateAsync()
      toast({
        title: "Connected",
        description: "GitHub integration is now connected.",
      })
    } catch (error) {
      toast({
        title: "Connection failed",
        description: error instanceof Error ? error.message : "Failed to connect GitHub.",
        variant: "destructive",
      })
    }
  }
  
  const handleGitHubDisconnect = async () => {
    try {
      await githubDisconnectMutation.mutateAsync()
      toast({
        title: "Disconnected",
        description: "GitHub integration has been disconnected.",
      })
    } catch {
      toast({
        title: "Error",
        description: "Failed to disconnect GitHub.",
        variant: "destructive",
      })
    }
  }
  
  // Slack handlers
  const handleSlackConnect = async () => {
    try {
      await slackConnectMutation.mutateAsync()
      toast({
        title: "Connected",
        description: "Slack workspace is now connected.",
      })
    } catch (error) {
      toast({
        title: "Connection failed",
        description: error instanceof Error ? error.message : "Failed to connect Slack.",
        variant: "destructive",
      })
    }
  }
  
  const handleSlackDisconnect = async () => {
    try {
      await slackDisconnectMutation.mutateAsync()
      toast({
        title: "Disconnected",
        description: "Slack workspace has been disconnected.",
      })
    } catch {
      toast({
        title: "Error",
        description: "Failed to disconnect Slack.",
        variant: "destructive",
      })
    }
  }
  
  if (gmailLoading || calendarLoading || driveLoading || githubLoading || slackLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-muted border-t-foreground rounded-full animate-spin" />
      </div>
    )
  }
  
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Integrations</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Connect your accounts to automate your workflow
        </p>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2">
        <IntegrationCard
          name="Gmail"
          description="Read and send emails automatically"
          connected={gmailStatus?.connected || false}
          email={gmailStatus?.email}
          webhookActive={gmailStatus?.webhook_active}
          onConnect={handleGmailConnect}
          onDisconnect={handleGmailDisconnect}
          onSync={handleGmailSync}
          onSetupWebhook={handleGmailWebhookSetup}
          loading={
            gmailConnectMutation.isPending ||
            gmailDisconnectMutation.isPending ||
            gmailSyncMutation.isPending
          }
          webhookLoading={gmailWebhookSetupMutation.isPending}
        />
        
        <IntegrationCard
          name="Calendar"
          description="Schedule meetings on Google Calendar"
          connected={calendarStatus?.connected || false}
          email={calendarStatus?.email}
          onConnect={handleCalendarConnect}
          onDisconnect={handleCalendarDisconnect}
          loading={
            calendarConnectMutation.isPending ||
            calendarDisconnectMutation.isPending
          }
        />
        
        <IntegrationCard
          name="Drive"
          description="Fetch and summarize meeting transcripts"
          connected={driveStatus?.connected || false}
          email={driveStatus?.email}
          webhookActive={driveStatus?.webhook_active}
          onConnect={handleDriveConnect}
          onDisconnect={handleDriveDisconnect}
          onSync={handleDriveSync}
          onSetupWebhook={handleDriveWebhookSetup}
          loading={
            driveConnectMutation.isPending ||
            driveDisconnectMutation.isPending ||
            driveSyncMutation.isPending
          }
          webhookLoading={driveWebhookSetupMutation.isPending}
        />
        
        <IntegrationCard
          name="GitHub"
          description="Manage repositories, issues, and pull requests"
          connected={githubStatus?.connected || false}
          email={githubStatus?.username ? `@${githubStatus.username}` : undefined}
          onConnect={handleGitHubConnect}
          onDisconnect={handleGitHubDisconnect}
          loading={
            githubConnectMutation.isPending ||
            githubDisconnectMutation.isPending
          }
        />
        
        <IntegrationCard
          name="Slack"
          description="Send and receive Slack messages"
          connected={slackStatus?.connected || false}
          email={slackStatus?.team_name}
          onConnect={handleSlackConnect}
          onDisconnect={handleSlackDisconnect}
          loading={
            slackConnectMutation.isPending ||
            slackDisconnectMutation.isPending
          }
        />
      </div>
    </div>
  )
}
