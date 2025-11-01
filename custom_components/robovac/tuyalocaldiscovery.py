import asyncio
import json
import logging
from hashlib import md5

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_LOGGER = logging.getLogger(__name__)

UDP_KEY = md5(b"yGAdlopoPVldABfn").digest()


class DiscoveryPortsNotAvailableException(Exception):
    """This model is not supported"""


class TuyaLocalDiscovery(asyncio.DatagramProtocol):
    def __init__(self, callback):
        self.devices = {}
        self._listeners = []
        self.discovered_callback = callback
        self._known_device_ids = set()
        self._known_ips = set()

    def add_device(self, device_id: str, ip: str = None):
        """Register a device to listen for"""
        self._known_device_ids.add(device_id)
        if ip:
            self._known_ips.add(ip)
        _LOGGER.info(f"Added device to discovery: device_id={device_id}, ip={ip}")

    def remove_device(self, device_id: str, ip: str = None):
        """Unregister a device"""
        self._known_device_ids.discard(device_id)
        if ip:
            self._known_ips.discard(ip)
        _LOGGER.info(f"Removed device from discovery: device_id={device_id}, ip={ip}")

    async def start(self):
        loop = asyncio.get_running_loop()
        listener = loop.create_datagram_endpoint(
            lambda: self, local_addr=("0.0.0.0", 6666), reuse_port=True
        )
        encrypted_listener = loop.create_datagram_endpoint(
            lambda: self, local_addr=("0.0.0.0", 6667), reuse_port=True
        )

        try:
            self._listeners = await asyncio.gather(listener, encrypted_listener)
            _LOGGER.info("Listening to broadcasts on UDP port 6666 and 6667")
        except Exception as e:
            raise DiscoveryPortsNotAvailableException(
                "Ports 6666 and 6667 are needed for autodiscovery but are unavailable. This may be due to having the localtuya integration installed and it not allowing other integrations to use the same ports. A pull request has been raised to address this: https://github.com/rospogrigio/localtuya/pull/1481"
            )

    def close(self, *args, **kwargs):
        for transport, _ in self._listeners:
            transport.close()

    def datagram_received(self, data, addr):
        # Early filtering based on known IPs - silently ignore unknown IPs
        if self._known_ips and addr[0] not in self._known_ips:
            return

        data = data[20:-8]
        try:
            cipher = Cipher(algorithms.AES(UDP_KEY), modes.ECB(), default_backend())
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(data) + decryptor.finalize()
            data = padded_data[: -ord(padded_data[len(padded_data) - 1 :])]

        except Exception:
            try:
                data = data.decode()
            except UnicodeDecodeError:
                return  # Silently ignore invalid data

        try:
            decoded = json.loads(data)

            # Check if this is a device we care about - silently ignore unknown devices
            device_id = decoded.get("gwId") or decoded.get("devId")
            
            if self._known_device_ids and device_id not in self._known_device_ids:
                return

            _LOGGER.info(f"Received valid broadcast from device {device_id} at {addr[0]}")
            asyncio.ensure_future(self.discovered_callback(decoded))
        except (json.JSONDecodeError, KeyError):
            return  # Silently ignore malformed data
