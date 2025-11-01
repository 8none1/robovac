# Copyright 2022 Brendan McCluskey
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""The Eufy Robovac integration."""
from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform, CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from .const import CONF_VACS, DOMAIN

from .tuyalocaldiscovery import TuyaLocalDiscovery

PLATFORMS = [Platform.VACUUM, Platform.SENSOR, Platform.SWITCH]
TUYA_DISCOVERY = "tuya_discovery"
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, entry) -> bool:
    hass.data.setdefault(DOMAIN, {CONF_VACS:{}})

    async def update_device(device):
        entry = async_get_config_entry_for_device(hass, device["gwId"])

        if entry == None:
            return

        if not entry.state.recoverable:
            return

        hass_data = entry.data.copy()
        if (
            device["gwId"] in hass_data[CONF_VACS]
            and device.get("ip") is not None
            and hass_data[CONF_VACS][device["gwId"]].get("autodiscovery", True)
        ):
            if hass_data[CONF_VACS][device["gwId"]][CONF_IP_ADDRESS] != device["ip"]:
                hass_data[CONF_VACS][device["gwId"]][CONF_IP_ADDRESS] = device["ip"]
                hass.config_entries.async_update_entry(entry, data=hass_data)
                await hass.config_entries.async_reload(entry.entry_id)
                _LOGGER.debug(
                    "Updated ip address of {} to {}".format(
                        device["gwId"], device["ip"]
                    )
                )

    if TUYA_DISCOVERY not in hass.data:
        tuyalocaldiscovery = TuyaLocalDiscovery(update_device)
        try:
            await tuyalocaldiscovery.start()
            hass.data[TUYA_DISCOVERY] = tuyalocaldiscovery
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, tuyalocaldiscovery.close)
        except Exception:
            _LOGGER.exception("failed to set up discovery")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    conf = entry.data

    # Ensure the domain structure exists
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(CONF_VACS, {})
    
    # Store entry data for platforms to access
    hass.data[DOMAIN][entry.entry_id] = conf

    # Register this device for discovery
    if TUYA_DISCOVERY in hass.data and CONF_VACS in conf:
        discovery = hass.data[TUYA_DISCOVERY]
        for device_id, device_conf in conf[CONF_VACS].items():
            ip = device_conf.get(CONF_IP_ADDRESS)
            discovery.add_device(device_id, ip)
            _LOGGER.debug(f"Registered device {device_id} with IP {ip} for discovery")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Handle removal of an entry."""
    conf = entry.data
    
    # Unregister device from discovery
    if TUYA_DISCOVERY in hass.data and CONF_VACS in conf:
        discovery = hass.data[TUYA_DISCOVERY]
        for device_id, device_conf in conf[CONF_VACS].items():
            ip = device_conf.get(CONF_IP_ADDRESS)
            discovery.remove_device(device_id, ip)
            _LOGGER.debug(f"Unregistered device {device_id} from discovery")
    
    unloaded = all(
        await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    )

    # Remove the device from hass.data
    if unloaded and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def update_listener(hass, entry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


def async_get_config_entry_for_device(hass, device_id):
    current_entries = hass.config_entries.async_entries(DOMAIN)
    for entry in current_entries:
        if device_id in entry.data[CONF_VACS]:
            return entry
    return None
