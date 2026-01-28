"""
DM Pairing - v0.4 Advanced Feature
Device pairing mechanism using codes or QR codes.

Features:
    - Generate pairing codes for device linking
    - QR code generation for easy mobile pairing
    - Time-limited pairing codes
    - Secure device registration
    - Multi-device support per user
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import asyncio
import hashlib
import secrets
import json
import base64

from ..utils.logger import logger


class DeviceType(Enum):
    """Types of paired devices."""
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"
    WEB = "web"
    CLI = "cli"
    IOT = "iot"


class PairingStatus(Enum):
    """Status of a pairing request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    USED = "used"


@dataclass
class PairingCode:
    """A pairing code for device linking."""
    code: str
    user_id: str
    device_name: str
    device_type: DeviceType
    status: PairingStatus = PairingStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = None
    used_at: datetime = None
    ip_address: str = None
    user_agent: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(minutes=5)
    
    @property
    def is_expired(self) -> bool:
        """Check if code has expired."""
        return datetime.now() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if code is still valid."""
        return self.status == PairingStatus.PENDING and not self.is_expired
    
    @property
    def remaining_seconds(self) -> int:
        """Get remaining seconds before expiration."""
        if self.is_expired:
            return 0
        delta = self.expires_at - datetime.now()
        return max(0, int(delta.total_seconds()))
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "code": self.code,
            "user_id": self.user_id,
            "device_name": self.device_name,
            "device_type": self.device_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "remaining_seconds": self.remaining_seconds,
            "ip_address": self.ip_address,
        }


@dataclass
class PairedDevice:
    """A paired device."""
    device_id: str
    user_id: str
    device_name: str
    device_type: DeviceType
    paired_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = None
    is_active: bool = True
    push_token: str = None  # For push notifications
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = self.paired_at
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "device_id": self.device_id,
            "user_id": self.user_id,
            "device_name": self.device_name,
            "device_type": self.device_type.value,
            "paired_at": self.paired_at.isoformat(),
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "is_active": self.is_active,
            "capabilities": self.capabilities,
        }


class DMPairingManager:
    """
    Manager for device pairing.
    
    Usage:
        manager = get_dm_pairing_manager()
        
        # Generate pairing code
        code = manager.generate_code(
            user_id="user123",
            device_name="My iPhone",
            device_type=DeviceType.MOBILE,
        )
        print(f"Enter this code: {code.code}")
        
        # Generate QR code
        qr_data = manager.generate_qr_code(code)
        
        # Complete pairing
        device = manager.complete_pairing(code.code, device_info)
        
        # List paired devices
        devices = manager.get_user_devices(user_id)
    """
    
    _instance: Optional["DMPairingManager"] = None
    
    def __init__(self):
        self._pending_codes: Dict[str, PairingCode] = {}
        self._devices: Dict[str, PairedDevice] = {}  # device_id -> device
        self._user_devices: Dict[str, List[str]] = {}  # user_id -> [device_ids]
        self._data_path = "data/dm_pairing.json"
        self._code_length = 6
        self._code_expiry_minutes = 5
        self._max_devices_per_user = 10
        self._load_data()
    
    def _load_data(self):
        """Load pairing data from disk."""
        try:
            import os
            if os.path.exists(self._data_path):
                with open(self._data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    for device_data in data.get("devices", []):
                        device = PairedDevice(
                            device_id=device_data["device_id"],
                            user_id=device_data["user_id"],
                            device_name=device_data["device_name"],
                            device_type=DeviceType(device_data["device_type"]),
                            paired_at=datetime.fromisoformat(device_data["paired_at"]),
                            is_active=device_data.get("is_active", True),
                            capabilities=device_data.get("capabilities", []),
                        )
                        self._devices[device.device_id] = device
                        
                        if device.user_id not in self._user_devices:
                            self._user_devices[device.user_id] = []
                        self._user_devices[device.user_id].append(device.device_id)
                
                logger.debug(f"Loaded {len(self._devices)} paired devices")
        except Exception as e:
            logger.warning(f"Failed to load pairing data: {e}")
    
    def _save_data(self):
        """Save pairing data to disk."""
        try:
            import os
            os.makedirs(os.path.dirname(self._data_path), exist_ok=True)
            
            data = {
                "devices": [device.to_dict() for device in self._devices.values()],
            }
            
            with open(self._data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save pairing data: {e}")
    
    def _generate_code_string(self) -> str:
        """Generate a random pairing code."""
        # Generate numeric code for easy typing
        return "".join(str(secrets.randbelow(10)) for _ in range(self._code_length))
    
    def _generate_device_id(self, user_id: str, device_name: str) -> str:
        """Generate unique device ID."""
        unique = f"{user_id}:{device_name}:{datetime.now().isoformat()}:{secrets.token_hex(8)}"
        return hashlib.sha256(unique.encode()).hexdigest()[:16]
    
    def generate_code(
        self,
        user_id: str,
        device_name: str,
        device_type: DeviceType = DeviceType.MOBILE,
        expiry_minutes: int = None,
    ) -> PairingCode:
        """
        Generate a new pairing code.
        
        Args:
            user_id: User requesting the pairing
            device_name: Name for the new device
            device_type: Type of device
            expiry_minutes: Code expiry time (default: 5 minutes)
        """
        # Check device limit
        user_device_ids = self._user_devices.get(user_id, [])
        active_devices = [
            self._devices[did] for did in user_device_ids
            if did in self._devices and self._devices[did].is_active
        ]
        
        if len(active_devices) >= self._max_devices_per_user:
            raise ValueError(f"Maximum devices ({self._max_devices_per_user}) reached")
        
        # Generate unique code
        code_str = self._generate_code_string()
        while code_str in self._pending_codes:
            code_str = self._generate_code_string()
        
        expiry = expiry_minutes or self._code_expiry_minutes
        
        code = PairingCode(
            code=code_str,
            user_id=user_id,
            device_name=device_name,
            device_type=device_type,
            expires_at=datetime.now() + timedelta(minutes=expiry),
        )
        
        self._pending_codes[code_str] = code
        logger.info(f"Generated pairing code for user {user_id}: {code_str[:3]}***")
        
        # Schedule cleanup
        asyncio.create_task(self._cleanup_expired_code(code_str, expiry * 60 + 10))
        
        return code
    
    async def _cleanup_expired_code(self, code: str, delay: int):
        """Cleanup expired code after delay."""
        await asyncio.sleep(delay)
        if code in self._pending_codes:
            pending = self._pending_codes[code]
            if pending.is_expired:
                pending.status = PairingStatus.EXPIRED
                del self._pending_codes[code]
    
    def generate_qr_data(self, code: PairingCode) -> str:
        """
        Generate QR code data for pairing.
        
        Returns a URL/data string for QR code generation.
        """
        # Create pairing data
        data = {
            "type": "cursorbot_pair",
            "code": code.code,
            "user": code.user_id[:8],  # Partial user ID
            "device": code.device_name,
            "exp": int(code.expires_at.timestamp()),
        }
        
        # Encode as base64 for QR code
        json_str = json.dumps(data, separators=(',', ':'))
        encoded = base64.urlsafe_b64encode(json_str.encode()).decode()
        
        # Return as cursorbot:// deep link
        return f"cursorbot://pair?data={encoded}"
    
    def generate_qr_code_svg(self, code: PairingCode) -> str:
        """
        Generate QR code as SVG string.
        
        Requires qrcode library.
        """
        try:
            import qrcode
            import qrcode.image.svg
            from io import BytesIO
            
            qr_data = self.generate_qr_data(code)
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            factory = qrcode.image.svg.SvgImage
            img = qr.make_image(fill_color="black", back_color="white", image_factory=factory)
            
            buffer = BytesIO()
            img.save(buffer)
            return buffer.getvalue().decode()
            
        except ImportError:
            logger.warning("qrcode library not installed, returning data URL instead")
            return self.generate_qr_data(code)
    
    def verify_code(self, code_str: str) -> Optional[PairingCode]:
        """Verify a pairing code."""
        code = self._pending_codes.get(code_str)
        
        if not code:
            return None
        
        if code.is_expired:
            code.status = PairingStatus.EXPIRED
            return None
        
        if code.status != PairingStatus.PENDING:
            return None
        
        return code
    
    def complete_pairing(
        self,
        code_str: str,
        ip_address: str = None,
        user_agent: str = None,
        push_token: str = None,
        capabilities: List[str] = None,
    ) -> Optional[PairedDevice]:
        """
        Complete the pairing process.
        
        Args:
            code_str: The pairing code
            ip_address: IP address of the device
            user_agent: User agent string
            push_token: Push notification token
            capabilities: List of device capabilities
            
        Returns:
            PairedDevice if successful, None otherwise
        """
        code = self.verify_code(code_str)
        
        if not code:
            return None
        
        # Mark code as used
        code.status = PairingStatus.USED
        code.used_at = datetime.now()
        code.ip_address = ip_address
        code.user_agent = user_agent
        
        # Create device
        device_id = self._generate_device_id(code.user_id, code.device_name)
        
        device = PairedDevice(
            device_id=device_id,
            user_id=code.user_id,
            device_name=code.device_name,
            device_type=code.device_type,
            push_token=push_token,
            capabilities=capabilities or [],
        )
        
        # Store device
        self._devices[device_id] = device
        
        if code.user_id not in self._user_devices:
            self._user_devices[code.user_id] = []
        self._user_devices[code.user_id].append(device_id)
        
        # Cleanup code
        del self._pending_codes[code_str]
        
        # Save
        self._save_data()
        
        logger.info(f"Device paired: {device_id} for user {code.user_id}")
        return device
    
    def get_device(self, device_id: str) -> Optional[PairedDevice]:
        """Get a device by ID."""
        return self._devices.get(device_id)
    
    def get_user_devices(self, user_id: str, active_only: bool = True) -> List[PairedDevice]:
        """Get all devices for a user."""
        device_ids = self._user_devices.get(user_id, [])
        devices = [self._devices[did] for did in device_ids if did in self._devices]
        
        if active_only:
            devices = [d for d in devices if d.is_active]
        
        return devices
    
    def update_last_seen(self, device_id: str):
        """Update last seen timestamp for a device."""
        device = self._devices.get(device_id)
        if device:
            device.last_seen = datetime.now()
    
    def unpair_device(self, device_id: str, user_id: str = None) -> bool:
        """
        Unpair a device.
        
        Args:
            device_id: Device to unpair
            user_id: Optional user ID for verification
        """
        device = self._devices.get(device_id)
        
        if not device:
            return False
        
        if user_id and device.user_id != user_id:
            return False
        
        # Mark as inactive (soft delete)
        device.is_active = False
        self._save_data()
        
        logger.info(f"Device unpaired: {device_id}")
        return True
    
    def unpair_all_devices(self, user_id: str) -> int:
        """Unpair all devices for a user."""
        devices = self.get_user_devices(user_id, active_only=True)
        
        for device in devices:
            device.is_active = False
        
        self._save_data()
        return len(devices)
    
    def get_status_message(self, user_id: str) -> str:
        """Get formatted status message."""
        devices = self.get_user_devices(user_id)
        pending = [c for c in self._pending_codes.values() if c.user_id == user_id and c.is_valid]
        
        lines = [
            "📱 **Device Pairing**",
            "",
            f"Paired Devices: {len(devices)}/{self._max_devices_per_user}",
            "",
        ]
        
        if devices:
            lines.append("**Your Devices:**")
            for device in devices:
                type_icon = {
                    DeviceType.DESKTOP: "🖥️",
                    DeviceType.MOBILE: "📱",
                    DeviceType.TABLET: "📱",
                    DeviceType.WEB: "🌐",
                    DeviceType.CLI: "💻",
                    DeviceType.IOT: "🔌",
                }.get(device.device_type, "📱")
                
                last_seen = "Now" if (datetime.now() - device.last_seen).seconds < 300 else device.last_seen.strftime("%Y-%m-%d")
                lines.append(f"{type_icon} {device.device_name} (Last: {last_seen})")
        else:
            lines.append("No devices paired yet.")
        
        if pending:
            lines.extend([
                "",
                "**Pending Codes:**",
            ])
            for code in pending:
                lines.append(f"• `{code.code}` - {code.device_name} ({code.remaining_seconds}s remaining)")
        
        lines.extend([
            "",
            "**Commands:**",
            "/pair - Generate pairing code",
            "/pair qr - Generate QR code",
            "/devices - List devices",
            "/unpair <device_id> - Unpair device",
        ])
        
        return "\n".join(lines)


# Singleton instance
_dm_pairing_manager: Optional[DMPairingManager] = None


def get_dm_pairing_manager() -> DMPairingManager:
    """Get the global DM pairing manager instance."""
    global _dm_pairing_manager
    if _dm_pairing_manager is None:
        _dm_pairing_manager = DMPairingManager()
    return _dm_pairing_manager


def reset_dm_pairing_manager():
    """Reset the manager (for testing)."""
    global _dm_pairing_manager
    _dm_pairing_manager = None


__all__ = [
    "DeviceType",
    "PairingStatus",
    "PairingCode",
    "PairedDevice",
    "DMPairingManager",
    "get_dm_pairing_manager",
    "reset_dm_pairing_manager",
]
