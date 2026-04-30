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

# ---------------------------------------------------------------------------
# snap7 stubs – replaced per-test with unittest.mock when behaviour matters
# ---------------------------------------------------------------------------

_make_stub("snap7", "snap7.client", "snap7.util", "snap7.types")

snap7_mod = sys.modules["snap7"]
snap7_client_mod = sys.modules["snap7.client"]
snap7_util_mod = sys.modules["snap7.util"]
snap7_types_mod = sys.modules["snap7.types"]


class _FakeSnap7Client:
    """Minimal snap7 client stub – all reads succeed and return a zero byte."""

    def get_connected(self) -> bool:
        return True

    def connect(self, *args) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def db_read(self, db: int, start: int, size: int):
        return bytearray(size)

    def db_write(self, db: int, start: int, data) -> None:
        pass

    def read_area(self, area, db: int, start: int, size: int):
        return bytearray(size)

    def write_area(self, area, db: int, start: int, data) -> None:
        pass


snap7_client_mod.Client = _FakeSnap7Client  # type: ignore[attr-defined]
# Expose the sub-module as an attribute (mirrors real import behaviour)
snap7_mod.client = snap7_client_mod  # type: ignore[attr-defined]


# Stub the utility functions used by the coordinator
def _noop_set(*args, **kwargs):
    pass


def _noop_get(*_args, **_kwargs):
    return 0


snap7_util_mod.get_bool = lambda buf, byte, bit: False  # type: ignore[attr-defined]
snap7_util_mod.get_int = _noop_get  # type: ignore[attr-defined]
snap7_util_mod.get_word = _noop_get  # type: ignore[attr-defined]
snap7_util_mod.get_dint = _noop_get  # type: ignore[attr-defined]
snap7_util_mod.get_dword = _noop_get  # type: ignore[attr-defined]
snap7_util_mod.get_real = _noop_get  # type: ignore[attr-defined]
snap7_util_mod.set_bool = _noop_set  # type: ignore[attr-defined]
snap7_util_mod.set_int = _noop_set  # type: ignore[attr-defined]
snap7_util_mod.set_word = _noop_set  # type: ignore[attr-defined]
snap7_util_mod.set_dint = _noop_set  # type: ignore[attr-defined]
snap7_util_mod.set_dword = _noop_set  # type: ignore[attr-defined]
snap7_util_mod.set_real = _noop_set  # type: ignore[attr-defined]

snap7_types_mod.Areas = types.SimpleNamespace(MK=0x83)  # type: ignore[attr-defined]
