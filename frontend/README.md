# Commander Frontend

Modern React + TypeScript UI for the Commander application.

## Tech Stack

- **React 18** with TypeScript
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **shadcn/ui** - Component library
- **Material UI** - Additional components and icons
- **React Query (TanStack Query)** - Data fetching and caching
- **React Router** - Routing

## Getting Started

### Prerequisites

- Node.js 18+ (you're currently on v22.11.0)
- Backend API running on `http://localhost:8000`

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build for Production

```bash
npm run build
```

The production build will be in the `dist/` directory.

## Features

### 1. Actions Tab

- View all generated actions in a list/card format
- Filter by status (pending, executed, skipped, error)
- Filter by source type (gmail, slack, meeting, calendar)
- Edit action payload before approval (JSON editor)
- Approve or skip actions
- Real-time badge showing pending action count

### 2. Real-Time Notifications

- Polls for new pending actions every 5 seconds
- Toast notifications for newly created actions
- Notification badge in header shows pending count
- First load doesn't show notifications (only new actions after initial load)

### 3. Integrations Tab

- View connected integrations (Gmail)
- Connect/disconnect Gmail via OAuth
- Sync Gmail emails manually
- Status badges showing connection state
- Account email displayed when connected

### 4. Action Edit Modal

- Edit action payloads as JSON (all fields editable)
- JSON validation
- Save changes or Save & Approve in one action
- Read-only context information (sender, summary, confidence)

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/              # shadcn/ui components
│   │   ├── actions/         # Action-related components
│   │   ├── integrations/    # Integration components
│   │   └── layout/          # Layout components
│   ├── pages/
│   │   ├── Actions.tsx
│   │   └── Integrations.tsx
│   ├── hooks/
│   │   ├── useActions.ts
│   │   ├── useGmailIntegration.ts
│   │   └── useNewActions.ts
│   ├── services/
│   │   ├── api.ts           # API client
│   │   └── types.ts         # TypeScript types
│   ├── App.tsx
│   └── main.tsx
├── package.json
└── vite.config.ts
```

## Environment Variables

Create a `.env.local` file:

```env
VITE_API_URL=http://localhost:8000
```

## API Integration

The frontend communicates with the backend API at `http://localhost:8000` (configurable via `VITE_API_URL`).

### Endpoints Used

- `GET /actions?status={status}` - List actions
- `POST /actions/{id}/approve` - Approve action
- `POST /actions/{id}/skip` - Skip action
- `PATCH /actions/{id}` - Update action payload
- `GET /integrations/gmail/status` - Get Gmail connection status
- `GET /integrations/gmail/auth-url` - Get OAuth URL
- `GET /integrations/gmail/auth?code={code}` - Complete OAuth
- `POST /integrations/gmail/disconnect` - Disconnect Gmail
- `POST /integrations/gmail/sync?max_results={n}` - Sync emails

## Development Notes

### Polling Strategy

The app polls for pending actions every 5 seconds. This is implemented in `useNewActions` hook which:
1. Fetches pending actions
2. Tracks seen action IDs in memory
3. Shows toast notifications for new actions
4. Updates the header badge count

### OAuth Flow

Gmail OAuth uses a popup window flow:
1. User clicks "Connect" button
2. Popup opens with Google OAuth consent screen
3. After authorization, Google redirects back with `code` parameter
4. Frontend sends message to opener window with the code
5. Main window completes the auth and closes popup

### State Management

- **React Query**: Server state (actions, integrations)
- **Component State**: UI state (filters, modals, editing)
- **No global state library needed** (React Query handles most of it)

## Future Enhancements

- WebSocket support for real-time updates (replace polling)
- Bulk actions (approve/skip multiple actions)
- Action detail view with full context
- Form validation for action editing
- Type-specific edit forms (instead of generic JSON editor)
- Dark mode toggle
- User preferences/settings page

## Troubleshooting

### CORS Errors

Make sure the backend has CORS middleware configured to allow `http://localhost:5173`.

### Backend Not Running

Ensure the backend API is running on port 8000:

```bash
cd /path/to/Commander
python -m uvicorn api:app --reload
```

### OAuth Popup Blocked

Some browsers block popups. Allow popups for `localhost:5173` in your browser settings.
