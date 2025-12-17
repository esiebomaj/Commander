export type ActionType = 
  | 'gmail_send_email'
  | 'gmail_create_draft'
  | 'schedule_meeting'
  | 'create_todo'
  | 'no_action'

export type SourceType = 
  | 'gmail'
  | 'slack'
  | 'meeting_transcript'
  | 'calendar_event'

export type ActionStatus = 
  | 'pending'
  | 'executed'
  | 'skipped'
  | 'error'

export interface ProposedAction {
  id: number
  context_id: string
  type: ActionType
  payload: Record<string, any>
  confidence: number
  status: ActionStatus
  created_at: string
  source_type: SourceType
  sender?: string
  summary?: string
}

export interface Integration {
  id: string
  name: string
  connected: boolean
  email?: string
  description?: string
}

export interface GmailStatus {
  connected: boolean
  email?: string
}

export interface GmailAuthUrlResponse {
  auth_url: string
  instructions: string
}

export interface CalendarStatus {
  connected: boolean
  email?: string
}

export interface CalendarAuthUrlResponse {
  auth_url: string
  instructions: string
}

export interface DriveStatus {
  connected: boolean
  email?: string
  webhook_active: boolean
  webhook_expiration?: string
}

export interface DriveAuthUrlResponse {
  auth_url: string
  instructions: string
}

export interface ProcessTranscriptResponse {
  success: boolean
  context_id?: string
  actions_created: number
  message: string
}
