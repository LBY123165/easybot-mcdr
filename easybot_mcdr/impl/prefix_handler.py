import re
from typing import Dict, List, Type

# Dynamically collect available handlers
_handler_map: Dict[str, Type] = {}
_handler_classes: List[Type] = []

_try_imports = [
    ("forge", "ForgeHandler"),
    ("fabric", "FabricHandler"),
    ("spigot", "SpigotHandler"),
    ("paper", "PaperHandler"),
    ("vanilla", "VanillaHandler"),
]

for name, cls_name in _try_imports:
    try:
        mod = __import__("mcdreforged.handler.impl", fromlist=[cls_name])
        cls = getattr(mod, cls_name)
        _handler_map[name] = cls
        _handler_classes.append(cls)
    except (ImportError, AttributeError):
        pass

# Final fallback: if nothing imported, raise at runtime clearly
if not _handler_classes:
    raise ImportError('No base handlers available from mcdreforged.handler.impl')

# Default base class is the first successfully imported handler
_default_base = _handler_classes[0]

AVAILABLE_HANDLERS = list(_handler_map.keys())


def _make_handler_class(base_class: Type, name: str = "PrefixNameHandler"):
    class Handler(base_class):
        def get_name(self) -> str:
            return 'easybot_prefix_handler'

        def parse_server_stdout(self, text: str):
            info = None
            for cls in _handler_classes:
                parser = getattr(self, f'_eb_{cls.__name__}', None)
                if parser is None:
                    try:
                        parser = cls()
                    except Exception:
                        continue
                    setattr(self, f'_eb_{cls.__name__}', parser)
                try:
                    last_info = parser.parse_server_stdout(text)
                    if last_info is not None:
                        info = last_info
                        if getattr(info, 'player', None):
                            break
                except Exception:
                    continue

            if info is None:
                info = super().parse_server_stdout(text)

            if info.player is None:
                m = re.fullmatch(r'(?:\[Not Secure\] )?<\[(?P<prefix>[^\]]+)\](?P<name>[^>]+)> (?P<message>.*)', info.content)
                if m is not None and self._verify_player_name(m['name']):
                    info.player = m['name']
                    info.content = m['message']
            return info

    Handler.__name__ = name
    Handler.__qualname__ = name
    return Handler


def create_handler(handler_name: str = "forge"):
    """
    Create a PrefixNameHandler instance based on the configured handler name.

    Args:
        handler_name: One of "forge", "fabric", "spigot", "paper", "vanilla".
                      Falls back to the default (first available) handler if not found.

    Returns:
        An instance of PrefixNameHandler with the appropriate base class.
    """
    handler_name = handler_name.lower()
    base_class = _handler_map.get(handler_name, _default_base)
    return _make_handler_class(base_class)()


def detect_handler_from_mcdr(server) -> str:
    """
    Automatically detect the server type from MCDR's current handler.

    Reads the handler that MCDR has already selected (from config or auto-detection),
    extracts its class name (e.g. ForgeHandler -> forge), and returns the matching
    handler name for create_handler(). Falls back to "forge" if detection fails.

    Args:
        server: PluginServerInterface instance (from on_load)

    Returns:
        Handler name string: "forge", "fabric", "spigot", "paper", or "vanilla"
    """
    try:
        # Access MCDR's internal handler manager to get the currently active handler
        handler_mgr = server._mcdr_server.server_handler_manager
        current = handler_mgr.get_current_handler()
        class_name = current.__class__.__name__  # e.g. "ForgeHandler"

        # Strip "Handler" suffix and lowercase: ForgeHandler -> forge
        detected = class_name.replace("Handler", "").lower()
        if detected in _handler_map:
            return detected
    except Exception:
        pass
    return "forge"
