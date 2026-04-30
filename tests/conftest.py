"""Provide minimal stubs so coordinator tests run without a real HA install."""
import sys
import types


def _make_stub(*names):
    """Create nested stub modules."""
    for name in names:
        parts = name.split(".")
        for i in range(len(parts)):
            mod_name = ".".join(parts[: i + 1])
            if mod_name not in sys.modules:
                sys.modules[mod_name] = types.ModuleType(mod_name)


# homeassistant stubs required by coordinator.py / __init__.py
_make_stub(
    "homeassistant",
    "homeassistant.core",
    "homeassistant.const",
    "homeassistant.config_entries",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.helpers.entity",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.config_validation",
    "homeassistant.components",
    "homeassistant.components.sensor",
    "homeassistant.components.binary_sensor",
    "homeassistant.components.switch",
)

# Minimal classes used at import time
ha_core = sys.modules["homeassistant.core"]
ha_core.HomeAssistant = object  # type: ignore[attr-defined]

ha_const = sys.modules["homeassistant.const"]
ha_const.Platform = types.SimpleNamespace(  # type: ignore[attr-defined]
    SENSOR="sensor",
    BINARY_SENSOR="binary_sensor",
    SWITCH="switch",
)

ha_entries = sys.modules["homeassistant.config_entries"]
ha_entries.ConfigEntry = object  # type: ignore[attr-defined]

ha_exc = sys.modules["homeassistant.exceptions"]
ha_exc.ConfigEntryNotReady = Exception  # type: ignore[attr-defined]

ha_coord = sys.modules["homeassistant.helpers.update_coordinator"]


class _FakeCoordinator:
    """Stub DataUpdateCoordinator for testing without Home Assistant."""

    def __init__(self, *args, **kwargs):
        """Accept and discard all coordinator constructor arguments."""


class _UpdateFailed(Exception):
    pass


ha_coord.DataUpdateCoordinator = _FakeCoordinator  # type: ignore[attr-defined]
ha_coord.UpdateFailed = _UpdateFailed  # type: ignore[attr-defined]

ha_entity = sys.modules["homeassistant.helpers.entity"]
ha_entity.DeviceInfo = dict  # type: ignore[attr-defined]
