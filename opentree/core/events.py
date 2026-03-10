"""
Simple event bus for application-wide events.
"""

from typing import Callable, Any
from dataclasses import dataclass
from collections import defaultdict


class Events:
    """Event name constants."""
    
    REPO_OPENED = "repo_opened"
    REPO_CLOSED = "repo_closed"
    STATUS_UPDATED = "status_updated"
    BRANCHES_UPDATED = "branches_updated"
    LOG_UPDATED = "log_updated"
    COMMAND_STARTED = "command_started"
    COMMAND_OUTPUT = "command_output"
    COMMAND_FINISHED = "command_finished"
    BUSY_CHANGED = "busy_changed"
    FILE_SELECTED = "file_selected"
    COMMIT_SELECTED = "commit_selected"


class EventBus:
    """
    Simple publish/subscribe event bus.
    
    Usage:
        events = EventBus()
        events.subscribe("my_event", my_handler)
        events.emit("my_event", arg1, arg2)
    """
    
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
    
    def subscribe(self, event: str, handler: Callable[..., Any]) -> None:
        """Subscribe a handler to an event."""
        if handler not in self._subscribers[event]:
            self._subscribers[event].append(handler)
    
    def unsubscribe(self, event: str, handler: Callable[..., Any]) -> None:
        """Unsubscribe a handler from an event."""
        if handler in self._subscribers[event]:
            self._subscribers[event].remove(handler)
    
    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Emit an event to all subscribers."""
        for handler in self._subscribers[event]:
            try:
                handler(*args, **kwargs)
            except Exception as e:
                print(f"Error in event handler for {event}: {e}")
    
    def clear(self, event: str | None = None) -> None:
        """Clear subscribers for an event or all events."""
        if event:
            self._subscribers[event] = []
        else:
            self._subscribers.clear()


# Global event bus instance
events = EventBus()
