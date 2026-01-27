"""
macOS Menu Bar Application for CursorBot

Provides:
- Quick access to CursorBot from menu bar
- Status indicator
- Quick chat
- Recent conversations

Requires: rumps (pip install rumps)
"""

import asyncio
import os
import platform
import threading
from typing import Optional

# Check if we're on macOS
IS_MACOS = platform.system() == "Darwin"

if IS_MACOS:
    try:
        import rumps
        RUMPS_AVAILABLE = True
    except ImportError:
        RUMPS_AVAILABLE = False
        rumps = None
else:
    RUMPS_AVAILABLE = False
    rumps = None


class CursorBotMenuBar:
    """
    macOS Menu Bar application for CursorBot.
    
    Features:
    - Status indicator (online/offline)
    - Quick chat input
    - Recent conversations
    - Quick actions
    """
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self._app = None
        self._status = "offline"
        self._recent_chats: list[str] = []
        self._llm_manager = None
        self._loop = None
    
    def run(self) -> None:
        """Run the menu bar application."""
        if not IS_MACOS:
            print("Menu Bar app is only available on macOS")
            return
        
        if not RUMPS_AVAILABLE:
            print("rumps not installed. Run: pip install rumps")
            return
        
        # Create app
        self._app = rumps.App(
            "CursorBot",
            icon=None,  # Will use default
            title="🤖",
            quit_button=None,
        )
        
        # Build menu
        self._build_menu()
        
        # Start status check timer
        rumps.Timer(self._check_status, 30).start()
        
        # Run app
        self._app.run()
    
    def _build_menu(self) -> None:
        """Build the menu structure."""
        self._app.menu = [
            rumps.MenuItem("Status: Offline", callback=None),
            None,  # Separator
            rumps.MenuItem("Quick Chat...", callback=self._quick_chat),
            None,  # Separator
            rumps.MenuItem("Recent", callback=None),
            rumps.MenuItem("  No recent chats", callback=None),
            None,  # Separator
            rumps.MenuItem("Actions", [
                rumps.MenuItem("New Conversation", callback=self._new_conversation),
                rumps.MenuItem("View Dashboard", callback=self._open_dashboard),
                rumps.MenuItem("Open Settings", callback=self._open_settings),
            ]),
            None,  # Separator
            rumps.MenuItem("About CursorBot", callback=self._show_about),
            rumps.MenuItem("Quit", callback=self._quit),
        ]
    
    def _check_status(self, _) -> None:
        """Check server status periodically."""
        import urllib.request
        import urllib.error
        
        try:
            req = urllib.request.Request(
                f"{self.server_url}/health",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    self._status = "online"
                    self._app.title = "🟢"
                    # Update menu item
                    try:
                        for key, item in self._app.menu.items():
                            if hasattr(item, 'title') and "Status:" in item.title:
                                item.title = "Status: Online"
                                break
                    except Exception:
                        pass
                else:
                    self._set_offline()
        except Exception:
            self._set_offline()
    
    def _set_offline(self) -> None:
        """Set status to offline."""
        self._status = "offline"
        self._app.title = "🔴"
        try:
            # Try to update menu item if exists
            for key, item in self._app.menu.items():
                if hasattr(item, 'title') and item.title == "Status: Online":
                    item.title = "Status: Offline"
                    break
        except Exception:
            pass
    
    def _quick_chat(self, _) -> None:
        """Open quick chat dialog."""
        # Create input window
        window = rumps.Window(
            message="Enter your message:",
            title="CursorBot Quick Chat",
            default_text="",
            ok="Send",
            cancel="Cancel",
            dimensions=(400, 100),
        )
        
        response = window.run()
        
        if response.clicked and response.text.strip():
            self._send_message(response.text.strip())
    
    def _send_message(self, message: str) -> None:
        """Send message to CursorBot."""
        import urllib.request
        import urllib.error
        import json
        
        try:
            data = json.dumps({"message": message}).encode()
            req = urllib.request.Request(
                f"{self.server_url}/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode())
                response_text = result.get("response", result.get("message", "No response"))
                
                # Show response
                rumps.notification(
                    title="CursorBot",
                    subtitle="Response",
                    message=response_text[:200] + ("..." if len(response_text) > 200 else ""),
                )
                
                # Add to recent
                self._add_recent(message)
                
        except urllib.error.URLError as e:
            rumps.notification(
                title="CursorBot",
                subtitle="Error",
                message=f"Failed to send: {e}",
            )
        except Exception as e:
            rumps.notification(
                title="CursorBot",
                subtitle="Error",
                message=str(e),
            )
    
    def _add_recent(self, message: str) -> None:
        """Add message to recent list."""
        # Truncate long messages
        display = message[:30] + "..." if len(message) > 30 else message
        
        # Remove duplicates
        if display in self._recent_chats:
            self._recent_chats.remove(display)
        
        # Add to front
        self._recent_chats.insert(0, display)
        
        # Keep only 5 recent
        self._recent_chats = self._recent_chats[:5]
        
        # Update menu (simplified approach)
        # Note: Full menu update would require rebuilding
    
    def _new_conversation(self, _) -> None:
        """Start a new conversation."""
        self._quick_chat(None)
    
    def _open_dashboard(self, _) -> None:
        """Open web dashboard in browser."""
        import webbrowser
        webbrowser.open(f"{self.server_url}/dashboard")
    
    def _open_settings(self, _) -> None:
        """Open settings in browser."""
        import webbrowser
        webbrowser.open(f"{self.server_url}/control")
    
    def _show_about(self, _) -> None:
        """Show about dialog."""
        rumps.alert(
            title="About CursorBot",
            message=(
                "CursorBot Menu Bar App\n\n"
                "A multi-platform AI assistant that integrates with "
                "Telegram, Discord, WhatsApp, and more.\n\n"
                "Version: 0.3.0\n"
                f"Server: {self.server_url}"
            ),
            ok="OK",
        )
    
    def _quit(self, _) -> None:
        """Quit the application."""
        rumps.quit_application()


def run_menubar(server_url: str = None) -> None:
    """
    Run the menu bar application.
    
    Args:
        server_url: CursorBot server URL (default: http://localhost:8000)
    """
    url = server_url or os.getenv("CURSORBOT_SERVER_URL", "http://localhost:8000")
    app = CursorBotMenuBar(server_url=url)
    app.run()


def create_launch_agent() -> str:
    """
    Create a macOS Launch Agent plist for auto-start.
    
    Returns:
        Path to the created plist file
    """
    import os
    import pwd
    
    username = pwd.getpwuid(os.getuid()).pw_name
    plist_dir = os.path.expanduser("~/Library/LaunchAgents")
    plist_path = os.path.join(plist_dir, "com.cursorbot.menubar.plist")
    
    # Get Python path from venv
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    python_path = os.path.join(project_root, "venv", "bin", "python")
    if not os.path.exists(python_path):
        import sys
        python_path = sys.executable
    
    script_path = os.path.abspath(__file__)
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.cursorbot.menubar</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/tmp/cursorbot-menubar.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/cursorbot-menubar.err</string>
</dict>
</plist>
"""
    
    # Ensure directory exists
    os.makedirs(plist_dir, exist_ok=True)
    
    # Write plist
    with open(plist_path, "w") as f:
        f.write(plist_content)
    
    print(f"Created Launch Agent: {plist_path}")
    print("To enable auto-start, run:")
    print(f"  launchctl load {plist_path}")
    print("To disable:")
    print(f"  launchctl unload {plist_path}")
    
    return plist_path


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--install":
        create_launch_agent()
    else:
        run_menubar()
