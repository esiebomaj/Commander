import type { ProposedAction } from '@/services/types'
import { Button } from '@/components/ui/button'
import { Check, X, Pencil, Mail, Calendar, MessageSquare, FileText, Clock, CheckCircle2, XCircle, AlertCircle } from 'lucide-react'
import { format } from 'date-fns'
import { getActionLabel, getPayloadDisplay, truncate } from '@/lib/actions'

interface ActionTableProps {
  actions: ProposedAction[]
  onEdit: (action: ProposedAction) => void
  onApprove: (actionId: number) => void
  onSkip: (actionId: number) => void
}

const getStatusConfig = (status: string) => {
  switch (status) {
    case 'pending':
      return { icon: Clock, color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-950', label: 'Pending' }
    case 'executed':
      return { icon: CheckCircle2, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-950', label: 'Executed' }
    case 'skipped':
      return { icon: XCircle, color: 'text-muted-foreground', bg: 'bg-muted', label: 'Skipped' }
    case 'error':
      return { icon: AlertCircle, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-50 dark:bg-red-950', label: 'Error' }
    default:
      return { icon: Clock, color: 'text-muted-foreground', bg: 'bg-muted', label: status }
  }
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



export function ActionTable({ actions, onEdit, onApprove, onSkip }: ActionTableProps) {
  if (actions.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
          <FileText className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-medium text-foreground mb-1">No actions found</h3>
        <p className="text-sm text-muted-foreground">Actions will appear here when generated</p>
      </div>
    )
  }

  return (
    <div className="bg-card rounded-xl border border-border overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">Action</th>
            <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">Status</th>
            <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">Source</th>
            <th className="text-left text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">Created</th>
            <th className="text-right text-xs font-medium text-muted-foreground uppercase tracking-wider px-4 py-3">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {actions.map((action) => {
            const statusConfig = getStatusConfig(action.status)
            const StatusIcon = statusConfig.icon
            const ActionIcon = getActionIcon(action.type)
            const payloadDisplay = getPayloadDisplay(action.type, action.payload)
            
            return (
              <tr key={action.id} className="hover:bg-muted/50 transition-colors">
                <td className="px-4 py-4">
                  <div className="flex items-start gap-3">
                    <div className="w-9 h-9 rounded-lg bg-muted flex items-center justify-center flex-shrink-0">
                      <ActionIcon className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs text-muted-foreground mb-0.5">
                        {getActionLabel(action.type)}
                      </div>
                      <div className="font-medium text-sm text-foreground truncate max-w-[300px]">
                        {payloadDisplay.primary}
                      </div>
                      {payloadDisplay.secondary && (
                        <div className="text-sm text-muted-foreground truncate max-w-[300px]">
                          {payloadDisplay.secondary}
                        </div>
                      )}
                      {payloadDisplay.detail && (
                        <div className="text-sm text-muted-foreground/70 truncate max-w-[300px] mt-0.5">
                          {truncate(payloadDisplay.detail, 80)}
                        </div>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-4 py-4">
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${statusConfig.bg} ${statusConfig.color}`}>
                    <StatusIcon className="h-3 w-3" />
                    {statusConfig.label}
                  </span>
                </td>
                <td className="px-4 py-4">
                  <span className="text-sm text-muted-foreground capitalize">{action.source_type}</span>
                </td>
                <td className="px-4 py-4">
                  <span className="text-sm text-muted-foreground">
                    {format(new Date(action.created_at), 'MMM d, h:mm a')}
                  </span>
                </td>
                <td className="px-4 py-4">
                  <div className="flex items-center justify-end gap-1">
                    {action.status != 'executed' && (
                      <>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onEdit(action)}
                          className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onApprove(action.id)}
                          className="h-8 w-8 p-0 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-500/10"
                        >
                          <Check className="h-4 w-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onSkip(action.id)}
                          className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
