"""Number platform for the Snap7 PLC integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_PLC_IP,
    CONF_RACK,
    CONF_SLOT,
    DATA_TYPE_DINT,
    DATA_TYPE_INPUT_NUMBER,
    DATA_TYPE_INT,
    DATA_TYPE_REAL,
    DEFAULT_RACK,
    DEFAULT_SLOT,
    DOMAIN,
)
from .coordinator import Snap7Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Snap7 number entities."""
    coordinator: Snap7Coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        Snap7Number(coordinator, tag, entry)
        for tag in coordinator.tags
        if tag["data_type"] == DATA_TYPE_INPUT_NUMBER
        or (
            tag["data_type"] in (DATA_TYPE_INT, DATA_TYPE_DINT, DATA_TYPE_REAL)
            and tag.get("writable", False)
        )
    ]
    async_add_entities(entities)


class Snap7Number(CoordinatorEntity[Snap7Coordinator], NumberEntity):
    """A writable number entity that reads and writes a numeric value on the PLC."""

    _attr_has_entity_name = False
    # Writable number entities are created only for INT/DINT/REAL (plus input_number).
    # INT and DINT must be exposed as whole numbers in Home Assistant.
    _INTEGER_TYPES = {DATA_TYPE_INT, DATA_TYPE_DINT}

    @property
    def has_entity_name(self) -> bool:
        """Return False so HA never prepends the device name to friendly_name."""
        return False

    def __init__(self, coordinator: Snap7Coordinator, tag: dict, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._tag = tag
        self._device_id = (
            f"{entry.data[CONF_PLC_IP]}:"
            f"{entry.data.get(CONF_RACK, DEFAULT_RACK)}:"
            f"{entry.data.get(CONF_SLOT, DEFAULT_SLOT)}"
        )
        self._device_name = entry.title
        self._attr_unique_id = f"{self._device_id}_{tag['id']}"
        self._attr_name = tag["name"].strip()
        unit = tag.get("unit", "")
        if unit:
            self._attr_native_unit_of_measurement = unit
        data_type = tag.get("data_type", DATA_TYPE_INPUT_NUMBER)
        if data_type == DATA_TYPE_INT:
            self._attr_native_min_value = -32768.0
            self._attr_native_max_value = 32767.0
            self._attr_native_step = 1.0
        elif data_type == DATA_TYPE_DINT:
            self._attr_native_min_value = -2147483648.0
            self._attr_native_max_value = 2147483647.0
            self._attr_native_step = 1.0
        else:
            self._attr_native_min_value = -1000000.0
            self._attr_native_max_value = 1000000.0
            self._attr_native_step = 1.0

    @property
    def native_value(self) -> int | float | None:
        """Return the current tag value."""
        if self.coordinator.data is None:
            return None
        value = self.coordinator.data.get(self._tag["id"])
        if value is None:
            return None
        if self._effective_data_type() in self._INTEGER_TYPES:
            return int(value)
        return float(value)

    @property
    def state(self) -> Any:
        """Return an unformatted state for integer PLC data types."""
        value = self.native_value
        if value is None:
            return None
        if self._effective_data_type() in self._INTEGER_TYPES:
            return str(int(value))
        # Keep Home Assistant's default state rendering for non-integer values.
        return super().state

    def _effective_data_type(self) -> str | None:
        """Return the parsed PLC data type for this tag when available."""
        parsed_tags = getattr(self.coordinator, "_parsed_tags", {})
        return parsed_tags.get(self._tag["id"], {}).get("data_type") or self._tag.get(
            "data_type"
        )

    async def async_set_native_value(self, value: float) -> None:
        """Write a new value to the PLC."""
        await self.coordinator.async_write_tag(self._tag["id"], value)

    @property
    def extra_state_attributes(self) -> dict:
        """Return PLC address metadata."""
        return {
            "plc_address": self._tag.get("address"),
            "data_type": self._tag.get("data_type"),
        }

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
            manufacturer="Siemens",
            model="S7 PLC",
        )
