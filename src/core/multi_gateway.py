"""
Multiple Gateways - v0.4 Advanced Feature
High availability gateway architecture with load balancing and failover.

Features:
    - Multiple gateway instances for redundancy
    - Automatic failover on gateway failure
    - Load balancing (round-robin, least-connections)
    - Health monitoring for each gateway
    - Session affinity (sticky sessions)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import asyncio
import hashlib
import json
import random
import time

from ..utils.logger import logger


class GatewayState(Enum):
    """State of a gateway instance."""
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"  # Stopping, but completing current requests
    STOPPED = "stopped"


class LoadBalanceStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    IP_HASH = "ip_hash"  # Session affinity by user ID hash
    WEIGHTED = "weighted"


@dataclass
class GatewayInstance:
    """A single gateway instance."""
    id: str
    name: str
    host: str
    port: int
    state: GatewayState = GatewayState.STARTING
    weight: int = 1  # For weighted load balancing
    max_connections: int = 1000
    current_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    last_health_check: datetime = None
    last_failure: datetime = None
    failure_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_available(self) -> bool:
        """Check if gateway is available for requests."""
        return self.state in (GatewayState.HEALTHY, GatewayState.DEGRADED)
    
    @property
    def url(self) -> str:
        """Get gateway URL."""
        return f"http://{self.host}:{self.port}"
    
    @property
    def utilization(self) -> float:
        """Get connection utilization (0.0 to 1.0)."""
        if self.max_connections == 0:
            return 1.0
        return self.current_connections / self.max_connections
    
    @property
    def error_rate(self) -> float:
        """Get error rate."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "url": self.url,
            "state": self.state.value,
            "weight": self.weight,
            "current_connections": self.current_connections,
            "max_connections": self.max_connections,
            "utilization": round(self.utilization * 100, 1),
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "error_rate": round(self.error_rate * 100, 2),
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
        }


@dataclass
class GatewayCluster:
    """Configuration for a gateway cluster."""
    name: str
    strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN
    health_check_interval: int = 30  # seconds
    failure_threshold: int = 3  # failures before marking unhealthy
    recovery_threshold: int = 2  # successes before marking healthy
    sticky_sessions: bool = True  # Enable session affinity
    sticky_ttl: int = 3600  # Session affinity TTL in seconds


class MultiGatewayManager:
    """
    Manager for multiple gateway instances.
    
    Usage:
        manager = get_multi_gateway_manager()
        
        # Register gateways
        manager.register_gateway("gw1", "gateway-1.local", 8001)
        manager.register_gateway("gw2", "gateway-2.local", 8002)
        
        # Get next available gateway (load balanced)
        gateway = manager.get_gateway(user_id="user123")
        
        # Send request through gateway
        response = await manager.send_request(user_id, message)
    """
    
    _instance: Optional["MultiGatewayManager"] = None
    
    def __init__(self):
        self._gateways: Dict[str, GatewayInstance] = {}
        self._cluster = GatewayCluster(name="default")
        self._round_robin_index = 0
        self._session_affinity: Dict[str, str] = {}  # user_id -> gateway_id
        self._session_timestamps: Dict[str, float] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable] = []
        self._lock = asyncio.Lock()
    
    def configure_cluster(
        self,
        name: str = "default",
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
        sticky_sessions: bool = True,
        health_check_interval: int = 30,
    ):
        """Configure the gateway cluster."""
        self._cluster = GatewayCluster(
            name=name,
            strategy=strategy,
            sticky_sessions=sticky_sessions,
            health_check_interval=health_check_interval,
        )
        logger.info(f"Configured gateway cluster: {name}, strategy: {strategy.value}")
    
    def register_gateway(
        self,
        gateway_id: str,
        host: str,
        port: int,
        name: str = None,
        weight: int = 1,
        max_connections: int = 1000,
    ) -> GatewayInstance:
        """
        Register a new gateway instance.
        
        Args:
            gateway_id: Unique identifier
            host: Gateway host
            port: Gateway port
            name: Display name
            weight: Weight for load balancing
            max_connections: Max concurrent connections
        """
        gateway = GatewayInstance(
            id=gateway_id,
            name=name or gateway_id,
            host=host,
            port=port,
            weight=weight,
            max_connections=max_connections,
        )
        
        self._gateways[gateway_id] = gateway
        logger.info(f"Registered gateway: {gateway_id} at {host}:{port}")
        
        return gateway
    
    def unregister_gateway(self, gateway_id: str) -> bool:
        """Unregister a gateway."""
        if gateway_id in self._gateways:
            gateway = self._gateways[gateway_id]
            gateway.state = GatewayState.DRAINING
            del self._gateways[gateway_id]
            
            # Clear session affinity for this gateway
            to_remove = [
                user_id for user_id, gw_id in self._session_affinity.items()
                if gw_id == gateway_id
            ]
            for user_id in to_remove:
                del self._session_affinity[user_id]
            
            logger.info(f"Unregistered gateway: {gateway_id}")
            return True
        return False
    
    def get_gateway(self, user_id: str = None) -> Optional[GatewayInstance]:
        """
        Get the next available gateway using configured load balancing.
        
        Args:
            user_id: User ID for session affinity
            
        Returns:
            GatewayInstance or None if no gateways available
        """
        available = [gw for gw in self._gateways.values() if gw.is_available]
        
        if not available:
            logger.warning("No available gateways")
            return None
        
        # Check session affinity first
        if self._cluster.sticky_sessions and user_id:
            if user_id in self._session_affinity:
                gateway_id = self._session_affinity[user_id]
                timestamp = self._session_timestamps.get(user_id, 0)
                
                # Check if affinity is still valid
                if time.time() - timestamp < self._cluster.sticky_ttl:
                    gateway = self._gateways.get(gateway_id)
                    if gateway and gateway.is_available:
                        return gateway
                
                # Affinity expired or gateway unavailable
                del self._session_affinity[user_id]
        
        # Select gateway based on strategy
        gateway = self._select_gateway(available, user_id)
        
        # Set session affinity
        if self._cluster.sticky_sessions and user_id and gateway:
            self._session_affinity[user_id] = gateway.id
            self._session_timestamps[user_id] = time.time()
        
        return gateway
    
    def _select_gateway(
        self,
        available: List[GatewayInstance],
        user_id: str = None,
    ) -> GatewayInstance:
        """Select a gateway based on load balancing strategy."""
        strategy = self._cluster.strategy
        
        if strategy == LoadBalanceStrategy.ROUND_ROBIN:
            self._round_robin_index = (self._round_robin_index + 1) % len(available)
            return available[self._round_robin_index]
        
        elif strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            return min(available, key=lambda gw: gw.current_connections)
        
        elif strategy == LoadBalanceStrategy.RANDOM:
            return random.choice(available)
        
        elif strategy == LoadBalanceStrategy.IP_HASH and user_id:
            # Use user_id hash for consistent routing
            hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            index = hash_val % len(available)
            return available[index]
        
        elif strategy == LoadBalanceStrategy.WEIGHTED:
            # Weighted random selection
            total_weight = sum(gw.weight for gw in available)
            r = random.uniform(0, total_weight)
            cumulative = 0
            for gw in available:
                cumulative += gw.weight
                if r <= cumulative:
                    return gw
            return available[-1]
        
        # Default to round robin
        self._round_robin_index = (self._round_robin_index + 1) % len(available)
        return available[self._round_robin_index]
    
    async def check_health(self, gateway: GatewayInstance) -> bool:
        """
        Check health of a gateway.
        
        Returns True if healthy.
        """
        try:
            import aiohttp
            
            url = f"{gateway.url}/health"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    gateway.last_health_check = datetime.now()
                    
                    if response.status == 200:
                        gateway.failure_count = 0
                        
                        if gateway.state == GatewayState.UNHEALTHY:
                            # Check recovery threshold
                            gateway.state = GatewayState.DEGRADED
                        else:
                            gateway.state = GatewayState.HEALTHY
                        
                        return True
                    else:
                        raise Exception(f"Unhealthy status: {response.status}")
                        
        except Exception as e:
            gateway.failure_count += 1
            gateway.last_failure = datetime.now()
            
            if gateway.failure_count >= self._cluster.failure_threshold:
                gateway.state = GatewayState.UNHEALTHY
                logger.warning(f"Gateway {gateway.id} marked unhealthy after {gateway.failure_count} failures")
            
            logger.debug(f"Health check failed for {gateway.id}: {e}")
            return False
    
    async def start_health_checks(self):
        """Start background health check task."""
        if self._health_check_task:
            return
        
        async def health_check_loop():
            while True:
                for gateway in list(self._gateways.values()):
                    await self.check_health(gateway)
                
                await asyncio.sleep(self._cluster.health_check_interval)
        
        self._health_check_task = asyncio.create_task(health_check_loop())
        logger.info("Started gateway health check loop")
    
    async def stop_health_checks(self):
        """Stop health check task."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
    
    def record_request(self, gateway_id: str, success: bool = True):
        """Record a request result for metrics."""
        gateway = self._gateways.get(gateway_id)
        if gateway:
            gateway.total_requests += 1
            if not success:
                gateway.failed_requests += 1
    
    def increment_connections(self, gateway_id: str):
        """Increment connection count."""
        gateway = self._gateways.get(gateway_id)
        if gateway:
            gateway.current_connections += 1
    
    def decrement_connections(self, gateway_id: str):
        """Decrement connection count."""
        gateway = self._gateways.get(gateway_id)
        if gateway and gateway.current_connections > 0:
            gateway.current_connections -= 1
    
    def get_all_gateways(self) -> List[GatewayInstance]:
        """Get all registered gateways."""
        return list(self._gateways.values())
    
    def get_available_gateways(self) -> List[GatewayInstance]:
        """Get all available gateways."""
        return [gw for gw in self._gateways.values() if gw.is_available]
    
    def get_cluster_stats(self) -> dict:
        """Get cluster statistics."""
        gateways = list(self._gateways.values())
        available = [gw for gw in gateways if gw.is_available]
        
        total_requests = sum(gw.total_requests for gw in gateways)
        total_failed = sum(gw.failed_requests for gw in gateways)
        total_connections = sum(gw.current_connections for gw in gateways)
        
        return {
            "cluster_name": self._cluster.name,
            "strategy": self._cluster.strategy.value,
            "total_gateways": len(gateways),
            "available_gateways": len(available),
            "total_requests": total_requests,
            "total_failed": total_failed,
            "error_rate": round(total_failed / total_requests * 100, 2) if total_requests > 0 else 0,
            "total_connections": total_connections,
            "sticky_sessions": self._cluster.sticky_sessions,
            "active_sessions": len(self._session_affinity),
        }
    
    def get_status_message(self) -> str:
        """Get formatted status message."""
        stats = self.get_cluster_stats()
        gateways = self.get_all_gateways()
        
        lines = [
            "🌐 **Multi-Gateway Status**",
            "",
            f"Cluster: **{stats['cluster_name']}**",
            f"Strategy: {stats['strategy']}",
            f"Gateways: {stats['available_gateways']}/{stats['total_gateways']} available",
            f"Total Requests: {stats['total_requests']}",
            f"Error Rate: {stats['error_rate']}%",
            f"Active Sessions: {stats['active_sessions']}",
            "",
            "**Gateways:**",
        ]
        
        for gw in gateways:
            state_icon = {
                GatewayState.HEALTHY: "🟢",
                GatewayState.DEGRADED: "🟡",
                GatewayState.UNHEALTHY: "🔴",
                GatewayState.STARTING: "⚪",
                GatewayState.DRAINING: "🟠",
                GatewayState.STOPPED: "⚫",
            }.get(gw.state, "⚪")
            
            lines.append(
                f"{state_icon} {gw.name}: {gw.host}:{gw.port} "
                f"({gw.current_connections}/{gw.max_connections} conn)"
            )
        
        return "\n".join(lines)


# Singleton instance
_multi_gateway_manager: Optional[MultiGatewayManager] = None


def get_multi_gateway_manager() -> MultiGatewayManager:
    """Get the global multi-gateway manager instance."""
    global _multi_gateway_manager
    if _multi_gateway_manager is None:
        _multi_gateway_manager = MultiGatewayManager()
    return _multi_gateway_manager


def reset_multi_gateway_manager():
    """Reset the manager (for testing)."""
    global _multi_gateway_manager
    _multi_gateway_manager = None


__all__ = [
    "GatewayState",
    "LoadBalanceStrategy",
    "GatewayInstance",
    "GatewayCluster",
    "MultiGatewayManager",
    "get_multi_gateway_manager",
    "reset_multi_gateway_manager",
]
