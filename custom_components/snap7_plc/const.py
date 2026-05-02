"""Constants for the Snap7 PLC integration."""

DOMAIN = "snap7_plc"

# Config / options keys
CONF_PLC_IP = "plc_ip"
CONF_RACK = "rack"
CONF_SLOT = "slot"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_TAGS = "tags"
CONF_LIBRARY = "library"

# Tag-level config keys
CONF_TAG_NAME = "name"
CONF_TAG_ADDRESS = "address"
CONF_TAG_DATA_TYPE = "data_type"
CONF_TAG_UNIT = "unit"
CONF_TAG_WRITABLE = "writable"

# Default connection settings
DEFAULT_RACK = 0
DEFAULT_SLOT = 1
DEFAULT_SCAN_INTERVAL = 30000

# Supported PLC communication libraries
LIBRARY_SNAP7 = "snap7"
LIBRARY_OPTIONS = [LIBRARY_SNAP7]
DEFAULT_LIBRARY = LIBRARY_SNAP7

# PLC memory areas
AREA_M = "M"
AREA_DB = "DB"

# Data types
DATA_TYPE_BOOL = "bool"
DATA_TYPE_BYTE = "byte"
DATA_TYPE_INT = "int"
DATA_TYPE_DINT = "dint"
DATA_TYPE_REAL = "real"
DATA_TYPE_WORD = "word"
DATA_TYPE_DWORD = "dword"
DATA_TYPE_STRING = "string"
DATA_TYPE_INPUT_NUMBER = "input_number"
DATA_TYPE_DATE = "date"

DATA_TYPES = [
    DATA_TYPE_BOOL,
    DATA_TYPE_BYTE,
    DATA_TYPE_INT,
    DATA_TYPE_DINT,
    DATA_TYPE_REAL,
    DATA_TYPE_WORD,
    DATA_TYPE_DWORD,
    DATA_TYPE_STRING,
    DATA_TYPE_INPUT_NUMBER,
    DATA_TYPE_DATE,
]
