"""Config flow for the Snap7 PLC integration."""
from __future__ import annotations

import uuid
import yaml
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from .const import (
    CONF_LIBRARY,
    CONF_PLC_IP,
    CONF_RACK,
    CONF_SCAN_INTERVAL,
    CONF_SLOT,
    CONF_TAGS,
    DATA_TYPE_BOOL,
    DATA_TYPE_DINT,
    DATA_TYPE_INPUT_NUMBER,
    DATA_TYPE_INT,
    DATA_TYPE_REAL,
    DATA_TYPES,
    DEFAULT_LIBRARY,
    DEFAULT_RACK,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLOT,
    DOMAIN,
    LIBRARY_OPTIONS,
)
from .coordinator import parse_address


# Data types that support writable entities
_WRITABLE_TYPES = (
    DATA_TYPE_BOOL,
    DATA_TYPE_INPUT_NUMBER,
    DATA_TYPE_INT,
    DATA_TYPE_DINT,
    DATA_TYPE_REAL,
)


def _validate_and_normalize_tag(item: Any) -> dict[str, Any]:
    """Validate and normalize a single tag from imported YAML.

    Required fields in *item*: ``name`` (non-empty string), ``address``.
    Optional fields: ``data_type`` (defaults to the first entry in ``DATA_TYPES``),
    ``unit`` (defaults to ``""``), ``writable`` (defaults to ``False``), ``id``
    (a valid non-empty string is preserved; otherwise a new UUID is generated).

    Transformations applied:
    - ``name`` and ``address`` are stripped of leading/trailing whitespace.
    - ``address`` is validated by ``parse_address``; the resolved data_type from
      that call (``resolved_data_type``) is stored unless the supplied
      ``data_type`` is ``input_number``, which is preserved as-is.
    - ``input_number`` tags are unconditionally set to ``writable=True``.
    - Other non-writable data_types with ``writable=True`` raise ``ValueError``.

    Returns a normalised tag ``dict`` with keys: ``id``, ``name``, ``address``,
    ``data_type``, ``unit``, ``writable``.

    Raises ``ValueError`` with a descriptive message on validation failure.
    """
    if not isinstance(item, dict):
        raise ValueError("Each tag entry must be a YAML mapping")

    name = str(item.get("name", "")).strip()
    if not name:
        raise ValueError("Tag 'name' is required and must not be empty")

    address = str(item.get("address", "")).strip()
    if not address:
        raise ValueError(f"Tag '{name}': 'address' is required")

    data_type_raw = item.get("data_type")
    data_type = str(data_type_raw).strip() if data_type_raw is not None else DATA_TYPES[0]
    if data_type not in DATA_TYPES:
        raise ValueError(f"Tag '{name}': unknown data_type '{data_type}'")

    try:
        parsed = parse_address(address, data_type)
    except ValueError as exc:
        raise ValueError(f"Tag '{name}': invalid address '{address}': {exc}") from exc

    effective_data_type = parsed["data_type"]

    writable = bool(item.get("writable", False))
    # input_number is always writable; parse_address resolves it to int/dint,
    # so we check the originally-supplied data_type before resolution.
    if data_type == DATA_TYPE_INPUT_NUMBER:
        writable = True
    elif writable and effective_data_type not in _WRITABLE_TYPES:
        raise ValueError(
            f"Tag '{name}': data_type '{effective_data_type}' cannot be writable"
        )

    raw_id = item.get("id")
    if raw_id and isinstance(raw_id, str) and raw_id.strip():
        tag_id = raw_id.strip()
    else:
        tag_id = str(uuid.uuid4())

    return {
        "id": tag_id,
        "name": name,
        "address": address,
        # Preserve input_number as the stored data_type; the coordinator has
        # explicit handling for it.  All other types use the value resolved by
        # parse_address (which may differ, e.g. word → int).
        "data_type": data_type if data_type == DATA_TYPE_INPUT_NUMBER else effective_data_type,
        "unit": str(item.get("unit") or ""),
        "writable": writable,
    }


def _merge_tags(existing: list[dict], imported: list[dict]) -> list[dict]:
    """Merge imported tags into existing tags.

    Neither *existing* nor *imported* is mutated; a new list is always returned.

    Matching strategy:
      1. Match by ``id`` when it corresponds to an existing tag.
      2. Otherwise match by ``(name.lower(), address.upper())``.
    Matched tags are updated with imported fields; unmatched imported tags are
    appended.  Existing tags not referenced by the import are kept unchanged.
    """
    result: list[dict] = [dict(t) for t in existing]

    id_index: dict[str, int] = {t["id"]: i for i, t in enumerate(result)}
    key_index: dict[tuple[str, str], int] = {
        (t["name"].lower().strip(), t["address"].upper().strip()): i
        for i, t in enumerate(result)
    }

    for imp_tag in imported:
        imp_id = imp_tag["id"]
        imp_key = (imp_tag["name"].lower().strip(), imp_tag["address"].upper().strip())

        if imp_id in id_index:
            result[id_index[imp_id]] = dict(imp_tag)
        elif imp_key in key_index:
            idx = key_index[imp_key]
            updated = dict(imp_tag)
            updated["id"] = result[idx]["id"]
            result[idx] = updated
        else:
            result.append(dict(imp_tag))

    return result


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
            menu_options=[
                "add_tag",
                "remove_tag",
                "import_tags",
                "export_tags",
                "settings",
                "save",
            ],
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
                if user_input.get("writable") and parsed["data_type"] not in _WRITABLE_TYPES:
                    errors["writable"] = "only_numeric_writable"
                else:
                    # input_number is always writable regardless of the checkbox
                    is_writable = (
                        True
                        if parsed["data_type"] == DATA_TYPE_INPUT_NUMBER
                        else user_input.get("writable", False)
                    )
                    tag: dict[str, Any] = {
                        "id": str(uuid.uuid4()),
                        "name": user_input["name"].strip(),
                        "address": address,
                        "data_type": parsed["data_type"],
                        "unit": user_input.get("unit", ""),
                        "writable": is_writable,
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

    # ── export tags ─────────────────────────────────────────────────────────

    async def async_step_export_tags(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Display the current tag list as YAML for copy/paste."""
        if user_input is not None:
            return await self.async_step_menu()

        tags_data = [
            {
                "id": t["id"],
                "name": t["name"],
                "address": t["address"],
                "data_type": t["data_type"],
                "unit": t.get("unit", ""),
                "writable": t.get("writable", False),
            }
            for t in self._tags
        ]
        yaml_text = yaml.dump(
            {"tags": tags_data},
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        return self.async_show_form(
            step_id="export_tags",
            data_schema=vol.Schema({}),
            description_placeholders={"yaml_content": yaml_text},
        )

    # ── import tags ──────────────────────────────────────────────────────────

    async def async_step_import_tags(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Import tags from YAML and merge with existing tags."""
        errors: dict[str, str] = {}

        if user_input is not None:
            raw_yaml = (user_input.get("yaml_content") or "").strip()
            try:
                parsed_yaml = yaml.safe_load(raw_yaml)
            except yaml.YAMLError:
                errors["yaml_content"] = "invalid_yaml"
                parsed_yaml = None

            if parsed_yaml is not None:
                if isinstance(parsed_yaml, list):
                    tag_list: list | None = parsed_yaml
                elif isinstance(parsed_yaml, dict) and isinstance(
                    parsed_yaml.get("tags"), list
                ):
                    tag_list = parsed_yaml["tags"]
                else:
                    errors["yaml_content"] = "invalid_yaml_structure"
                    tag_list = None

                if tag_list is not None:
                    validated: list[dict] = []
                    for item in tag_list:
                        try:
                            validated.append(_validate_and_normalize_tag(item))
                        except ValueError:
                            errors["yaml_content"] = "yaml_tag_validation_error"
                            break

                    if not errors:
                        self._tags = _merge_tags(self._tags, validated)
                        return await self.async_step_menu()

        schema = vol.Schema(
            {
                vol.Required("yaml_content"): TextSelector(
                    TextSelectorConfig(multiline=True)
                ),
            }
        )

        return self.async_show_form(
            step_id="import_tags",
            data_schema=schema,
            errors=errors,
        )

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
