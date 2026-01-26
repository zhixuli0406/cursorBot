#!/usr/bin/env python3
"""
Standalone MCP Server runner
Run this in a separate terminal to provide MCP services to CursorBot
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.cursor.mcp_server import run_mcp_server


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════╗
    ║                                               ║
    ║   🔌 CursorBot MCP Server                     ║
    ║                                               ║
    ║   Provides local MCP services                 ║
    ║                                               ║
    ╚═══════════════════════════════════════════════╝
    """)

    try:
        asyncio.run(run_mcp_server())
    except KeyboardInterrupt:
        print("\nMCP Server stopped")
