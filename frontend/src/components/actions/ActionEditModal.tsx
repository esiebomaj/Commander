import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import type { ProposedAction } from '@/services/types'
import { useUpdateAction, useApproveAction } from '@/hooks/useActions'
import { useToast } from '@/components/ui/use-toast'
import { getActionLabel, getPayloadDisplay } from '@/lib/actions'
import { Mail, Calendar, FileText, MessageSquare, ChevronDown, ChevronRight } from 'lucide-react'

interface ActionEditModalProps {
  action: ProposedAction | null
  open: boolean
  onClose: () => void
}

const getActionIcon = (type: string) => {
  switch (type) {
    case 'gmail_send_email':
    case 'gmail_create_draft':
      return Mail
    case 'schedule_meeting':
      return Calendar
    case 'create_todo':
      return FileText
    default:
      return MessageSquare
  }
}

export function ActionEditModal({ action, open, onClose }: ActionEditModalProps) {
  const [payloadJson, setPayloadJson] = useState('')
  const [jsonError, setJsonError] = useState('')
  const [sourceInfoOpen, setSourceInfoOpen] = useState(false)
  
  const updateMutation = useUpdateAction()
  const approveMutation = useApproveAction()
  const { toast } = useToast()
  
  useEffect(() => {
    if (action) {
      setPayloadJson(JSON.stringify(action.payload, null, 2))
      setJsonError('')
      setSourceInfoOpen(false)
    }
  }, [action])
  
  const handlePayloadChange = (value: string) => {
    setPayloadJson(value)
    try {
      JSON.parse(value)
      setJsonError('')
    } catch {
      setJsonError('Invalid JSON')
    }
  }
  
  const handleSave = async () => {
    if (!action || jsonError) return
    
    try {
      const payload = JSON.parse(payloadJson)
      await updateMutation.mutateAsync({ actionId: action.id, payload })
      toast({
        title: "Saved",
        description: "Action updated successfully.",
      })
      onClose()
    } catch {
      toast({
        title: "Error",
        description: "Failed to update action.",
        variant: "destructive",
      })
    }
  }
  
  const handleSaveAndApprove = async () => {
    if (!action || jsonError) return
    
    try {
      const payload = JSON.parse(payloadJson)
      await updateMutation.mutateAsync({ actionId: action.id, payload })
      await approveMutation.mutateAsync(action.id)
      toast({
        title: "Approved",
        description: "Action updated and executed.",
      })
      onClose()
    } catch {
      toast({
        title: "Error",
        description: "Failed to update and approve action.",
        variant: "destructive",
      })
    }
  }
  
  if (!action) return null
  
  const Icon = getActionIcon(action.type)
  const payloadDisplay = getPayloadDisplay(action.type, action.payload)
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
              <Icon className="h-5 w-5 text-gray-600" />
            </div>
            <div>
              <DialogDescription className="text-xs text-gray-500">
                {getActionLabel(action.type)}
              </DialogDescription>
              <DialogTitle className="text-lg">{payloadDisplay.primary}</DialogTitle>
              {payloadDisplay.secondary && (
                <p className="text-sm text-gray-500 mt-0.5">{payloadDisplay.secondary}</p>
              )}
            </div>
          </div>
        </DialogHeader>
        
        <div className="space-y-4 py-2">
          {payloadDisplay.detail && (
            <div className="text-sm text-gray-600 bg-gray-50 rounded-lg p-3 whitespace-pre-wrap">
              {payloadDisplay.detail}
            </div>
          )}
          
          {/* Source Info - Collapsible */}
          {(action.sender || action.summary || action.source_type) && (
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <button
                type="button"
                onClick={() => setSourceInfoOpen(!sourceInfoOpen)}
                className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                <span>Source Info</span>
                {sourceInfoOpen ? (
                  <ChevronDown className="h-4 w-4 text-gray-500" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-gray-500" />
                )}
              </button>
              {sourceInfoOpen && (
                <div className="px-3 py-3 border-t border-gray-200 bg-gray-50 space-y-2 text-sm">
                  {action.source_type && (
                    <div>
                      <span className="text-gray-500">Source:</span>{' '}
                      <span className="text-gray-900 capitalize">{action.source_type}</span>
                    </div>
                  )}
                  {action.sender && (
                    <div>
                      <span className="text-gray-500">Sender:</span>{' '}
                      <span className="text-gray-900">{action.sender}</span>
                    </div>
                  )}
                  {action.summary && (
                    <div>
                      <span className="text-gray-500 block mb-1">Summary:</span>
                      <p className="text-gray-700 whitespace-pre-wrap">{action.summary}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1.5 block">
              Payload (JSON)
            </label>
            <Textarea
              value={payloadJson}
              onChange={(e) => handlePayloadChange(e.target.value)}
              className="font-mono text-sm min-h-[200px] bg-gray-50"
              placeholder="{}"
            />
            {jsonError && (
              <p className="text-xs text-red-500 mt-1">{jsonError}</p>
            )}
          </div>
        </div>
        
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button 
            variant="outline"
            onClick={handleSave}
            disabled={!!jsonError || updateMutation.isPending}
          >
            Save
          </Button>
          <Button 
            onClick={handleSaveAndApprove}
            disabled={!!jsonError || updateMutation.isPending || approveMutation.isPending}
            className="bg-gray-900 hover:bg-gray-800"
          >
            Save & Approve
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
