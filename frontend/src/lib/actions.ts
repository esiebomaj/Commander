export function getActionLabel(type: string): string {
  switch (type) {
    case 'gmail_send_email':
      return 'Send Email'
    case 'gmail_create_draft':
      return 'Create Draft'
    case 'schedule_meeting':
      return 'Schedule Meeting'
    case 'create_todo':
      return 'Create Todo'
    case 'no_action':
      return 'No Action'
    default:
      return type
  }
}

export interface PayloadDisplay {
  primary: string
  secondary: string | null
  detail: string | null
}

export function getPayloadDisplay(type: string, payload: Record<string, any>): PayloadDisplay {
  switch (type) {
    case 'gmail_send_email':
    case 'gmail_create_draft':
      return {
        primary: payload.subject || 'No subject',
        secondary: payload.to_email ? `To: ${payload.to_email}` : null,
        detail: payload.body || null,
      }
    case 'schedule_meeting': {
      const timeStr = payload.meeting_time 
        ? new Date(payload.meeting_time).toLocaleString(undefined, { 
            month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' 
          })
        : null
      const durationStr = payload.duration_mins ? ` (${payload.duration_mins} min)` : ''
      return {
        primary: payload.meeting_title || 'Untitled meeting',
        secondary: timeStr ? timeStr + durationStr : null,
        detail: payload.meeting_description || null,
      }
    }
    case 'create_todo': {
      return {
        primary: payload.title || 'Untitled todo',
        secondary: payload.due_date 
          ? `Due: ${new Date(payload.due_date).toLocaleDateString(undefined, { 
              month: 'short', day: 'numeric', year: 'numeric' 
            })}`
          : null,
        detail: payload.notes || null,
      }
    }
    default:
      return {
        primary: type,
        secondary: null,
        detail: null,
      }
  }
}

export function truncate(text: string | null, length: number): string | null {
  if (!text) return null
  if (text.length <= length) return text
  return text.slice(0, length) + '...'
}
