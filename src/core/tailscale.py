"""
Tailscale VPN Integration for CursorBot

Provides:
- Tailscale network status
- Device management
- Secure remote access
- Network discovery
"""

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from ..utils.logger import logger


class TailscaleStatus(Enum):
    """Tailscale connection status."""
    NOT_INSTALLED = "not_installed"
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    NEEDS_LOGIN = "needs_login"
    ERROR = "error"


@dataclass
class TailscaleDevice:
    """Represents a Tailscale device."""
    id: str
    hostname: str
    name: str
    ip_addresses: list[str]
    os: str
    online: bool
    last_seen: Optional[datetime] = None
    tags: list[str] = field(default_factory=list)
    is_self: bool = False


@dataclass
class TailscaleNetwork:
    """Tailscale network information."""
    name: str
    magic_dns_suffix: str
    devices: list[TailscaleDevice] = field(default_factory=list)


@dataclass
class TailscaleConfig:
    """Tailscale configuration."""
    # API settings
    api_key: str = ""
    tailnet: str = ""  # e.g., "example.com" or "example@gmail.com"
    
    # CLI settings
    use_cli: bool = True  # Use CLI instead of API
    tailscale_path: str = "tailscale"  # Path to tailscale binary
    
    # Features
    accept_dns: bool = True
    accept_routes: bool = True
    shields_up: bool = False  # Block incoming connections


class TailscaleManager:
    """
    Manages Tailscale VPN integration.
    
    Can use either:
    - Tailscale CLI (local machine)
    - Tailscale API (remote management)
    """
    
    def __init__(self, config: TailscaleConfig = None):
        self.config = config or TailscaleConfig(
            api_key=os.getenv("TAILSCALE_API_KEY", ""),
            tailnet=os.getenv("TAILSCALE_TAILNET", ""),
        )
        self._status = TailscaleStatus.STOPPED
        self._http_client = None
    
    # ============================================
    # Status & Info
    # ============================================
    
    async def get_status(self) -> TailscaleStatus:
        """Get Tailscale status."""
        if self.config.use_cli:
            return await self._get_cli_status()
        return await self._get_api_status()
    
    async def _get_cli_status(self) -> TailscaleStatus:
        """Get status via CLI."""
        try:
            result = await self._run_cli("status", "--json")
            
            if result is None:
                return TailscaleStatus.NOT_INSTALLED
            
            data = json.loads(result)
            
            if data.get("BackendState") == "Running":
                self._status = TailscaleStatus.RUNNING
            elif data.get("BackendState") == "NeedsLogin":
                self._status = TailscaleStatus.NEEDS_LOGIN
            elif data.get("BackendState") == "Stopped":
                self._status = TailscaleStatus.STOPPED
            else:
                self._status = TailscaleStatus.STARTING
            
            return self._status
            
        except json.JSONDecodeError:
            return TailscaleStatus.ERROR
        except Exception as e:
            logger.error(f"Tailscale status error: {e}")
            return TailscaleStatus.ERROR
    
    async def _get_api_status(self) -> TailscaleStatus:
        """Get status via API."""
        if not self.config.api_key:
            return TailscaleStatus.ERROR
        
        try:
            devices = await self.get_devices()
            if devices:
                self._status = TailscaleStatus.RUNNING
            return self._status
        except Exception as e:
            logger.error(f"API status error: {e}")
            return TailscaleStatus.ERROR
    
    async def get_self(self) -> Optional[TailscaleDevice]:
        """Get current device info."""
        try:
            result = await self._run_cli("status", "--json")
            if not result:
                return None
            
            data = json.loads(result)
            self_info = data.get("Self", {})
            
            return TailscaleDevice(
                id=self_info.get("ID", ""),
                hostname=self_info.get("HostName", ""),
                name=self_info.get("DNSName", "").split(".")[0],
                ip_addresses=self_info.get("TailscaleIPs", []),
                os=self_info.get("OS", ""),
                online=self_info.get("Online", False),
                is_self=True,
            )
            
        except Exception as e:
            logger.error(f"Get self error: {e}")
            return None
    
    # ============================================
    # Device Management
    # ============================================
    
    async def get_devices(self) -> list[TailscaleDevice]:
        """Get all devices in tailnet."""
        if self.config.use_cli:
            return await self._get_devices_cli()
        return await self._get_devices_api()
    
    async def _get_devices_cli(self) -> list[TailscaleDevice]:
        """Get devices via CLI."""
        try:
            result = await self._run_cli("status", "--json")
            if not result:
                return []
            
            data = json.loads(result)
            devices = []
            
            # Add self
            self_info = data.get("Self", {})
            if self_info:
                devices.append(TailscaleDevice(
                    id=self_info.get("ID", ""),
                    hostname=self_info.get("HostName", ""),
                    name=self_info.get("DNSName", "").split(".")[0],
                    ip_addresses=self_info.get("TailscaleIPs", []),
                    os=self_info.get("OS", ""),
                    online=True,
                    is_self=True,
                ))
            
            # Add peers
            for peer_id, peer in data.get("Peer", {}).items():
                devices.append(TailscaleDevice(
                    id=peer_id,
                    hostname=peer.get("HostName", ""),
                    name=peer.get("DNSName", "").split(".")[0],
                    ip_addresses=peer.get("TailscaleIPs", []),
                    os=peer.get("OS", ""),
                    online=peer.get("Online", False),
                    last_seen=datetime.fromisoformat(peer["LastSeen"]) if peer.get("LastSeen") else None,
                ))
            
            return devices
            
        except Exception as e:
            logger.error(f"Get devices CLI error: {e}")
            return []
    
    async def _get_devices_api(self) -> list[TailscaleDevice]:
        """Get devices via API."""
        if not self.config.api_key or not self.config.tailnet:
            return []
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.tailscale.com/api/v2/tailnet/{self.config.tailnet}/devices",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                    timeout=30,
                )
                
                if response.status_code != 200:
                    logger.error(f"API error: {response.status_code}")
                    return []
                
                data = response.json()
                devices = []
                
                for device in data.get("devices", []):
                    devices.append(TailscaleDevice(
                        id=device.get("id", ""),
                        hostname=device.get("hostname", ""),
                        name=device.get("name", ""),
                        ip_addresses=device.get("addresses", []),
                        os=device.get("os", ""),
                        online=device.get("online", False),
                        last_seen=datetime.fromisoformat(device["lastSeen"].replace("Z", "+00:00")) if device.get("lastSeen") else None,
                        tags=device.get("tags", []),
                    ))
                
                return devices
                
        except Exception as e:
            logger.error(f"Get devices API error: {e}")
            return []
    
    async def find_device(self, name: str) -> Optional[TailscaleDevice]:
        """Find device by name or hostname."""
        devices = await self.get_devices()
        
        for device in devices:
            if device.name.lower() == name.lower():
                return device
            if device.hostname.lower() == name.lower():
                return device
        
        return None
    
    # ============================================
    # Connection Management
    # ============================================
    
    async def connect(self, authkey: str = None) -> bool:
        """
        Connect to Tailscale network.
        
        Args:
            authkey: Optional auth key for automated login
        
        Returns:
            True if connected successfully
        """
        try:
            args = ["up"]
            
            if authkey:
                args.extend(["--authkey", authkey])
            
            if self.config.accept_dns:
                args.append("--accept-dns")
            
            if self.config.accept_routes:
                args.append("--accept-routes")
            
            if self.config.shields_up:
                args.append("--shields-up")
            
            result = await self._run_cli(*args)
            
            # Check status
            await asyncio.sleep(2)
            status = await self.get_status()
            
            return status == TailscaleStatus.RUNNING
            
        except Exception as e:
            logger.error(f"Connect error: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Tailscale network."""
        try:
            await self._run_cli("down")
            self._status = TailscaleStatus.STOPPED
            return True
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
            return False
    
    async def logout(self) -> bool:
        """Log out from Tailscale."""
        try:
            await self._run_cli("logout")
            self._status = TailscaleStatus.NEEDS_LOGIN
            return True
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False
    
    # ============================================
    # Network Operations
    # ============================================
    
    async def ping(self, target: str, count: int = 3) -> Optional[float]:
        """
        Ping a Tailscale device.
        
        Args:
            target: Device name, hostname, or IP
            count: Number of pings
        
        Returns:
            Average latency in ms, or None if failed
        """
        try:
            result = await self._run_cli("ping", "--c", str(count), target)
            
            if not result:
                return None
            
            # Parse ping output
            latencies = []
            for line in result.split("\n"):
                if "in" in line and "ms" in line:
                    # Extract latency
                    parts = line.split("in")
                    if len(parts) > 1:
                        ms = parts[1].strip().replace("ms", "").strip()
                        try:
                            latencies.append(float(ms))
                        except ValueError:
                            pass
            
            if latencies:
                return sum(latencies) / len(latencies)
            return None
            
        except Exception as e:
            logger.error(f"Ping error: {e}")
            return None
    
    async def get_ip(self, ipv4: bool = True) -> Optional[str]:
        """Get Tailscale IP address."""
        try:
            args = ["ip"]
            if ipv4:
                args.append("-4")
            else:
                args.append("-6")
            
            result = await self._run_cli(*args)
            return result.strip() if result else None
            
        except Exception as e:
            logger.error(f"Get IP error: {e}")
            return None
    
    # ============================================
    # CLI Helper
    # ============================================
    
    async def _run_cli(self, *args) -> Optional[str]:
        """Run Tailscale CLI command."""
        try:
            cmd = [self.config.tailscale_path] + list(args)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error = stderr.decode().strip()
                if "command not found" in error or "not found" in error:
                    return None
                logger.warning(f"CLI warning: {error}")
            
            return stdout.decode().strip()
            
        except FileNotFoundError:
            logger.warning("Tailscale CLI not found")
            return None
        except Exception as e:
            logger.error(f"CLI error: {e}")
            return None
    
    # ============================================
    # Status Properties
    # ============================================
    
    @property
    def status(self) -> TailscaleStatus:
        return self._status
    
    @property
    def is_connected(self) -> bool:
        return self._status == TailscaleStatus.RUNNING
    
    def get_stats(self) -> dict:
        return {
            "status": self._status.value,
            "use_cli": self.config.use_cli,
            "has_api_key": bool(self.config.api_key),
            "tailnet": self.config.tailnet,
        }


# ============================================
# Global Instance
# ============================================

_tailscale_manager: Optional[TailscaleManager] = None


def get_tailscale_manager() -> TailscaleManager:
    """Get global Tailscale manager instance."""
    global _tailscale_manager
    if _tailscale_manager is None:
        _tailscale_manager = TailscaleManager()
    return _tailscale_manager


__all__ = [
    "TailscaleStatus",
    "TailscaleDevice",
    "TailscaleNetwork",
    "TailscaleConfig",
    "TailscaleManager",
    "get_tailscale_manager",
]
