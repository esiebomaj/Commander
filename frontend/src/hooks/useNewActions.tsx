import { useEffect, useRef, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getActions } from '@/services/api'
import type { ProposedAction } from '@/services/types'
import { useToast } from '@/components/ui/use-toast'
import { useApproveAction, useSkipAction } from '@/hooks/useActions'
import { usePushSubscription } from '@/hooks/usePushNotifications'
import { getActionLabel, getPayloadDisplay, truncate } from '@/lib/actions'
import { Check, X, Eye } from 'lucide-react'

export function useNewActions() {
  const { toast, dismiss } = useToast()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const seenActionIds = useRef(new Set<number>())
  const isFirstLoad = useRef(true)
  
  const approveMutation = useApproveAction()
  const skipMutation = useSkipAction()
  
  // Check if push notifications are active
  const { isSubscribed: isPushActive } = usePushSubscription()
  
  // Poll pending actions every 5 seconds, but disable polling if push notifications are active
  const { data: pendingActions } = useQuery({
    queryKey: ['actions', 'pending'],
    queryFn: () => getActions('pending'),
    refetchInterval: isPushActive ? false : 5000,
  })
  
  const handleApprove = useCallback(async (action: ProposedAction, toastId: string) => {
    try {
      await approveMutation.mutateAsync(action.id)
      dismiss(toastId)
    } catch {
      // Error handling is done by the mutation
    }
  }, [approveMutation, dismiss])
  
  const handleSkip = useCallback(async (action: ProposedAction, toastId: string) => {
    try {
      await skipMutation.mutateAsync(action.id)
      dismiss(toastId)
    } catch {
      // Error handling is done by the mutation
    }
  }, [skipMutation, dismiss])
  
  const handleView = useCallback((action: ProposedAction, toastId: string) => {
    dismiss(toastId)
    navigate(`/actions?edit=${action.id}`)
  }, [dismiss, navigate])
  
  const showActionNotification = useCallback((action: ProposedAction) => {
    const actionTypeLabel = getActionLabel(action.type)
    const payloadDisplay = getPayloadDisplay(action.type, action.payload)
    // Generate a predictable toastId based on action id
    const toastId = `action-${action.id}`
    
    toast({
      id: toastId,
      title: `New Action: ${actionTypeLabel}`,
      description: (
        <div className="space-y-1">
          <p className="text-sm font-medium">{payloadDisplay.primary}</p>
          {payloadDisplay.secondary && (
            <p className="text-sm text-muted-foreground">{payloadDisplay.secondary}</p>
          )}
          {payloadDisplay.detail && (
            <p className="text-sm text-muted-foreground line-clamp-2">
              {truncate(payloadDisplay.detail, 60)}
            </p>
          )}
        </div>
      ),
      action: (
        <ActionNotificationButtons
          action={action}
          toastId={toastId}
          onApprove={handleApprove}
          onSkip={handleSkip}
          onView={handleView}
        />
      ),
    })
  }, [toast, handleApprove, handleSkip, handleView])
  
  useEffect(() => {
    if (!pendingActions) return
    
    // On first load, mark all existing actions as seen without showing notifications
    if (isFirstLoad.current) {
      pendingActions.forEach(action => {
        seenActionIds.current.add(action.id)
      })
      isFirstLoad.current = false
      return
    }
    
    // Check for new actions
    const newActions = pendingActions.filter(
      action => !seenActionIds.current.has(action.id)
    )
    
    // If there are new actions, invalidate the main actions list
    if (newActions.length > 0) {
      queryClient.invalidateQueries({ queryKey: ['actions'] })
    }
    
    // Show toast for each new action
    newActions.forEach(action => {
      seenActionIds.current.add(action.id)
      showActionNotification(action)
    })
  }, [pendingActions, showActionNotification, queryClient])
  
  return {
    pendingCount: pendingActions?.length || 0,
  }
}

// Separate component to avoid closure issues with toastId
function ActionNotificationButtons({
  action,
  toastId,
  onApprove,
  onSkip,
  onView,
}: {
  action: ProposedAction
  toastId: string
  onApprove: (action: ProposedAction, toastId: string) => void
  onSkip: (action: ProposedAction, toastId: string) => void
  onView: (action: ProposedAction, toastId: string) => void
}) {
  return (
    <div className="flex gap-1 mt-2">
      <button
        onClick={() => onApprove(action, toastId)}
        className="inline-flex items-center justify-center h-8 w-8 rounded-md bg-green-600 hover:bg-green-700 text-white transition-colors"
        title="Approve"
      >
        <Check className="h-4 w-4" />
      </button>
      <button
        onClick={() => onSkip(action, toastId)}
        className="inline-flex items-center justify-center h-8 w-8 rounded-md bg-gray-200 hover:bg-gray-300 text-gray-700 transition-colors"
        title="Skip"
      >
        <X className="h-4 w-4" />
      </button>
      <button
        onClick={() => onView(action, toastId)}
        className="inline-flex items-center justify-center h-8 px-3 rounded-md bg-gray-900 hover:bg-gray-800 text-white text-sm font-medium transition-colors"
        title="View & Edit"
      >
        <Eye className="h-4 w-4 mr-1" />
        View
      </button>
    </div>
  )
}

