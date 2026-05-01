"""PLC communication backend abstractions for the Snap7 PLC integration.

Each backend wraps a third-party library and exposes a uniform interface so
that the coordinator never imports library-specific code directly.

Adding a new backend
--------------------
1. Create a class that inherits from :class:`PlcBackend`.
2. Implement all abstract methods.
3. Add a new ``LIBRARY_*`` constant to ``const.py`` and include it in
   ``LIBRARY_OPTIONS``.
4. Register the class in :func:`create_backend`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class PlcBackend(ABC):
    """Abstract base class for PLC communication backends.

    All read/write methods operate on raw :class:`bytearray` objects; the
    coordinator is responsible for encoding and decoding typed values.
    """

    @abstractmethod
    def connect(self, ip: str, rack: int, slot: int) -> None:
        """Open a connection to the PLC."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection to the PLC."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Return *True* if the backend currently has an active connection."""

    @abstractmethod
    def db_read(self, db: int, start: int, size: int) -> bytearray:
        """Read *size* bytes from data block *db* starting at *start*."""

    @abstractmethod
    def db_write(self, db: int, start: int, data: bytearray) -> None:
        """Write *data* to data block *db* starting at *start*."""

    @abstractmethod
    def read_area_mk(self, start: int, size: int) -> bytearray:
        """Read *size* bytes from the Merker (M) area starting at *start*."""

    @abstractmethod
    def write_area_mk(self, start: int, data: bytearray) -> None:
        """Write *data* to the Merker (M) area starting at *start*."""


# ---------------------------------------------------------------------------
# python-snap7 backend
# ---------------------------------------------------------------------------

class Snap7Backend(PlcBackend):
    """Backend that uses the *python-snap7* library (``pip install python-snap7``).

    This is the default backend and wraps the ``snap7.client.Client`` class.
    The underlying C library (*libsnap7*) must be accessible on the system.
    """

    def __init__(self) -> None:
        self._client: Any = None

    # ── connection ──────────────────────────────────────────────────────────

    def connect(self, ip: str, rack: int, slot: int) -> None:
        import snap7

        if self._client is None:
            self._client = snap7.client.Client()
        self._client.connect(ip, rack, slot)

    def disconnect(self) -> None:
        if self._client is not None:
            try:
                if self._client.get_connected():
                    self._client.disconnect()
            except Exception:  # noqa: BLE001
                pass
            self._client = None

    def is_connected(self) -> bool:
        if self._client is None:
            return False
        try:
            return bool(self._client.get_connected())
        except Exception:  # noqa: BLE001
            return False

    # ── read / write ────────────────────────────────────────────────────────

    def db_read(self, db: int, start: int, size: int) -> bytearray:
        return bytearray(self._client.db_read(db, start, size))

    def db_write(self, db: int, start: int, data: bytearray) -> None:
        self._client.db_write(db, start, data)

    def read_area_mk(self, start: int, size: int) -> bytearray:
        from snap7.type import Areas

        return bytearray(self._client.read_area(Areas.MK, 0, start, size))

    def write_area_mk(self, start: int, data: bytearray) -> None:
        from snap7.type import Areas

        self._client.write_area(Areas.MK, 0, start, data)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_backend(library: str) -> PlcBackend:
    """Instantiate and return the backend for the given *library* name.

    Parameters
    ----------
    library:
        One of the ``LIBRARY_*`` constants defined in :mod:`.const`.

    Raises
    ------
    ValueError
        If *library* is not a recognised backend identifier.
    ImportError
        If the underlying library is not installed.
    """
    from .const import LIBRARY_SNAP7

    if library == LIBRARY_SNAP7:
        return Snap7Backend()

    raise ValueError(f"Unknown PLC library: '{library}'")
