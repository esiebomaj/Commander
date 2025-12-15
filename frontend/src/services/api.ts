import type { ProposedAction, GmailStatus, GmailAuthUrlResponse } from './types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

class ApiError extends Error {
  constructor(_status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
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
  console.log('Payload:', payload);
  console.log("--------------------------------");
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

export async function completeGmailAuth(code: string, state?: string): Promise<GmailStatus> {
  const params = new URLSearchParams({ code })
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
