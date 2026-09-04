# HALOCAS Next.js Frontend Client

The official web dashboard and command interface for the **HALOCAS (Halo Collision Avoidance System)** mining safety platform.

## 🚀 Overview

The frontend application provides real-time spatial safety monitoring, multi-camera CCTV feeds, DeepFace biometric management, and interactive incident review for open-pit and underground mining operations.

### Key Features
- **Command Center Dashboard**: Real-time KPI telemetry, active machine counts, worker statuses, and spatial Halo safety radar.
- **Live Monitoring**: Multi-camera grid with bounding box overlays, ByteTrack trajectory vectors, and camera switching.
- **Incident Forensics**: Historical proximity breaches, closing velocity diagnostics, and 5-second MP4 video replays.
- **Personnel & Biometrics**: Worker registry, 512-D Facenet512 enrollment status, supervisor hierarchy, and zone authorization.
- **Equipment Fleet**: Haul truck and excavator asset registry with live speeds, operating zones, and mounted camera buffers.
- **Safety Calibration**: Interactive threshold tuning for critical distance, warning distance, and camera pixels-per-meter constants.

---

## 🎨 Brand Design System

Built on modern cyberpunk/industrial aesthetics:
- **Background**: `#111827` (Dark carbon)
- **Panels**: `#1f2937` (Raised telemetry cards)
- **Borders**: `#374151` (Industrial slate outline)
- **Cyan**: `#00FFFF` (Primary beacon, radar glow, brand accent)
- **Red**: `#FF3B30` (Critical proximity breaches, emergency sirens)
- **Green**: `#10B981` (Safe zone, authorized status, normal health)
- **Amber**: `#F59E0B` (Warning distance buffer)
- **Typography**: `Inter` from Google Fonts

---

## 🛠️ Getting Started

### Prerequisites
- Node.js 18+ (tested on Node v22.17.0)
- npm 9+

### Environment Variables
Copy `.env.example` to `.env.local`:
```bash
cp .env.example .env.local
```

Configured values:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1/ws/telemetry
```

### Running Locally
```bash
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build
```bash
npm run build
npm run start
```
