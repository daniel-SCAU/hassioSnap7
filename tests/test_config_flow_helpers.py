"""Tests for config_flow helper functions: _validate_and_normalize_tag and _merge_tags."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import custom_components.snap7_plc.config_flow as config_flow_module
from custom_components.snap7_plc.config_flow import (
    Snap7OptionsFlow,
    _apply_label_to_new_imported_tags,
    _format_tag_name_with_label,
    _merge_tags,
    _validate_and_normalize_tag,
)
from custom_components.snap7_plc.const import CONF_SCAN_INTERVAL

DEFAULT_TEST_SCAN_INTERVAL = 30000


# ---------------------------------------------------------------------------
# _validate_and_normalize_tag
# ---------------------------------------------------------------------------


class TestValidateAndNormalizeTag:
    """Tests for the YAML tag validation/normalisation helper."""

    def test_valid_real_tag(self):
        tag = _validate_and_normalize_tag(
            {
                "name": "Temperature",
                "address": "DB1.DBD0",
                "data_type": "real",
                "unit": "°C",
                "writable": False,
            }
        )
        assert tag["name"] == "Temperature"
        assert tag["data_type"] == "real"
        assert tag["unit"] == "°C"
        assert tag["writable"] is False
        assert tag["id"]  # auto-generated UUID

    def test_valid_bool_tag(self):
        tag = _validate_and_normalize_tag(
            {"name": "RunBit", "address": "M0.0", "data_type": "bool"}
        )
        assert tag["data_type"] == "bool"
        assert tag["writable"] is False

    def test_name_is_stripped(self):
        tag = _validate_and_normalize_tag(
            {"name": "  Motor  ", "address": "MB1", "data_type": "byte"}
        )
        assert tag["name"] == "Motor"

    def test_id_is_preserved_when_provided(self):
        tag = _validate_and_normalize_tag(
            {"id": "my-custom-id", "name": "X", "address": "M0.0", "data_type": "bool"}
        )
        assert tag["id"] == "my-custom-id"

    def test_id_is_generated_when_missing(self):
        tag = _validate_and_normalize_tag(
            {"name": "X", "address": "M0.0", "data_type": "bool"}
        )
        assert len(tag["id"]) > 0

    def test_unit_defaults_to_empty_string(self):
        tag = _validate_and_normalize_tag(
            {"name": "X", "address": "M0.0", "data_type": "bool"}
        )
        assert tag["unit"] == ""

    def test_unit_none_becomes_empty_string(self):
        tag = _validate_and_normalize_tag(
            {"name": "X", "address": "M0.0", "data_type": "bool", "unit": None}
        )
        assert tag["unit"] == ""

    def test_input_number_is_always_writable(self):
        tag = _validate_and_normalize_tag(
            {
                "name": "Setpoint",
                "address": "DB1.DBD0",
                "data_type": "input_number",
                "writable": False,
            }
        )
        assert tag["writable"] is True

    def test_bool_writable_is_accepted(self):
        tag = _validate_and_normalize_tag(
            {"name": "Switch", "address": "M0.0", "data_type": "bool", "writable": True}
        )
        assert tag["writable"] is True

    def test_int_writable_is_accepted(self):
        tag = _validate_and_normalize_tag(
            {"name": "Counter", "address": "DB1.DBW0", "data_type": "int", "writable": True}
        )
        assert tag["writable"] is True

    def test_non_writable_type_with_writable_flag_raises(self):
        with pytest.raises(ValueError, match="cannot be writable"):
            _validate_and_normalize_tag(
                {"name": "X", "address": "DB1.DBW0", "data_type": "word", "writable": True}
            )

    def test_missing_name_raises(self):
        with pytest.raises(ValueError, match="'name' is required"):
            _validate_and_normalize_tag({"address": "M0.0", "data_type": "bool"})

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="'name' is required"):
            _validate_and_normalize_tag(
                {"name": "   ", "address": "M0.0", "data_type": "bool"}
            )

    def test_missing_address_raises(self):
        with pytest.raises(ValueError, match="'address' is required"):
            _validate_and_normalize_tag({"name": "X", "data_type": "bool"})

    def test_invalid_address_raises(self):
        with pytest.raises(ValueError, match="invalid address"):
            _validate_and_normalize_tag(
                {"name": "X", "address": "NOTVALID", "data_type": "bool"}
            )

    def test_unknown_data_type_raises(self):
        with pytest.raises(ValueError, match="unknown data_type"):
            _validate_and_normalize_tag(
                {"name": "X", "address": "M0.0", "data_type": "foobar"}
            )

    def test_non_dict_raises(self):
        with pytest.raises(ValueError, match="YAML mapping"):
            _validate_and_normalize_tag("not-a-dict")

    def test_data_type_defaults_to_first_when_missing(self):
        """data_type is optional; defaults to the first entry in DATA_TYPES."""
        from custom_components.snap7_plc.const import DATA_TYPES

        tag = _validate_and_normalize_tag({"name": "X", "address": "M0.0"})
        # The effective data_type may differ because parse_address may resolve it
        # (e.g. bool address → bool type). Just ensure no exception is raised.
        assert tag["data_type"] in DATA_TYPES


# ---------------------------------------------------------------------------
# _merge_tags
# ---------------------------------------------------------------------------


class TestMergeTags:
    """Tests for the tag-merge helper."""

    def _make_tag(self, tag_id, name, address, **kwargs):
        return {
            "id": tag_id,
            "name": name,
            "address": address,
            "data_type": "bool",
            "unit": "",
            "writable": False,
            **kwargs,
        }

    def test_update_matched_by_id(self):
        existing = [self._make_tag("a", "Old Name", "M0.0")]
        imported = [self._make_tag("a", "New Name", "M0.0")]
        result = _merge_tags(existing, imported)
        assert len(result) == 1
        assert result[0]["name"] == "New Name"

    def test_append_unmatched_imported_tag(self):
        existing = [self._make_tag("a", "Tag A", "M0.0")]
        imported = [self._make_tag("b", "Tag B", "M0.1")]
        result = _merge_tags(existing, imported)
        assert len(result) == 2
        assert result[1]["name"] == "Tag B"

    def test_keep_existing_not_in_import(self):
        existing = [
            self._make_tag("a", "Tag A", "M0.0"),
            self._make_tag("b", "Tag B", "M0.1"),
        ]
        imported = [self._make_tag("a", "Tag A Updated", "M0.0")]
        result = _merge_tags(existing, imported)
        assert len(result) == 2
        assert result[1]["name"] == "Tag B"

    def test_match_by_name_address_key_preserves_existing_id(self):
        existing = [self._make_tag("original-id", "Motor Speed", "DB1.DBD0")]
        # Same logical tag, different id, normalized name/address
        imported = [self._make_tag("imported-id", "motor speed", "db1.dbd0")]
        result = _merge_tags(existing, imported)
        assert len(result) == 1
        assert result[0]["id"] == "original-id"

    def test_id_match_takes_priority_over_name_address(self):
        existing = [
            self._make_tag("a", "Tag A", "M0.0"),
            self._make_tag("b", "Tag B", "M0.1"),
        ]
        # id 'a' matches first tag; name/address also matches second (won't apply)
        imported = [self._make_tag("a", "tag b", "m0.1")]
        result = _merge_tags(existing, imported)
        assert len(result) == 2
        # id 'a' was updated with new name
        assert result[0]["name"] == "tag b"
        # Tag B is unchanged
        assert result[1]["name"] == "Tag B"

    def test_empty_existing(self):
        imported = [self._make_tag("a", "New Tag", "M0.0")]
        result = _merge_tags([], imported)
        assert len(result) == 1

    def test_empty_imported(self):
        existing = [self._make_tag("a", "Existing", "M0.0")]
        result = _merge_tags(existing, [])
        assert len(result) == 1
        assert result[0]["name"] == "Existing"

    def test_does_not_mutate_existing_list(self):
        existing = [self._make_tag("a", "Tag A", "M0.0")]
        original_name = existing[0]["name"]
        _merge_tags(existing, [self._make_tag("a", "Modified", "M0.0")])
        assert existing[0]["name"] == original_name


class TestLabelBasedNaming:
    def test_missing_label_raises(self):
        with pytest.raises(ValueError, match="label is required"):
            _format_tag_name_with_label("Ready to start", "   ")

    def test_formats_plc_prefixed_name(self):
        assert (
            _format_tag_name_with_label("PLC 192_168_1_1 Ready to start", "LINE_A")
            == "[LINE_A].Ready to start"
        )

    def test_import_applies_label_only_to_new_tags(self):
        existing = [
            {
                "id": "existing-id",
                "name": "PLC 192_168_1_1 Ready to start",
                "address": "M0.0",
                "data_type": "bool",
                "unit": "",
                "writable": False,
            }
        ]
        imported = [
            {
                "id": "existing-id",
                "name": "PLC 192_168_1_1 Ready to start",
                "address": "M0.0",
                "data_type": "bool",
                "unit": "",
                "writable": False,
            },
            {
                "id": "new-id",
                "name": "PLC 192_168_1_1 Pump Running",
                "address": "M0.1",
                "data_type": "bool",
                "unit": "",
                "writable": False,
            },
        ]

        processed = _apply_label_to_new_imported_tags(existing, imported, "LINE_A")
        merged = _merge_tags(existing, processed)

        assert merged[0]["name"] == "PLC 192_168_1_1 Ready to start"
        assert merged[1]["name"] == "[LINE_A].Pump Running"


class TestOptionsFlowLabelValidation:
    @staticmethod
    def _flow(monkeypatch) -> Snap7OptionsFlow:
        entry = SimpleNamespace(
            options={}, data={CONF_SCAN_INTERVAL: DEFAULT_TEST_SCAN_INTERVAL}
        )
        flow = Snap7OptionsFlow(entry)
        monkeypatch.setattr(config_flow_module, "TextSelector", lambda _config=None: str)
        flow.async_show_form = lambda **kwargs: kwargs
        flow.async_step_menu = AsyncMock(return_value={"type": "menu"})
        return flow

    def test_add_tag_requires_label(self, monkeypatch):
        flow = self._flow(monkeypatch)
        result = asyncio.run(
            flow.async_step_add_tag(
                {
                    "label": " ",
                    "name": "Ready to start",
                    "address": "M0.0",
                    "data_type": "bool",
                }
            )
        )
        assert result["errors"]["label"] == "label_required"
        assert flow._tags == []

    def test_import_tags_requires_label(self, monkeypatch):
        flow = self._flow(monkeypatch)
        result = asyncio.run(
            flow.async_step_import_tags(
                {
                    "label": "",
                    "yaml_content": "- name: Ready to start\n  address: M0.0\n  data_type: bool",
                }
            )
        )
        assert result["errors"]["label"] == "label_required"

    def test_add_tag_formats_name_with_label(self, monkeypatch):
        flow = self._flow(monkeypatch)
        asyncio.run(
            flow.async_step_add_tag(
                {
                    "label": "LINE_A",
                    "name": "PLC 192_168_1_1 Ready to start",
                    "address": "M0.0",
                    "data_type": "bool",
                }
            )
        )
        assert flow._tags[0]["name"] == "[LINE_A].Ready to start"

    def test_import_new_tag_formats_name_with_label(self, monkeypatch):
        flow = self._flow(monkeypatch)
        asyncio.run(
            flow.async_step_import_tags(
                {
                    "label": "LINE_A",
                    "yaml_content": (
                        "- id: new-id\n"
                        "  name: PLC 192_168_1_1 Pump Running\n"
                        "  address: M0.1\n"
                        "  data_type: bool"
                    ),
                }
            )
        )
        assert flow._tags[0]["name"] == "[LINE_A].Pump Running"
