# CursorBot macOS App

Full-featured macOS native application for CursorBot with Talk Mode, Debug Tools, and Remote Gateway support.

## Features

### Talk Mode
- **Speech Recognition**: Real-time voice-to-text using Apple's Speech framework
- **Text-to-Speech**: Natural voice responses
- **Voice Wake**: Hands-free activation with customizable wake phrase (default: "Hey Cursor")
- **Continuous Conversation**: Natural back-and-forth dialogue

### Debug Tools
- **Real-time Logs**: View application logs with filtering
- **Network Inspector**: Monitor API requests and responses
- **System Status**: Memory, CPU, and connection monitoring
- **Export/Import**: Debug data for troubleshooting

### Remote Gateway
- **WebSocket Connection**: Real-time bidirectional communication
- **Auto-reconnect**: Automatic connection recovery
- **Multiple Gateways**: Save and switch between servers
- **Secure Authentication**: Token-based authentication

### Additional Features
- **Menu Bar App**: Quick access from system menu bar
- **Global Hotkeys**: System-wide keyboard shortcuts
- **Auto-launch**: Start with macOS
- **Native Notifications**: Desktop alerts for responses

## Requirements

- macOS 14.0 (Sonoma) or later
- Xcode 15.0 or later (for building)

## Building

### Using Build Script (Recommended)

The build script creates a proper `.app` bundle with all required permissions:

```bash
cd apps/macos/CursorBot
./build-app.sh
open CursorBot.app
```

### Using Swift Package Manager (Development Only)

For quick development builds (note: Talk Mode may not work due to permission issues):

```bash
cd apps/macos/CursorBot
swift build
```

### Using Xcode

1. Open `Package.swift` in Xcode
2. Select the CursorBot scheme
3. Build and run (⌘R)

### Installing to Applications

After building, you can install the app:

```bash
mv CursorBot.app /Applications/
```

## Configuration

### Gateway Connection

1. Launch the app
2. Click the antenna icon in the toolbar
3. Enter your CursorBot server URL (e.g., `http://localhost:8000`)
4. Enter your authentication token (if required)
5. Click "Connect"

### Voice Settings

1. Go to Settings → Voice
2. Enable Voice Wake if desired
3. Customize the wake phrase
4. Adjust sensitivity and speaking rate

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| ⌘⇧T | Toggle Talk Mode |
| ⌘⇧N | New Conversation |
| ⌘⇧G | Gateway Connection |
| ⌘⌥D | Toggle Debug Panel |
| ⌘⇧Space | Quick Chat (Global) |

## Architecture

```
CursorBot/
├── Sources/
│   ├── App/
│   │   ├── CursorBotApp.swift      # App entry point
│   │   └── AppState.swift          # Global state management
│   ├── Views/
│   │   ├── ContentView.swift       # Main window
│   │   ├── DebugPanelView.swift    # Debug tools
│   │   ├── GatewayConnectionSheet.swift
│   │   ├── SettingsView.swift
│   │   └── MenuBarView.swift
│   ├── Models/
│   │   └── Models.swift            # Data models
│   ├── Services/
│   │   ├── GatewayService.swift    # WebSocket connection
│   │   └── AudioService.swift      # Speech recognition/TTS
│   └── Utils/
│       └── HotkeyManager.swift     # Global hotkeys
└── Package.swift
```

## Dependencies

- **Alamofire**: HTTP networking (for REST API calls)
- **Starscream**: WebSocket client
- **Swift Collections**: Efficient data structures

## Permissions

The app requires the following permissions:

- **Microphone**: For speech recognition
- **Speech Recognition**: For voice-to-text
- **Notifications**: For desktop alerts

## Troubleshooting

### Speech Recognition Not Working

1. Check System Preferences → Privacy & Security → Microphone
2. Ensure CursorBot is allowed
3. Check Speech Recognition permissions as well

### Gateway Connection Failed

1. Verify the server URL is correct
2. Check if the server is running
3. Verify network connectivity
4. Check firewall settings

### No Audio Output

1. Check System Preferences → Sound → Output
2. Verify volume is not muted
3. Try a different output device

## License

MIT License - See LICENSE file for details
