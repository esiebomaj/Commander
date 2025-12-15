import { useState, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ActionFilters } from '@/components/actions/ActionFilters'
import { ActionTable } from '@/components/actions/ActionTable'
import { ActionEditModal } from '@/components/actions/ActionEditModal'
import { useActions, useApproveAction, useSkipAction } from '@/hooks/useActions'
import type { ProposedAction } from '@/services/types'
import { useToast } from '@/components/ui/use-toast'

export function ActionsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [statusFilter, setStatusFilter] = useState('pending')
  const [sourceFilter, setSourceFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')
  
  const { toast } = useToast()
  
  const { data: actions, isLoading, error } = useActions()
  
  const approveMutation = useApproveAction()
  const skipMutation = useSkipAction()
  
  // Derive editing action from URL
  const editId = searchParams.get('edit')
  const editingAction = editId && actions 
    ? actions.find(a => a.id === parseInt(editId)) ?? null 
    : null
  
  const filteredActions = useMemo(() => {
    if (!actions) return []
    
    return actions.filter((action) => {
      const statusMatch = statusFilter === 'all' || action.status === statusFilter
      const sourceMatch = sourceFilter === 'all' || action.source_type === sourceFilter
      const typeMatch = typeFilter === 'all' || action.type === typeFilter
      return statusMatch && sourceMatch && typeMatch
    })
  }, [actions, statusFilter, sourceFilter, typeFilter])
  
  const handleEdit = (action: ProposedAction) => {
    searchParams.set('edit', action.id.toString())
    setSearchParams(searchParams)
  }
  
  const handleApprove = async (actionId: number) => {
    try {
      await approveMutation.mutateAsync(actionId)
      toast({
        title: "Action approved",
        description: "The action has been executed successfully.",
      })
    } catch {
      toast({
        title: "Error",
        description: "Failed to approve action.",
        variant: "destructive",
      })
    }
  }
  
  const handleSkip = async (actionId: number) => {
    try {
      await skipMutation.mutateAsync(actionId)
      toast({
        title: "Action skipped",
        description: "The action has been skipped.",
      })
    } catch {
      toast({
        title: "Error",
        description: "Failed to skip action.",
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
  
  if (error) {
    return (
      <div className="text-center py-16">
        <p className="text-red-600">Error loading actions. Please try again.</p>
      </div>
    )
  }
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Actions</h1>
          <p className="text-sm text-gray-500 mt-1">
            Review and manage your automated actions
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-500">{filteredActions.length} actions</span>
        </div>
      </div>
      
      <ActionFilters
        statusFilter={statusFilter}
        sourceFilter={sourceFilter}
        typeFilter={typeFilter}
        onStatusChange={setStatusFilter}
        onSourceChange={setSourceFilter}
        onTypeChange={setTypeFilter}
      />
      
      <ActionTable
        actions={filteredActions}
        onEdit={handleEdit}
        onApprove={handleApprove}
        onSkip={handleSkip}
      />
      
      <ActionEditModal
        action={editingAction}
        open={!!editingAction}
        onClose={() => {
          searchParams.delete('edit')
          setSearchParams(searchParams)
        }}
      />
    </div>
  )
}
