# Moneta Frontend (Next.js)

A modern Next.js 15.4 frontend for the Moneta agentic assistant application.

## Tech Stack

- **Next.js 15.4** - React framework with SSR/SSG
- **React 19** - UI library
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first CSS framework
- **Radix UI** - Headless UI components
- **Lucide React** - Icon library

## Getting Started

### Prerequisites

- Node.js 20+
- npm or yarn

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

The app will be available at http://localhost:3000

### Environment Variables

Copy `.env.example` to `.env.local` and configure:

```bash
cp .env.example .env.local
```

Required environment variables:

- `NEXT_PUBLIC_BACKEND_ENDPOINT` - Backend API endpoint (default: http://localhost:8000)

### Build

```bash
npm run build
```

### Production

```bash
npm run start
```

## Docker

### Build Image

```bash
docker build -t moneta-frontend .
```

### Run Container

```bash
docker run -p 8000:8000 -e NEXT_PUBLIC_BACKEND_ENDPOINT=http://backend:8000 moneta-frontend
```

## Project Structure

```
src/
├── app/                    # Next.js App Router
│   ├── globals.css         # Global styles
│   ├── layout.tsx          # Root layout
│   └── page.tsx            # Home page
├── components/
│   ├── chat/               # Chat-related components
│   ├── providers/          # Context providers
│   ├── sidebar/            # Sidebar components
│   └── ui/                 # Reusable UI components
└── lib/
    ├── api.ts              # API client
    ├── constants.ts        # App constants
    ├── types.ts            # TypeScript types
    └── utils.ts            # Utility functions
```

## Features

- 💬 Real-time chat with AI agents
- 🔄 Use case switching (Banking/Insurance)
- 🔍 Deep Research mode
- 📱 Responsive design
- 🌙 Dark mode support
- 💾 Conversation history
