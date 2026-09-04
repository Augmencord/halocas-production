# HALOCAS Frontend

This directory is reserved for the Next.js frontend client for the HALOCAS (Halo Collision Avoidance System) platform.

## Architecture

The frontend application will interface with the FastAPI backend through:
- REST API for incident querying, worker management, and system configuration
- WebSockets for real-time collision alerts and live safety feeds
- Video player component for viewing 5-second incident clips stored in Cloudflare R2

## Technology Stack

- **Framework**: Next.js 14+ (App Router)
- **Styling**: Tailwind CSS & Radix UI / Shadcn
- **State Management**: TanStack Query (React Query)
- **Real-time Client**: Native WebSocket connection with auto-reconnect
