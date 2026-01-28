# CursorBot Android Node

Android native application for CursorBot with Canvas, Talk Mode, Camera, and Screen Recording support.

## Features

### Live Canvas
- **Real-time Updates**: WebSocket-based canvas synchronization
- **Interactive Components**: Text, code, images, buttons, inputs
- **Gesture Support**: Pinch to zoom, drag to pan, tap to select
- **Agent-driven**: AI can create and manipulate canvas elements

### Talk Mode
- **Speech Recognition**: Real-time voice-to-text using Android Speech API
- **Text-to-Speech**: Natural voice responses
- **Continuous Conversation**: Natural back-and-forth dialogue
- **Multi-language**: Support for multiple languages

### Camera
- **CameraX Integration**: Modern camera API
- **Photo Capture**: High-quality image capture
- **AI Analysis**: Send images to AI for analysis
- **Real-time Preview**: Live camera feed
- **Flash Control**: Toggle flash on/off

### Screen Recording
- **MediaProjection API**: Native screen recording
- **Background Service**: Record while using other apps
- **MP4 Output**: Standard video format
- **AI Analysis**: Send recordings for analysis

### Device Pairing
- **Pairing Code**: Easy device pairing mechanism
- **Secure**: Token-based authentication
- **Multi-device**: Connect multiple devices

## Requirements

- Android 9.0 (API 28) or later
- Android Studio Hedgehog or later
- Kotlin 1.9+

## Building

### Using Gradle

```bash
cd apps/android
./gradlew assembleDebug
```

### Using Android Studio

1. Open the `apps/android` folder in Android Studio
2. Sync Gradle
3. Select device/emulator
4. Run the app (Shift+F10)

## Configuration

### Gateway Connection

1. Launch the app
2. Go to Settings → Gateway
3. Enter your CursorBot server URL
4. Enter authentication token (if required)
5. Tap "Connect"

### Voice Settings

1. Go to Settings → Voice Settings
2. Enable Voice Wake if desired
3. Customize wake phrase
4. Adjust sensitivity

## Architecture

```
app/src/main/java/com/cursorbot/node/
├── CursorBotApplication.kt     # Application class
├── MainActivity.kt             # Main activity
├── di/
│   └── AppModule.kt            # Hilt dependency injection
├── model/
│   └── Models.kt               # Data models
├── viewmodel/
│   └── MainViewModel.kt        # ViewModel
├── service/
│   ├── GatewayService.kt       # WebSocket service
│   ├── PreferencesManager.kt   # Settings storage
│   └── ScreenRecordingService.kt
└── ui/
    ├── Navigation.kt           # Navigation setup
    ├── theme/
    │   └── Theme.kt            # Material 3 theme
    └── screens/
        ├── ChatScreen.kt
        ├── CanvasScreen.kt
        ├── CameraScreen.kt
        └── SettingsScreen.kt
```

## Dependencies

- **Jetpack Compose**: Modern UI toolkit
- **Material 3**: Design system
- **Hilt**: Dependency injection
- **CameraX**: Camera API
- **OkHttp**: HTTP client
- **Java-WebSocket**: WebSocket client
- **Coil**: Image loading

## Permissions

The app requires:

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION" />
```

## Screen Recording

To use screen recording:

1. Go to Settings → Screen Recording
2. Tap "Start Recording"
3. Grant screen recording permission
4. Record your screen
5. Tap "Stop Recording" when done

## Troubleshooting

### Speech Recognition Not Working

1. Check Settings → Apps → CursorBot Node → Permissions
2. Ensure Microphone is allowed
3. Check internet connection (cloud recognition)

### Camera Not Working

1. Check camera permission
2. Try clearing app data
3. Restart the app

### Connection Issues

1. Verify server URL is correct
2. Check network connectivity
3. Ensure server is running
4. Check firewall settings

## ProGuard Rules

Add to `proguard-rules.pro`:

```proguard
-keep class com.cursorbot.node.model.** { *; }
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName <fields>;
}
```

## License

MIT License - See LICENSE file for details
