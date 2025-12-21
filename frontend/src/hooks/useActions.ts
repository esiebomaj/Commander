import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getActions, approveAction, skipAction, updateAction } from '@/services/api'

export function useActions(status?: string) {
  return useQuery({
    queryKey: ['actions', status || 'all'],
    queryFn: () => getActions(status),
  })
}

export function useApproveAction() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (actionId: number) => approveAction(actionId),
    onSuccess: () => {
      // Invalidate all action queries to refresh the list
      queryClient.invalidateQueries({ queryKey: ['actions'] })
    },
  })
}

export function useSkipAction() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (actionId: number) => skipAction(actionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] })
    },
  })
}

export function useUpdateAction() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ actionId, payload }: { actionId: number; payload: Record<string, any> }) =>
      updateAction(actionId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] })
    },
  })
}
