#!/usr/bin/env python3
"""
Interactive Setup Wizard - v0.4 Feature
Guided setup experience for CursorBot.

Usage:
    ./cursorbot setup
    python -m src.cli.setup
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
import json
import re

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class Colors:
    """ANSI color codes."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_header(text: str):
    """Print header text."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")


def print_step(step: int, total: int, text: str):
    """Print step indicator."""
    print(f"\n{Colors.YELLOW}[Step {step}/{total}]{Colors.END} {Colors.BOLD}{text}{Colors.END}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def prompt(text: str, default: str = None, required: bool = False) -> str:
    """Prompt for input."""
    if default:
        display = f"{text} [{default}]: "
    else:
        display = f"{text}: "
    
    while True:
        value = input(display).strip()
        
        if not value:
            if default:
                return default
            if required:
                print_error("This field is required")
                continue
            return ""
        
        return value


def prompt_yes_no(text: str, default: bool = True) -> bool:
    """Prompt for yes/no."""
    default_str = "Y/n" if default else "y/N"
    response = input(f"{text} [{default_str}]: ").strip().lower()
    
    if not response:
        return default
    
    return response in ('y', 'yes', '1', 'true')


def prompt_choice(text: str, choices: list, default: int = 0) -> str:
    """Prompt for choice from list."""
    print(f"\n{text}")
    for i, choice in enumerate(choices):
        marker = ">" if i == default else " "
        print(f"  {marker} {i + 1}. {choice}")
    
    while True:
        response = input(f"Enter choice [1-{len(choices)}]: ").strip()
        
        if not response:
            return choices[default]
        
        try:
            idx = int(response) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            pass
        
        print_error(f"Please enter a number between 1 and {len(choices)}")


def validate_telegram_token(token: str) -> bool:
    """Validate Telegram bot token format."""
    return bool(re.match(r'^\d+:[A-Za-z0-9_-]{35,}$', token))


def validate_api_key(key: str, prefix: str = "") -> bool:
    """Validate API key format."""
    if prefix:
        return key.startswith(prefix) and len(key) > len(prefix) + 10
    return len(key) >= 20


class SetupWizard:
    """Interactive setup wizard for CursorBot."""
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.env_file = Path(".env")
        self.total_steps = 6
    
    def run(self):
        """Run the setup wizard."""
        print_header("CursorBot Setup Wizard")
        
        print(f"""
Welcome to CursorBot!

This wizard will help you configure CursorBot step by step.
You can press Enter to accept default values shown in [brackets].

Let's get started!
        """)
        
        try:
            # Step 1: Telegram
            self._setup_telegram()
            
            # Step 2: AI Provider
            self._setup_ai_provider()
            
            # Step 3: Workspace
            self._setup_workspace()
            
            # Step 4: Optional platforms
            self._setup_optional_platforms()
            
            # Step 5: Advanced settings
            self._setup_advanced()
            
            # Step 6: Save and finish
            self._finish()
            
        except KeyboardInterrupt:
            print("\n\n")
            print_warning("Setup cancelled")
            sys.exit(1)
    
    def _setup_telegram(self):
        """Setup Telegram bot."""
        print_step(1, self.total_steps, "Telegram Bot Setup")
        
        print("""
To use CursorBot, you need a Telegram bot token.

1. Open Telegram and search for @BotFather
2. Send /newbot and follow the instructions
3. Copy the API token provided
        """)
        
        while True:
            token = prompt("Telegram Bot Token", required=True)
            
            if validate_telegram_token(token):
                self.config["TELEGRAM_BOT_TOKEN"] = token
                print_success("Token format looks valid")
                break
            else:
                print_error("Invalid token format. Should be like: 123456789:ABCdef...")
        
        # Allowed users
        print("""
For security, CursorBot only responds to allowed users.
Enter your Telegram user ID (you can find it using @userinfobot).
        """)
        
        user_id = prompt("Your Telegram User ID", required=True)
        self.config["TELEGRAM_ALLOWED_USERS"] = user_id
        
        print_success("Telegram configured")
    
    def _setup_ai_provider(self):
        """Setup AI provider."""
        print_step(2, self.total_steps, "AI Provider Setup")
        
        print("""
CursorBot supports multiple AI providers:
        """)
        
        provider = prompt_choice(
            "Select your preferred AI provider:",
            [
                "OpenRouter (recommended - access to many models)",
                "OpenAI (GPT-4, GPT-5)",
                "Anthropic (Claude)",
                "Google (Gemini)",
                "Ollama (local models)",
                "Skip for now",
            ],
            default=0,
        )
        
        if "OpenRouter" in provider:
            self._setup_openrouter()
        elif "OpenAI" in provider:
            self._setup_openai()
        elif "Anthropic" in provider:
            self._setup_anthropic()
        elif "Google" in provider:
            self._setup_google()
        elif "Ollama" in provider:
            self._setup_ollama()
        else:
            print_warning("No AI provider configured. You can add one later in .env")
    
    def _setup_openrouter(self):
        """Setup OpenRouter."""
        print("""
OpenRouter provides access to many AI models with one API key.
Get your API key at: https://openrouter.ai/keys
        """)
        
        key = prompt("OpenRouter API Key", required=True)
        self.config["OPENROUTER_API_KEY"] = key
        
        model = prompt(
            "Model",
            default="google/gemini-2.0-flash-exp:free",
        )
        self.config["OPENROUTER_MODEL"] = model
        
        print_success("OpenRouter configured")
    
    def _setup_openai(self):
        """Setup OpenAI."""
        print("""
Get your OpenAI API key at: https://platform.openai.com/api-keys
        """)
        
        key = prompt("OpenAI API Key", required=True)
        self.config["OPENAI_API_KEY"] = key
        
        model = prompt("Model", default="gpt-4o")
        self.config["OPENAI_MODEL"] = model
        
        print_success("OpenAI configured")
    
    def _setup_anthropic(self):
        """Setup Anthropic."""
        print("""
Get your Anthropic API key at: https://console.anthropic.com/
        """)
        
        key = prompt("Anthropic API Key", required=True)
        self.config["ANTHROPIC_API_KEY"] = key
        
        model = prompt("Model", default="claude-3-5-sonnet-20241022")
        self.config["ANTHROPIC_MODEL"] = model
        
        print_success("Anthropic configured")
    
    def _setup_google(self):
        """Setup Google Gemini."""
        print("""
Get your Google API key at: https://aistudio.google.com/apikey
        """)
        
        key = prompt("Google AI API Key", required=True)
        self.config["GOOGLE_GENERATIVE_AI_API_KEY"] = key
        
        model = prompt("Model", default="gemini-2.0-flash")
        self.config["GOOGLE_MODEL"] = model
        
        print_success("Google Gemini configured")
    
    def _setup_ollama(self):
        """Setup Ollama."""
        print("""
Ollama runs AI models locally.
Install from: https://ollama.ai
        """)
        
        self.config["OLLAMA_ENABLED"] = "true"
        
        api_base = prompt("Ollama API URL", default="http://localhost:11434")
        self.config["OLLAMA_API_BASE"] = api_base
        
        model = prompt("Model", default="llama3.2")
        self.config["OLLAMA_MODEL"] = model
        
        print_success("Ollama configured")
    
    def _setup_workspace(self):
        """Setup workspace path."""
        print_step(3, self.total_steps, "Workspace Setup")
        
        print("""
Set the path to your projects directory.
CursorBot will have access to files in this directory.
        """)
        
        default_path = os.path.expanduser("~/Projects")
        path = prompt("Workspace Path", default=default_path)
        
        # Expand and validate
        path = os.path.expanduser(path)
        
        if os.path.exists(path):
            self.config["CURSOR_WORKSPACE_PATH"] = path
            print_success(f"Workspace set to: {path}")
        else:
            if prompt_yes_no(f"Path doesn't exist. Create it?"):
                os.makedirs(path, exist_ok=True)
                self.config["CURSOR_WORKSPACE_PATH"] = path
                print_success(f"Created and set workspace: {path}")
            else:
                print_warning("Workspace not configured")
    
    def _setup_optional_platforms(self):
        """Setup optional platforms."""
        print_step(4, self.total_steps, "Optional Platforms")
        
        print("""
CursorBot supports multiple platforms. You can configure them later.
        """)
        
        # Discord
        if prompt_yes_no("Configure Discord?", default=False):
            token = prompt("Discord Bot Token")
            if token:
                self.config["DISCORD_ENABLED"] = "true"
                self.config["DISCORD_BOT_TOKEN"] = token
                guild_id = prompt("Discord Guild ID (Server ID)")
                if guild_id:
                    self.config["DISCORD_ALLOWED_GUILDS"] = guild_id
                print_success("Discord configured")
        
        # Skip other platforms for now
        print_info("Other platforms (LINE, Slack, WhatsApp, etc.) can be configured in .env")
    
    def _setup_advanced(self):
        """Setup advanced settings."""
        print_step(5, self.total_steps, "Advanced Settings")
        
        if not prompt_yes_no("Configure advanced settings?", default=False):
            # Set defaults
            self.config["SECRET_KEY"] = os.urandom(32).hex()
            self.config["LOG_LEVEL"] = "INFO"
            print_info("Using default advanced settings")
            return
        
        # Server port
        port = prompt("API Server Port", default="8000")
        self.config["SERVER_PORT"] = port
        
        # Log level
        level = prompt_choice(
            "Log Level:",
            ["DEBUG", "INFO", "WARNING", "ERROR"],
            default=1,
        )
        self.config["LOG_LEVEL"] = level
        
        # Secret key
        self.config["SECRET_KEY"] = os.urandom(32).hex()
        
        print_success("Advanced settings configured")
    
    def _finish(self):
        """Save configuration and finish."""
        print_step(6, self.total_steps, "Finish Setup")
        
        # Check if .env exists
        if self.env_file.exists():
            if not prompt_yes_no(".env file exists. Overwrite?"):
                backup = self.env_file.with_suffix('.env.backup')
                self.env_file.rename(backup)
                print_info(f"Backed up to {backup}")
        
        # Generate .env content
        lines = [
            "# CursorBot Configuration",
            "# Generated by setup wizard",
            "",
        ]
        
        sections = {
            "Telegram": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_USERS"],
            "AI Providers": [
                "OPENROUTER_API_KEY", "OPENROUTER_MODEL",
                "OPENAI_API_KEY", "OPENAI_MODEL",
                "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL",
                "GOOGLE_GENERATIVE_AI_API_KEY", "GOOGLE_MODEL",
                "OLLAMA_ENABLED", "OLLAMA_API_BASE", "OLLAMA_MODEL",
            ],
            "Discord": ["DISCORD_ENABLED", "DISCORD_BOT_TOKEN", "DISCORD_ALLOWED_GUILDS"],
            "Workspace": ["CURSOR_WORKSPACE_PATH"],
            "Server": ["SERVER_PORT", "SERVER_HOST"],
            "Security": ["SECRET_KEY", "LOG_LEVEL"],
        }
        
        for section, keys in sections.items():
            section_lines = []
            for key in keys:
                if key in self.config:
                    section_lines.append(f"{key}={self.config[key]}")
            
            if section_lines:
                lines.append(f"# === {section} ===")
                lines.extend(section_lines)
                lines.append("")
        
        # Write file
        content = "\n".join(lines)
        self.env_file.write_text(content)
        
        print_success(f"Configuration saved to {self.env_file}")
        
        # Summary
        print_header("Setup Complete!")
        
        print("""
Your CursorBot is now configured! Here's what to do next:

1. Start the bot:
   ./start.sh          (Linux/macOS)
   start.bat           (Windows)
   docker compose up   (Docker)

2. Open Telegram and message your bot

3. Send /help to see available commands

For more information, see README.md
        """)
        
        # Show what was configured
        print(f"\n{Colors.BOLD}Configured:{Colors.END}")
        if "TELEGRAM_BOT_TOKEN" in self.config:
            print_success("Telegram Bot")
        if any(k in self.config for k in ["OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]):
            print_success("AI Provider")
        if "CURSOR_WORKSPACE_PATH" in self.config:
            print_success("Workspace")
        if "DISCORD_ENABLED" in self.config:
            print_success("Discord")


def main():
    """Main entry point."""
    wizard = SetupWizard()
    wizard.run()


if __name__ == "__main__":
    main()
