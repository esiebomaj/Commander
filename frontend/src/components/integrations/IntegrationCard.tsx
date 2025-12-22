import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Mail, MessageSquare, Calendar, CheckCircle2, Circle, FileText, BellOff } from 'lucide-react'

interface IntegrationCardProps {
  name: string
  description: string
  connected: boolean
  email?: string
  extraInfo?: string
  webhookActive?: boolean
  onConnect?: () => void
  onDisconnect?: () => void
  onSync?: () => void
  onSetupWebhook?: () => void
  loading?: boolean
  webhookLoading?: boolean
}

const integrationConfig: Record<string, { icon: typeof Mail; color: string; bg: string }> = {
  Gmail: { icon: Mail, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-50 dark:bg-red-950' },
  Slack: { icon: MessageSquare, color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-50 dark:bg-purple-950' },
  Calendar: { icon: Calendar, color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-950' },
  Drive: { icon: FileText, color: 'text-green-600 dark:text-green-400', bg: 'bg-green-50 dark:bg-green-950' },
}

export function IntegrationCard({
  name,
  description,
  connected,
  email,
  extraInfo,
  webhookActive,
  onConnect,
  onDisconnect,
  onSync,
  onSetupWebhook,
  loading,
  webhookLoading,
}: IntegrationCardProps) {
  const config = integrationConfig[name] || { icon: Mail, color: 'text-muted-foreground', bg: 'bg-muted' }
  const Icon = config.icon
  
  return (
    <Card className="p-5 hover:border-muted-foreground/30 transition-colors">
      <div className="flex items-start gap-4">
        <div className={`w-11 h-11 rounded-xl ${config.bg} flex items-center justify-center`}>
          <Icon className={`h-5 w-5 ${config.color}`} />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-foreground">{name}</h3>
            {connected ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="h-3 w-3" />
                Connected
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground">
                <Circle className="h-3 w-3" />
                Not connected
              </span>
            )}
          </div>
          
          <p className="text-sm text-muted-foreground mt-0.5">{description}</p>
          
          {connected && email && (
            <p className="text-sm text-foreground/80 mt-2 font-medium">{email}</p>
          )}
          
          {connected && extraInfo && (
            <p className="text-xs text-muted-foreground mt-1">{extraInfo}</p>
          )}
          
          {/* Webhook status indicator */}
          {connected && webhookActive !== undefined && (
            <div className="flex items-center gap-1.5 mt-2">
              {webhookActive ? null
                : <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600 dark:text-amber-400">
                    <BellOff className="h-3 w-3" />
                    Webhook disabled
                  </span>
                }
            </div>
          )}
          
          <div className="flex items-center gap-2 mt-4">
            {connected ? (
              <>
                {onSync && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onSync}
                    disabled={loading}
                    className="h-8 text-sm"
                  >
                    Sync
                  </Button>
                )}
                {/* Show webhook setup button if webhook is not active */}
                {onSetupWebhook && webhookActive === false && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={onSetupWebhook}
                    disabled={webhookLoading}
                    className="h-8 text-sm"
                  >
                    {webhookLoading ? 'Setting up...' : 'Enable Webhook'}
                  </Button>
                )}
                {onDisconnect && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onDisconnect}
                    disabled={loading}
                    className="h-8 text-sm text-red-600 hover:text-red-700 hover:bg-red-500/10 dark:text-red-400 dark:hover:text-red-300"
                  >
                    Disconnect
                  </Button>
                )}
              </>
            ) : (
              onConnect && (
                <Button
                  size="sm"
                  onClick={onConnect}
                  disabled={loading}
                  className="h-8 text-sm"
                >
                  Connect
                </Button>
              )
            )}
          </div>
        </div>
      </div>
    </Card>
  )
}
