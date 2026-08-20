"""Binary sensors for Delonghi Primadonna."""

from homeassistant.components.binary_sensor import (BinarySensorDeviceClass,
                                                    BinarySensorEntity)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .base_entity import DelonghiDeviceEntity
from .const import DOMAIN
from .device import DelongiPrimadonna
from .machine_switch import MachineSwitch


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
):
    """Register binary sensor entities for a config entry."""

    delongh_device: DelongiPrimadonna = hass.data[DOMAIN][entry.unique_id]
    async_add_entities(
        [
            DelongiPrimadonnaDescaleSensor(delongh_device, hass),
            DelongiPrimadonnaFilterSensor(delongh_device, hass),
            DelongiPrimadonnaEnabledSensor(delongh_device, hass),
            DelongiPrimadonnaDispensingSensor(delongh_device, hass),
            DelongiPrimadonnaWaterTankSensor(delongh_device, hass),
            DelongiPrimadonnaWaterLevelLowSensor(delongh_device, hass),
            DelongiPrimadonnaGroundsContainerSensor(delongh_device, hass),
        ]
    )
    return True


class DelongiPrimadonnaEnabledSensor(
    DelonghiDeviceEntity, BinarySensorEntity
):
    """Shows whether the machine is out of standby.

    Deliberately not a RestoreEntity: is_on reads the machine state, so
    there is nothing of its own to restore, and writing a remembered
    value back into the device made it claim a state no frame had
    reported yet.
    """

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = 'enabled'

    @property
    def icon(self) -> str:
        """Return the icon of the device."""
        if self.device.switches.is_on:
            return 'mdi:coffee-maker-check'
        if self.device.connected:
            return 'mdi:coffee-maker-check-outline'
        return 'mdi:coffee-maker-outline'

    @property
    def native_value(self):
        return self.device.switches.is_on

    @property
    def is_on(self) -> bool:
        return self.device.switches.is_on


class DelongiPrimadonnaWaterTankSensor(
    DelonghiDeviceEntity, BinarySensorEntity
):
    """Problem when the water tank is missing or empty."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = 'water_tank'
    _attr_icon = 'mdi:cup-water'

    @property
    def is_on(self) -> bool:
        """True when the tank is absent or the empty-tank alarm is set."""
        return (
            MachineSwitch.WATER_TANK_ABSENT in self.device.active_switches
            or bool(self.device.service & 0x01)
        )


class DelongiPrimadonnaWaterLevelLowSensor(
    DelonghiDeviceEntity, BinarySensorEntity
):
    """Problem when the water level is low."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = 'water_level_low'
    _attr_icon = 'mdi:water-alert'

    @property
    def is_on(self) -> bool:
        """True while the machine reports a low water level."""
        return MachineSwitch.WATER_LEVEL_LOW in self.device.active_switches


class DelongiPrimadonnaGroundsContainerSensor(
    DelonghiDeviceEntity, BinarySensorEntity
):
    """Problem when the grounds container is missing or full."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = 'grounds_container'
    _attr_icon = 'mdi:coffee-maker-check'

    @property
    def is_on(self) -> bool:
        """True when the container is out or the full alarm is set."""
        return (
            MachineSwitch.COFFEE_WASTE_CONTAINER
            in self.device.active_switches
            or bool(self.device.service & 0x02)
        )


class DelongiPrimadonnaDispensingSensor(
    DelonghiDeviceEntity, BinarySensorEntity
):
    """On while the machine is dispensing a beverage."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_translation_key = 'dispensing'
    _attr_icon = 'mdi:coffee-to-go'

    @property
    def is_on(self) -> bool:
        """Return True while a beverage is being dispensed."""
        return self.device.is_dispensing

    @property
    def extra_state_attributes(self) -> dict:
        """Expose the dispensing progress percentage."""
        return {'percentage': self.device.dispensing_percentage}


class DelongiPrimadonnaDescaleSensor(
    DelonghiDeviceEntity, BinarySensorEntity, RestoreEntity
):
    """
    Shows if the device needs descaling
    """

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = 'descaling'

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == 'on'

    @property
    def native_value(self):
        return self.device.service

    @property
    def is_on(self) -> bool:
        return bool((self.device.service >> 2) % 2)

    @property
    def icon(self):
        result = 'mdi:dishwasher'
        if self.is_on:
            result = 'mdi:dishwasher-alert'
        return result


class DelongiPrimadonnaFilterSensor(
    DelonghiDeviceEntity, BinarySensorEntity, RestoreEntity
):
    """
    Shows if the filter need to be changed
    """

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = 'filter'

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._attr_is_on = last_state.state == 'on'

    @property
    def native_value(self):
        return self.device.service

    @property
    def is_on(self) -> bool:
        return bool((self.device.service >> 3) % 2)

    @property
    def icon(self):
        result = 'mdi:filter'
        if self.is_on:
            result = 'mdi:filter-off'
        return result
