"""Binary sensor platform for the Snap7 PLC integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    """Set up Snap7 binary sensor entities."""
    coordinator: Snap7Coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        Snap7BinarySensor(coordinator, tag)
        for tag in coordinator.tags
        if tag["data_type"] == DATA_TYPE_BOOL and not tag.get("writable", False)
    ]
    async_add_entities(entities)


class Snap7BinarySensor(CoordinatorEntity[Snap7Coordinator], BinarySensorEntity):
    """A read-only binary sensor that reflects a PLC boolean tag."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: Snap7Coordinator, tag: dict) -> None:
        super().__init__(coordinator)
        self._tag = tag
        self._attr_unique_id = f"{coordinator.plc_ip}_{tag['id']}"
        self._attr_name = tag["name"]

    @property
    def is_on(self) -> bool | None:
        """Return True when the PLC bit is set."""
        if self.coordinator.data is None:
            return None
        value = self.coordinator.data.get(self._tag["id"])
        return bool(value) if value is not None else None

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
