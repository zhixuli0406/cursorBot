"""
Terminal User Interface (TUI) for CursorBot

Provides:
- Interactive terminal chat interface
- Real-time status display
- Session management
- Command palette
"""

import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

from ..utils.logger import logger


class TUIMode(Enum):
    """TUI display modes."""
    CHAT = "chat"
    STATUS = "status"
    LOGS = "logs"
    HELP = "help"


@dataclass
class ChatMessage:
    """Chat message for TUI."""
    role: str
    content: str
    timestamp: datetime


class CursorBotTUI:
    """
    Terminal User Interface for CursorBot.
    """
    
    def __init__(self):
        self._mode = TUIMode.CHAT
        self._messages: list[ChatMessage] = []
        self._input_buffer = ""
        self._running = False
        self._status = "Ready"
        self._llm_handler: Optional[Callable] = None
    
    # ============================================
    # Main Interface
    # ============================================
    
    async def run(self) -> None:
        """Run the TUI interface."""
        self._running = True
        
        # Try to use rich library for better formatting
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.layout import Layout
            from rich.live import Live
            from rich.markdown import Markdown
            from rich.prompt import Prompt
            
            self._console = Console()
            await self._run_rich_tui()
        except ImportError:
            # Fallback to basic TUI
            await self._run_basic_tui()
    
    async def _run_rich_tui(self) -> None:
        """Run TUI with rich library."""
        from rich.console import Console
        from rich.panel import Panel
        from rich.markdown import Markdown
        from rich.prompt import Prompt
        from rich.text import Text
        from rich.table import Table
        
        console = self._console
        
        # Welcome message
        console.clear()
        console.print(Panel(
            "[bold cyan]CursorBot Terminal Interface[/bold cyan]\\n"
            "Type your message and press Enter. Commands: /help, /status, /clear, /quit",
            title="Welcome",
            border_style="cyan",
        ))
        console.print()
        
        while self._running:
            try:
                # Get input
                user_input = Prompt.ask("[bold green]You[/bold green]")
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue
                
                # Store user message
                self._messages.append(ChatMessage(
                    role="user",
                    content=user_input,
                    timestamp=datetime.now(),
                ))
                
                # Get AI response
                console.print("[dim]Thinking...[/dim]", end="\\r")
                
                response = await self._get_response(user_input)
                
                # Clear thinking message and show response
                console.print(" " * 20, end="\\r")
                
                self._messages.append(ChatMessage(
                    role="assistant",
                    content=response,
                    timestamp=datetime.now(),
                ))
                
                # Display response
                console.print()
                console.print(Panel(
                    Markdown(response),
                    title="[bold blue]CursorBot[/bold blue]",
                    border_style="blue",
                ))
                console.print()
                
            except KeyboardInterrupt:
                console.print("\\n[yellow]Use /quit to exit[/yellow]")
            except EOFError:
                break
        
        console.print("[cyan]Goodbye![/cyan]")
    
    async def _run_basic_tui(self) -> None:
        """Run basic TUI without rich library."""
        print("=" * 50)
        print("  CursorBot Terminal Interface")
        print("  Commands: /help, /status, /clear, /quit")
        print("=" * 50)
        print()
        
        while self._running:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue
                
                # Store message
                self._messages.append(ChatMessage(
                    role="user",
                    content=user_input,
                    timestamp=datetime.now(),
                ))
                
                # Get response
                print("Thinking...", end="\\r")
                response = await self._get_response(user_input)
                print(" " * 20, end="\\r")
                
                self._messages.append(ChatMessage(
                    role="assistant",
                    content=response,
                    timestamp=datetime.now(),
                ))
                
                print(f"\\nCursorBot: {response}\\n")
                
            except KeyboardInterrupt:
                print("\\nUse /quit to exit")
            except EOFError:
                break
        
        print("Goodbye!")
    
    # ============================================
    # Commands
    # ============================================
    
    async def _handle_command(self, cmd: str) -> None:
        """Handle TUI command."""
        parts = cmd.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if command == "/quit" or command == "/exit":
            self._running = False
            
        elif command == "/help":
            self._show_help()
            
        elif command == "/clear":
            self._clear_screen()
            self._messages.clear()
            print("Chat cleared.")
            
        elif command == "/status":
            await self._show_status()
            
        elif command == "/history":
            self._show_history()
            
        elif command == "/model":
            if args:
                await self._set_model(args[0])
            else:
                await self._show_models()
            
        elif command == "/export":
            filename = args[0] if args else "chat_export.txt"
            self._export_chat(filename)
            
        else:
            print(f"Unknown command: {command}")
            print("Type /help for available commands")
    
    def _show_help(self) -> None:
        """Show help information."""
        help_text = """
Available Commands:
  /help      - Show this help message
  /status    - Show bot status
  /clear     - Clear chat history
  /history   - Show chat history
  /model     - Show/set current model
  /export    - Export chat to file
  /quit      - Exit the TUI
        """
        
        try:
            from rich.panel import Panel
            self._console.print(Panel(help_text, title="Help", border_style="yellow"))
        except:
            print(help_text)
    
    async def _show_status(self) -> None:
        """Show bot status."""
        try:
            from ..core.llm_providers import get_llm_manager
            from ..core.context import get_context_manager
            
            llm = get_llm_manager()
            ctx = get_context_manager()
            
            status_text = f"""
Status: {self._status}
Current Model: {llm.current_model or 'default'}
Active Sessions: {len(ctx._contexts)}
Messages in Chat: {len(self._messages)}
            """
            
            try:
                from rich.panel import Panel
                self._console.print(Panel(status_text, title="Status", border_style="green"))
            except:
                print(status_text)
                
        except Exception as e:
            print(f"Status error: {e}")
    
    def _show_history(self) -> None:
        """Show chat history."""
        if not self._messages:
            print("No messages in history.")
            return
        
        print("\\n--- Chat History ---")
        for msg in self._messages[-20:]:
            role = "You" if msg.role == "user" else "Bot"
            time_str = msg.timestamp.strftime("%H:%M")
            print(f"[{time_str}] {role}: {msg.content[:100]}...")
        print("--- End ---\\n")
    
    async def _show_models(self) -> None:
        """Show available models."""
        try:
            from ..core.llm_providers import get_llm_manager
            llm = get_llm_manager()
            
            print(f"\\nCurrent model: {llm.current_model}")
            print("\\nAvailable providers:")
            for p in llm._providers.keys():
                print(f"  - {p.value}")
        except Exception as e:
            print(f"Error: {e}")
    
    async def _set_model(self, model: str) -> None:
        """Set current model."""
        try:
            from ..core.llm_providers import get_llm_manager
            llm = get_llm_manager()
            llm._default_model = model
            print(f"Model set to: {model}")
        except Exception as e:
            print(f"Error: {e}")
    
    def _export_chat(self, filename: str) -> None:
        """Export chat to file."""
        try:
            with open(filename, "w") as f:
                f.write("CursorBot Chat Export\\n")
                f.write(f"Date: {datetime.now().isoformat()}\\n")
                f.write("=" * 50 + "\\n\\n")
                
                for msg in self._messages:
                    role = "You" if msg.role == "user" else "CursorBot"
                    time_str = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{time_str}] {role}:\\n{msg.content}\\n\\n")
            
            print(f"Chat exported to {filename}")
        except Exception as e:
            print(f"Export error: {e}")
    
    def _clear_screen(self) -> None:
        """Clear the terminal screen."""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
    
    # ============================================
    # LLM Integration
    # ============================================
    
    async def _get_response(self, user_input: str) -> str:
        """Get response from LLM."""
        try:
            if self._llm_handler:
                return await self._llm_handler(user_input)
            
            # Default: use LLM manager
            from ..core.llm_providers import get_llm_manager
            
            llm = get_llm_manager()
            
            # Build messages
            messages = [{"role": "system", "content": "You are CursorBot, a helpful AI assistant."}]
            
            for msg in self._messages[-10:]:
                messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })
            
            messages.append({"role": "user", "content": user_input})
            
            response = await llm.generate(messages)
            return response
            
        except Exception as e:
            logger.error(f"TUI response error: {e}")
            return f"Error: {e}"
    
    def set_llm_handler(self, handler: Callable) -> None:
        """Set custom LLM handler."""
        self._llm_handler = handler


# ============================================
# Entry Point
# ============================================

async def run_tui():
    """Run the TUI."""
    tui = CursorBotTUI()
    await tui.run()


def main():
    """CLI entry point."""
    asyncio.run(run_tui())


__all__ = [
    "CursorBotTUI",
    "TUIMode",
    "run_tui",
    "main",
]
