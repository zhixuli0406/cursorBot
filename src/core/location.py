"""
Location Services for CursorBot

Provides:
- Location sharing and storage
- Geocoding and reverse geocoding
- Distance calculations
- Location-based features
"""

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..utils.logger import logger


@dataclass
class Location:
    """Represents a geographic location."""
    latitude: float
    longitude: float
    accuracy: float = 0  # meters
    altitude: float = None
    heading: float = None  # degrees
    speed: float = None  # m/s
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Optional address info
    address: str = ""
    city: str = ""
    country: str = ""
    
    def to_dict(self) -> dict:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy": self.accuracy,
            "altitude": self.altitude,
            "heading": self.heading,
            "speed": self.speed,
            "timestamp": self.timestamp.isoformat(),
            "address": self.address,
            "city": self.city,
            "country": self.country,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Location":
        return cls(
            latitude=data["latitude"],
            longitude=data["longitude"],
            accuracy=data.get("accuracy", 0),
            altitude=data.get("altitude"),
            heading=data.get("heading"),
            speed=data.get("speed"),
            address=data.get("address", ""),
            city=data.get("city", ""),
            country=data.get("country", ""),
        )
    
    def to_google_maps_url(self) -> str:
        """Generate Google Maps URL."""
        return f"https://maps.google.com/?q={self.latitude},{self.longitude}"
    
    def to_osm_url(self) -> str:
        """Generate OpenStreetMap URL."""
        return f"https://www.openstreetmap.org/?mlat={self.latitude}&mlon={self.longitude}&zoom=15"
    
    def distance_to(self, other: "Location") -> float:
        """
        Calculate distance to another location in meters.
        Uses Haversine formula.
        """
        R = 6371000  # Earth's radius in meters
        
        lat1 = math.radians(self.latitude)
        lat2 = math.radians(other.latitude)
        delta_lat = math.radians(other.latitude - self.latitude)
        delta_lon = math.radians(other.longitude - self.longitude)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def bearing_to(self, other: "Location") -> float:
        """Calculate bearing to another location in degrees."""
        lat1 = math.radians(self.latitude)
        lat2 = math.radians(other.latitude)
        delta_lon = math.radians(other.longitude - self.longitude)
        
        x = math.sin(delta_lon) * math.cos(lat2)
        y = (math.cos(lat1) * math.sin(lat2) -
             math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon))
        
        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360


@dataclass
class LocationShare:
    """Represents a shared location."""
    user_id: int
    location: Location
    share_id: str = ""
    expires_at: datetime = None
    live: bool = False  # Live location sharing
    
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "share_id": self.share_id,
            "location": self.location.to_dict(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "live": self.live,
        }


class LocationManager:
    """
    Manages location sharing and services.
    """
    
    def __init__(self):
        self._user_locations: dict[int, Location] = {}
        self._shared_locations: dict[str, LocationShare] = {}
        self._live_shares: dict[int, LocationShare] = {}  # user_id -> active live share
    
    # ============================================
    # Location Storage
    # ============================================
    
    def update_user_location(self, user_id: int, location: Location) -> None:
        """Update a user's current location."""
        self._user_locations[user_id] = location
        
        # Update live share if active
        if user_id in self._live_shares:
            self._live_shares[user_id].location = location
        
        logger.debug(f"Updated location for user {user_id}")
    
    def get_user_location(self, user_id: int) -> Optional[Location]:
        """Get a user's last known location."""
        return self._user_locations.get(user_id)
    
    def clear_user_location(self, user_id: int) -> None:
        """Clear a user's location."""
        self._user_locations.pop(user_id, None)
    
    # ============================================
    # Location Sharing
    # ============================================
    
    def share_location(
        self,
        user_id: int,
        location: Location,
        duration_minutes: int = None,
        live: bool = False,
    ) -> LocationShare:
        """
        Share a location.
        
        Args:
            user_id: User sharing the location
            location: Location to share
            duration_minutes: How long to share (None = permanent)
            live: Whether this is a live location share
        
        Returns:
            LocationShare object
        """
        import uuid
        from datetime import timedelta
        
        share_id = str(uuid.uuid4())[:8]
        
        expires_at = None
        if duration_minutes:
            expires_at = datetime.now() + timedelta(minutes=duration_minutes)
        
        share = LocationShare(
            user_id=user_id,
            location=location,
            share_id=share_id,
            expires_at=expires_at,
            live=live,
        )
        
        self._shared_locations[share_id] = share
        
        if live:
            self._live_shares[user_id] = share
        
        logger.info(f"User {user_id} shared location (id: {share_id}, live: {live})")
        return share
    
    def get_shared_location(self, share_id: str) -> Optional[LocationShare]:
        """Get a shared location by ID."""
        share = self._shared_locations.get(share_id)
        if share and share.is_expired():
            self.stop_sharing(share_id)
            return None
        return share
    
    def stop_sharing(self, share_id: str) -> bool:
        """Stop sharing a location."""
        share = self._shared_locations.pop(share_id, None)
        if share:
            if share.user_id in self._live_shares:
                if self._live_shares[share.user_id].share_id == share_id:
                    del self._live_shares[share.user_id]
            return True
        return False
    
    def stop_live_sharing(self, user_id: int) -> bool:
        """Stop live location sharing for a user."""
        if user_id in self._live_shares:
            share = self._live_shares.pop(user_id)
            self._shared_locations.pop(share.share_id, None)
            return True
        return False
    
    def get_active_shares(self, user_id: int) -> list[LocationShare]:
        """Get all active shares for a user."""
        return [
            share for share in self._shared_locations.values()
            if share.user_id == user_id and not share.is_expired()
        ]
    
    # ============================================
    # Distance and Proximity
    # ============================================
    
    def distance_between_users(self, user1_id: int, user2_id: int) -> Optional[float]:
        """Calculate distance between two users in meters."""
        loc1 = self.get_user_location(user1_id)
        loc2 = self.get_user_location(user2_id)
        
        if not loc1 or not loc2:
            return None
        
        return loc1.distance_to(loc2)
    
    def find_nearby_users(
        self,
        location: Location,
        radius_meters: float,
        exclude_user: int = None,
    ) -> list[tuple[int, float]]:
        """
        Find users within a radius.
        
        Args:
            location: Center location
            radius_meters: Search radius
            exclude_user: User ID to exclude
        
        Returns:
            List of (user_id, distance) tuples
        """
        nearby = []
        
        for user_id, user_loc in self._user_locations.items():
            if exclude_user and user_id == exclude_user:
                continue
            
            distance = location.distance_to(user_loc)
            if distance <= radius_meters:
                nearby.append((user_id, distance))
        
        nearby.sort(key=lambda x: x[1])
        return nearby
    
    # ============================================
    # Formatting
    # ============================================
    
    @staticmethod
    def format_distance(meters: float) -> str:
        """Format distance for display."""
        if meters < 1000:
            return f"{meters:.0f} m"
        else:
            return f"{meters / 1000:.1f} km"
    
    @staticmethod
    def format_coordinates(lat: float, lon: float, precision: int = 6) -> str:
        """Format coordinates for display."""
        lat_dir = "N" if lat >= 0 else "S"
        lon_dir = "E" if lon >= 0 else "W"
        return f"{abs(lat):.{precision}f}°{lat_dir}, {abs(lon):.{precision}f}°{lon_dir}"
    
    @staticmethod
    def format_bearing(degrees: float) -> str:
        """Format bearing as compass direction."""
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        index = round(degrees / 45) % 8
        return directions[index]
    
    # ============================================
    # Statistics
    # ============================================
    
    def get_stats(self) -> dict:
        """Get location service statistics."""
        return {
            "users_with_location": len(self._user_locations),
            "active_shares": len(self._shared_locations),
            "live_shares": len(self._live_shares),
        }
    
    def cleanup_expired(self) -> int:
        """Remove expired shares."""
        expired = [
            share_id for share_id, share in self._shared_locations.items()
            if share.is_expired()
        ]
        
        for share_id in expired:
            self.stop_sharing(share_id)
        
        return len(expired)


# ============================================
# Global Instance
# ============================================

_location_manager: Optional[LocationManager] = None


def get_location_manager() -> LocationManager:
    """Get the global location manager instance."""
    global _location_manager
    if _location_manager is None:
        _location_manager = LocationManager()
    return _location_manager


__all__ = [
    "Location",
    "LocationShare",
    "LocationManager",
    "get_location_manager",
]
