#!/bin/bash
# Build CursorBot macOS App Bundle

set -e

echo "Building CursorBot..."

# Build the executable
swift build -c release

# Create app bundle structure
APP_NAME="CursorBot"
APP_BUNDLE="$APP_NAME.app"
CONTENTS_DIR="$APP_BUNDLE/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

# Clean previous build
rm -rf "$APP_BUNDLE"

# Create directories
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# Copy executable
cp ".build/release/CursorBot" "$MACOS_DIR/CursorBot"

# Copy Info.plist
cp "Sources/Info.plist" "$CONTENTS_DIR/Info.plist"

# Create PkgInfo
echo -n "APPL????" > "$CONTENTS_DIR/PkgInfo"

# Sign the app (ad-hoc for development)
codesign --force --deep --sign - "$APP_BUNDLE"

echo ""
echo "Build complete!"
echo "App bundle created at: $APP_BUNDLE"
echo ""
echo "To run the app:"
echo "  open $APP_BUNDLE"
echo ""
echo "Or move it to /Applications:"
echo "  mv $APP_BUNDLE /Applications/"
