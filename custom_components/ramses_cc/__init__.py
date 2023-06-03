#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Support for Honeywell's RAMSES-II RF protocol, as used by CH/DHW & HVAC.

Requires a Honeywell HGI80 (or compatible) gateway.
"""
from __future__ import annotations

import logging
from typing import Any

import ramses_rf
import voluptuous as vol
from homeassistant.const import (
    EVENT_HOMEASSISTANT_START,
    PRECISION_TENTHS,
    Platform,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.service import verify_domain_control
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from .const import BROKER, DOMAIN
from .coordinator import RamsesCoordinator
from .schemas import (
    SCH_DOMAIN_CONFIG,
    SVC_SEND_PACKET,
    SVCS_DOMAIN,
    SZ_ADVANCED_FEATURES,
    SZ_MESSAGE_EVENTS,
)
from .version import __version__ as VERSION

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema({DOMAIN: SCH_DOMAIN_CONFIG}, extra=vol.ALLOW_EXTRA)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.WATER_HEATER,
]





import aioesphomeapi
import asyncio

import sys, importlib

def import_module_from_string(parent_name,name: str, source: str):
  """
  Import module from source string.
  Example use:
  import_module_from_string("m", "f = lambda: print('hello')")
  m.f()
  """
  parent_module = importlib.import_module(parent_name)
  spec = importlib.util.spec_from_loader(name, loader=None)
  module = importlib.util.module_from_spec(spec)
  absolute_name = importlib.util.resolve_name("."+name, parent_name)
  sys.modules[absolute_name] = module
  exec(source, module.__dict__)
  setattr(parent_module, name, module)


import_module_from_string('ramses_rf','protocol_esphomeapi',"""
class klass():
    def __init__(self, junk, *args, **kwargs):
        return
    def open(self):
        return

import logging

def serial_class_for_url(url):
    _LOGTEMP=logging.getLogger(__name__)
    _LOGTEMP.warning("serial_class_for_url called: %s",url)

    return url,klass
"""
)

#url, klass = ramses_rf.protocol_foobar.serial_class_for_url("url")


import serial
serial.protocol_handler_packages.append("ramses_rf")




from queue import Queue
#from ramses_rf.protocol.transport import POLLER_TASK
POLLER_TASK='poller_task'
class EspHomeAPITransport(asyncio.Transport):
    """Interface for a packet transport using polling."""

    MAX_BUFFER_SIZE = 500

    def __init__(self, loop, protocol, ser_instance, extra=None):
        super().__init__(extra=extra)

        self._loop = loop
        self._protocol = protocol
        self.serial = ser_instance
        self._cli=None
        self._is_closing = None
        self._write_queue = None
        self._sensors = None
        self._services = None

        _LOGGER.warning("EspHomeAPITransport init called %s",ser_instance)
        self._extra[POLLER_TASK] = self._loop.create_task(self._polling_loop())
        #self._extra[POLLER_TASK] = self._start()
        _LOGGER.warning("EspHomeAPITransport init finished %s",ser_instance)


    async def _serialwrite(self,data: str ):
        await self._cli.execute_service(self._services[0], {"send_data": data})
        #print("data sent: {}".format(data))

    async def _subscribe_state_changes(self):
        def change_callback(state):
            """Print the state changes of the device.."""
            if state.key in [t.key for t in self._sensors if "evohome" in t.name]:
                #print(state, self._sensors)
                #print(state.state)
                self._protocol.data_received(state.state.encode())

        # Subscribe to the state changes
        await self._cli.subscribe_states(change_callback)


    async def _setupesphome(self):
        assert not self._cli,"esphomeapi must be connected"
        if not self._sensors:
             entities = await self._cli.list_entities_services()
             self._sensors = entities[0]
        if not self._services:
             entities = await self._cli.list_entities_services()
             self._services = entities[1]

    async def _start(self):
        _LOGGER.warning("EspHomeAPITransport _start called")
        self._write_queue = Queue(maxsize=self.MAX_BUFFER_SIZE)
        cli = aioesphomeapi.APIClient("esphome-web-39fca8.local", 6053, None,
                                      noise_psk="MtaqewXP8Jim+YPbyFe0NhUUt8lPEg2JAb03VJp8WQ4=")
        self._cli=cli

        while not self._cli._connection:
            try: 
               await self._cli.connect(login=True)
               break
            except:
               await asyncio.sleep(1.0)

        # Get API version of the device's firmware
        _LOGGER.warning("esphomeAPI verion: %s",cli.api_version)

        # Show device details
        device_info = await cli.device_info()
        print(device_info)

        # List all entities of the device
        await self._setupesphome()

        _LOGGER.warning("esphomeAPI sensor: %s",self._sensors)
        _LOGGER.warning("esphomeAPI services: %s",self._services)

        await self._subscribe_state_changes()
        _LOGGER.warning("esphomeAPI subscribed")

        self._protocol.connection_made(self)

    async def _polling_loop(self):

        await self._start()
        _LOGGER.warning("esphomeAPI _polling_loop called _start() completed")

        while True:
            await asyncio.sleep(0.001)

            if self._cli._connection is None:
                await self._cli.connect(login=True)#TODO resubscribe??
                await self._setupesphome()
                await self._subscribe_state_changes()


            if not self._write_queue.empty():
                await self._serialwrite(self._write_queue.get())
                self._write_queue.task_done()

        self._protocol.connection_lost(exc=None)

    def write(self, cmd):
        """Write some data bytes to the transport.

        This does not block; it buffers the data and arranges for it to be sent out
        asynchronously.
        """
        #print("writing: {}".format(cmd))
        self._write_queue.put_nowait(cmd)

import ramses_rf.protocol.transport


_LOGGER.warning(
    "ramses_rf now: %s",ramses_rf.protocol.transport.SerTransportAsync
)


ramses_rf.protocol.transport.SerTransportAsync=EspHomeAPITransport
ramses_rf.protocol.transport.SerTransportPoll=EspHomeAPITransport




















_LOGGER.warning(
    "ramses_rf has been successfully patched: %s",ramses_rf.protocol.transport.SerTransportAsync
)


async def async_setup(
    hass: HomeAssistant,
    hass_config: ConfigType,
) -> bool:
    """Create a ramses_rf (RAMSES_II)-based system."""

    _LOGGER.info(f"{DOMAIN} v{VERSION}, is using ramses_rf v{ramses_rf.VERSION}")
    _LOGGER.debug("\r\n\nConfig = %s\r\n", hass_config[DOMAIN])

    broker = RamsesCoordinator(hass, hass_config)
    hass.data[DOMAIN] = {BROKER: broker}

    if _LOGGER.isEnabledFor(logging.DEBUG):  # TODO: remove
        app_storage = await broker._async_load_storage()
        _LOGGER.debug("\r\n\nStore = %s\r\n", app_storage)

    await broker.start()
    # NOTE: .async_listen_once(EVENT_HOMEASSISTANT_START, awaitable_coro)
    # NOTE: will be passed event, as: async def awaitable_coro(_event: Event):
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, broker.async_update)

    register_service_functions(hass, broker)
    register_trigger_events(hass, broker)

    return True


@callback  # TODO: add async_ to routines where required to do so
def register_trigger_events(hass: HomeAssistantType, broker):
    """Set up the handlers for the system-wide events."""

    @callback
    def process_msg(msg, *args, **kwargs):  # process_msg(msg, prev_msg=None)
        event_data = {
            "dtm": msg.dtm.isoformat(),
            "src": msg.src.id,
            "dst": msg.dst.id,
            "verb": msg.verb,
            "code": msg.code,
            "payload": msg.payload,
            "packet": str(msg._pkt),
        }
        hass.bus.async_fire(f"{DOMAIN}_message", event_data)

    if broker.config[SZ_ADVANCED_FEATURES][SZ_MESSAGE_EVENTS]:
        broker.client.create_client(process_msg)


@callback  # TODO: add async_ to routines where required to do so
def register_service_functions(hass: HomeAssistantType, broker):
    """Set up the handlers for the domain-wide services."""

    @verify_domain_control(hass, DOMAIN)
    async def svc_fake_device(call: ServiceCall) -> None:
        try:
            broker.client.fake_device(**call.data)
        except LookupError as exc:
            _LOGGER.error("%s", exc)
            return
        hass.helpers.event.async_call_later(5, broker.async_update)

    @verify_domain_control(hass, DOMAIN)
    async def svc_force_update(call: ServiceCall) -> None:
        await broker.async_update()

    @verify_domain_control(hass, DOMAIN)
    async def svc_send_packet(call: ServiceCall) -> None:
        broker.client.send_cmd(broker.client.create_cmd(**call.data))
        hass.helpers.event.async_call_later(5, broker.async_update)

    domain_service = SVCS_DOMAIN
    if not broker.config[SZ_ADVANCED_FEATURES].get(SVC_SEND_PACKET):
        del domain_service[SVC_SEND_PACKET]

    services = {k: v for k, v in locals().items() if k.startswith("svc")}
    [
        hass.services.async_register(DOMAIN, k, services[f"svc_{k}"], schema=v)
        for k, v in SVCS_DOMAIN.items()
        if f"svc_{k}" in services
    ]


class RamsesEntity(Entity):
    """Base for any RAMSES II-compatible entity (e.g. Climate, Sensor)."""

    entity_id: str = None  # type: ignore[assignment]
    # _attr_assumed_state: bool = False
    # _attr_attribution: str | None = None
    # _attr_context_recent_time: timedelta = timedelta(seconds=5)
    # _attr_device_info: DeviceInfo | None = None
    # _attr_entity_category: EntityCategory | None
    # _attr_has_entity_name: bool
    # _attr_entity_picture: str | None = None
    # _attr_entity_registry_enabled_default: bool
    # _attr_entity_registry_visible_default: bool
    # _attr_extra_state_attributes: MutableMapping[str, Any]
    # _attr_force_update: bool
    _attr_icon: str | None
    _attr_name: str | None
    _attr_should_poll: bool = True
    _attr_unique_id: str | None = None
    # _attr_unit_of_measurement: str | None

    def __init__(self, broker, device) -> None:
        """Initialize the entity."""
        self.hass = broker.hass
        self._broker = broker
        self._device = device

        self._attr_should_poll = False

        self._entity_state_attrs = ()

        # NOTE: this is bad: self.update_ha_state(delay=5)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the integration-specific state attributes."""
        attrs = {
            a: getattr(self._device, a)
            for a in self._entity_state_attrs
            if hasattr(self._device, a)
        }
        # TODO: use self._device._parent?
        # attrs["controller_id"] = self._device.ctl.id if self._device.ctl else None
        return attrs

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._broker._entities[self.unique_id] = self
        async_dispatcher_connect(self.hass, DOMAIN, self.async_handle_dispatch)

    @callback  # TODO: WIP
    def _call_client_api(self, func, *args, **kwargs) -> None:
        """Wrap client APIs to make them threadsafe."""
        # self.hass.loop.call_soon_threadsafe(
        #     func(*args, **kwargs)
        # )  # HACK: call_soon_threadsafe should not be needed

        func(*args, **kwargs)
        self.update_ha_state()

    @callback
    def async_handle_dispatch(self, *args) -> None:  # TODO: remove as unneeded?
        """Process a dispatched message.

        Data validation is not required, it will have been done upstream.
        This routine is threadsafe.
        """
        if not args:
            self.update_ha_state()

    @callback
    def update_ha_state(self, delay=3) -> None:
        """Update HA state after a short delay to allow system to quiesce.

        This routine is threadsafe.
        """
        args = (delay, self.async_schedule_update_ha_state)
        self.hass.loop.call_soon_threadsafe(
            self.hass.helpers.event.async_call_later, *args
        )  # HACK: call_soon_threadsafe should not be needed


class RamsesDeviceBase(RamsesEntity):  # for: binary_sensor & sensor
    """Base for any RAMSES II-compatible entity (e.g. BinarySensor, Sensor)."""

    def __init__(
        self,
        broker,
        device,
        state_attr,
        device_class=None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(broker, device)

        self.entity_id = f"{DOMAIN}.{device.id}-{state_attr}"

        self._attr_device_class = device_class
        self._attr_unique_id = f"{device.id}-{state_attr}"  # dont include domain (ramses_cc) / platform (binary_sesnor/sensor)

        self._state_attr = state_attr

    @property
    def available(self) -> bool:
        """Return True if the sensor is available."""
        return getattr(self._device, self._state_attr) is not None

    @property
    def name(self) -> str:
        """Return the name of the binary_sensor/sensor."""
        if not hasattr(self._device, "name") or not self._device.name:
            return f"{self._device.id} {self._state_attr}"
        return f"{self._device.name} {self._state_attr}"


class EvohomeZoneBase(RamsesEntity):  # for: climate & water_heater
    """Base for any RAMSES RF-compatible entity (e.g. Controller, DHW, Zones)."""

    _attr_precision: float = PRECISION_TENTHS
    _attr_temperature_unit: str = UnitOfTemperature.CELSIUS

    def __init__(self, broker, device) -> None:
        """Initialize the sensor."""
        super().__init__(broker, device)

        # dont include platform/domain (climate.ramses_cc)
        self._attr_unique_id = device.id

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._device.temperature

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the integration-specific state attributes."""
        return {
            **super().extra_state_attributes,
            "schema": self._device.schema,
            "params": self._device.params,
        }

    @property
    def name(self) -> str | None:
        """Return the name of the climate/water_heater entity."""
        return self._device.name
