# Commander

Commander, an AI-powered task automation for your work. knows everything and can do everything.

## Features
- **AI-Powered Action Management**: Automatically propose and manage actions based on the context.
- **Smart Context Storage**: Vector-based semantic search for contextual information.
- **Push Notifications**: Real-time notifications for new actions and updates
- **Action Approval Workflow**: Review, edit, approve, or skip AI-generated actions

## Currently Supported Contexts 
- Email (Gmail)
- Calendar (Google Calendar)
- Meetings (Google Meet)

## Currently Supported Actions
- Send Email
- Create Draft Email
- Schedule Meeting
- Create Todo

## Development

### Backend
```bash
# Run with auto-reload
uvicorn backend.api:app --reload

```

### Frontend
```bash
# Development server
npm run dev

```

## API Documentation

Once the backend is running, visit `http://localhost:8000/docs` for interactive API documentation.

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
