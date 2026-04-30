"""Data coordinator for the Snap7 PLC integration."""
from __future__ import annotations

import logging
import re
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
      - Boolean  : ``M<byte>.<bit>``   e.g. ``M0.0``
      - Byte     : ``MB<byte>``         e.g. ``MB10``
      - Word/Int : ``MW<byte>``         e.g. ``MW20``
      - DWord …  : ``MD<byte>``         e.g. ``MD100``

    DB area (Data Block):
      - Boolean  : ``DB<n>.DBX<byte>.<bit>``  e.g. ``DB1.DBX0.0``
      - Byte     : ``DB<n>.DBB<byte>``         e.g. ``DB1.DBB2``
      - Word/Int : ``DB<n>.DBW<byte>``         e.g. ``DB1.DBW4``
      - DWord …  : ``DB<n>.DBD<byte>``         e.g. ``DB1.DBD8``

    The *data_type* argument refines interpretation when the address prefix
    is ambiguous (e.g. ``DBW`` can be ``word`` or ``int``).
    """
    addr = address.strip().upper()

    # ── DB area ────────────────────────────────────────────────────────────
    m = re.match(r"^DB(\d+)\.DBX(\d+)\.(\d+)$", addr)
    if m:
        return {
            "area": AREA_DB,
            "db": int(m.group(1)),
            "byte": int(m.group(2)),
            "bit": int(m.group(3)),
            "data_type": DATA_TYPE_BOOL,
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
        return {
            "area": AREA_M,
            "db": 0,
            "byte": int(m.group(1)),
            "bit": int(m.group(2)),
            "data_type": DATA_TYPE_BOOL,
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
            update_interval=timedelta(seconds=scan_interval),
        )
        self.plc_ip = plc_ip
        self.rack = rack
        self.slot = slot
        self.tags = tags
        self._client: Any = None

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

        return self._client

    def disconnect(self) -> None:
        """Gracefully disconnect from the PLC."""
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
        import snap7
        from snap7.util import (
            get_bool,
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
            raw[0] = int(value) & 0xFF
        elif data_type == DATA_TYPE_WORD:
            set_word(raw, 0, int(value))
        elif data_type == DATA_TYPE_INT:
            set_int(raw, 0, int(value))
        elif data_type == DATA_TYPE_DWORD:
            set_dword(raw, 0, int(value))
        elif data_type == DATA_TYPE_DINT:
            set_dint(raw, 0, int(value))
        elif data_type == DATA_TYPE_REAL:
            set_real(raw, 0, float(value))

        if area == AREA_DB:
            client.db_write(db, byte, raw)
        else:
            client.write_area(Areas.MK, 0, byte, raw)

    # ── async wrappers ──────────────────────────────────────────────────────

    async def async_write_tag(self, tag_id: str, value: Any) -> None:
        """Write *value* to the PLC tag identified by *tag_id*, then refresh."""
        await self.hass.async_add_executor_job(self._write_value, tag_id, value)
        await self.async_request_refresh()

    # ── coordinator refresh ─────────────────────────────────────────────────

    def _fetch_all(self) -> dict:
        """Read all tags from the PLC (blocking, runs in executor)."""
        # Ensure the client connects (raises on failure – caught by caller)
        try:
            self._get_client()
        except Exception as exc:
            self._client = None
            raise exc

        result: dict[str, Any] = {}
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
        return result

    async def _async_update_data(self) -> dict:
        """Fetch all PLC tags. Called by the DataUpdateCoordinator."""
        try:
            return await self.hass.async_add_executor_job(self._fetch_all)
        except Exception as exc:
            raise UpdateFailed(
                f"Error communicating with PLC at {self.plc_ip}: {exc}"
            ) from exc
