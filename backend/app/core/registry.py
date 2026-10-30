# OWNER: P1
import importlib
from typing import Any, Callable, Dict, List, Optional, Tuple

# Change handlers: action -> handler instance or class
_change_handlers: Dict[str, Any] = {}

# Seeders: list of (order, name, fn)
_seeders: List[Tuple[int, str, Callable[..., Any]]] = []

# Participant sections: name -> fn(participant_id, session) -> dict
_participant_sections: Dict[str, Callable[..., Any]] = {}

# Impact hooks: list of hook functions
_impact_hooks: List[Callable[..., Any]] = []

def register_change_handler(action: str):
    """Decorator to register a handler for an action (e.g. 'participant.update')."""
    def decorator(cls_or_fn: Any):
        _change_handlers[action] = cls_or_fn
        return cls_or_fn
    return decorator

def get_change_handler(action: str) -> Optional[Any]:
    if action not in _change_handlers:
        module_slug = action.split(".")[0]
        try:
            importlib.import_module(f"app.services.{module_slug}.handlers")
        except Exception:
            pass
        if action not in _change_handlers:
            try:
                importlib.import_module(f"app.services.{module_slug}")
            except Exception:
                pass
    return _change_handlers.get(action)

def register_seeder(name: str, order: int = 100):
    """Decorator to register a database seeder with execution order."""
    def decorator(fn: Callable[..., Any]):
        _seeders.append((order, name, fn))
        _seeders.sort(key=lambda x: x[0])
        return fn
    return decorator

def get_seeders() -> List[Tuple[int, str, Callable[..., Any]]]:
    return list(_seeders)

def register_participant_section(name: str):
    """Decorator to register a participant 360 section provider."""
    def decorator(fn: Callable[..., Any]):
        _participant_sections[name] = fn
        return fn
    return decorator

def get_participant_sections() -> Dict[str, Callable[..., Any]]:
    return dict(_participant_sections)

def register_impact_hook(fn: Callable[..., Any]):
    """Register an impact assessment hook called after mutations."""
    _impact_hooks.append(fn)
    return fn

def get_impact_hooks() -> List[Callable[..., Any]]:
    return list(_impact_hooks)

def iter_public_modules() -> List[Dict[str, Any]]:
    """Discover all modules under app.services that expose public.py.
    Returns module metadata and loaded functions.
    """
    discovered = []
    try:
        import os

        import app.services as services_pkg
        for pkg_path in services_pkg.__path__:
            if os.path.exists(pkg_path):
                for entry in os.listdir(pkg_path):
                    entry_dir = os.path.join(pkg_path, entry)
                    if os.path.isdir(entry_dir) and not entry.startswith((".", "_")):
                        try:
                            public_mod = importlib.import_module(f"app.services.{entry}.public")
                            discovered.append({
                                "slug": entry,
                                "has_summary": hasattr(public_mod, "summary"),
                                "has_risks": hasattr(public_mod, "risks"),
                                "has_dependents": hasattr(public_mod, "dependents"),
                                "module": public_mod
                            })
                        except Exception:
                            discovered.append({
                                "slug": entry,
                                "has_summary": False,
                                "has_risks": False,
                                "has_dependents": False,
                                "module": None
                            })
    except Exception:
        pass
    discovered.sort(key=lambda x: x["slug"])
    return discovered
