"""
Live Canvas (A2UI) - v0.4 Advanced Feature
Agent-driven visual workspace using Agent-to-UI rendering.

Features:
    - Real-time canvas rendering
    - Agent-controlled UI components
    - Interactive widgets (charts, code, tables)
    - WebSocket-based live updates
    - Multi-user canvas sharing
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
import asyncio
import json
import uuid

from ..utils.logger import logger


class ComponentType(Enum):
    """Types of canvas components."""
    # Basic
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    IMAGE = "image"
    
    # Code
    CODE = "code"
    TERMINAL = "terminal"
    DIFF = "diff"
    
    # Data
    TABLE = "table"
    CHART = "chart"
    JSON = "json"
    
    # Interactive
    BUTTON = "button"
    INPUT = "input"
    SELECT = "select"
    SLIDER = "slider"
    CHECKBOX = "checkbox"
    
    # Layout
    CONTAINER = "container"
    GRID = "grid"
    TABS = "tabs"
    ACCORDION = "accordion"
    
    # Status
    PROGRESS = "progress"
    SPINNER = "spinner"
    ALERT = "alert"
    BADGE = "badge"
    
    # Media
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"


class ChartType(Enum):
    """Types of charts."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"


class AlertType(Enum):
    """Types of alerts."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Position:
    """Position on canvas."""
    x: int = 0
    y: int = 0
    width: int = None
    height: int = None
    z_index: int = 0


@dataclass
class CanvasComponent:
    """A component on the canvas."""
    id: str
    type: ComponentType
    content: Any
    position: Position = field(default_factory=Position)
    style: Dict[str, Any] = field(default_factory=dict)
    props: Dict[str, Any] = field(default_factory=dict)
    visible: bool = True
    locked: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = self.created_at
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "position": {
                "x": self.position.x,
                "y": self.position.y,
                "width": self.position.width,
                "height": self.position.height,
                "z_index": self.position.z_index,
            },
            "style": self.style,
            "props": self.props,
            "visible": self.visible,
            "locked": self.locked,
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class CanvasSession:
    """A canvas session."""
    session_id: str
    user_id: str
    name: str = "Untitled Canvas"
    components: Dict[str, CanvasComponent] = field(default_factory=dict)
    shared_with: Set[str] = field(default_factory=set)
    is_public: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = self.created_at
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "name": self.name,
            "components": {k: v.to_dict() for k, v in self.components.items()},
            "shared_with": list(self.shared_with),
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class LiveCanvasManager:
    """
    Manager for Live Canvas functionality.
    
    Usage:
        canvas = get_live_canvas_manager()
        
        # Create a new canvas session
        session = canvas.create_session(user_id, "My Canvas")
        
        # Add components
        canvas.add_text(session.session_id, "Hello World!")
        canvas.add_code(session.session_id, "print('Hello')", language="python")
        canvas.add_chart(session.session_id, data, chart_type=ChartType.LINE)
        
        # Update component
        canvas.update_component(session.session_id, component_id, content="New text")
        
        # Render for WebSocket
        render_data = canvas.render(session.session_id)
    """
    
    _instance: Optional["LiveCanvasManager"] = None
    
    def __init__(self):
        self._sessions: Dict[str, CanvasSession] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]
        self._websocket_clients: Dict[str, Set] = {}  # session_id -> set of websockets
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._component_counter = 0
    
    def _generate_id(self, prefix: str = "comp") -> str:
        """Generate unique component ID."""
        self._component_counter += 1
        return f"{prefix}_{self._component_counter}_{uuid.uuid4().hex[:8]}"
    
    def create_session(
        self,
        user_id: str,
        name: str = "Untitled Canvas",
        is_public: bool = False,
    ) -> CanvasSession:
        """Create a new canvas session."""
        session_id = f"canvas_{uuid.uuid4().hex[:12]}"
        
        session = CanvasSession(
            session_id=session_id,
            user_id=user_id,
            name=name,
            is_public=is_public,
        )
        
        self._sessions[session_id] = session
        
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session_id)
        
        logger.info(f"Created canvas session: {session_id} for user {user_id}")
        return session
    
    def get_session(self, session_id: str, user_id: str = None) -> Optional[CanvasSession]:
        """Get a canvas session."""
        session = self._sessions.get(session_id)
        
        if not session:
            return None
        
        # Check access
        if user_id:
            if session.user_id != user_id and user_id not in session.shared_with:
                if not session.is_public:
                    return None
        
        return session
    
    def delete_session(self, session_id: str, user_id: str) -> bool:
        """Delete a canvas session."""
        session = self._sessions.get(session_id)
        
        if not session or session.user_id != user_id:
            return False
        
        del self._sessions[session_id]
        
        if user_id in self._user_sessions:
            self._user_sessions[user_id] = [
                sid for sid in self._user_sessions[user_id] if sid != session_id
            ]
        
        return True
    
    def get_user_sessions(self, user_id: str) -> List[CanvasSession]:
        """Get all sessions for a user."""
        session_ids = self._user_sessions.get(user_id, [])
        return [self._sessions[sid] for sid in session_ids if sid in self._sessions]
    
    def add_component(
        self,
        session_id: str,
        component_type: ComponentType,
        content: Any,
        position: Position = None,
        style: Dict = None,
        props: Dict = None,
    ) -> Optional[CanvasComponent]:
        """Add a component to the canvas."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        component = CanvasComponent(
            id=self._generate_id(),
            type=component_type,
            content=content,
            position=position or Position(),
            style=style or {},
            props=props or {},
        )
        
        session.components[component.id] = component
        session.updated_at = datetime.now()
        
        # Emit update event
        self._emit_update(session_id, "add", component)
        
        return component
    
    def add_text(
        self,
        session_id: str,
        text: str,
        position: Position = None,
        style: Dict = None,
    ) -> Optional[CanvasComponent]:
        """Add a text component."""
        return self.add_component(
            session_id,
            ComponentType.TEXT,
            text,
            position,
            style,
        )
    
    def add_markdown(
        self,
        session_id: str,
        markdown: str,
        position: Position = None,
    ) -> Optional[CanvasComponent]:
        """Add a markdown component."""
        return self.add_component(
            session_id,
            ComponentType.MARKDOWN,
            markdown,
            position,
        )
    
    def add_code(
        self,
        session_id: str,
        code: str,
        language: str = "python",
        position: Position = None,
        show_line_numbers: bool = True,
    ) -> Optional[CanvasComponent]:
        """Add a code component."""
        return self.add_component(
            session_id,
            ComponentType.CODE,
            code,
            position,
            props={
                "language": language,
                "showLineNumbers": show_line_numbers,
            },
        )
    
    def add_terminal(
        self,
        session_id: str,
        output: str,
        position: Position = None,
    ) -> Optional[CanvasComponent]:
        """Add a terminal output component."""
        return self.add_component(
            session_id,
            ComponentType.TERMINAL,
            output,
            position,
            style={"fontFamily": "monospace"},
        )
    
    def add_table(
        self,
        session_id: str,
        headers: List[str],
        rows: List[List[Any]],
        position: Position = None,
    ) -> Optional[CanvasComponent]:
        """Add a table component."""
        return self.add_component(
            session_id,
            ComponentType.TABLE,
            {"headers": headers, "rows": rows},
            position,
        )
    
    def add_chart(
        self,
        session_id: str,
        data: Dict[str, Any],
        chart_type: ChartType = ChartType.LINE,
        title: str = None,
        position: Position = None,
    ) -> Optional[CanvasComponent]:
        """
        Add a chart component.
        
        Args:
            data: Chart data with labels and datasets
            chart_type: Type of chart
            title: Chart title
        """
        return self.add_component(
            session_id,
            ComponentType.CHART,
            data,
            position,
            props={
                "chartType": chart_type.value,
                "title": title,
            },
        )
    
    def add_image(
        self,
        session_id: str,
        url: str,
        alt: str = "",
        position: Position = None,
    ) -> Optional[CanvasComponent]:
        """Add an image component."""
        return self.add_component(
            session_id,
            ComponentType.IMAGE,
            url,
            position,
            props={"alt": alt},
        )
    
    def add_alert(
        self,
        session_id: str,
        message: str,
        alert_type: AlertType = AlertType.INFO,
        title: str = None,
        position: Position = None,
    ) -> Optional[CanvasComponent]:
        """Add an alert component."""
        return self.add_component(
            session_id,
            ComponentType.ALERT,
            message,
            position,
            props={
                "alertType": alert_type.value,
                "title": title,
            },
        )
    
    def add_progress(
        self,
        session_id: str,
        value: int,
        max_value: int = 100,
        label: str = None,
        position: Position = None,
    ) -> Optional[CanvasComponent]:
        """Add a progress bar component."""
        return self.add_component(
            session_id,
            ComponentType.PROGRESS,
            {"value": value, "max": max_value, "label": label},
            position,
        )
    
    def add_button(
        self,
        session_id: str,
        label: str,
        action: str,
        position: Position = None,
        variant: str = "primary",
    ) -> Optional[CanvasComponent]:
        """Add a button component."""
        return self.add_component(
            session_id,
            ComponentType.BUTTON,
            label,
            position,
            props={
                "action": action,
                "variant": variant,
            },
        )
    
    def add_json(
        self,
        session_id: str,
        data: Any,
        position: Position = None,
        collapsed: bool = False,
    ) -> Optional[CanvasComponent]:
        """Add a JSON viewer component."""
        return self.add_component(
            session_id,
            ComponentType.JSON,
            data,
            position,
            props={"collapsed": collapsed},
        )
    
    def update_component(
        self,
        session_id: str,
        component_id: str,
        content: Any = None,
        position: Position = None,
        style: Dict = None,
        props: Dict = None,
        visible: bool = None,
    ) -> bool:
        """Update a component."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        component = session.components.get(component_id)
        if not component or component.locked:
            return False
        
        if content is not None:
            component.content = content
        if position is not None:
            component.position = position
        if style is not None:
            component.style.update(style)
        if props is not None:
            component.props.update(props)
        if visible is not None:
            component.visible = visible
        
        component.updated_at = datetime.now()
        session.updated_at = datetime.now()
        
        # Emit update event
        self._emit_update(session_id, "update", component)
        
        return True
    
    def remove_component(self, session_id: str, component_id: str) -> bool:
        """Remove a component from the canvas."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        if component_id not in session.components:
            return False
        
        del session.components[component_id]
        session.updated_at = datetime.now()
        
        # Emit update event
        self._emit_update(session_id, "remove", {"id": component_id})
        
        return True
    
    def clear_canvas(self, session_id: str) -> bool:
        """Clear all components from canvas."""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session.components.clear()
        session.updated_at = datetime.now()
        
        # Emit update event
        self._emit_update(session_id, "clear", None)
        
        return True
    
    def render(self, session_id: str) -> Optional[dict]:
        """Render canvas for WebSocket transmission."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        return {
            "type": "canvas_render",
            "session_id": session_id,
            "name": session.name,
            "components": [
                comp.to_dict()
                for comp in session.components.values()
                if comp.visible
            ],
            "updated_at": session.updated_at.isoformat(),
        }
    
    def _emit_update(self, session_id: str, action: str, data: Any):
        """Emit update event to WebSocket clients."""
        message = {
            "type": "canvas_update",
            "session_id": session_id,
            "action": action,
            "data": data.to_dict() if hasattr(data, "to_dict") else data,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Queue for async broadcast
        asyncio.create_task(self._broadcast(session_id, message))
    
    async def _broadcast(self, session_id: str, message: dict):
        """Broadcast message to connected clients."""
        clients = self._websocket_clients.get(session_id, set())
        
        for client in clients.copy():
            try:
                await client.send_json(message)
            except Exception:
                clients.discard(client)
    
    def register_websocket(self, session_id: str, websocket):
        """Register a WebSocket connection for canvas updates."""
        if session_id not in self._websocket_clients:
            self._websocket_clients[session_id] = set()
        self._websocket_clients[session_id].add(websocket)
    
    def unregister_websocket(self, session_id: str, websocket):
        """Unregister a WebSocket connection."""
        if session_id in self._websocket_clients:
            self._websocket_clients[session_id].discard(websocket)
    
    def get_status_message(self, user_id: str) -> str:
        """Get formatted status message."""
        sessions = self.get_user_sessions(user_id)
        
        lines = [
            "🎨 **Live Canvas**",
            "",
            f"Your Canvases: {len(sessions)}",
            "",
        ]
        
        if sessions:
            lines.append("**Sessions:**")
            for session in sessions[:10]:
                comp_count = len(session.components)
                lines.append(f"• {session.name} ({comp_count} components)")
        else:
            lines.append("No canvas sessions yet.")
        
        lines.extend([
            "",
            "**Commands:**",
            "/canvas new [name] - Create new canvas",
            "/canvas list - List your canvases",
            "/canvas open <id> - Open canvas",
            "/canvas clear - Clear current canvas",
        ])
        
        return "\n".join(lines)


# Singleton instance
_live_canvas_manager: Optional[LiveCanvasManager] = None


def get_live_canvas_manager() -> LiveCanvasManager:
    """Get the global live canvas manager instance."""
    global _live_canvas_manager
    if _live_canvas_manager is None:
        _live_canvas_manager = LiveCanvasManager()
    return _live_canvas_manager


def reset_live_canvas_manager():
    """Reset the manager (for testing)."""
    global _live_canvas_manager
    _live_canvas_manager = None


__all__ = [
    "ComponentType",
    "ChartType",
    "AlertType",
    "Position",
    "CanvasComponent",
    "CanvasSession",
    "LiveCanvasManager",
    "get_live_canvas_manager",
    "reset_live_canvas_manager",
]
