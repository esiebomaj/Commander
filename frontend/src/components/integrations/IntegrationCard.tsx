import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Mail, MessageSquare, Calendar, CheckCircle2, Circle, FileText } from 'lucide-react'

interface IntegrationCardProps {
  name: string
  description: string
  connected: boolean
  email?: string
  extraInfo?: string
  onConnect?: () => void
  onDisconnect?: () => void
  onSync?: () => void
  loading?: boolean
}

const integrationConfig: Record<string, { icon: typeof Mail; color: string; bg: string }> = {
  Gmail: { icon: Mail, color: 'text-red-600', bg: 'bg-red-50' },
  Slack: { icon: MessageSquare, color: 'text-purple-600', bg: 'bg-purple-50' },
  Calendar: { icon: Calendar, color: 'text-blue-600', bg: 'bg-blue-50' },
  Drive: { icon: FileText, color: 'text-green-600', bg: 'bg-green-50' },
}

export function IntegrationCard({
  name,
  description,
  connected,
  email,
  extraInfo,
  onConnect,
  onDisconnect,
  onSync,
  loading,
}: IntegrationCardProps) {
  const config = integrationConfig[name] || { icon: Mail, color: 'text-gray-600', bg: 'bg-gray-50' }
  const Icon = config.icon
  
  return (
    <Card className="p-5 hover:border-gray-300 transition-colors">
      <div className="flex items-start gap-4">
        <div className={`w-11 h-11 rounded-xl ${config.bg} flex items-center justify-center`}>
          <Icon className={`h-5 w-5 ${config.color}`} />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-gray-900">{name}</h3>
            {connected ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600">
                <CheckCircle2 className="h-3 w-3" />
                Connected
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-gray-400">
                <Circle className="h-3 w-3" />
                Not connected
              </span>
            )}
          </div>
          
          <p className="text-sm text-gray-500 mt-0.5">{description}</p>
          
          {connected && email && (
            <p className="text-sm text-gray-600 mt-2 font-medium">{email}</p>
          )}
          
          {connected && extraInfo && (
            <p className="text-xs text-gray-500 mt-1">{extraInfo}</p>
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
                {onDisconnect && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onDisconnect}
                    disabled={loading}
                    className="h-8 text-sm text-red-600 hover:text-red-700 hover:bg-red-50"
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
                  className="h-8 text-sm bg-gray-900 hover:bg-gray-800"
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
