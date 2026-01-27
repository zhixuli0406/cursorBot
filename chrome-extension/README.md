# CursorBot Chrome Extension

Browser integration for CursorBot AI Assistant.

## Features

- **Quick Chat**: Chat with AI directly from any webpage
- **Context Menu**: Right-click to ask, explain, translate, or summarize
- **Page Summarization**: Summarize any webpage with one click
- **Selection Actions**: Select text and get instant AI responses

## Installation

### Development Mode

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" in the top right
3. Click "Load unpacked"
4. Select the `chrome-extension` folder

### Build for Production

```bash
cd chrome-extension
zip -r cursorbot-extension.zip . -x "*.git*" -x "README.md"
```

## Configuration

1. Click the extension icon
2. Click "Settings"
3. Enter your CursorBot server URL (default: `http://localhost:8000`)
4. Optionally enter an API key

## Usage

### Quick Chat

- Click the extension icon
- Type your question and press Enter
- Or press `Ctrl+Shift+Y` to toggle chat overlay on any page

### Context Menu

1. Select text on any webpage
2. Right-click and choose "CursorBot"
3. Select an action:
   - **Ask about this**: Get AI response about the selection
   - **Explain this**: Get a simple explanation
   - **Translate this**: Translate the text
   - **Summarize page**: Summarize the entire page

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+Y` | Toggle chat overlay |

## API Integration

The extension communicates with your CursorBot server via REST API:

```
POST /api/agent
{
  "message": "your question",
  "model": "gpt-4o-mini"
}
```

Make sure your server is running and accessible.

## Development

### File Structure

```
chrome-extension/
├── manifest.json      # Extension manifest
├── background.js      # Service worker
├── content.js         # Content script
├── content.css        # Content styles
├── popup.html         # Popup UI
├── popup.js           # Popup logic
├── options.html       # Settings page
└── icons/             # Extension icons
```

### Building Icons

Create icons in the following sizes:
- `icon16.png` (16x16)
- `icon48.png` (48x48)
- `icon128.png` (128x128)

### Testing

1. Make changes to the code
2. Go to `chrome://extensions/`
3. Click the refresh button on the extension card
4. Test the changes

## Permissions

- `activeTab`: Access current tab content
- `storage`: Save settings
- `contextMenus`: Add right-click menu
- `notifications`: Show notifications

## Troubleshooting

### "Server not connected"

- Make sure CursorBot server is running
- Check the server URL in settings
- Verify CORS is enabled on the server

### Context menu not appearing

- Refresh the page
- Reload the extension
- Check browser console for errors

## License

MIT License - See main project for details.
