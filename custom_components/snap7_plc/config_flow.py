"""Config flow for the Snap7 PLC integration."""
from __future__ import annotations

import uuid
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_LIBRARY,
    CONF_PLC_IP,
    CONF_RACK,
    CONF_SCAN_INTERVAL,
    CONF_SLOT,
    CONF_TAGS,
    DATA_TYPE_BOOL,
    DATA_TYPES,
    DEFAULT_LIBRARY,
    DEFAULT_RACK,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLOT,
    DOMAIN,
    LIBRARY_OPTIONS,
)
from .coordinator import parse_address


_S7_PORT = 102  # Standard Siemens S7 TCP port
_NETWORK_TIMEOUT = 3  # seconds


def _validate_connection_config(plc_ip: str, rack: int, slot: int, library: str) -> str | None:
    """Validate config entry inputs; return an error key or *None* on success.

    Steps
    -----
    1. Verify that the selected PLC library can be imported (checks installation).
    2. Validate that *plc_ip* is a syntactically valid IP address.

    The actual TCP/PLC connection is intentionally **not** tested here so that
    the entry can be created even when the PLC is temporarily offline.  The
    coordinator will retry the connection via ``ConfigEntryNotReady``.
    """
    import ipaddress

    from .const import LIBRARY_SNAP7

    # ── Step 1: library available? ──────────────────────────────────────────
    if library == LIBRARY_SNAP7:
        try:
            import snap7 as _snap7  # noqa: F401
        except ImportError:
            return "snap7_not_installed"
    else:
        return "library_not_supported"

    # ── Step 2: valid IP address format? ────────────────────────────────────
    try:
        ipaddress.ip_address(plc_ip)
    except ValueError:
        return "invalid_ip"

    return None


# ---------------------------------------------------------------------------
# Main config flow
# ---------------------------------------------------------------------------

class Snap7ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration of a Snap7 PLC."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the first step (connection settings)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            error_key = await self.hass.async_add_executor_job(
                _validate_connection_config,
                user_input[CONF_PLC_IP],
                user_input[CONF_RACK],
                user_input[CONF_SLOT],
                user_input.get(CONF_LIBRARY, DEFAULT_LIBRARY),
            )
            if error_key:
                errors["base"] = error_key
            else:
                plc_ip = user_input[CONF_PLC_IP]
                rack = user_input[CONF_RACK]
                slot = user_input[CONF_SLOT]
                await self.async_set_unique_id(f"{plc_ip}:{rack}:{slot}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"PLC {plc_ip}",
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_PLC_IP): str,
                vol.Optional(CONF_RACK, default=DEFAULT_RACK): vol.Coerce(int),
                vol.Optional(CONF_SLOT, default=DEFAULT_SLOT): vol.Coerce(int),
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=100)),
                vol.Optional(CONF_LIBRARY, default=DEFAULT_LIBRARY): vol.In(
                    LIBRARY_OPTIONS
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Allow the user to update IP / rack / slot without losing options."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            error_key = await self.hass.async_add_executor_job(
                _validate_connection_config,
                user_input[CONF_PLC_IP],
                user_input[CONF_RACK],
                user_input[CONF_SLOT],
                user_input.get(CONF_LIBRARY, DEFAULT_LIBRARY),
            )
            if error_key:
                errors["base"] = error_key
            else:
                plc_ip = user_input[CONF_PLC_IP]
                rack = user_input[CONF_RACK]
                slot = user_input[CONF_SLOT]
                await self.async_set_unique_id(f"{plc_ip}:{rack}:{slot}")
                self._abort_if_unique_id_configured(
                    updates=user_input, reload_on_update=False
                )
                return self.async_update_reload_and_abort(
                    entry, data_updates=user_input
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PLC_IP, default=entry.data.get(CONF_PLC_IP, "")
                ): str,
                vol.Optional(
                    CONF_RACK, default=entry.data.get(CONF_RACK, DEFAULT_RACK)
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_SLOT, default=entry.data.get(CONF_SLOT, DEFAULT_SLOT)
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=100)),
                vol.Optional(
                    CONF_LIBRARY,
                    default=entry.data.get(CONF_LIBRARY, DEFAULT_LIBRARY),
                ): vol.In(LIBRARY_OPTIONS),
            }
        )

        return self.async_show_form(
            step_id="reconfigure", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> Snap7OptionsFlow:
        """Return the options flow handler."""
        return Snap7OptionsFlow(config_entry)


# ---------------------------------------------------------------------------
# Options flow  (tag management + scan interval override)
# ---------------------------------------------------------------------------

class Snap7OptionsFlow(config_entries.OptionsFlow):
    """Handle options: add / remove tags and update scan interval."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._tags: list[dict] = list(config_entry.options.get(CONF_TAGS, []))
        self._scan_interval: int = config_entry.options.get(
            CONF_SCAN_INTERVAL,
            config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

    # ── menu ────────────────────────────────────────────────────────────────

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        return await self.async_step_menu()

    async def async_step_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        return self.async_show_menu(
            step_id="menu",
            menu_options=["add_tag", "remove_tag", "settings", "save"],
        )

    # ── add tag ─────────────────────────────────────────────────────────────

    async def async_step_add_tag(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input.get("address", "").strip()
            data_type = user_input.get("data_type", "")
            try:
                parsed = parse_address(address, data_type)
            except ValueError:
                errors["address"] = "invalid_address"
            else:
                if user_input.get("writable") and parsed["data_type"] != DATA_TYPE_BOOL:
                    errors["writable"] = "only_bool_writable"
                else:
                    tag: dict[str, Any] = {
                        "id": str(uuid.uuid4()),
                        "name": user_input["name"].strip(),
                        "address": address,
                        "data_type": parsed["data_type"],
                        "unit": user_input.get("unit", ""),
                        "writable": user_input.get("writable", False),
                    }
                    self._tags.append(tag)
                    return await self.async_step_menu()

        schema = vol.Schema(
            {
                vol.Required("name"): str,
                vol.Required("address"): str,
                vol.Required("data_type"): vol.In(DATA_TYPES),
                vol.Optional("unit", default=""): str,
                vol.Optional("writable", default=False): bool,
            }
        )

        return self.async_show_form(
            step_id="add_tag", data_schema=schema, errors=errors
        )

    # ── remove tag ──────────────────────────────────────────────────────────

    async def async_step_remove_tag(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if not self._tags:
            return await self.async_step_menu()

        if user_input is not None:
            ids_to_remove: list[str] = user_input.get("tags_to_remove", [])
            self._tags = [t for t in self._tags if t["id"] not in ids_to_remove]
            return await self.async_step_menu()

        tag_options = {t["id"]: f"{t['name']} ({t['address']})" for t in self._tags}

        schema = vol.Schema(
            {
                vol.Optional("tags_to_remove"): cv.multi_select(tag_options),
            }
        )

        return self.async_show_form(step_id="remove_tag", data_schema=schema)

    # ── settings ────────────────────────────────────────────────────────────

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        if user_input is not None:
            self._scan_interval = user_input[CONF_SCAN_INTERVAL]
            return await self.async_step_menu()

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=self._scan_interval
                ): vol.All(vol.Coerce(int), vol.Range(min=100)),
            }
        )

        return self.async_show_form(step_id="settings", data_schema=schema)

    # ── save ────────────────────────────────────────────────────────────────

    async def async_step_save(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        return self.async_create_entry(
            title="",
            data={
                CONF_TAGS: self._tags,
                CONF_SCAN_INTERVAL: self._scan_interval,
            },
        )
