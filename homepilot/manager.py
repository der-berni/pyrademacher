import asyncio
import logging
from typing import Dict

from .hub import HomePilotHub
from .sensor import HomePilotSensor
from .switch import HomePilotSwitch
from .cover import HomePilotCover
from .api import HomePilotApi

from .device import HomePilotDevice

_LOGGER = logging.getLogger(__name__)


class HomePilotManager:
    _api: HomePilotApi
    _devices: Dict[str, HomePilotDevice]

    def __init__(self, host: str, password: str) -> None:
        self._api = HomePilotApi(host, password)

    @staticmethod
    def build_manager(host: str, password: str):
        return asyncio.run(HomePilotManager.async_build_manager(host, password))

    @staticmethod
    async def async_build_manager(host: str, password: str):
        manager = HomePilotManager(host=host, password=password)
        manager.devices = {
            id_type["did"]: await HomePilotManager.async_build_device(manager.api, id_type)
            for id_type in await manager.get_device_ids_types()
            if id_type["type"] in ["-1", "1", "2", "3"]
        }
        return manager

    @staticmethod
    async def async_build_device(api, id_type):
        if id_type["type"] == "-1":
            return await HomePilotHub.async_build_from_api(api, id_type["did"])
        if id_type["type"] == "1":
            return await HomePilotSwitch.async_build_from_api(api, id_type["did"])
        if id_type["type"] == "2":
            return await HomePilotCover.async_build_from_api(api, id_type["did"])
        if id_type["type"] == "3":
            return await HomePilotSensor.async_build_from_api(api, id_type["did"])
        return None

    async def get_hub_state(self):
        return {
            "status": await self.api.async_get_fw_status(),
            "version": await self.api.async_get_fw_version(),
            "led": await self.api.async_get_led_status(),
        }

    async def update_states(self):
        try:
            states = await self.api.async_get_devices_state()
            states["-1"] = await self.get_hub_state()
        except Exception:
            for did in self.devices:
                device: HomePilotDevice = self.devices[did]
                device.available = False
            raise

        for did in self.devices:
            device: HomePilotDevice = self.devices[did]
            if device.did in states:
                device.update_state(states[did])
            else:
                device.available = False

        return self.devices

    async def get_device_ids_types(self):
        devices = await self.api.get_devices()
        devices.append(HomePilotHub.get_capabilities())
        return [HomePilotDevice.get_did_type_from_json(device) for device in devices]

    @property
    def api(self) -> HomePilotApi:
        return self._api

    @property
    def devices(self) -> Dict[str, HomePilotDevice]:
        return self._devices

    @devices.setter
    def devices(self, devices: Dict[str, HomePilotDevice]):
        self._devices = devices
