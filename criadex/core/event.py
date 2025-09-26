"""
Event module for Criadex (Elasticsearch version)
Implements event handling, hooks, and triggers for semantic search and orchestration.
"""


class Event:
    """
    Event system for Criadex (Elasticsearch version)
    Supports hooks for search, insert, delete, and custom actions.
    """
    SEARCH = "search"
    INSERT = "insert"
    DELETE = "delete"

    def __init__(self):
        self._listeners = {}

    def on(self, event_name, callback):
        """Register a callback for an event."""
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        self._listeners[event_name].append(callback)

    def emit(self, event_name, *args, **kwargs):
        """Trigger all callbacks for an event."""
        for callback in self._listeners.get(event_name, []):
            callback(*args, **kwargs)

    def once(self, event_name, callback):
        """Register a callback that runs only once."""
        def wrapper(*args, **kwargs):
            callback(*args, **kwargs)
            self.remove(event_name, wrapper)
        self.on(event_name, wrapper)

    def remove(self, event_name, callback):
        """Remove a specific callback from an event."""
        if event_name in self._listeners:
            self._listeners[event_name] = [cb for cb in self._listeners[event_name] if cb != callback]

    # Example usage for migration:
    # event = Event()
    # event.on(Event.SEARCH, lambda query: print(f"Search event: {query}"))
    # event.emit(Event.SEARCH, query="example")
