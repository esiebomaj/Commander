import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Filter } from 'lucide-react'

interface ActionFiltersProps {
  statusFilter: string
  sourceFilter: string
  typeFilter: string
  onStatusChange: (value: string) => void
  onSourceChange: (value: string) => void
  onTypeChange: (value: string) => void
}

export function ActionFilters({
  statusFilter,
  sourceFilter,
  typeFilter,
  onStatusChange,
  onSourceChange,
  onTypeChange,
}: ActionFiltersProps) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Filter className="h-4 w-4" />
        <span>Filter</span>
      </div>
      
      <Select value={statusFilter} onValueChange={onStatusChange}>
        <SelectTrigger className="w-[140px] h-9 text-sm bg-card border-border">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          <SelectItem value="pending">Pending</SelectItem>
          <SelectItem value="executed">Executed</SelectItem>
          <SelectItem value="skipped">Skipped</SelectItem>
          <SelectItem value="error">Error</SelectItem>
        </SelectContent>
      </Select>
      
      <Select value={typeFilter} onValueChange={onTypeChange}>
        <SelectTrigger className="w-[160px] h-9 text-sm bg-card border-border">
          <SelectValue placeholder="Type" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All types</SelectItem>
          <SelectItem value="gmail_send_email">Send Email</SelectItem>
          <SelectItem value="gmail_create_draft">Create Draft</SelectItem>
          <SelectItem value="schedule_meeting">Schedule Meeting</SelectItem>
          <SelectItem value="create_todo">Create Todo</SelectItem>
        </SelectContent>
      </Select>
      
      <Select value={sourceFilter} onValueChange={onSourceChange}>
        <SelectTrigger className="w-[140px] h-9 text-sm bg-card border-border">
          <SelectValue placeholder="Source" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All sources</SelectItem>
          <SelectItem value="gmail">Gmail</SelectItem>
          <SelectItem value="slack">Slack</SelectItem>
          <SelectItem value="meeting_transcript">Meeting</SelectItem>
          <SelectItem value="calendar_event">Calendar</SelectItem>
        </SelectContent>
      </Select>
    </div>
  )
}
