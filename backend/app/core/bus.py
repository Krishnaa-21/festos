# OWNER: P1
import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List

logger = logging.getLogger("festos.bus")

_subscribers: Dict[str, List[Callable[..., Any]]] = {}

def subscribe(event_name: str):
    """Decorator to subscribe a function to a domain event topic."""
    def decorator(fn: Callable[..., Any]):
        _subscribers.setdefault(event_name, []).append(fn)
        return fn
    return decorator

def publish(event_name: str, payload: Any = None) -> None:
    """Publish a domain event to all registered subscribers."""
    handlers = _subscribers.get(event_name, [])
    # Also check wildcard subscriptions
    for sub_pattern, sub_handlers in _subscribers.items():
        if sub_pattern.endswith("*") and event_name.startswith(sub_pattern[:-1]) and sub_pattern != event_name:
            handlers.extend(sub_handlers)

    for handler in handlers:
        try:
            if inspect.iscoroutinefunction(handler):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(handler(payload))
                except RuntimeError:
                    asyncio.run(handler(payload))
            else:
                handler(payload)
        except Exception as e:
            logger.error(f"Error executing event subscriber for '{event_name}': {e}", exc_info=True)

def clear_subscribers() -> None:
    """Clear all subscribers (mainly for testing)."""
    _subscribers.clear()
