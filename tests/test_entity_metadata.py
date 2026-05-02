"""Entity metadata tests for naming and identity."""
from types import SimpleNamespace

from custom_components.snap7_plc.binary_sensor import Snap7BinarySensor
from custom_components.snap7_plc.number import Snap7Number
from custom_components.snap7_plc.sensor import Snap7Sensor
from custom_components.snap7_plc.switch import Snap7Switch
from custom_components.snap7_plc.const import DOMAIN


def _entry():
    return SimpleNamespace(
        data={"plc_ip": "192.168.1.10", "rack": 0, "slot": 1},
        title="PLC 1",
    )


def _coordinator():
    return SimpleNamespace(data={"tag1": True})


def _tag(data_type: str = "bool"):
    return {
        "id": "tag1",
        "name": "  Good Reads  ",
        "address": "DB1.DBX0.0",
        "data_type": data_type,
        "unit": "kWh",
    }


def _assert_common(entity):
    assert entity.has_entity_name is False
    assert entity._attr_name == "Good Reads"
    assert entity._attr_unique_id == "192.168.1.10:0:1_tag1"
    assert entity.device_info["identifiers"] == {(DOMAIN, "192.168.1.10:0:1")}
    assert entity.device_info["name"] == "PLC 1"


def test_binary_sensor_metadata():
    _assert_common(Snap7BinarySensor(_coordinator(), _tag("bool"), _entry()))


def test_switch_metadata():
    _assert_common(Snap7Switch(_coordinator(), _tag("bool"), _entry()))


def test_sensor_metadata():
    _assert_common(Snap7Sensor(_coordinator(), _tag("real"), _entry()))


def test_number_metadata():
    _assert_common(Snap7Number(_coordinator(), _tag("input_number"), _entry()))
