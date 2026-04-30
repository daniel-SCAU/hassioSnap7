"""Data coordinator for the Snap7 PLC integration."""
from __future__ import annotations

import logging
import re
import threading
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    AREA_DB,
    AREA_M,
    DATA_TYPE_BOOL,
    DATA_TYPE_BYTE,
    DATA_TYPE_DINT,
    DATA_TYPE_DWORD,
    DATA_TYPE_INT,
    DATA_TYPE_REAL,
    DATA_TYPE_STRING,
    DATA_TYPE_WORD,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Address parser
# ---------------------------------------------------------------------------

def parse_address(address: str, data_type: str) -> dict:
    """Parse a PLC address string into a structured dict.

    Supported address formats
    -------------------------
    M area (Merker):
      - Boolean  : ``M<byte>.<bit>``        e.g. ``M0.0``
      - Byte     : ``MB<byte>``              e.g. ``MB10``
      - Word/Int : ``MW<byte>``              e.g. ``MW20``
      - DWord …  : ``MD<byte>``              e.g. ``MD100``
      - String   : ``MB<byte>(<length>)``    e.g. ``MB140(4)``

    DB area (Data Block):
      - Boolean  : ``DB<n>.DBX<byte>.<bit>``         e.g. ``DB1.DBX0.0``
      - Byte     : ``DB<n>.DBB<byte>``                e.g. ``DB1.DBB2``
      - Word/Int : ``DB<n>.DBW<byte>``                e.g. ``DB1.DBW4``
      - DWord …  : ``DB<n>.DBD<byte>``                e.g. ``DB1.DBD8``
      - String   : ``DB<n>.DBB<byte>(<length>)``      e.g. ``DB1.DBB0(10)``

    For **string** addresses the *length* specifies how many consecutive bytes
    form the raw ASCII byte array.  Each byte is interpreted as its ASCII
    decimal value and the bytes are joined into a single string.  Null bytes
    (0x00) at the end are stripped automatically.

    Note: this is **not** the Siemens S7 STRING format (which uses a 2-byte
    header of max-length and actual-length before the character data).  Use
    this type for raw byte arrays that happen to contain printable ASCII text.

    The *data_type* argument refines interpretation when the address prefix
    is ambiguous (e.g. ``DBW`` can be ``word`` or ``int``).
    """
    addr = address.strip().upper()

    # ── DB area ────────────────────────────────────────────────────────────
    m = re.match(r"^DB(\d+)\.DBX(\d+)\.(\d+)$", addr)
    if m:
        bit = int(m.group(3))
        if bit > 7:
            raise ValueError(
                f"Bit index {bit!r} is out of range 0–7 in address '{address}'"
            )
        return {
            "area": AREA_DB,
            "db": int(m.group(1)),
            "byte": int(m.group(2)),
            "bit": bit,
            "data_type": DATA_TYPE_BOOL,
        }

    m = re.match(r"^DB(\d+)\.DBB(\d+)\((\d+)\)$", addr)
    if m:
        length = int(m.group(3))
        if length < 1:
            raise ValueError(f"String length must be at least 1, got {length!r}")
        return {
            "area": AREA_DB,
            "db": int(m.group(1)),
            "byte": int(m.group(2)),
            "bit": 0,
            "data_type": DATA_TYPE_STRING,
            "string_length": length,
        }

    m = re.match(r"^DB(\d+)\.DBB(\d+)$", addr)
    if m:
        return {
            "area": AREA_DB,
            "db": int(m.group(1)),
            "byte": int(m.group(2)),
            "bit": 0,
            "data_type": data_type if data_type in [DATA_TYPE_BYTE] else DATA_TYPE_BYTE,
        }

    m = re.match(r"^DB(\d+)\.DBW(\d+)$", addr)
    if m:
        valid = [DATA_TYPE_WORD, DATA_TYPE_INT]
        return {
            "area": AREA_DB,
            "db": int(m.group(1)),
            "byte": int(m.group(2)),
            "bit": 0,
            "data_type": data_type if data_type in valid else DATA_TYPE_WORD,
        }

    m = re.match(r"^DB(\d+)\.DBD(\d+)$", addr)
    if m:
        valid = [DATA_TYPE_DWORD, DATA_TYPE_DINT, DATA_TYPE_REAL]
        return {
            "area": AREA_DB,
            "db": int(m.group(1)),
            "byte": int(m.group(2)),
            "bit": 0,
            "data_type": data_type if data_type in valid else DATA_TYPE_DWORD,
        }

    # ── M area ─────────────────────────────────────────────────────────────
    m = re.match(r"^M(\d+)\.(\d+)$", addr)
    if m:
        bit = int(m.group(2))
        if bit > 7:
            raise ValueError(
                f"Bit index {bit!r} is out of range 0–7 in address '{address}'"
            )
        return {
            "area": AREA_M,
            "db": 0,
            "byte": int(m.group(1)),
            "bit": bit,
            "data_type": DATA_TYPE_BOOL,
        }

    m = re.match(r"^MB(\d+)\((\d+)\)$", addr)
    if m:
        length = int(m.group(2))
        if length < 1:
            raise ValueError(f"String length must be at least 1, got {length!r}")
        return {
            "area": AREA_M,
            "db": 0,
            "byte": int(m.group(1)),
            "bit": 0,
            "data_type": DATA_TYPE_STRING,
            "string_length": length,
        }

    m = re.match(r"^MB(\d+)$", addr)
    if m:
        return {
            "area": AREA_M,
            "db": 0,
            "byte": int(m.group(1)),
            "bit": 0,
            "data_type": data_type if data_type in [DATA_TYPE_BYTE] else DATA_TYPE_BYTE,
        }

    m = re.match(r"^MW(\d+)$", addr)
    if m:
        valid = [DATA_TYPE_WORD, DATA_TYPE_INT]
        return {
            "area": AREA_M,
            "db": 0,
            "byte": int(m.group(1)),
            "bit": 0,
            "data_type": data_type if data_type in valid else DATA_TYPE_WORD,
        }

    m = re.match(r"^MD(\d+)$", addr)
    if m:
        valid = [DATA_TYPE_DWORD, DATA_TYPE_DINT, DATA_TYPE_REAL]
        return {
            "area": AREA_M,
            "db": 0,
            "byte": int(m.group(1)),
            "bit": 0,
            "data_type": data_type if data_type in valid else DATA_TYPE_DWORD,
        }

    raise ValueError(f"Unrecognised PLC address format: '{address}'")


def _data_size(data_type: str) -> int:
    """Return the number of bytes required to store *data_type*."""
    if data_type in (DATA_TYPE_BOOL, DATA_TYPE_BYTE):
        return 1
    if data_type in (DATA_TYPE_WORD, DATA_TYPE_INT):
        return 2
    return 4  # dword / dint / real


# ---------------------------------------------------------------------------
# Coordinator
# ---------------------------------------------------------------------------

class Snap7Coordinator(DataUpdateCoordinator):
    """Periodically poll a Siemens PLC over the snap7 protocol."""

    def __init__(
        self,
        hass: HomeAssistant,
        plc_ip: str,
        rack: int,
        slot: int,
        tags: list[dict],
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(milliseconds=scan_interval),
        )
        self.plc_ip = plc_ip
        self.rack = rack
        self.slot = slot
        self.tags = tags
        self._client: Any = None
        self._lock = threading.Lock()

        # Pre-parse all tag addresses once at startup
        self._parsed_tags: dict[str, dict] = {}
        for tag in tags:
            try:
                self._parsed_tags[tag["id"]] = parse_address(
                    tag["address"], tag["data_type"]
                )
            except ValueError as exc:
                _LOGGER.error(
                    "Ignoring tag '%s' – invalid address '%s': %s",
                    tag.get("name"),
                    tag.get("address"),
                    exc,
                )

    # ── connection management ───────────────────────────────────────────────

    def _get_client(self):
        """Return a connected snap7 client, (re-)connecting if needed."""
        import snap7

        if self._client is None:
            self._client = snap7.client.Client()

        if not self._client.get_connected():
            self._client.connect(self.plc_ip, self.rack, self.slot)
            if not self._client.get_connected():
                raise ConnectionError(
                    f"Failed to connect to PLC at {self.plc_ip} "
                    f"(rack={self.rack}, slot={self.slot})"
                )

        return self._client

    def disconnect(self) -> None:
        """Gracefully disconnect from the PLC."""
        with self._lock:
            if self._client is not None:
                try:
                    if self._client.get_connected():
                        self._client.disconnect()
                except Exception:  # noqa: BLE001
                    pass
                self._client = None

    # ── read / write helpers (blocking – run in executor) ──────────────────

    def _read_value(self, parsed: dict) -> Any:
        """Read a single value from the PLC (blocking)."""
        import snap7
        from snap7.util import (
            get_bool,
            get_dint,
            get_dword,
            get_int,
            get_real,
            get_word,
        )
        from snap7.types import Areas

        client = self._get_client()
        area = parsed["area"]
        db = parsed["db"]
        byte = parsed["byte"]
        bit = parsed["bit"]
        data_type = parsed["data_type"]

        # ── String: read N bytes and decode as ASCII ────────────────────────
        if data_type == DATA_TYPE_STRING:
            length = parsed["string_length"]
            if area == AREA_DB:
                raw = client.db_read(db, byte, length)
            else:
                raw = client.read_area(Areas.MK, 0, byte, length)
            _ASCII_PRINTABLE_MIN = 32
            _ASCII_PRINTABLE_MAX = 126
            return "".join(
                chr(b) if _ASCII_PRINTABLE_MIN <= b <= _ASCII_PRINTABLE_MAX else ""
                for b in raw
            ).rstrip("\x00")

        size = _data_size(data_type)

        if area == AREA_DB:
            raw = client.db_read(db, byte, size)
        else:
            raw = client.read_area(Areas.MK, 0, byte, size)

        if data_type == DATA_TYPE_BOOL:
            return get_bool(raw, 0, bit)
        if data_type == DATA_TYPE_BYTE:
            return raw[0]
        if data_type == DATA_TYPE_WORD:
            return get_word(raw, 0)
        if data_type == DATA_TYPE_INT:
            return get_int(raw, 0)
        if data_type == DATA_TYPE_DWORD:
            return get_dword(raw, 0)
        if data_type == DATA_TYPE_DINT:
            return get_dint(raw, 0)
        if data_type == DATA_TYPE_REAL:
            return get_real(raw, 0)
        return None

    def _write_value(self, tag_id: str, value: Any) -> None:
        """Write a value to the PLC (blocking)."""
        from snap7.util import (
            set_bool,
            set_dint,
            set_dword,
            set_int,
            set_real,
            set_word,
        )
        from snap7.types import Areas

        if tag_id not in self._parsed_tags:
            raise ValueError(f"Tag '{tag_id}' not found in coordinator")

        parsed = self._parsed_tags[tag_id]

        with self._lock:
            try:
                client = self._get_client()
                area = parsed["area"]
                db = parsed["db"]
                byte = parsed["byte"]
                bit = parsed["bit"]
                data_type = parsed["data_type"]
                size = _data_size(data_type)

                # Read-modify-write (required for bit operations)
                if area == AREA_DB:
                    raw = client.db_read(db, byte, size)
                else:
                    raw = client.read_area(Areas.MK, 0, byte, size)

                if data_type == DATA_TYPE_BOOL:
                    set_bool(raw, 0, bit, bool(value))
                elif data_type == DATA_TYPE_BYTE:
                    v = int(value)
                    if not 0 <= v <= 255:
                        raise ValueError(f"Byte value {v} is out of range 0–255")
                    raw[0] = v
                elif data_type == DATA_TYPE_WORD:
                    v = int(value)
                    if not 0 <= v <= 65535:
                        raise ValueError(f"Word value {v} is out of range 0–65535")
                    set_word(raw, 0, v)
                elif data_type == DATA_TYPE_INT:
                    v = int(value)
                    if not -32768 <= v <= 32767:
                        raise ValueError(f"Int value {v} is out of range -32768–32767")
                    set_int(raw, 0, v)
                elif data_type == DATA_TYPE_DWORD:
                    v = int(value)
                    if not 0 <= v <= 4294967295:
                        raise ValueError(
                            f"DWord value {v} is out of range 0–4294967295"
                        )
                    set_dword(raw, 0, v)
                elif data_type == DATA_TYPE_DINT:
                    v = int(value)
                    if not -2147483648 <= v <= 2147483647:
                        raise ValueError(
                            f"DInt value {v} is out of range -2147483648–2147483647"
                        )
                    set_dint(raw, 0, v)
                elif data_type == DATA_TYPE_REAL:
                    import math

                    f = float(value)
                    if not math.isfinite(f):
                        raise ValueError(
                            f"Real value {f!r} is not a finite number"
                        )
                    set_real(raw, 0, f)

                if area == AREA_DB:
                    client.db_write(db, byte, raw)
                else:
                    client.write_area(Areas.MK, 0, byte, raw)
            except Exception:
                self._client = None
                raise

    # ── async wrappers ──────────────────────────────────────────────────────

    async def async_write_tag(self, tag_id: str, value: Any) -> None:
        """Write *value* to the PLC tag identified by *tag_id*, then refresh."""
        await self.hass.async_add_executor_job(self._write_value, tag_id, value)
        await self.async_request_refresh()

    # ── coordinator refresh ─────────────────────────────────────────────────

    def _fetch_all(self) -> dict:
        """Read all tags from the PLC (blocking, runs in executor)."""
        with self._lock:
            # Ensure the client connects (raises on failure – caught by caller)
            try:
                self._get_client()
            except Exception:
                self._client = None
                raise

            result: dict[str, Any] = {}
            failed = 0
            for tag in self.tags:
                tag_id = tag["id"]
                if tag_id not in self._parsed_tags:
                    result[tag_id] = None
                    continue
                try:
                    result[tag_id] = self._read_value(self._parsed_tags[tag_id])
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.warning(
                        "Error reading tag '%s' (%s): %s",
                        tag.get("name"),
                        tag.get("address"),
                        exc,
                    )
                    result[tag_id] = None
                    failed += 1

            if self.tags and failed == len(self.tags):
                self._client = None
                raise ConnectionError(
                    f"All {failed} PLC tag read(s) failed for {self.plc_ip} – "
                    "disconnecting client"
                )

            return result

    async def _async_update_data(self) -> dict:
        """Fetch all PLC tags. Called by the DataUpdateCoordinator."""
        try:
            return await self.hass.async_add_executor_job(self._fetch_all)
        except Exception as exc:
            raise UpdateFailed(
                f"Error communicating with PLC at {self.plc_ip}: {exc}"
            ) from exc
