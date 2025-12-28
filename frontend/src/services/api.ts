import { supabase } from '@/lib/supabase'
import type { ProposedAction, GmailStatus, GmailAuthUrlResponse, CalendarStatus, CalendarAuthUrlResponse, DriveStatus, DriveAuthUrlResponse, GitHubStatus, GitHubAuthUrlResponse, SlackStatus, SlackAuthUrlResponse, PushStatus, VapidPublicKeyResponse, PushSubscribeRequest, PushSubscribeResponse, PushTestResponse, WebhookSetupResponse } from './types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const { data: { session } } = await supabase.auth.getSession()
  
  if (!session?.access_token) {
    throw new ApiError(401, 'Not authenticated')
  }
  
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${session.access_token}`,
  }
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const headers = await getAuthHeaders()
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      ...headers,
      ...options?.headers,
    },
  })

  if (response.status === 401) {
    // Token expired or invalid - sign out
    await supabase.auth.signOut()
    throw new ApiError(401, 'Session expired. Please sign in again.')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new ApiError(response.status, error.detail || 'Request failed')
  }

  return response.json()
}

// Public endpoint (no auth required)
async function fetchPublicApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new ApiError(response.status, error.detail || 'Request failed')
  }

  return response.json()
}

// Actions API
export async function getActions(status?: string): Promise<ProposedAction[]> {
  const query = status ? `?status=${status}` : ''
  const response = await fetchApi<{ actions: ProposedAction[] }>(`/actions${query}`)
  return response.actions
}

export async function approveAction(actionId: number): Promise<ProposedAction> {
  return fetchApi<ProposedAction>(`/actions/${actionId}/approve`, {
    method: 'POST',
  })
}

export async function skipAction(actionId: number): Promise<ProposedAction> {
  return fetchApi<ProposedAction>(`/actions/${actionId}/skip`, {
    method: 'POST',
  })
}

export async function updateAction(
  actionId: number,
  payload: Record<string, any>
): Promise<ProposedAction> {
  return fetchApi<ProposedAction>(`/actions/${actionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ payload }),
  })
}

// Gmail Integration API
export async function getGmailStatus(): Promise<GmailStatus> {
  return fetchApi<GmailStatus>('/integrations/gmail/status')
}

export async function getGmailAuthUrl(redirectUri?: string): Promise<GmailAuthUrlResponse> {
  const query = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : ''
  return fetchApi<GmailAuthUrlResponse>(`/integrations/gmail/auth-url${query}`)
}

export async function completeGmailAuth(code: string, redirectUri: string, state?: string): Promise<GmailStatus> {
  const params = new URLSearchParams({ code, redirect_uri: redirectUri })
  if (state) params.append('state', state)
  return fetchApi<GmailStatus>(`/integrations/gmail/auth?${params.toString()}`)
}

export async function disconnectGmail(): Promise<GmailStatus> {
  return fetchApi<GmailStatus>('/integrations/gmail/disconnect', {
    method: 'POST',
  })
}

export async function syncGmail(maxResults: number = 20): Promise<{ synced_count: number; message: string }> {
  return fetchApi(`/integrations/gmail/sync?max_results=${maxResults}`, {
    method: 'POST',
  })
}

export async function processNewGmailEmails(): Promise<{ proposed_actions: ProposedAction[] }> {
  return fetchApi('/integrations/gmail/process-new', {
    method: 'POST',
  })
}

export async function setupGmailWebhook(): Promise<WebhookSetupResponse> {
  return fetchApi<WebhookSetupResponse>('/integrations/gmail/webhook/setup', {
    method: 'POST',
  })
}

// Calendar Integration API
export async function getCalendarStatus(): Promise<CalendarStatus> {
  return fetchApi<CalendarStatus>('/integrations/calendar/status')
}

export async function getCalendarAuthUrl(redirectUri?: string): Promise<CalendarAuthUrlResponse> {
  const query = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : ''
  return fetchApi<CalendarAuthUrlResponse>(`/integrations/calendar/auth-url${query}`)
}

export async function completeCalendarAuth(code: string, redirectUri: string, state?: string): Promise<CalendarStatus> {
  const params = new URLSearchParams({ code, redirect_uri: redirectUri })
  if (state) params.append('state', state)
  return fetchApi<CalendarStatus>(`/integrations/calendar/auth?${params.toString()}`)
}

export async function disconnectCalendar(): Promise<CalendarStatus> {
  return fetchApi<CalendarStatus>('/integrations/calendar/disconnect', {
    method: 'POST',
  })
}

// Drive Integration API
export async function getDriveStatus(): Promise<DriveStatus> {
  return fetchApi<DriveStatus>('/integrations/drive/status')
}

export async function getDriveAuthUrl(redirectUri?: string): Promise<DriveAuthUrlResponse> {
  const query = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : ''
  return fetchApi<DriveAuthUrlResponse>(`/integrations/drive/auth-url${query}`)
}

export async function completeDriveAuth(code: string, redirectUri: string, state?: string): Promise<DriveStatus> {
  const params = new URLSearchParams({ code, redirect_uri: redirectUri })
  if (state) params.append('state', state)
  return fetchApi<DriveStatus>(`/integrations/drive/auth?${params.toString()}`)
}

export async function disconnectDrive(): Promise<DriveStatus> {
  return fetchApi<DriveStatus>('/integrations/drive/disconnect', {
    method: 'POST',
  })
}

export async function processRecentTranscripts(maxFiles: number = 5, sinceHours: number = 24): Promise<{ success: boolean; processed_count: number; transcripts: Array<{ context_id: string; title: string; actions_created: number }> }> {
  return fetchApi(`/integrations/drive/process-recent?max_files=${maxFiles}&since_hours=${sinceHours}`, {
    method: 'POST',
  })
}

export async function setupDriveWebhook(): Promise<WebhookSetupResponse> {
  return fetchApi<WebhookSetupResponse>('/integrations/drive/setup-webhook', {
    method: 'POST',
  })
}

// GitHub Integration API
export async function getGitHubStatus(): Promise<GitHubStatus> {
  return fetchApi<GitHubStatus>('/integrations/github/status')
}

export async function getGitHubAuthUrl(redirectUri: string): Promise<GitHubAuthUrlResponse> {
  return fetchApi<GitHubAuthUrlResponse>(`/integrations/github/auth-url?redirect_uri=${encodeURIComponent(redirectUri)}`)
}

export async function completeGitHubAuth(code: string, redirectUri: string, state?: string): Promise<GitHubStatus> {
  const params = new URLSearchParams({ code, redirect_uri: redirectUri })
  if (state) params.append('state', state)
  return fetchApi<GitHubStatus>(`/integrations/github/auth?${params.toString()}`)
}

export async function disconnectGitHub(): Promise<GitHubStatus> {
  return fetchApi<GitHubStatus>('/integrations/github/disconnect', {
    method: 'POST',
  })
}

// Slack Integration API
export async function getSlackStatus(): Promise<SlackStatus> {
  return fetchApi<SlackStatus>('/integrations/slack/status')
}

export async function getSlackAuthUrl(redirectUri: string): Promise<SlackAuthUrlResponse> {
  return fetchApi<SlackAuthUrlResponse>(`/integrations/slack/auth-url?redirect_uri=${encodeURIComponent(redirectUri)}`)
}

export async function completeSlackAuth(code: string, redirectUri: string, state?: string): Promise<SlackStatus> {
  const params = new URLSearchParams({ code, redirect_uri: redirectUri })
  if (state) params.append('state', state)
  return fetchApi<SlackStatus>(`/integrations/slack/auth?${params.toString()}`)
}

export async function disconnectSlack(): Promise<SlackStatus> {
  return fetchApi<SlackStatus>('/integrations/slack/disconnect', {
    method: 'POST',
  })
}

// Push Notification API
export async function getVapidPublicKey(): Promise<VapidPublicKeyResponse> {
  // VAPID key endpoint doesn't require auth
  return fetchPublicApi<VapidPublicKeyResponse>('/push/vapid-public-key')
}

export async function subscribeToPush(subscription: PushSubscribeRequest): Promise<PushSubscribeResponse> {
  return fetchApi<PushSubscribeResponse>('/push/subscribe', {
    method: 'POST',
    body: JSON.stringify(subscription),
  })
}

export async function unsubscribeFromPush(endpoint: string): Promise<PushSubscribeResponse> {
  return fetchApi<PushSubscribeResponse>('/push/unsubscribe', {
    method: 'POST',
    body: JSON.stringify({ endpoint }),
  })
}

export async function sendTestNotification(title?: string, body?: string): Promise<PushTestResponse> {
  return fetchApi<PushTestResponse>('/push/test', {
    method: 'POST',
    body: JSON.stringify({ title, body }),
  })
}

export async function getPushStatus(): Promise<PushStatus> {
  return fetchApi<PushStatus>('/push/status')
}

// User Profile API
export async function getCurrentUser(): Promise<{ id: string; email: string; full_name: string | null; avatar_url: string | null }> {
  return fetchApi('/me')
}
