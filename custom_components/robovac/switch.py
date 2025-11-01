"""Eufy Robovac switch platform."""
import logging
from datetime import timedelta

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_VACS, DOMAIN, REFRESH_RATE
from .robovac import RoboVacEntityFeature

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=REFRESH_RATE)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Robovac switch entities."""
    _LOGGER.info(f"Setting up switch entities for entry {config_entry.entry_id}")
    vacuums_config = config_entry.data[CONF_VACS]
    entities = []
    
    for device_id, item in vacuums_config.items():
        # Check if the vacuum entity exists and supports Boost IQ
        if DOMAIN in hass.data and CONF_VACS in hass.data[DOMAIN]:
            vacuum_entity = hass.data[DOMAIN][CONF_VACS].get(device_id)
            if vacuum_entity and vacuum_entity.robovac_supported & RoboVacEntityFeature.BOOST_IQ:
                entity = BoostIQSwitch(item, device_id)
                entities.append(entity)
                _LOGGER.info(f"Created Boost IQ switch for device {device_id}")
    
    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} switch entities")


class BoostIQSwitch(SwitchEntity):
    """Representation of a Boost IQ switch."""
    
    _attr_has_entity_name = True
    _attr_name = "Boost IQ"
    _attr_available = False

    def __init__(self, item, device_id):
        """Initialize the switch."""
        self.robovac_id = device_id
        self._attr_unique_id = f"{device_id}_boost_iq"
        self._is_on = False
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=item[CONF_NAME]
        )

    def update(self):
        """Fetch new state data for the switch."""
        try:
            vacuum_entity = self.hass.data[DOMAIN][CONF_VACS][self.robovac_id]
            if vacuum_entity and hasattr(vacuum_entity, '_attr_boost_iq'):
                self._is_on = vacuum_entity._attr_boost_iq
                self._attr_available = vacuum_entity.available
            else:
                self._attr_available = False
        except Exception as e:
            _LOGGER.debug(f"Failed to get Boost IQ state for {self.robovac_id}: {e}")
            self._attr_available = False

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        try:
            vacuum_entity = self.hass.data[DOMAIN][CONF_VACS][self.robovac_id]
            if vacuum_entity and hasattr(vacuum_entity, 'vacuum'):
                # Use async_set like other vacuum commands
                await vacuum_entity.vacuum.async_set({"118": True})
                # Request an immediate update to reflect the new state
                await vacuum_entity.async_update()
                self.schedule_update_ha_state(True)
        except Exception as e:
            _LOGGER.error(f"Failed to turn on Boost IQ for {self.robovac_id}: {e}")

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        try:
            vacuum_entity = self.hass.data[DOMAIN][CONF_VACS][self.robovac_id]
            if vacuum_entity and hasattr(vacuum_entity, 'vacuum'):
                # Use async_set like other vacuum commands
                await vacuum_entity.vacuum.async_set({"118": False})
                # Request an immediate update to reflect the new state
                await vacuum_entity.async_update()
                self.schedule_update_ha_state(True)
        except Exception as e:
            _LOGGER.error(f"Failed to turn off Boost IQ for {self.robovac_id}: {e}")