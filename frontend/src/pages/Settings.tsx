import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { usePushNotifications, isPushSupported } from '@/hooks/usePushNotifications'
import { useTheme, type Theme } from '@/hooks/useTheme'
import { useToast } from '@/components/ui/use-toast'
import { Sun, Moon, Monitor } from 'lucide-react'

export function SettingsPage() {
  const { toast } = useToast()
  const { theme, setTheme, isDark } = useTheme()
  const {
    supported,
    permission,
    isSubscribed,
    subscriptionCount,
    isLoading,
    subscribe,
    unsubscribe,
    sendTestNotification,
    isTestingNotification,
  } = usePushNotifications()
  
  const [isToggling, setIsToggling] = useState(false)
  
  const handleToggleNotifications = async () => {
    setIsToggling(true)
    try {
      if (isSubscribed) {
        await unsubscribe()
        toast({
          title: "Notifications disabled",
          description: "You will no longer receive push notifications.",
        })
      } else {
        await subscribe()
        toast({
          title: "Notifications enabled",
          description: "You will now receive push notifications for new actions.",
        })
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to toggle notifications.",
        variant: "destructive",
      })
    } finally {
      setIsToggling(false)
    }
  }
  
  const handleTestNotification = async () => {
    try {
      const result = await sendTestNotification({
        title: "Test Notification",
        body: "Push notifications are working correctly!",
      })
      toast({
        title: "Test sent",
        description: result.message,
      })
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to send test notification.",
        variant: "destructive",
      })
    }
  }
  
  const getPermissionStatus = () => {
    if (!supported) return { text: "Not supported", color: "text-muted-foreground" }
    if (permission === "denied") return { text: "Blocked", color: "text-red-500" }
    if (permission === "granted") return { text: "Allowed", color: "text-green-500" }
    return { text: "Not requested", color: "text-yellow-500" }
  }
  
  const permissionStatus = getPermissionStatus()
  
  const themeOptions: { value: Theme; label: string; icon: typeof Sun }[] = [
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'dark', label: 'Dark', icon: Moon },
    { value: 'system', label: 'System', icon: Monitor },
  ]
  
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Configure your Commander preferences
        </p>
      </div>
      
      {/* Appearance Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {isDark ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            Appearance
          </CardTitle>
          <CardDescription>
            Customize how Commander looks on your device
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-sm font-medium text-foreground mb-3">Theme</p>
            <div className="flex gap-2">
              {themeOptions.map((option) => {
                const Icon = option.icon
                const isActive = theme === option.value
                return (
                  <button
                    key={option.value}
                    onClick={() => setTheme(option.value)}
                    className={`
                      flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                      ${isActive 
                        ? 'bg-primary text-primary-foreground' 
                        : 'bg-secondary text-secondary-foreground hover:bg-accent'
                      }
                    `}
                  >
                    <Icon className="w-4 h-4" />
                    {option.label}
                  </button>
                )
              })}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {theme === 'system' 
                ? 'Commander will automatically match your system preferences'
                : `Commander is set to ${theme} mode`
              }
            </p>
          </div>
        </CardContent>
      </Card>
      
      {/* Push Notifications Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
              />
            </svg>
            Push Notifications
          </CardTitle>
          <CardDescription>
            Get notified when new actions are proposed that need your review
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Support Status */}
          <div className="flex items-center justify-between py-2 border-b border-border">
            <div>
              <p className="text-sm font-medium text-foreground">Browser Support</p>
              <p className="text-xs text-muted-foreground">
                {supported ? "Your browser supports push notifications" : "Push notifications are not available in this browser"}
              </p>
            </div>
            <span className={`text-sm font-medium ${supported ? 'text-green-500' : 'text-red-500'}`}>
              {supported ? "Supported" : "Not Supported"}
            </span>
          </div>
          
          {/* Permission Status */}
          <div className="flex items-center justify-between py-2 border-b border-border">
            <div>
              <p className="text-sm font-medium text-foreground">Permission Status</p>
              <p className="text-xs text-muted-foreground">
                {permission === "denied" 
                  ? "Notifications are blocked. Please enable them in your browser settings."
                  : permission === "granted"
                  ? "Notifications are allowed"
                  : "Click 'Enable Notifications' to request permission"
                }
              </p>
            </div>
            <span className={`text-sm font-medium ${permissionStatus.color}`}>
              {permissionStatus.text}
            </span>
          </div>
          
          {/* Subscription Status */}
          <div className="flex items-center justify-between py-2 border-b border-border">
            <div>
              <p className="text-sm font-medium text-foreground">Subscription Status</p>
              <p className="text-xs text-muted-foreground">
                {isSubscribed 
                  ? "You are subscribed to push notifications"
                  : "You are not subscribed to push notifications"
                }
              </p>
            </div>
            <span className={`text-sm font-medium ${isSubscribed ? 'text-green-500' : 'text-muted-foreground'}`}>
              {isLoading ? "Loading..." : isSubscribed ? "Active" : "Inactive"}
            </span>
          </div>
          
          {/* Active Subscriptions Count */}
          {subscriptionCount > 0 && (
            <div className="flex items-center justify-between py-2 border-b border-border">
              <div>
                <p className="text-sm font-medium text-foreground">Active Subscriptions</p>
                <p className="text-xs text-muted-foreground">
                  Total number of subscribed devices
                </p>
              </div>
              <span className="text-sm font-medium text-foreground">
                {subscriptionCount}
              </span>
            </div>
          )}
          
          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <Button
              onClick={handleToggleNotifications}
              disabled={!supported || permission === "denied" || isLoading || isToggling}
              variant={isSubscribed ? "outline" : "default"}
            >
              {isToggling ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  {isSubscribed ? "Disabling..." : "Enabling..."}
                </>
              ) : isSubscribed ? (
                "Disable Notifications"
              ) : (
                "Enable Notifications"
              )}
            </Button>
            
            {isSubscribed && (
              <Button
                onClick={handleTestNotification}
                disabled={isTestingNotification}
                variant="outline"
              >
                {isTestingNotification ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Sending...
                  </>
                ) : (
                  "Send Test Notification"
                )}
              </Button>
            )}
          </div>
          
          {/* Help text for blocked notifications */}
          {permission === "denied" && (
            <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
              <p className="text-sm text-amber-600 dark:text-amber-400">
                <strong>Notifications are blocked.</strong> To enable them:
              </p>
              <ol className="text-sm text-amber-600/80 dark:text-amber-400/80 mt-2 list-decimal list-inside space-y-1">
                <li>Click the lock icon in your browser's address bar</li>
                <li>Find "Notifications" and change it to "Allow"</li>
                <li>Refresh this page</li>
              </ol>
            </div>
          )}
          
          {/* System notification tip */}
          {isSubscribed && (
            <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
              <p className="text-sm text-blue-600 dark:text-blue-400">
                <strong>Not seeing system notifications?</strong> Check your OS settings:
              </p>
              <ul className="text-sm text-blue-600/80 dark:text-blue-400/80 mt-2 list-disc list-inside space-y-1">
                <li><strong>macOS:</strong> System Settings → Notifications → Find your browser → Enable notifications and set to "Banners" or "Alerts"</li>
                <li><strong>Windows:</strong> Settings → System → Notifications → Ensure your browser is enabled</li>
                <li><strong>Tip:</strong> Close or minimize this tab, then send a test notification</li>
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

