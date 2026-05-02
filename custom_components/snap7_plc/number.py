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
    DATA_TYPE_INPUT_NUMBER,
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
    ]
    async_add_entities(entities)


class Snap7Number(CoordinatorEntity[Snap7Coordinator], NumberEntity):
    """A writable number entity that reads and writes a real value on the PLC."""

    _attr_has_entity_name = False
    _attr_native_min_value = -1000000.0

    @property
    def has_entity_name(self) -> bool:
        """Return False so HA never prepends the device name to friendly_name."""
        return False

    _attr_native_max_value = 1000000.0
    _attr_native_step = 1.0

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

    @property
    def native_value(self) -> float | None:
        """Return the current tag value."""
        if self.coordinator.data is None:
            return None
        value = self.coordinator.data.get(self._tag["id"])
        return float(value) if value is not None else None

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
