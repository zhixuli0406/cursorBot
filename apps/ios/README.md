# CursorBot iOS Node

iOS native application for CursorBot with Canvas, Voice Wake, Talk Mode, and Camera integration.

## Features

### Live Canvas
- **Real-time Updates**: WebSocket-based canvas synchronization
- **Interactive Components**: Text, code, images, buttons, inputs
- **Gesture Support**: Pinch to zoom, drag to pan, tap to select
- **Agent-driven**: AI can create and manipulate canvas elements

### Voice Wake
- **Hands-free Activation**: Wake phrase detection (default: "Hey Cursor")
- **Customizable**: Change wake phrase and sensitivity
- **Background Support**: Works even when app is in background (with limitations)

### Talk Mode
- **Speech Recognition**: Real-time voice-to-text
- **Text-to-Speech**: Natural voice responses
- **Continuous Conversation**: Natural back-and-forth dialogue
- **Multi-language**: Support for multiple languages

### Camera
- **Photo Capture**: High-quality image capture
- **AI Analysis**: Send images to AI for analysis
- **Real-time Preview**: Live camera feed
- **Focus & Zoom**: Tap to focus, pinch to zoom

### Device Pairing
- **QR Code**: Easy pairing with other devices
- **Secure**: Token-based authentication
- **Multi-device**: Connect multiple devices to same account

## Requirements

- iOS 17.0 or later
- Xcode 15.0 or later (for building)
- iPhone or iPad

## Building

### Using Xcode (Required)

iOS apps require Xcode and iOS SDK to build:

```bash
cd apps/ios
open CursorBotNode.xcodeproj
```

Then in Xcode:
1. Select the CursorBotNode scheme
2. Select target device (iPhone/iPad simulator or real device)
3. Build and run (⌘R)

**Note**: Swift Package Manager command-line build (`swift build`) is not supported for iOS apps as they require UIKit and iOS SDK.

## Configuration

### Gateway Connection

1. Launch the app
2. Go to Settings → Gateway
3. Enter your CursorBot server URL
4. Enter authentication token (if required)
5. Tap "Connect"

### Voice Settings

1. Go to Settings → Voice Settings
2. Customize wake phrase
3. Adjust sensitivity
4. Select preferred language

## Architecture

```
CursorBotNode/
├── Sources/
│   ├── App/
│   │   ├── CursorBotNodeApp.swift    # App entry point
│   │   └── NodeAppState.swift        # Global state
│   ├── Views/
│   │   ├── MainTabView.swift         # Tab navigation
│   │   ├── CanvasView.swift          # Live Canvas
│   │   ├── CameraView.swift          # Camera
│   │   └── SettingsView.swift        # Settings
│   ├── Models/
│   │   └── Models.swift              # Data models
│   └── Services/
│       ├── GatewayService.swift      # WebSocket
│       ├── AudioService.swift        # Speech
│       └── CameraService.swift       # Camera
└── Package.swift
```

## Permissions

The app requires:

- **Microphone**: For speech recognition
- **Speech Recognition**: For voice-to-text
- **Camera**: For photo capture and analysis
- **Notifications**: For push notifications

Add to Info.plist:

```xml
<key>NSMicrophoneUsageDescription</key>
<string>CursorBot needs microphone access for voice commands</string>
<key>NSSpeechRecognitionUsageDescription</key>
<string>CursorBot needs speech recognition for voice commands</string>
<key>NSCameraUsageDescription</key>
<string>CursorBot needs camera access for image analysis</string>
```

## Background Modes

For continuous voice wake, enable background modes in Xcode:

1. Select target → Signing & Capabilities
2. Add "Background Modes"
3. Enable "Audio, AirPlay, and Picture in Picture"

## Troubleshooting

### Speech Recognition Not Working

1. Check Settings → Privacy → Speech Recognition
2. Ensure CursorBot is allowed
3. Check microphone permissions

### Camera Not Working

1. Check Settings → Privacy → Camera
2. Ensure CursorBot is allowed
3. Try restarting the app

### Connection Issues

1. Verify server URL is correct
2. Check network connectivity
3. Ensure server is running

## License

MIT License - See LICENSE file for details
