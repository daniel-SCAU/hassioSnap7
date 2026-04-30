"""Sensor platform for the Snap7 PLC integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_TYPE_BOOL, DOMAIN
from .coordinator import Snap7Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Snap7 sensor entities."""
    coordinator: Snap7Coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        Snap7Sensor(coordinator, tag)
        for tag in coordinator.tags
        if tag["data_type"] != DATA_TYPE_BOOL
    ]
    async_add_entities(entities)


class Snap7Sensor(CoordinatorEntity[Snap7Coordinator], SensorEntity):
    """A sensor entity that reads a numeric value from the PLC."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: Snap7Coordinator, tag: dict) -> None:
        super().__init__(coordinator)
        self._tag = tag
        self._attr_unique_id = f"{coordinator.plc_ip}_{tag['id']}"
        self._attr_name = tag["name"]
        unit = tag.get("unit", "")
        if unit:
            self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        """Return the current tag value."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._tag["id"])

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
            identifiers={(DOMAIN, self.coordinator.plc_ip)},
            name=f"Snap7 PLC {self.coordinator.plc_ip}",
            manufacturer="Siemens",
            model="S7 PLC",
        )
