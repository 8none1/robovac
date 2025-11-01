import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, CONF_NAME, CONF_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_VACS, DOMAIN, REFRESH_RATE

_LOGGER = logging.getLogger(__name__)

BATTERY = "Battery"
SCAN_INTERVAL = timedelta(seconds=REFRESH_RATE)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize my test integration 2 config entry."""
    _LOGGER.info(f"Setting up sensor entities for entry {config_entry.entry_id}")
    vacuums = config_entry.data[CONF_VACS]
    _LOGGER.info(f"Found {len(vacuums)} vacuums in config")
    entities = []
    for item in vacuums:
        item = vacuums[item]
        entity = RobovacSensorEntity(item)
        entities.append(entity)
        _LOGGER.info(f"Created sensor entity for device {item[CONF_ID]}")
    async_add_entities(entities)
    _LOGGER.info(f"Added {len(entities)} sensor entities")

class RobovacSensorEntity(SensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_available = False

    def __init__(self, item):
        self.robovac = item
        self.robovac_id = item[CONF_ID]
        self._attr_unique_id = item[CONF_ID]
        self._battery_level = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, item[CONF_ID])},
            name=item[CONF_NAME]
        )

    def update(self):
        try:
            vacuum_entity = self.hass.data[DOMAIN][CONF_VACS][self.robovac_id]
            # Access the internal battery level variable (not _attr_battery_level to avoid deprecation)
            self._battery_level = vacuum_entity._battery_level
            self._attr_available = True
        except Exception as e:
            _LOGGER.debug(f"Failed to get battery level for {self.robovac_id}: {e}")
            self._battery_level = None
            self._attr_available = False
    
    @property
    def native_value(self) -> str | None:
        """Return the state."""
        if self._battery_level is not None:
            return self._battery_level
        return None

