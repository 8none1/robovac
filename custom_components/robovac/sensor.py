from datetime import timedelta
import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, CONF_NAME, CONF_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_VACS, DOMAIN, REFRESH_RATE
from .robovac import RoboVacEntityFeature

_LOGGER = logging.getLogger(__name__)

BATTERY = "Battery"
MODE = "Mode"
SCAN_INTERVAL = timedelta(seconds=REFRESH_RATE)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize robovac sensor config entry."""
    _LOGGER.info(f"Setting up sensor entities for entry {config_entry.entry_id}")
    vacuums = config_entry.data[CONF_VACS]
    _LOGGER.info(f"Found {len(vacuums)} vacuums in config")
    entities = []
    
    for item in vacuums:
        item = vacuums[item]
        
        # Add battery sensor
        battery_entity = RobovacBatterySensorEntity(item)
        entities.append(battery_entity)
        _LOGGER.info(f"Created battery sensor entity for device {item[CONF_ID]}")
        
        # Add mode sensor
        mode_entity = RobovacModeSensorEntity(item)
        entities.append(mode_entity)
        _LOGGER.info(f"Created mode sensor entity for device {item[CONF_ID]}")
    
    async_add_entities(entities)
    _LOGGER.info(f"Added {len(entities)} sensor entities")


class RobovacBatterySensorEntity(SensorEntity):
    """Representation of a Robovac battery sensor."""
    
    _attr_has_entity_name = True
    _attr_name = BATTERY
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_available = False

    def __init__(self, item):
        """Initialize the sensor."""
        self.robovac_id = item[CONF_ID]
        self._attr_unique_id = f"{item[CONF_ID]}_battery"
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
    def native_value(self):
        """Return the state of the sensor."""
        return self._battery_level


class RobovacModeSensorEntity(SensorEntity):
    """Representation of a Robovac cleaning mode sensor."""
    
    _attr_has_entity_name = True
    _attr_name = MODE
    _attr_icon = "mdi:robot-vacuum-variant"
    _attr_available = False

    def __init__(self, item):
        """Initialize the sensor."""
        self.robovac_id = item[CONF_ID]
        self._attr_unique_id = f"{item[CONF_ID]}_mode"
        self._mode = None
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, item[CONF_ID])},
            name=item[CONF_NAME]
        )

    def update(self):
        try:
            vacuum_entity = self.hass.data[DOMAIN][CONF_VACS][self.robovac_id]
            # Access the mode from the vacuum entity
            self._mode = vacuum_entity._attr_mode
            self._attr_available = vacuum_entity.available
        except Exception as e:
            _LOGGER.debug(f"Failed to get mode for {self.robovac_id}: {e}")
            self._mode = None
            self._attr_available = False

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self._mode:
            # Capitalize and format the mode nicely
            return self._mode.replace("_", " ").title()
        return None

