"""Sensors showing the values read from the Fronius Solar API."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CONF_HOST, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FroniusMeterEmulatorConfigEntry
from .const import DOMAIN, MANUFACTURER, METER_MODEL_NAME
from .coordinator import FroniusSolarApiCoordinator


@dataclass(frozen=True, kw_only=True)
class FroniusSensorDescription(SensorEntityDescription):
    """Describes a Fronius Solar API sensor."""

    value_fn: Callable[[dict], float] = lambda data: 0.0


SENSOR_DESCRIPTIONS: tuple[FroniusSensorDescription, ...] = (
    FroniusSensorDescription(
        key="P_PV",
        translation_key="pv_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: data["P_PV"],
    ),
    FroniusSensorDescription(
        key="P_Grid",
        translation_key="grid_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: data["P_Grid"],
    ),
    FroniusSensorDescription(
        key="P_Load",
        translation_key="load_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: data["P_Load"],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FroniusMeterEmulatorConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for a config entry."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        FroniusSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class FroniusSensor(CoordinatorEntity[FroniusSolarApiCoordinator], SensorEntity):
    """A sensor backed by the Fronius Solar API coordinator."""

    entity_description: FroniusSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FroniusSolarApiCoordinator,
        entry: FroniusMeterEmulatorConfigEntry,
        description: FroniusSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=MANUFACTURER,
            name=f"Fronius Meter Emulator ({entry.data[CONF_HOST]})",
            model=METER_MODEL_NAME,
        )

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
