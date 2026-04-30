"""Tests for the Snap7 PLC integration – coordinator address parser."""
import pytest

# Make sure imports work without a real Home Assistant instance
import sys
import os

# Add the repo root so we can import custom_components directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.snap7_plc.coordinator import parse_address
from custom_components.snap7_plc.const import (
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
