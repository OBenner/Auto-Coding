# Auto Code Web Interface

Browser-based UI for Auto Code autonomous coding framework. Connects to the Auto Code backend API to provide task management, real-time agent progress, and spec creation from any device.

## Features

- **Browser-based access** - No desktop installation required
- **Real-time updates** - WebSocket connection for live agent progress
- **Responsive design** - Works on tablet and desktop
- **Secure connection** - JWT authentication with backend API

## Development

### Prerequisites

- Node.js >= 24.0.0
- npm >= 10.0.0
- Auto Code backend running (see `apps/web-backend/`)

### Quick Start

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Start development server
npm run dev

# Open browser to http://localhost:3000
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
VITE_API_URL=http://localhost:8000    # Backend API URL
VITE_WS_URL=ws://localhost:8000       # WebSocket URL
```

See `.env.example` for all available options.

## Scripts

```bash
npm run dev          # Start dev server (http://localhost:3000)
npm run build        # Build for production
npm run preview      # Preview production build
npm test             # Run unit tests
npm run test:e2e     # Run end-to-end tests
npm run lint         # Lint code
npm run typecheck    # Type check with TypeScript
```

## Architecture

### Tech Stack

- **React 19** - UI framework
- **Vite** - Build tool and dev server
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Radix UI** - Accessible components
- **Zustand** - State management
- **i18next** - Internationalization

### Project Structure

```
src/
├── api/              # API client and WebSocket logic
├── components/       # Reusable UI components
├── pages/            # Page components
├── hooks/            # Custom React hooks
├── lib/              # Utility functions
├── styles/           # Global styles
├── App.tsx           # Root component
└── main.tsx          # Application entry point
```

### API Integration

The web frontend communicates with the backend API via:

1. **REST API** - Task/spec management (`/api/tasks`, `/api/specs`)
2. **WebSocket** - Real-time agent events (`/ws/agent-events`)

See `src/api/client.ts` for API client implementation.

## Building for Production

```bash
# Build optimized bundle
npm run build

# Preview production build locally
npm run preview
```

Output is in `dist/` directory.

## Testing

```bash
# Run unit tests
npm test

# Run unit tests in watch mode
npm run test:watch

# Run E2E tests
npm run test:e2e

# Generate coverage report
npm run test:coverage
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment instructions (created in phase 3).

## Related Projects

- **Backend API** - `apps/web-backend/` - FastAPI server
- **Desktop UI** - `apps/frontend/` - Electron desktop app
- **Core Backend** - `apps/backend/` - Auto Code core logic

## License

AGPL-3.0 - see [LICENSE](../../LICENSE)
