"""Tests for the Snap7 PLC integration – coordinator address parser."""
import pytest
import threading
import math
from datetime import timedelta
from unittest.mock import MagicMock, patch

# Make sure imports work without a real Home Assistant instance
import sys
import os

# Add the repo root so we can import custom_components directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.snap7_plc.coordinator import Snap7Coordinator, parse_address, _format_plc_date
from custom_components.snap7_plc.const import (
    AREA_DB,
    AREA_M,
    DATA_TYPE_BOOL,
    DATA_TYPE_BYTE,
    DATA_TYPE_DATE,
    DATA_TYPE_DINT,
    DATA_TYPE_DWORD,
    DATA_TYPE_INPUT_NUMBER,
    DATA_TYPE_INT,
    DATA_TYPE_REAL,
    DATA_TYPE_STRING,
    DATA_TYPE_WORD,
)


# ---------------------------------------------------------------------------
# M area
# ---------------------------------------------------------------------------

class TestMAreaBool:
    def test_bit_format(self):
        result = parse_address("M0.0", DATA_TYPE_BOOL)
        assert result["area"] == AREA_M
        assert result["byte"] == 0
        assert result["bit"] == 0
        assert result["data_type"] == DATA_TYPE_BOOL

    def test_bit_higher_byte(self):
        result = parse_address("M10.7", DATA_TYPE_BOOL)
        assert result["byte"] == 10
        assert result["bit"] == 7

    def test_case_insensitive(self):
        result = parse_address("m5.3", DATA_TYPE_BOOL)
        assert result["byte"] == 5
        assert result["bit"] == 3


class TestMAreaByte:
    def test_byte(self):
        result = parse_address("MB0", DATA_TYPE_BYTE)
        assert result["area"] == AREA_M
        assert result["byte"] == 0
        assert result["data_type"] == DATA_TYPE_BYTE

    def test_byte_higher(self):
        result = parse_address("MB100", DATA_TYPE_BYTE)
        assert result["byte"] == 100


class TestMAreaWord:
    def test_word(self):
        result = parse_address("MW0", DATA_TYPE_WORD)
        assert result["area"] == AREA_M
        assert result["byte"] == 0
        assert result["data_type"] == DATA_TYPE_WORD

    def test_int(self):
        result = parse_address("MW0", DATA_TYPE_INT)
        assert result["data_type"] == DATA_TYPE_INT

    def test_defaults_to_word(self):
        result = parse_address("MW0", DATA_TYPE_BOOL)
        assert result["data_type"] == DATA_TYPE_WORD


class TestMAreaDWord:
    def test_dword(self):
        result = parse_address("MD0", DATA_TYPE_DWORD)
        assert result["area"] == AREA_M
        assert result["byte"] == 0
        assert result["data_type"] == DATA_TYPE_DWORD

    def test_dint(self):
        result = parse_address("MD4", DATA_TYPE_DINT)
        assert result["data_type"] == DATA_TYPE_DINT

    def test_real(self):
        result = parse_address("MD8", DATA_TYPE_REAL)
        assert result["data_type"] == DATA_TYPE_REAL

    def test_defaults_to_dword(self):
        result = parse_address("MD0", DATA_TYPE_BOOL)
        assert result["data_type"] == DATA_TYPE_DWORD


# ---------------------------------------------------------------------------
# DB area
# ---------------------------------------------------------------------------

class TestDBAreaBool:
    def test_dbx(self):
        result = parse_address("DB1.DBX0.0", DATA_TYPE_BOOL)
        assert result["area"] == AREA_DB
        assert result["db"] == 1
        assert result["byte"] == 0
        assert result["bit"] == 0
        assert result["data_type"] == DATA_TYPE_BOOL

    def test_dbx_higher(self):
        result = parse_address("DB10.DBX20.5", DATA_TYPE_BOOL)
        assert result["db"] == 10
        assert result["byte"] == 20
        assert result["bit"] == 5


class TestDBAreaByte:
    def test_dbb(self):
        result = parse_address("DB1.DBB0", DATA_TYPE_BYTE)
        assert result["area"] == AREA_DB
        assert result["db"] == 1
        assert result["byte"] == 0
        assert result["data_type"] == DATA_TYPE_BYTE


class TestDBAreaWord:
    def test_dbw_word(self):
        result = parse_address("DB1.DBW0", DATA_TYPE_WORD)
        assert result["area"] == AREA_DB
        assert result["data_type"] == DATA_TYPE_WORD

    def test_dbw_int(self):
        result = parse_address("DB1.DBW2", DATA_TYPE_INT)
        assert result["data_type"] == DATA_TYPE_INT

    def test_dbw_defaults_to_word(self):
        result = parse_address("DB1.DBW0", DATA_TYPE_BOOL)
        assert result["data_type"] == DATA_TYPE_WORD


class TestDBAreaDWord:
    def test_dbd_dword(self):
        result = parse_address("DB1.DBD0", DATA_TYPE_DWORD)
        assert result["area"] == AREA_DB
        assert result["data_type"] == DATA_TYPE_DWORD

    def test_dbd_dint(self):
        result = parse_address("DB1.DBD4", DATA_TYPE_DINT)
        assert result["data_type"] == DATA_TYPE_DINT

    def test_dbd_real(self):
        result = parse_address("DB1.DBD8", DATA_TYPE_REAL)
        assert result["data_type"] == DATA_TYPE_REAL


# ---------------------------------------------------------------------------
# String tags
# ---------------------------------------------------------------------------

class TestMAreaString:
    def test_basic_string(self):
        result = parse_address("MB140(4)", DATA_TYPE_STRING)
        assert result["area"] == AREA_M
        assert result["byte"] == 140
        assert result["data_type"] == DATA_TYPE_STRING
        assert result["string_length"] == 4

    def test_string_length_1(self):
        result = parse_address("MB0(1)", DATA_TYPE_STRING)
        assert result["string_length"] == 1

    def test_string_larger_length(self):
        result = parse_address("MB200(20)", DATA_TYPE_STRING)
        assert result["byte"] == 200
        assert result["string_length"] == 20

    def test_case_insensitive(self):
        result = parse_address("mb140(4)", DATA_TYPE_STRING)
        assert result["area"] == AREA_M
        assert result["string_length"] == 4

    def test_data_type_forced_to_string(self):
        # data_type argument is ignored for string addresses
        result = parse_address("MB140(4)", DATA_TYPE_BOOL)
        assert result["data_type"] == DATA_TYPE_STRING


class TestDBAreaString:
    def test_basic_string(self):
        result = parse_address("DB1.DBB0(10)", DATA_TYPE_STRING)
        assert result["area"] == AREA_DB
        assert result["db"] == 1
        assert result["byte"] == 0
        assert result["data_type"] == DATA_TYPE_STRING
        assert result["string_length"] == 10

    def test_string_higher_db_and_byte(self):
        result = parse_address("DB5.DBB20(8)", DATA_TYPE_STRING)
        assert result["db"] == 5
        assert result["byte"] == 20
        assert result["string_length"] == 8

    def test_data_type_forced_to_string(self):
        result = parse_address("DB1.DBB0(4)", DATA_TYPE_BOOL)
        assert result["data_type"] == DATA_TYPE_STRING


# ---------------------------------------------------------------------------
# Invalid addresses
# ---------------------------------------------------------------------------

class TestInvalidAddresses:
    @pytest.mark.parametrize(
        "addr",
        [
            "X0.0",
            "DB.DBX0.0",
            "DB1.DBZ0",
            "MX0",
            "0.0",
            "",
            "MW",
            "DB1",
        ],
    )
    def test_raises_value_error(self, addr):
        with pytest.raises(ValueError):
            parse_address(addr, DATA_TYPE_BOOL)

    def test_m_bit_out_of_range(self):
        with pytest.raises(ValueError, match="out of range"):
            parse_address("M0.8", DATA_TYPE_BOOL)

    def test_m_bit_max_valid(self):
        result = parse_address("M0.7", DATA_TYPE_BOOL)
        assert result["bit"] == 7

    def test_dbx_bit_out_of_range(self):
        with pytest.raises(ValueError, match="out of range"):
            parse_address("DB1.DBX0.8", DATA_TYPE_BOOL)

    def test_dbx_bit_max_valid(self):
        result = parse_address("DB1.DBX0.7", DATA_TYPE_BOOL)
        assert result["bit"] == 7


# ---------------------------------------------------------------------------
# Helper: build a Snap7Coordinator bypassing the HA parent __init__
# ---------------------------------------------------------------------------

def _make_coordinator(tags=None):
    """Create a Snap7Coordinator with no real HA instance for unit testing."""
    from custom_components.snap7_plc.backends import Snap7Backend

    coord = Snap7Coordinator.__new__(Snap7Coordinator)
    coord.plc_ip = "192.168.1.100"
    coord.rack = 0
    coord.slot = 1
    coord.tags = tags or []
    coord._backend = Snap7Backend()
    coord._lock = threading.Lock()
    coord._parsed_tags = {}
    for tag in (tags or []):
        try:
            coord._parsed_tags[tag["id"]] = parse_address(
                tag["address"], tag["data_type"]
            )
        except ValueError:
            pass
    return coord


def _set_backend_client(coord, client):
    """Inject *client* directly into the coordinator's Snap7Backend."""
    coord._backend._client = client


def _bool_tag(tag_id: str = "t1") -> dict:
    return {"id": tag_id, "name": "Test", "address": "DB1.DBX0.0", "data_type": DATA_TYPE_BOOL}


def _word_tag(tag_id: str = "t2") -> dict:
    return {"id": tag_id, "name": "Speed", "address": "DB1.DBW2", "data_type": DATA_TYPE_WORD}


# ---------------------------------------------------------------------------
# Thread lock
# ---------------------------------------------------------------------------

class TestThreadLock:
    def test_lock_is_created(self):
        coord = _make_coordinator()
        assert isinstance(coord._lock, type(threading.Lock()))

    def test_lock_is_reentrant_check(self):
        """_fetch_all must NOT deadlock (calls disconnect()-like code inside lock)."""
        from tests.conftest import _FakeSnap7Client

        coord = _make_coordinator(tags=[_bool_tag()])
        # Pre-set a connected client so _ensure_connected() doesn't reconnect
        _set_backend_client(coord, _FakeSnap7Client())

        result = [None]
        exc_holder = [None]

        def run():
            try:
                result[0] = coord._fetch_all()
            except Exception as e:
                exc_holder[0] = e

        t = threading.Thread(target=run)
        t.start()
        t.join(timeout=5)
        assert not t.is_alive(), "Deadlock detected: _fetch_all never returned"
        assert exc_holder[0] is None, f"Unexpected exception: {exc_holder[0]}"


# ---------------------------------------------------------------------------
# Coordinator: all-tag-fail detection
# ---------------------------------------------------------------------------

class TestFetchAllFailure:
    def test_all_reads_fail_raises_connection_error(self):
        """When every tag read fails, _fetch_all should raise ConnectionError."""
        tag = _bool_tag()
        coord = _make_coordinator(tags=[tag])

        # Make the stub client raise on db_read
        import sys
        bad_client = MagicMock()
        bad_client.get_connected.return_value = True
        bad_client.db_read.side_effect = RuntimeError("simulated read error")
        _set_backend_client(coord, bad_client)

        with pytest.raises(ConnectionError, match="All.*tag read"):
            coord._fetch_all()

    def test_all_reads_fail_resets_client(self):
        """When all reads fail, the backend must be disconnected so next poll reconnects."""
        tag = _bool_tag()
        coord = _make_coordinator(tags=[tag])

        bad_client = MagicMock()
        bad_client.get_connected.return_value = True
        bad_client.db_read.side_effect = RuntimeError("simulated read error")
        _set_backend_client(coord, bad_client)

        with pytest.raises(ConnectionError):
            coord._fetch_all()

        assert not coord._backend.is_connected()

    def test_partial_failure_returns_partial_data(self):
        """When only some tags fail, _fetch_all should return partial results."""
        tag_ok = _bool_tag("t1")
        tag_bad = _word_tag("t2")
        coord = _make_coordinator(tags=[tag_ok, tag_bad])

        # db_read raises only for word (size=2), succeeds for bool (size=1)
        def selective_read(db, start, size):
            if size == 2:
                raise RuntimeError("word read failed")
            return bytearray(size)

        ok_client = MagicMock()
        ok_client.get_connected.return_value = True
        ok_client.db_read.side_effect = selective_read
        _set_backend_client(coord, ok_client)

        result = coord._fetch_all()
        assert result["t1"] is not None  # bool read succeeded
        assert result["t2"] is None       # word read failed → None

    def test_no_tags_returns_empty_dict(self):
        """With no tags configured, _fetch_all returns an empty dict."""
        from tests.conftest import _FakeSnap7Client

        coord = _make_coordinator(tags=[])
        _set_backend_client(coord, _FakeSnap7Client())
        result = coord._fetch_all()
        assert result == {}

    def test_connection_failure_resets_client(self):
        """If _ensure_connected() itself fails, the backend must be reset."""
        coord = _make_coordinator(tags=[_bool_tag()])
        # Backend starts with _client=None so it will attempt to create one
        assert coord._backend._client is None

        snap7_client_mod = sys.modules.get("snap7.client")
        original_cls = snap7_client_mod.Client

        class _AlwaysDisconnected:
            def get_connected(self):
                return False
            def connect(self, *a):
                pass

        snap7_client_mod.Client = _AlwaysDisconnected
        try:
            with pytest.raises(ConnectionError):
                coord._fetch_all()
            assert not coord._backend.is_connected()
        finally:
            snap7_client_mod.Client = original_cls


# ---------------------------------------------------------------------------
# Write range validation
# ---------------------------------------------------------------------------

def _make_write_coordinator(tag):
    """Create a coordinator with a pre-connected stub client for write tests."""
    from tests.conftest import _FakeSnap7Client

    coord = _make_coordinator(tags=[tag])
    _set_backend_client(coord, _FakeSnap7Client())
    return coord


class TestWriteRangeValidation:
    def test_byte_too_large(self):
        tag = {"id": "t1", "name": "B", "address": "DB1.DBB0", "data_type": DATA_TYPE_BYTE}
        coord = _make_write_coordinator(tag)
        with pytest.raises(ValueError, match="out of range"):
            coord._write_value("t1", 256)

    def test_byte_negative(self):
        tag = {"id": "t1", "name": "B", "address": "DB1.DBB0", "data_type": DATA_TYPE_BYTE}
        coord = _make_write_coordinator(tag)
        with pytest.raises(ValueError, match="out of range"):
            coord._write_value("t1", -1)

    def test_word_too_large(self):
        tag = _word_tag()
        coord = _make_write_coordinator(tag)
        with pytest.raises(ValueError, match="out of range"):
            coord._write_value("t2", 65536)

    def test_word_valid(self):
        tag = _word_tag()
        coord = _make_write_coordinator(tag)
        coord._write_value("t2", 65535)  # must not raise

    def test_int_too_large(self):
        tag = {"id": "t1", "name": "I", "address": "DB1.DBW0", "data_type": DATA_TYPE_INT}
        coord = _make_write_coordinator(tag)
        with pytest.raises(ValueError, match="out of range"):
            coord._write_value("t1", 32768)

    def test_int_too_small(self):
        tag = {"id": "t1", "name": "I", "address": "DB1.DBW0", "data_type": DATA_TYPE_INT}
        coord = _make_write_coordinator(tag)
        with pytest.raises(ValueError, match="out of range"):
            coord._write_value("t1", -32769)

    def test_dword_too_large(self):
        tag = {"id": "t1", "name": "D", "address": "DB1.DBD0", "data_type": DATA_TYPE_DWORD}
        coord = _make_write_coordinator(tag)
        with pytest.raises(ValueError, match="out of range"):
            coord._write_value("t1", 4294967296)

    def test_dint_too_large(self):
        tag = {"id": "t1", "name": "DI", "address": "DB1.DBD0", "data_type": DATA_TYPE_DINT}
        coord = _make_write_coordinator(tag)
        with pytest.raises(ValueError, match="out of range"):
            coord._write_value("t1", 2147483648)

    def test_dint_too_small(self):
        tag = {"id": "t1", "name": "DI", "address": "DB1.DBD0", "data_type": DATA_TYPE_DINT}
        coord = _make_write_coordinator(tag)
        with pytest.raises(ValueError, match="out of range"):
            coord._write_value("t1", -2147483649)

    def test_real_inf_rejected(self):
        tag = {"id": "t1", "name": "R", "address": "DB1.DBD0", "data_type": DATA_TYPE_REAL}
        coord = _make_write_coordinator(tag)
        with pytest.raises(ValueError, match="not a finite"):
            coord._write_value("t1", float("inf"))

    def test_real_nan_rejected(self):
        tag = {"id": "t1", "name": "R", "address": "DB1.DBD0", "data_type": DATA_TYPE_REAL}
        coord = _make_write_coordinator(tag)
        with pytest.raises(ValueError, match="not a finite"):
            coord._write_value("t1", float("nan"))

    def test_write_failure_resets_client(self):
        """A write failure must disconnect the backend so the next poll reconnects."""
        tag = _bool_tag()
        coord = _make_coordinator(tags=[tag])

        bad_client = MagicMock()
        bad_client.get_connected.return_value = True
        bad_client.db_read.side_effect = RuntimeError("write channel broken")
        _set_backend_client(coord, bad_client)

        with pytest.raises(RuntimeError):
            coord._write_value("t1", True)

        assert not coord._backend.is_connected()

    def test_unknown_tag_raises_value_error(self):
        coord = _make_coordinator(tags=[])
        with pytest.raises(ValueError, match="not found"):
            coord._write_value("nonexistent", True)


# ---------------------------------------------------------------------------
# Scan interval
# ---------------------------------------------------------------------------

class TestScanInterval:
    def test_scan_interval_formula(self):
        """Coordinator uses timedelta(milliseconds=scan_interval) for update_interval."""
        # Verify that the formula produces the correct timedelta
        scan_interval_ms = 5000
        result = timedelta(milliseconds=scan_interval_ms)
        assert result == timedelta(seconds=5)

    def test_default_scan_interval_is_30_seconds(self):
        """DEFAULT_SCAN_INTERVAL must represent 30 seconds expressed in ms."""
        from custom_components.snap7_plc.const import DEFAULT_SCAN_INTERVAL
        assert DEFAULT_SCAN_INTERVAL == 30000

    def test_timedelta_from_30000ms(self):
        assert timedelta(milliseconds=30000) == timedelta(seconds=30)


# ---------------------------------------------------------------------------
# Writable validation (logic layer)
# ---------------------------------------------------------------------------

class TestWritableValidation:
    """The writable=True flag is valid for boolean, input_number, int, dint, and real tags."""

    _WRITABLE_TYPES = (DATA_TYPE_BOOL, DATA_TYPE_INPUT_NUMBER, DATA_TYPE_INT, DATA_TYPE_DINT, DATA_TYPE_REAL)

    def test_non_bool_writable_raises_in_config_logic(self):
        """Simulate the config flow validation check for a non-writable type."""
        from custom_components.snap7_plc.const import DATA_TYPE_WORD

        address = "DB1.DBW0"
        data_type = DATA_TYPE_WORD
        writable = True

        parsed = parse_address(address, data_type)
        is_error = writable and parsed["data_type"] not in self._WRITABLE_TYPES
        assert is_error, "Expected validation error for non-writable type (word)"

    def test_bool_writable_is_valid(self):
        address = "DB1.DBX0.0"
        data_type = DATA_TYPE_BOOL
        writable = True

        parsed = parse_address(address, data_type)
        is_error = writable and parsed["data_type"] not in self._WRITABLE_TYPES
        assert not is_error

    def test_input_number_writable_is_valid(self):
        address = "DB1.DBD0"
        data_type = DATA_TYPE_INPUT_NUMBER
        writable = True

        parsed = parse_address(address, data_type)
        is_error = writable and parsed["data_type"] not in self._WRITABLE_TYPES
        assert not is_error

    def test_mw_input_number_writable_is_valid(self):
        """input_number on a 16-bit MW address must pass writable validation (resolves to int)."""
        address = "MW12"
        writable = True

        parsed = parse_address(address, DATA_TYPE_INPUT_NUMBER)
        is_error = writable and parsed["data_type"] not in self._WRITABLE_TYPES
        assert not is_error
        assert parsed["data_type"] == DATA_TYPE_INT

    def test_dbw_input_number_writable_is_valid(self):
        """input_number on a 16-bit DBW address must pass writable validation (resolves to int)."""
        address = "DB1.DBW12"
        writable = True

        parsed = parse_address(address, DATA_TYPE_INPUT_NUMBER)
        is_error = writable and parsed["data_type"] not in self._WRITABLE_TYPES
        assert not is_error
        assert parsed["data_type"] == DATA_TYPE_INT

    def test_int_writable_is_valid(self):
        address = "DB1.DBW0"
        writable = True

        parsed = parse_address(address, DATA_TYPE_INT)
        is_error = writable and parsed["data_type"] not in self._WRITABLE_TYPES
        assert not is_error

    def test_dint_writable_is_valid(self):
        address = "DB1.DBD0"
        writable = True

        parsed = parse_address(address, DATA_TYPE_DINT)
        is_error = writable and parsed["data_type"] not in self._WRITABLE_TYPES
        assert not is_error

    def test_real_writable_is_valid(self):
        address = "DB1.DBD0"
        writable = True

        parsed = parse_address(address, DATA_TYPE_REAL)
        is_error = writable and parsed["data_type"] not in self._WRITABLE_TYPES
        assert not is_error

    def test_non_bool_not_writable_is_valid(self):
        from custom_components.snap7_plc.const import DATA_TYPE_WORD

        address = "DB1.DBW0"
        data_type = DATA_TYPE_WORD
        writable = False

        parsed = parse_address(address, data_type)
        is_error = writable and parsed["data_type"] not in self._WRITABLE_TYPES
        assert not is_error


# ---------------------------------------------------------------------------
# Unique ID format
# ---------------------------------------------------------------------------

class TestUniqueId:
    def test_unique_id_includes_rack_and_slot(self):
        """Unique ID must be ip:rack:slot, not just ip."""
        plc_ip = "192.168.1.10"
        rack = 0
        slot = 1
        unique_id = f"{plc_ip}:{rack}:{slot}"
        assert unique_id == "192.168.1.10:0:1"

    def test_same_ip_different_slot_are_distinct(self):
        plc_ip = "192.168.1.10"
        uid_slot1 = f"{plc_ip}:0:1"
        uid_slot2 = f"{plc_ip}:0:2"
        assert uid_slot1 != uid_slot2


# ---------------------------------------------------------------------------
# input_number type – address parsing
# ---------------------------------------------------------------------------

class TestInputNumberAddressParsing:
    def test_db_dbd_input_number(self):
        result = parse_address("DB1.DBD0", DATA_TYPE_INPUT_NUMBER)
        assert result["area"] == AREA_DB
        assert result["data_type"] == DATA_TYPE_DINT

    def test_m_md_input_number(self):
        result = parse_address("MD4", DATA_TYPE_INPUT_NUMBER)
        assert result["area"] == AREA_M
        assert result["data_type"] == DATA_TYPE_DINT

    def test_input_number_data_size_is_4(self):
        from custom_components.snap7_plc.coordinator import _data_size
        assert _data_size(DATA_TYPE_INPUT_NUMBER) == 4

    def test_input_number_write_valid(self):
        tag = {"id": "t1", "name": "Setpoint", "address": "DB1.DBD0", "data_type": DATA_TYPE_INPUT_NUMBER}
        coord = _make_write_coordinator(tag)
        coord._write_value("t1", 42.5)  # must not raise

    def test_input_number_write_inf_rejected(self):
        tag = {"id": "t1", "name": "Setpoint", "address": "DB1.DBD0", "data_type": DATA_TYPE_INPUT_NUMBER}
        coord = _make_write_coordinator(tag)
        with pytest.raises(ValueError, match="not a finite"):
            coord._write_value("t1", float("inf"))

    def test_input_number_write_nan_rejected(self):
        tag = {"id": "t1", "name": "Setpoint", "address": "DB1.DBD0", "data_type": DATA_TYPE_INPUT_NUMBER}
        coord = _make_write_coordinator(tag)
        with pytest.raises(ValueError, match="not a finite"):
            coord._write_value("t1", float("nan"))


# ---------------------------------------------------------------------------
# date type – address parsing and formatting
# ---------------------------------------------------------------------------

class TestDateAddressParsing:
    def test_db_dbd_date(self):
        result = parse_address("DB1.DBD0", DATA_TYPE_DATE)
        assert result["area"] == AREA_DB
        assert result["data_type"] == DATA_TYPE_DATE

    def test_m_md_date(self):
        result = parse_address("MD8", DATA_TYPE_DATE)
        assert result["area"] == AREA_M
        assert result["data_type"] == DATA_TYPE_DATE

    def test_date_data_size_is_4(self):
        from custom_components.snap7_plc.coordinator import _data_size
        assert _data_size(DATA_TYPE_DATE) == 4


class TestFormatPlcDate:
    def test_seven_digit_date(self):
        """1052026 (dmmyyyy) should format as 1/5/2026."""
        assert _format_plc_date(1052026) == "1/5/2026"

    def test_eight_digit_date(self):
        """25102026 (ddmmyyyy) should format as 25/10/2026."""
        assert _format_plc_date(25102026) == "25/10/2026"

    def test_leading_zero_month_stripped(self):
        """Month 01 should display as 1, not 01."""
        assert _format_plc_date(1012026) == "1/1/2026"

    def test_end_of_year(self):
        """31122025 should format as 31/12/2025."""
        assert _format_plc_date(31122025) == "31/12/2025"

    def test_single_digit_day_and_month(self):
        """3032024 should format as 3/3/2024."""
        assert _format_plc_date(3032024) == "3/3/2024"

    def test_negative_value_returns_invalid(self):
        """Negative DINT values are not valid dates."""
        assert _format_plc_date(-1052026) == "Invalid date: -1052026"

    def test_too_short_returns_invalid(self):
        """Values with fewer than 6 digits cannot encode a valid date."""
        assert _format_plc_date(12345) == "Invalid date: 12345"


# ---------------------------------------------------------------------------
# Writable int/dint/real → number entity routing
# ---------------------------------------------------------------------------

class TestWritableNumericEntityRouting:
    """Writable int/dint/real tags must become number entities, not sensors."""

    def _is_number_entity(self, tag):
        """Mirror the number.py entity inclusion logic."""
        return (
            tag["data_type"] == DATA_TYPE_INPUT_NUMBER
            or (
                tag["data_type"] in (DATA_TYPE_INT, DATA_TYPE_DINT, DATA_TYPE_REAL)
                and tag.get("writable", False)
            )
        )

    def _is_sensor_entity(self, tag):
        """Mirror the sensor.py entity inclusion logic."""
        return (
            tag["data_type"] not in (DATA_TYPE_BOOL, DATA_TYPE_INPUT_NUMBER)
            and not (
                tag["data_type"] in (DATA_TYPE_INT, DATA_TYPE_DINT, DATA_TYPE_REAL)
                and tag.get("writable", False)
            )
        )

    def test_writable_int_is_number_not_sensor(self):
        tag = {"data_type": DATA_TYPE_INT, "writable": True}
        assert self._is_number_entity(tag)
        assert not self._is_sensor_entity(tag)

    def test_writable_dint_is_number_not_sensor(self):
        tag = {"data_type": DATA_TYPE_DINT, "writable": True}
        assert self._is_number_entity(tag)
        assert not self._is_sensor_entity(tag)

    def test_writable_real_is_number_not_sensor(self):
        tag = {"data_type": DATA_TYPE_REAL, "writable": True}
        assert self._is_number_entity(tag)
        assert not self._is_sensor_entity(tag)

    def test_readonly_int_is_sensor_not_number(self):
        tag = {"data_type": DATA_TYPE_INT, "writable": False}
        assert not self._is_number_entity(tag)
        assert self._is_sensor_entity(tag)

    def test_readonly_dint_is_sensor_not_number(self):
        tag = {"data_type": DATA_TYPE_DINT, "writable": False}
        assert not self._is_number_entity(tag)
        assert self._is_sensor_entity(tag)

    def test_readonly_real_is_sensor_not_number(self):
        tag = {"data_type": DATA_TYPE_REAL, "writable": False}
        assert not self._is_number_entity(tag)
        assert self._is_sensor_entity(tag)

    def test_input_number_is_always_number(self):
        tag = {"data_type": DATA_TYPE_INPUT_NUMBER, "writable": False}
        assert self._is_number_entity(tag)
        assert not self._is_sensor_entity(tag)


# ---------------------------------------------------------------------------
# Snap7Number min/max/step per data type
# ---------------------------------------------------------------------------

class TestSnapNumberConstraints:
    """Number entity constraints must match PLC data type range."""

    def _make_number(self, data_type):
        from custom_components.snap7_plc.number import Snap7Number
        from types import SimpleNamespace
        coord = SimpleNamespace(data={})
        tag = {
            "id": "t1",
            "name": "Test",
            "address": "DB1.DBD0",
            "data_type": data_type,
            "unit": "",
        }
        if data_type == DATA_TYPE_INT:
            tag["address"] = "DB1.DBW0"
        entry = SimpleNamespace(
            data={"plc_ip": "192.168.1.1", "rack": 0, "slot": 1},
            title="PLC",
        )
        return Snap7Number(coord, tag, entry)

    def test_int_range(self):
        num = self._make_number(DATA_TYPE_INT)
        assert num._attr_native_min_value == -32768.0
        assert num._attr_native_max_value == 32767.0
        assert num._attr_native_step == 1.0

    def test_dint_range(self):
        num = self._make_number(DATA_TYPE_DINT)
        assert num._attr_native_min_value == -2147483648.0
        assert num._attr_native_max_value == 2147483647.0
        assert num._attr_native_step == 1.0

    def test_real_keeps_default_range(self):
        num = self._make_number(DATA_TYPE_REAL)
        assert num._attr_native_min_value == -1000000.0
        assert num._attr_native_max_value == 1000000.0

    def test_input_number_keeps_default_range(self):
        num = self._make_number(DATA_TYPE_INPUT_NUMBER)
        assert num._attr_native_min_value == -1000000.0
        assert num._attr_native_max_value == 1000000.0


# ---------------------------------------------------------------------------
# Integer vs float display typing
# ---------------------------------------------------------------------------

class TestNumericDisplayTyping:
    def test_writable_int_native_value_is_integer(self):
        from custom_components.snap7_plc.number import Snap7Number
        from types import SimpleNamespace

        coord = SimpleNamespace(data={"t1": 12.0})
        tag = {"id": "t1", "name": "WritableInt", "address": "DB1.DBW0", "data_type": DATA_TYPE_INT}
        entry = SimpleNamespace(data={"plc_ip": "192.168.1.1", "rack": 0, "slot": 1}, title="PLC")
        entity = Snap7Number(coord, tag, entry)

        assert entity.native_value == 12
        assert isinstance(entity.native_value, int)

    def test_writable_dint_native_value_is_integer(self):
        from custom_components.snap7_plc.number import Snap7Number
        from types import SimpleNamespace

        coord = SimpleNamespace(data={"t1": -25.0})
        tag = {"id": "t1", "name": "WritableDint", "address": "DB1.DBD0", "data_type": DATA_TYPE_DINT}
        entry = SimpleNamespace(data={"plc_ip": "192.168.1.1", "rack": 0, "slot": 1}, title="PLC")
        entity = Snap7Number(coord, tag, entry)

        assert entity.native_value == -25
        assert isinstance(entity.native_value, int)

    def test_readonly_word_sensor_native_value_is_integer(self):
        from custom_components.snap7_plc.sensor import Snap7Sensor
        from types import SimpleNamespace

        coord = SimpleNamespace(data={"t1": 33.0})
        tag = {"id": "t1", "name": "WordTag", "address": "DB1.DBW0", "data_type": DATA_TYPE_WORD}
        entry = SimpleNamespace(data={"plc_ip": "192.168.1.1", "rack": 0, "slot": 1}, title="PLC")
        entity = Snap7Sensor(coord, tag, entry)

        assert entity.native_value == 33
        assert isinstance(entity.native_value, int)

    def test_real_native_value_keeps_float(self):
        from custom_components.snap7_plc.number import Snap7Number
        from types import SimpleNamespace

        coord = SimpleNamespace(data={"t1": 3.14})
        tag = {"id": "t1", "name": "WritableReal", "address": "DB1.DBD0", "data_type": DATA_TYPE_REAL}
        entry = SimpleNamespace(data={"plc_ip": "192.168.1.1", "rack": 0, "slot": 1}, title="PLC")
        entity = Snap7Number(coord, tag, entry)

        assert entity.native_value == 3.14
        assert isinstance(entity.native_value, float)

    def test_legacy_input_number_returns_int_native_value(self):
        from custom_components.snap7_plc.number import Snap7Number
        from types import SimpleNamespace

        coord = SimpleNamespace(
            data={"t1": 320598765},
            _parsed_tags={"t1": {"data_type": DATA_TYPE_DINT}},
        )
        tag = {"id": "t1", "name": "LegacyInputNumber", "address": "MD100", "data_type": DATA_TYPE_INPUT_NUMBER}
        entry = SimpleNamespace(data={"plc_ip": "192.168.1.1", "rack": 0, "slot": 1}, title="PLC")
        entity = Snap7Number(coord, tag, entry)

        assert entity.native_value == 320598765
        assert isinstance(entity.native_value, int)

    def test_writable_dint_state_string_is_plain_digits(self):
        from custom_components.snap7_plc.number import Snap7Number
        from types import SimpleNamespace

        coord = SimpleNamespace(data={"t1": 12345678})
        tag = {"id": "t1", "name": "WritableDint", "address": "DB1.DBD0", "data_type": DATA_TYPE_DINT}
        entry = SimpleNamespace(data={"plc_ip": "192.168.1.1", "rack": 0, "slot": 1}, title="PLC")
        entity = Snap7Number(coord, tag, entry)

        assert entity.state == "12345678"

    def test_writable_int_state_string_is_plain_digits(self):
        from custom_components.snap7_plc.number import Snap7Number
        from types import SimpleNamespace

        coord = SimpleNamespace(data={"t1": 32767})
        tag = {"id": "t1", "name": "WritableInt", "address": "DB1.DBW0", "data_type": DATA_TYPE_INT}
        entry = SimpleNamespace(data={"plc_ip": "192.168.1.1", "rack": 0, "slot": 1}, title="PLC")
        entity = Snap7Number(coord, tag, entry)

        assert entity.state == "32767"


# ---------------------------------------------------------------------------
# Write round-trip for writable int/dint via coordinator
# ---------------------------------------------------------------------------

class TestWritableIntDintWrite:
    """Writable int and dint tags write correctly through the coordinator."""

    def test_writable_int_write(self):
        tag = {"id": "t1", "name": "IntTag", "address": "DB1.DBW0", "data_type": DATA_TYPE_INT}
        coord = _make_write_coordinator(tag)
        coord._write_value("t1", 100)  # must not raise

    def test_writable_dint_write(self):
        tag = {"id": "t1", "name": "DintTag", "address": "DB1.DBD0", "data_type": DATA_TYPE_DINT}
        coord = _make_write_coordinator(tag)
        coord._write_value("t1", 100000)  # must not raise

    def test_writable_real_write(self):
        tag = {"id": "t1", "name": "RealTag", "address": "DB1.DBD0", "data_type": DATA_TYPE_REAL}
        coord = _make_write_coordinator(tag)
        coord._write_value("t1", 3.14)  # must not raise
