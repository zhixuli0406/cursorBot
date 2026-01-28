# CursorBot Native Applications

This directory contains native applications for different platforms.

## Applications

### macOS App (`/macos`)

Full-featured macOS native application built with SwiftUI.

**Features:**
- Talk Mode (Speech Recognition + TTS)
- Debug Tools (Logs, Network Inspector, Status)
- Remote Gateway (WebSocket connection)
- Menu Bar integration
- Global Hotkeys
- Voice Wake

**Build:**
```bash
cd macos/CursorBot
swift build
swift run
```

### iOS Node (`/ios`)

iOS native application for remote node functionality.

**Features:**
- Live Canvas (Agent-driven visual workspace)
- Voice Wake
- Talk Mode
- Camera (Photo capture + AI analysis)
- Device Pairing (QR Code)

**Build (requires Xcode):**
```bash
cd ios
open CursorBotNode.xcodeproj
# In Xcode: Select device → Build and Run (⌘R)
```

### Android Node (`/android`)

Android native application built with Kotlin and Jetpack Compose.

**Features:**
- Live Canvas
- Talk Mode
- Camera (CameraX integration)
- Screen Recording (MediaProjection)
- Device Pairing

**Build:**
```bash
cd android
./gradlew assembleDebug
```

## Architecture

All applications share a common architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                     CursorBot Server                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    Gateway API                           ││
│  │  - WebSocket /ws/node                                    ││
│  │  - REST API /api/*                                       ││
│  │  - Canvas Updates                                        ││
│  │  - Pairing Codes                                         ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
    ┌───────────┐      ┌───────────┐      ┌───────────┐
    │  macOS    │      │   iOS     │      │  Android  │
    │   App     │      │   Node    │      │   Node    │
    └───────────┘      └───────────┘      └───────────┘
```

## Communication Protocol

### WebSocket Messages

**Request Format:**
```json
{
  "id": "uuid",
  "type": "chat|canvas|pairing|image|command",
  "payload": {
    "message": "...",
    "action": "..."
  }
}
```

**Response Format:**
```json
{
  "requestId": "uuid",
  "type": "message|canvas|pairing",
  "payload": "...",
  "error": null
}
```

### Canvas Protocol

```json
{
  "id": "canvas-uuid",
  "components": [
    {
      "id": "comp-uuid",
      "type": "text|code|image|button|input",
      "x": 100,
      "y": 100,
      "width": 200,
      "height": 100,
      "content": "Hello World",
      "style": {
        "backgroundColor": "#FFFFFF",
        "textColor": "#000000"
      }
    }
  ]
}
```

## Requirements

| Platform | Minimum Version | IDE |
|----------|-----------------|-----|
| macOS | 14.0 (Sonoma) | Xcode 15+ |
| iOS | 17.0 | Xcode 15+ |
| Android | 9.0 (API 28) | Android Studio Hedgehog+ |

## Getting Started

1. Start the CursorBot server:
   ```bash
   cd /path/to/cursorBot
   python -m src.main
   ```

2. Build and run your preferred platform app

3. Connect to the gateway using the server URL

4. Start chatting or use advanced features!

## License

MIT License - See LICENSE file for details
